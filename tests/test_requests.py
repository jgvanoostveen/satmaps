import unittest
from satmaps import requests
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
import socket
import datetime


class TestRequest(unittest.TestCase):
    """Test handling JSON requests"""

    def setUp(self):
        self.sane_request = {
                'sensor': ['S1'] }
        self.db = None

    def test_fail_with_wrong_dict_keys(self):
        insane_request = {"sensors": []}
        with self.assertRaises(TypeError):
            requests.Request(insane_request)

    def test_get_mongo_connection(self):
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

    def test_get_latest_request_from_db(self):
        test_request = {'sensor': ['S1'],
                          'end_date': datetime.datetime.now()}
        db = requests.get_db()
        db.insert_request()
        latest_request = db.get_last_request()
        self.assertEqual(test_request, latest_request)

    def test_getcolleciton_returns_mongodb_collection(self):
        from pymongo.collection import Collection
        collection = requests.get_local_collection()
        self.assertIsInstance(collection, Collection)


def check_not_dev_host():
    hostname = socket.gethostname()
    if 'linode' or 'vagrant' in hostname:
        return True
    else:
        return False

if __name__ == '__main__':
    unittest.main()
