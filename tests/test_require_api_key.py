import unittest
from unittest.mock import patch
from flask import Flask, jsonify, request
from api import require_api_key, err, ok
import api

class TestRequireApiKey(unittest.TestCase):
    def setUp(self):
        # Create a fresh app for each test
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True

        @self.app.route("/test_require_api_key")
        @require_api_key
        def test_route():
            return ok("success")

        self.client = self.app.test_client()
        api.API_KEY = "supersecret"

    def test_missing_api_key(self):
        response = self.client.get("/test_require_api_key")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json["error"]["code"], "unauthorized")

    def test_valid_api_key_header(self):
        response = self.client.get("/test_require_api_key", headers={"X-API-Key": "supersecret"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"], "success")

    def test_invalid_api_key_query_param(self):
        response = self.client.get("/test_require_api_key?api_key=supersecret")
        self.assertEqual(response.status_code, 401)

    def test_invalid_api_key(self):
        response = self.client.get("/test_require_api_key", headers={"X-API-Key": "wrong"})
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main()
