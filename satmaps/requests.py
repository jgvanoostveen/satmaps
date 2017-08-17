import rasterio
import numpy
import warnings
from pymongo import MongoClient
import pymongo
import json
import re
import datetime
from affine import Affine
from pyproj import Proj

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
             "spatial_resolution": None,
             "time_window": None,
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


def create_empty_dst(fpath, coords_list, res, crs, dtype):
    a_pixel_width = res
    b_rotation = 0
    d_column_rotation = 0
    e_pixel_height = res

    crs = str(crs).upper()

    (x_array, y_array) = convert_coords(coords_list, crs)
    c_x_ul = x_array.min()
    f_y_ul = y_array.max()
    height = (y_array.max() - y_array.min()) / res
    width = (x_array.max() - x_array.min()) / res

    aff = Affine(a_pixel_width,
                 b_rotation,
                 c_x_ul,
                 d_column_rotation,
                 -1 * e_pixel_height,
                 f_y_ul)

    dst = rasterio.open(fpath,
                        'w',
                        driver='GTiff',
                        height=height,
                        width=width,
                        count=1,
                        dtype=dtype,
                        crs=crs,
                        transform=aff,
                        nodata=0)
    return dst


def convert_coords(coords_list, crs):
    src_proj = Proj(init='EPSG:4326')
    trg_proj = Proj(init=crs)
    xy_list = [trg_proj(c[0], c[1]) for c in coords_list[0]]
    x_array = numpy.array([c[0] for c in xy_list])
    y_array = numpy.array([c[1] for c in xy_list])

    return x_array, y_array
