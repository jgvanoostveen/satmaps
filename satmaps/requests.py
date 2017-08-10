# Obtain the request from json
# Obtain the latest request from the database
# Obtain the request from the email
# Return the request contents
import warnings
from pymongo import MongoClient
import pymongo

sane_dict = {
             "sensor": [],
             "end_date": [],
             "roi_box": [],
             "send_to": None,
             "history": [],
             }

class Request(dict):
    def __init__(self, request_dict):
        self.keys = request_dict.keys
        self.values = request_dict.values
        self.check_sanity()

    def check_sanity(self):
        keys = self.keys()
        for k in keys:
            try:
                k in sane_dict.keys
            except:
                raise TypeError('Key {} is not a valid parameter'.format(k))


def get_client(server_uri):
    client = MongoClient(server_uri)
    return client

def get_local_collection(client):
    collection = client.local.local
    return collection

def get_latest_request(collection):
    cursor = collection.find().sort([('_id', pymongo.DESCENDING)])
    if cursor.count() < 1:
        raise ValueError('No documents found')
    else:
        request_dict = cursor.next()
        return request_dict
