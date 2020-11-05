import os
import time

import ccxt

min_payment_amount_tier1 = float(os.environ.get('PAYMENT_AMOUNT_TIER1', 35))
min_payment_amount_tier2 = float(os.environ.get('PAYMENT_AMOUNT_TIER2', 200))

coinbase = ccxt.coinbasepro()
last_amount_update_time = None
eth_price = None


def get_eth_amount(amount):
    global eth_price
    global last_amount_update_time

    if last_amount_update_time is None or (int(time.time()) - 60) > last_amount_update_time:
        eth_price = coinbase.fetch_ticker('ETH/USD')['close']
        last_amount_update_time = int(time.time())

    if eth_price is None:
        return None

    return float('{:.6f}'.format(amount / eth_price))
