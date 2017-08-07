# Obtain the request from json
# Obtain the latest request from the database
# Obtain the request from the email
# Return the request contents
import warnings
from pymongo import MongoClient

sane_dict = {
             "sensor": [],
             "end_date": []
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


def get_db(hostname, db_name):
    client = MongoClient('localhost', 27017)
    db = client.local
    return db


def get_latest_request(connection):
    return request_json
