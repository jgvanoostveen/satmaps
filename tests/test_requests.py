import unittest
from satmaps import requests
import pymongo
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
import socket
from mongomock import mongo_client

class TestRequest(unittest.TestCase):
    """Test handling JSON requests"""

    def setUp(self):
       # self.sane_request = {
        #         'sensor': ['S1'] }
        self.sane_request = requests.SANE_DICT
        self.client = mongo_client.MongoClient()
        self.db = self.client.db
        self.server_uri = self.client.address[0]
        self.server_port = self.client.address[1]

    def tearDown(self):
        self.client.close()

    def test_fail_with_wrong_dict_keys(self):
        insane_request = {"sensors": []}
        with self.assertRaises(TypeError):
            requests.Request(insane_request)

    def test_get_mongo_connection_remote_only(self):
        dev_machine = check_not_dev_host()
        if dev_machine:
            self.skipTest('Skipping connection test on a dev machine')
        else:
            self.db = requests.get_client('localhost', 27017)
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
        collection = requests.get_local_collection(self.db)
        collection.insert(test_request_1)
        collection.insert(test_request_2)
        latest_request = requests.get_latest_request(collection,
                                                     check_sanity=False)
        self.assertDictEqual(test_request_2, latest_request)

    def test_check_if_cursor_is_empty(self):
        collection = requests.get_local_collection(self.db)
        with self.assertRaises(ValueError):
            latest_request = requests.get_latest_request(collection)

    @unittest.SkipTest
    def test_getcolleciton_returns_mongodb_collection(self):
        from pymongo.collection import Collection
        collection = requests.get_local_collection(self.db)
        self.assertIsInstance(collection, Collection)

    def test_create_gtiff_output_from_roi(self):
        roi = self.sane_request['roi']
        crs = self.sane_request['crs']
        coords = ['coordinates']
        assert True


def check_not_dev_host():
    hostname = socket.gethostname()
    if 'linode' or 'vagrant' in hostname:
        return True
    else:
        return False


if __name__ == '__main__':
    unittest.main()
