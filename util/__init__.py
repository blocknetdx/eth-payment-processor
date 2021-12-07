import logging
import os
import time
import ccxt
import json
from web3 import Web3

min_payment_amount_tier1 = float(os.environ.get('PAYMENT_AMOUNT_TIER1', 35))
min_payment_amount_tier2 = float(os.environ.get('PAYMENT_AMOUNT_TIER2', 200))
discount = float((100 - os.environ.get('DISCOUNT', 20))/100)

aBlock = Web3.toChecksumAddress('0xe692c8d72bd4ac7764090d54842a305546dd1de5')
USDT = Web3.toChecksumAddress('0xdac17f958d2ee523a2206206994597c13d831ec7')

coinbase = ccxt.coinbasepro()
last_amount_update_time_eth = None
last_amount_update_time_ablock = None
eth_price = None
ablock_price = None

ETH_HOST = os.environ.get('ETH_HOST', 'localhost')
ETH_PORT = os.environ.get('ETH_PORT', 8546)
w3 = Web3(Web3.WebsocketProvider('ws://{}:{}'.format(ETH_HOST, ETH_PORT)))


with open("util/uniswap_router_abi.json", 'r') as file:
    UniswapRouterABI = json.load(file)


def get_price(address1, address2):
    router = w3.eth.contract(address=UniswapRouterABI['contractAddress'], abi=UniswapRouterABI['abi'])
    token = w3.toWei(1, 'Ether')

    price = router.functions.getAmountsOut(token, [address1, address2]).call()
    price = price[1] / (10 ** 2)
    return price


def get_eth_amount(amount):
    global eth_price
    global last_amount_update_time_eth

    try:
        if last_amount_update_time_eth is None or (int(time.time()) - 60) > last_amount_update_time_eth:
            eth_price = coinbase.fetch_ticker('ETH/USD')['close']

            last_amount_update_time_eth = int(time.time())
    except Exception as e:
        logging.info('coinbase eth price lookup failed with error: {}'.format(e))
        return None

    if eth_price is None:
        return None

    return float('{:.6f}'.format(amount / eth_price))


def get_ablock_amount(amount):
    global ablock_price
    global last_amount_update_time_ablock

    try:
        if last_amount_update_time_ablock is None or (int(time.time()) - 60) > last_amount_update_time_ablock:
            ablock_price = get_price(aBlock, USDT)
            last_amount_update_time_ablock = int(time.time())
    except Exception as e:
        logging.info('Uniswap ablock price lookup failed with error: {}'.format(e))
        return None

    if ablock_price is None:
        return None

    return float('{:.6f}'.format(amount / ablock_price))

