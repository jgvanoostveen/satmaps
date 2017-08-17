import rasterio
import unittest
from satmaps import requests as maprequests
import pymongo
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
import socket
from mongomock import mongo_client
import rasterio

class TestRequest(unittest.TestCase):
    """Test handling JSON maprequests"""

    def setUp(self):
       # self.sane_request = {
        #         'sensor': ['S1'] }
        self.sane_request = maprequests.SANE_DICT
        self.client = mongo_client.MongoClient()
        self.db = self.client.db
        self.server_uri = self.client.address[0]
        self.server_port = self.client.address[1]

    def tearDown(self):
        self.client.close()

    def test_fail_with_wrong_dict_keys(self):
        insane_request = {"sensors": []}
        with self.assertRaises(TypeError):
            maprequests.Request(insane_request)

    def test_get_mongo_connection_remote_only(self):
        dev_machine = check_not_dev_host()
        if dev_machine:
            self.skipTest('Skipping connection test on a dev machine')
        else:
            self.db = maprequests.get_client('localhost', 27017)
            with self.assertRaises(ConnectionFailure):
                self.db.admin.command('isadmin')

    def test_non_existing_mongoconnection_fails_fast(self):
        with self.assertRaises(ServerSelectionTimeoutError):
             client = MongoClient("someInvalidURIOrNonExistantHost",
                             serverSelectionTimeoutMS=1)
             client.server_info()

    def test_get_latest_request_from_collection(self):
        import datetime
        test_request_1 = {u'sensor': ['S1'],
                        u'end_date': u'2017-01-01',
                        u'_id': datetime.datetime.utcnow()}
        test_request_2 = {u'sensor': ['S1'],
                        u'end_date': u'2017-01-01',
                        u'_id': datetime.datetime.utcnow()}
        collection = maprequests.get_local_collection(self.db)
        collection.insert(test_request_1)
        collection.insert(test_request_2)
        latest_request = maprequests.get_latest_request(collection,
                                                     check_sanity=False)
        self.assertDictEqual(test_request_2, latest_request)

    def test_check_if_cursor_is_empty(self):
        collection = maprequests.get_local_collection(self.db)
        with self.assertRaises(ValueError):
            latest_request = maprequests.get_latest_request(collection)

    @unittest.SkipTest
    def test_getcolleciton_returns_mongodb_collection(self):
        from pymongo.collection import Collection
        collection = maprequests.get_local_collection(self.db)
        self.assertIsInstance(collection, Collection)

    def test_create_gtiff_output_from_roi(self):
        roi = self.sane_request['roi']
        roi['coordinates'] = [[[[-49.26743,80.42166],[26.70664,70.01680]]]]
        crs = self.sane_request['crs']
        crs = 'EPSG:3035'
        fpath = '/tmp/o.tif'
        coords = roi['coordinates'][0]
        xres = 1500
        yres = 1500
        dtype = rasterio.uint16
        dst = maprequests.create_empty_dst(fpath,
                                           coords,
                                           xres,
                                           crs,
                                           dtype)
        self.assertTrue(dst.crs == crs)


def check_not_dev_host():
    hostname = socket.gethostname()
    if 'linode' or 'vagrant' in hostname:
        return True
    else:
        return False


if __name__ == '__main__':
    unittest.main()
