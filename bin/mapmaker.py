#!/usr/bin/env python

from satmaps import requests
from pymongo import MongoClient
import datetime
from copy import deepcopy
from sentinelsat import SentinelAPI
from sentinelsat import geojson_to_wkt
import argparse
from zipfile import ZipFile

def process_sentinel_scene(product):
    """
    Extract the contents of the obtained file
    and put it in the right place
    """
    with ZipFile(product['identifier'] + ".zip") as zf:
        zf.extractall(".")

def update_document(request, collection):
    result = collection.find_one({"_id": request["_id"]})
    result["obtained"] = request["obtained"]
    collection.save(result)


def main():

    p = argparse.ArgumentParser()
    p.add_argument("-u", "--user")
    p.add_argument("-p", "--password")
    p.add_argument("-d", "--download", default=None)
    args = p.parse_args()

    user = args.user
    password = args.password
    client = MongoClient()
    collection = requests.get_local_collection(client)
    sane_request = deepcopy(requests.SANE_DICT)
    sane_request['_id'] = datetime.datetime.utcnow()
    # collection.insert_one(sane_request)
    request = requests.Request(requests.get_latest_request(collection))
    request['end_date'] = datetime.datetime(2018,1,1)
    print request

    api = SentinelAPI(user, password)
    footprint = geojson_to_wkt(request['roi'])

    if request['end_date'] >= datetime.datetime.utcnow():
        start_time = datetime.datetime.utcnow() - datetime.timedelta(hours=20)
        end_time = datetime.datetime.utcnow()
        products = api.query(footprint,
                             date = (start_time, end_time),
                             producttype = 'GRD',
                             sensoroperationalmode='EW')

        for item_id in products.keys():
            if item_id not in request['obtained']:
                if args.download:
                    api.download(item_id)
                    rocess_sentinel_scene(products[item_id])
                    request['obtained'].append(item_id)
                    update_document(request, collection)
            else:
                print "{} has been obtained earlier".format(item_id)


if __name__ == "__main__":
    main()
