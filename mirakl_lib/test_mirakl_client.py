import os
import unittest
from dotenv import load_dotenv
from mirakl_lib.client import MiraklClient  # Assuming MiraklClient class implementation is in mirakl_lib.client

# Load environment variables from .env file
load_dotenv()

class TestMiraklClient(unittest.TestCase):

    def setUp(self):
        # Initialize MiraklClient with environment variables
        api_url = os.getenv('MIRAKL_API_URL')
        api_key = os.getenv('MIRAKL_API_KEY')
        self.client = MiraklClient(marketplace="your_marketplace_name", base_url=api_url, api_key=api_key)

    def test_get_offers(self):
        # Call the get_all_offers method
        offers = self.client.get_all_offers()

        # Assertions
        self.assertIsInstance(offers, list)
        self.assertGreater(len(offers), 0)  # Ensure we fetched some offers

if __name__ == '__main__':
    unittest.main()

