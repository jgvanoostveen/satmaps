#!/usr/bin/env python

from satmaps import requests
from pymongo import MongoClient
import datetime
from copy import deepcopy
from sentinelsat import SentinelAPI
from sentinelsat import geojson_to_wkt
import argparse
from zipfile import ZipFile
import rasterio
from rasterio import crs

def distribute_via_gmail(send_to=None,
                         attachment_path=None,
                         from_addr=None):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = send_to
    msg['Subject'] = "Maps from NPI"
    body = "Sample map"
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


def process_sentinel_scene(product):
    """
    Extract the contents of the obtained file
    and put it in the right place
    """
    with ZipFile(product['identifier'] + ".zip") as zf:
        zf.extractall(".")


def create_output_dataset(request, output_path=None):
    xres = request['resolution']
    yres = request['resolution']
    projection = request['projection']
    roi = request['roi']
    dataset = rasterio.open(output_path,
                            'w',
                            driver='GTiff',
                            height=height,
                            width=width,
                            count=1,
                            dtype=rasterio.uint8,
                            crs=crs.CRS({'init': request['crs']}))


def convert_roi_coordinates(roi):
    coordinate_pairs = roi['coordinate']
    x, y = Proj(lons)
    y = Proj(lats)

def update_document(request, collection):
    result = collection.find_one({"_id": request["_id"]})
    result["obtained"] = request["obtained"]
    collection.save(result)


def read_credentials(filepath):
    with open(filepath, 'r') as credentials:
        user = credentials.readline().rstrip('\n')
        password = credentials.readline().rstrip('\n')
        return user, password


def main():

    p = argparse.ArgumentParser()
    p.add_argument("-u", "--user")
    p.add_argument("-p", "--password")
    p.add_argument("-c", "--credentials", default=None)
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
        request = requests.load_from_file(args.input_json_file)
    elif args.from_database:
        client = MongoClient()
        collection = requests.get_local_collection(client)
        request = requests.Request(requests.get_latest_request(collection))
    else:
        raise Exception("Request should come from either database or file, got None")

    api = SentinelAPI(user, password)
    footprint = geojson_to_wkt(request['roi'])

    if request['end_date'] >= datetime.datetime.utcnow():
        start_time = datetime.datetime.utcnow() - datetime.timedelta(hours=20)
        end_time = datetime.datetime.utcnow()
        # products = api.query(footprint,
        #                      date = (start_time, end_time),
        #                      platformname=request['sensor'],
        #                      producttype = 'GRD',
        #                      sensoroperationalmode='EW')

        # for item_id in products.keys():
        #     if item_id not in request['obtained']:
        #         if args.download:
        #             # api.download(item_id)
        #             # process_sentinel_scene(products[item_id])
        #             # request['obtained'].append(item_id)
        #             # update_document(request, collection)
        #     else:
        #         print "{} has been obtained earlier".format(item_id)
        distribute_via_gmail(send_to = request['send_to'],
                             from_addr='npi.cruise.data@gmail.com',
                             attachment_path='../tmp/iskart_2017-05-15.jpg')


if __name__ == "__main__":
    main()
