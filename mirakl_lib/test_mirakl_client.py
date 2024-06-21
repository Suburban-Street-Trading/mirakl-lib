import os
import unittest
from dotenv import load_dotenv
from mirakl_lib.client import MiraklClient, GetWaitingOrdersResult  

# Load environment variables from .env file
load_dotenv()

class TestMiraklClient(unittest.TestCase):

    def setUp(self):
        # Initialize MiraklClient with environment variables
        api_url = os.getenv('MIRAKL_API_URL')
        api_key = os.getenv('MIRAKL_API_KEY')
        if not api_url or not api_key:
            self.fail("API URL and API Key must be set in the environment variables.")
        self.client = MiraklClient(marketplace="your_marketplace_name", base_url=api_url, api_key=api_key)

    def test_get_offers(self):
        # Call the get_all_offers method
        offers = self.client.get_all_offers()

        # Assertions
        self.assertIsInstance(offers, list, "Offers should be a list")
        self.assertGreater(len(offers), 0, "Offers list should not be empty")

    def test_get_orders(self):
        offset = 0
        size = 10
        status = "WAITING_ACCEPTANCE"  
        
        # Call the get_orders method
        result = self.client.get_orders(offset=offset, size=size, status=status)
        
        # Assertions
        self.assertIsInstance(result, GetWaitingOrdersResult, "Result should be of type GetWaitingOrdersResult")
        self.assertIsInstance(result.orders, list, "Orders should be a list")
        self.assertGreater(len(result.orders), 0, "Orders list should not be empty")
        self.assertIsInstance(result.has_more, bool, "has_more should be a boolean")
        self.assertIsInstance(result.next_order_start_offset, int, "next_order_start_offset should be an integer")

        # Additional checks for order details 
        for order in result.orders:
            self.assertIsInstance(order.order_id, str, "Order ID should be a string")
            self.assertIsInstance(order.order_state, str, "Order state should be a string")
            self.assertIsInstance(order.customer, dict, "Customer should be a dictionary")
            self.assertIsInstance(order.order_lines, list, "Order lines should be a list")
            self.assertGreater(len(order.order_lines), 0, "Order lines should not be empty")
            
            for line in order.order_lines:
                self.assertIsInstance(line.order_line_id, str, "Order line ID should be a string")
                self.assertIsInstance(line.price, float, "Order line price should be a float")

if __name__ == '__main__':
    unittest.main()
