#!/usr/bin/env python

from satmaps import requests

collection = requests.get_local_collection()
request = requests.get_latest_request(collection)
print request

