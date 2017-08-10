#!/usr/bin/env python

from satmaps import requests
from pymongo import MongoClient
client = MongoClient()
collection = requests.get_local_collection(client)
request = requests.get_latest_request(collection)
