# Obtain the request from json
# Obtain the latest request from the database
# Obtain the request from the email
# Return the request contents
import warnings
from pymongo import MongoClient
import pymongo

sane_dict = {
             "_id": None,
             "sensor": [],
             "end_date": [],
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
             "history": [],
             }

class Request(dict):
    def __init__(self, request_dict, check_sanity=True):
        super(Request, self).__init__()
        self.update({x: request_dict[x] for x in request_dict.keys()})
        if check_sanity:
            self.check_sanity()

    def check_sanity(self):
        required_keys = sane_dict.keys()
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
