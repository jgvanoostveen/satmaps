#!/usr/bin/env python

import argparse
import datetime
import glob
import os
import subprocess
from zipfile import ZipFile
import multiprocessing
from functools import partial

import rasterio
from pymongo import MongoClient
from sentinelsat import SentinelAPI, geojson_to_wkt

from satmaps import requests as maprequests


def make_email_body(attachment_path=None):
    body = ""
    body.join("Satellite imagery from: {}.\n")
    if attachment_path:
        attachment_size = os.path.getsize(attachment_path)
        attachment_size_mb = "{} MB".format(attachment_size / 1000000.)
        body = body.join("Attachment size {}\n".format(attachment_size_mb))
    else:
        body.join("This message has no attachment.\n")
    return body


def distribute_via_gmail(send_to=None,
                         attachment_path=None,
                         from_addr=None,
                         subject=""
                        ):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = ", ".join(send_to)
    msg['Subject'] = "Automatic Fram Strait Satellite Observations"

    body = make_email_body(attachment_path=attachment_path)

    msg.attach(MIMEText(body, 'plain'))
    attachment = open(attachment_path, "rb")
    p = MIMEBase('application', 'octet-stream')
    p.set_payload((attachment).read())
    encoders.encode_base64(p)
    p.add_header('Content-Disposition', "attachment; filename= %s" % attachment_path)
    msg.attach(p)
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login("foo", "bar")
    text = msg.as_string()
    s.sendmail(from_addr, send_to, text)
    s.quit()


def process_sentinel_scene(product, output_filepath):
    """
    Extract the contents of the obtained file
    and put it in the right place
    """
    with ZipFile(".".join([product['identifier'], "zip"])) as zf:
        zf.extractall(".")
        input_filepath = glob.glob(".".join([product['identifier'], "SAFE/measurement/*hh*.tiff"]))[0]
        subprocess.call([
            "gdalwarp",
            "-t_srs",
            "EPSG:3035",
            "-r",
            "bilinear",
            input_filepath,
            output_filepath
        ])


def zip_tif_to_jpeg(input_filepath):
    basename, ext  = os.path.splitext(input_filepath)
    jpeg_filepath  = ".".join([basename, "jpeg"])
    world_filepath = ".".join([basename, "wld"])
    zip_filepath   = ".".join([basename, "archive"])
    subprocess.call([
        "gdal_translate",
        "-scale",
        "-ot",
        "Byte",
        "-of",
        "JPEG",
        "-co",
        "WORLDFILE=YES",
        "-co",
        "QUALITY=85",
        input_filepath,
        jpeg_filepath
    ])
    with ZipFile(zip_filepath, 'w') as zipball:
        for f in [jpeg_filepath, world_filepath]:
            zipball.write(f)

    return zip_filepath


def update_document(request, collection):
    result = collection.find_one({"_id": request["_id"]})
    result["obtained"] = request["obtained"]
    collection.save(result)


def read_credentials(filepath):
    with open(filepath, 'r') as credentials:
        user = credentials.readline().rstrip('\n')
        password = credentials.readline().rstrip('\n')
        return user, password


def make_output_filepath(dir_path):
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    fname = 'S1_{}.tif'.format(timestamp)
    fpath = os.path.join(dir_path, fname)
    return fpath

def process_sentinel_product(
                        product_key,
                        products,
                        api,
                        request,
                        output_path
                    ):

    print("Obtaining item {}".format(product_key))
    if product_key not in request['obtained']:
        api.download(product_key)
        process_sentinel_scene(products[product_key], output_path)
        request['obtained'].append(product_key)
    else:
        print "{} has been obtained earlier".format(product_key)

def main():

    p = argparse.ArgumentParser()
    p.add_argument("-u", "--user")
    p.add_argument("-p", "--password")
    p.add_argument("-c", "--credentials", default=None)
    p.add_argument("-s", "--send", default=None)
    p.add_argument("-d", "--download", default=None)
    p.add_argument("-e", "--end-date", default=datetime.datetime(2018,1,1))
    p.add_argument("-i", "--input-json-file", default=None)
    p.add_argument("-b", "--from-database", action="store_true")
    p.add_argument("-n", "--insert-into-database", default=False)
    args = p.parse_args()

    if args.credentials is not None:
        (user, password) = read_credentials(args.credentials)
    else:
        user = args.user
        password = args.password

    if all((args.input_json_file, args.from_database)):
        raise Exception("Request should come from either database or file, not both, quiting")
        # TODO: print messages through logger

    elif args.input_json_file:
        request = maprequests.load_from_file(args.input_json_file)
    elif args.from_database:
        client = MongoClient()
        collection = maprequests.get_local_collection(client)
        request = maprequests.Request(maprequests.get_latest_request(collection))
    else:
        raise Exception("Request should come from either database or file, got None")

    api_url = 'https://colhub.met.no/'
    api = SentinelAPI(user, password, api_url=api_url, show_progressbars=True)
    footprint = geojson_to_wkt(request['roi'])

    if request['end_date'] >= datetime.datetime.utcnow():

        output_path = make_output_filepath(args.download)
        maprequests.create_empty_dst(
            output_path,
            request['roi']['coordinates'],
            request['spatial_resolution'],
            request['crs'],
            rasterio.uint16
        )

        start_time = datetime.datetime.utcnow() - datetime.timedelta(hours=request['time_window'])
        end_time = datetime.datetime.utcnow()

        products = api.query(
            footprint,
            date = (start_time, end_time),
            platformname=request['sensor'],
            producttype = 'GRD',
            sensoroperationalmode='EW'
        )

        print("Found {} scenes".format(len(products.keys())))
        if (len(products.keys()) < 1):
            raise ValueError('No scenes found, exiting.')

        pool = multiprocessing.Pool(processes=1)
        output = pool.map(partial(process_sentinel_product,
                                  products=products,
                                  api=api,
                                  output_path=output_path,
                                  request=request), products.keys())

        zip_filepath = zip_tif_to_jpeg(output_path)

        distribute_via_gmail(send_to = request['send_to'],
                                 attachment_path=zip_filepath)


if __name__ == "__main__":
    main()
