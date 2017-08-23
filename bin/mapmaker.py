#!/usr/bin/env python

import argparse
import datetime
import glob
import os
import subprocess
from zipfile import ZipFile
import multiprocessing
from functools import partial
import yaml
import logging
import io
import time
import shutil


import rasterio
from pymongo import MongoClient
from sentinelsat import SentinelAPI, geojson_to_wkt

from satmaps import requests as maprequests


def distribute_via_gmail(mail_user=None,
                         mail_pass=None,
                         send_to=None,
                         attachment_path=None,
                         message_text=None,
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

    body = message_text
    msg.attach(MIMEText(body, 'plain'))

    if attachment_path:
        attachment = open(attachment_path, "rb")
        p = MIMEBase('application', 'octet-stream')
        p.set_payload((attachment).read())
        encoders.encode_base64(p)
        p.add_header('Content-Disposition', "attachment; filename= %s" % attachment_path)
        msg.attach(p)

    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(mail_user, mail_pass)
    text = msg.as_string()
    s.sendmail(from_addr, send_to, text)
    s.quit()


def process_sentinel_scene(product, data_dir, output_filepath):
    """
    Extract the contents of the obtained file
    and put it in the right place
    """
    with ZipFile(os.path.join(data_dir, ".".join([product['identifier'], "zip"]))) as zf:
        zf.extractall(data_dir)
        input_filepath = glob.glob(os.path.join(data_dir, ".".join([product['identifier'],"SAFE/measurement/*hh*.tiff"])))[0]
        subprocess.call([
            "gdalwarp",
            "-t_srs",
            "EPSG:3035",
            "-srcnodata",
            "0",
            "-dstnodata",
            "0",
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
            zipball.write(f, os.path.basename(f))

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
    name = 'S1_{}'.format(timestamp)
    fname = '.'.join((name, 'tif'))
    odirpath = os.path.join(dir_path, name)
    fpath = os.path.join(odirpath, fname)
    try:
        os.mkdir(odirpath)
    except:
        raise
    return fpath


def download_sentinel_product(
                        product_key,
                        products,
                        api,
                        request,
                        output_path
                    ):

    print("Obtaining item {}".format(product_key))
    if product_key not in request['obtained']:
        api.download(product_key, directory_path=output_path)
    else:
        print "{} has been obtained earlier".format(product_key)


def empty_dir(path):
    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))


def main():

    p = argparse.ArgumentParser()
    p.add_argument("-c", "--credentials", default=None)
    p.add_argument("-s", "--send", action="store_true")
    p.add_argument("-u", "--cleanup", action="store_true")
    p.add_argument("-d", "--download", default=None)
    p.add_argument("-e", "--end-date", default=datetime.datetime(2018,1,1))
    p.add_argument("-i", "--input-json-file", default=None)
    p.add_argument("-b", "--from-database", action="store_true")
    p.add_argument("-n", "--insert-into-database", default=False)
    args = p.parse_args()

    if args.credentials is not None:
        with open(args.credentials, 'r') as crd:
            credentials_dict = yaml.load(crd)
            MAIL_USER = credentials_dict['mail_user']
            MAIL_PASS = credentials_dict['mail_password']
            SHUB_USER = credentials_dict['shub_user']
            SHUB_PASS = credentials_dict['shub_password']

    zip_filepath = None

    logger = logging.getLogger('mapmaker')
    logger.setLevel(logging.DEBUG)
    log_capture_string = io.BytesIO()
    ch = logging.StreamHandler(log_capture_string)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s  %(name)s  %(levelname)s: %(message)s')
    logging.Formatter.converter = time.gmtime
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if os.path.exists(args.download):
        logger.debug('Emptying directory {}'.format(args.download))
        try:
            empty_dir(args.download)
        except:
            raise

    if args.download and not os.path.exists(args.download):
        try:
            os.mkdir(args.download)
        except:
            error_msg = 'Could not make a directory for downloads.'
            logger.error(error_msg)
            raise

    if all((args.input_json_file, args.from_database)):
        raise Exception("Request should come from either database or file, not both, quiting")

    elif args.input_json_file:
        request = maprequests.load_from_file(args.input_json_file)
    elif args.from_database:
        client = MongoClient()
        collection = maprequests.get_local_collection(client)
        request = maprequests.Request(maprequests.get_latest_request(collection))
    else:
        raise Exception("Request should come from either database or file, got None")

    api_url = 'https://colhub.met.no/'
    api = SentinelAPI(SHUB_USER, SHUB_PASS, api_url=api_url, show_progressbars=True)
    footprint = geojson_to_wkt(request['roi'])

    if request['end_date'] >= datetime.datetime.utcnow():

        start_time = datetime.datetime.utcnow() - datetime.timedelta(hours=request['time_window'])
        end_time = datetime.datetime.utcnow()

        products = api.query(
            footprint,
            date = (start_time, end_time),
            platformname=request['sensor'],
            producttype = 'GRD',
            sensoroperationalmode='EW'
        )

        logger.info("Found {} scenes".format(len(products.keys())))
        logger.info("Scenes list:\n{}".format("\n".join(['\t'+products[key]['identifier'] for key in products.keys()])))

        if len(products.keys()) >= 1:

            output_path = make_output_filepath(args.download)
            maprequests.create_empty_dst(
                output_path,
                request['roi']['coordinates'],
                request['spatial_resolution'],
                request['crs'],
                rasterio.uint16
            )

            data_dir = os.path.dirname(output_path)

            pool = multiprocessing.Pool(processes=1)
            output = pool.map(partial(download_sentinel_product,
                                      products=products,
                                      api=api,
                                      output_path=data_dir,
                                      request=request), products.keys())

            for product_key in products.keys():
                process_sentinel_scene(products[product_key], data_dir, output_path)

            zip_filepath = zip_tif_to_jpeg(output_path)
            attachment_size = os.path.getsize(zip_filepath)
            attachment_size_mb = "{} MB".format(attachment_size / 1000000.)
            logger.info('Attachment size is {}'.format(attachment_size_mb))

        else:
            logger.warn('Not enough scenes found, aborting')

        log_contents = log_capture_string.getvalue()
        log_capture_string.close()

        if args.send:
            distribute_via_gmail(mail_user=MAIL_USER,
                     mail_pass=MAIL_PASS,
                     send_to = request['send_to'],
                     attachment_path=zip_filepath,
                     message_text=log_contents)


if __name__ == "__main__":
    main()
