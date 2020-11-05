import unittest

from util import get_eth_amount, min_payment_amount_tier1, min_payment_amount_tier2


class MainTests(unittest.TestCase):
    def test_cctx_coinbase_tier1(self):
        result = get_eth_amount(min_payment_amount_tier1)
        self.assertEqual(isinstance(result, float), True, 'expecting tier1 result to be a float')
        self.assertGreater(result, 0, 'expecting tier1 eth amount to be > 0')

    def test_cctx_coinbase_tier2(self):
        result = get_eth_amount(min_payment_amount_tier2)
        self.assertEqual(isinstance(result, float), True, 'expecting tier2 result to be a float')
        self.assertGreater(result, 0, 'expecting tier2 eth amount to be > 0')


if __name__ == '__main__':
    unittest.main()
