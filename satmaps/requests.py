import warnings
from pymongo import MongoClient
import pymongo
import json
import re
import datetime

SANE_DICT = {
             "_id": None,
             "sensor": None,
             "start_date": None,
             "end_date": None,
             "roi": {
                      'coordinates':
                        [[[-2.21, 82.84],
                          [14.14, 83.13],
                          [13.26, 73.37],
                          [-3.9, 74.25],
                          [-2.21, 82.84]]],
                       'type': 'Polygon'
                       },
             "send_to": None,
             "history": None,
             "spatial_scale": None,
             "crs": None,
             "obtained": [],
             "processed": []
             }

class Request(dict):
    def __init__(self, request_dict, check_sanity=True):
        super(Request, self).__init__()
        self.update({x: request_dict[x] for x in request_dict.keys()})
        if check_sanity:
            self.check_sanity()

    def check_sanity(self):
        required_keys = SANE_DICT.keys()
        if not all(k in self.keys() for k in required_keys):
            raise TypeError('Received an invalid set of parameters, exiting')

def get_client(server_uri):
    client = MongoClient(server_uri)
    return client

def get_local_collection(client):
    collection = client.local.local
    return collection

def get_latest_request(collection, check_sanity=True):
    cursor = collection.find().sort([('_id', pymongo.DESCENDING)])
    if cursor.count() < 1:
        raise ValueError('No documents found')
    else:
        request_dict = cursor.next()
        return Request(request_dict, check_sanity=check_sanity)

def load_from_file(filepath):
    with open(filepath, mode='r') as filehandle:
        json_dict = json.load(filehandle, object_hook=parse_datetime)
        request = Request(json_dict)
    return request

def parse_datetime(dct, date_format=None):
    if date_format is None:
        date_format = "%Y-%m-%dT%H:%M:%S UTC"
    for k, v in dct.items():
        if isinstance(v, basestring) and re.search("\ UTC", v):
            try:
                dct[k] = datetime.datetime.strptime(v, date_format)
            except:
                raise ValueError("Not sure if the date is UTC, exiting")
    return dct
