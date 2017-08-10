#!/usr/bin/env python

from satmaps import requests
from pymongo import MongoClient
import datetime
from copy import deepcopy

client = MongoClient()
collection = requests.get_local_collection(client)

sane_request = deepcopy(requests.sane_dict)
sane_request['_id'] = datetime.datetime.utcnow()

collection.insert_one(sane_request)
request = requests.Request(requests.get_latest_request(collection))
