import unittest
from satmaps import requests

class TestRequest(unittest.TestCase):
    """Test handling JSON requests"""

    def setUp(self):
        self.sane_request = {
                'sensor': ['S1'] }

    def test_fail_with_wrong_dict_keys(self):
        insane_request = {"sensors": []}
        with self.assertRaises(TypeError):
            requests.Request(insane_request)


if __name__ == '__main__':
    unittest.main()
