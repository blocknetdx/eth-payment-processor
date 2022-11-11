import logging
import os
import time
import json
from web3 import Web3
from web3.middleware import geth_poa_middleware
from util.price_aablock import get_price_aablock
from util.price_sysblock import get_price_pegasys, get_price_sysblock

quote_valid_hours = 1 # number of hours for which price quote given to client is valid; afterwhich, payments get half API calls
min_api_calls = 1000
ref_api_calls = 6000000
min_payment_amount_xquery = float(os.environ.get('PAYMENT_AMOUNT_XQUERY', -1))*min_api_calls/ref_api_calls
min_payment_amount_tier1 = float(os.environ.get('PAYMENT_AMOUNT_TIER1', -1))*min_api_calls/ref_api_calls
min_payment_amount_tier2 = float(os.environ.get('PAYMENT_AMOUNT_TIER2', -1))*min_api_calls/ref_api_calls
discount_ablock = float((100 - int(os.environ.get('DISCOUNT_ABLOCK', 20)))/100)
discount_aablock = float((100 - int(os.environ.get('DISCOUNT_AABLOCK', 0)))/100)
discount_sysblock = float((100 - int(os.environ.get('DISCOUNT_SYSBLOCK', 10)))/100)

aBlock = Web3.toChecksumAddress('0xe692c8d72bd4ac7764090d54842a305546dd1de5')
USDT = Web3.toChecksumAddress('0xdac17f958d2ee523a2206206994597c13d831ec7')
WETH = Web3.toChecksumAddress('0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2')
WSYS = Web3.toChecksumAddress('0xd3e822f3ef011Ca5f17D82C956D952D8d7C3A1BB')
sysUSDT = Web3.toChecksumAddress('0x922D641a426DcFFaeF11680e5358F34d97d112E1')

last_amount_update_time_eth = None
last_amount_update_time_ablock = None
last_amount_update_time_avax = None
last_amount_update_time_aablock = None
last_amount_update_time_wsys = None
last_amount_update_time_sysblock = None
eth_price = None
ablock_price = None
avax_price = None
aablock_price = None
wsys_price = None
sysblock_price = None

ETH_HOST = os.environ.get('ETH_HOST', '')
ETH_PORT = os.environ.get('ETH_PORT', '')
ETH_HOST_TYPE = os.environ.get('ETH_HOST_TYPE','')


if ETH_HOST_TYPE in ['http','https']:
    w3_conn = Web3(Web3.HTTPProvider(f'{ETH_HOST_TYPE}://{ETH_HOST}:{ETH_PORT}'))
    w3_conn.middleware_onion.inject(geth_poa_middleware, layer=0)
elif ETH_HOST_TYPE in ['ws','wss']:
    w3_conn = Web3(Web3.WebsocketProvider(f'{ETH_HOST_TYPE}://{ETH_HOST}:{ETH_PORT}'))
    w3_conn.middleware_onion.inject(geth_poa_middleware, layer=0)
else:
    w3_conn = None
with open("util/uniswap_router_abi.json", 'r') as file:
    UniswapRouterABI = json.load(file)


def get_price(address1, address2):
    if w3_conn is not None:
        router = w3_conn.eth.contract(address=UniswapRouterABI['contractAddress'], abi=UniswapRouterABI['abi'])
        token = w3_conn.toWei(1, 'Ether')

        price = router.functions.getAmountsOut(token, [address1, address2]).call()
        price = price[1] / (10 ** 2)
    else:
        price = None
    return price


def get_avax_amount(amount):
    global avax_price
    global last_amount_update_time_avax

    try:
        if last_amount_update_time_avax is None or (int(time.time()) - 60) > last_amount_update_time_avax:
            avax_price = get_price__avax_aablock(True)/(10**4)
            last_amount_update_time_avax = int(time.time())
    except Exception as e:
        logging.warning('AVAX price lookup failed with error:', exc_info=True)
        return None

    if avax_price is None:
        return None

    return float('{:.6f}'.format(amount / avax_price))

def get_eth_amount(amount):
    global eth_price
    global last_amount_update_time_eth

    try:
        if last_amount_update_time_eth is None or (int(time.time()) - 60) > last_amount_update_time_eth:
            eth_price = get_price(WETH,USDT)/(10**4)
            last_amount_update_time_eth = int(time.time())
    except Exception as e:
        logging.warning('ETH price lookup failed with error:', exc_info=True)
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
        logging.warning('Uniswap aBLOCK price lookup failed with error:',exc_info=True)
        return None

    if ablock_price is None:
        return None

    return float('{:.6f}'.format(amount / ablock_price))


def get_aablock_amount(amount):
    global aablock_price
    global last_amount_update_time_aablock

    try:
        if last_amount_update_time_aablock is None or (int(time.time()) - 60) > last_amount_update_time_aablock:
            aablock_price = get_price__avax_aablock(False)
            last_amount_update_time_aablock = int(time.time())
    except Exception as e:
        logging.warning('Pangolin aaBLOCK price lookup failed with error:', exc_info=True)
        return None

    if aablock_price is None:
        return None

    return float('{:.6f}'.format(amount / aablock_price))


def get_sysblock_amount(amount):
    global sysblock_price
    global last_amount_update_time_sysblock

    try:
        if last_amount_update_time_sysblock is None or (int(time.time()) - 60) > last_amount_update_time_sysblock:
            sysblock_price = get_price_sysblock()
            last_amount_update_time_sysblock = int(time.time())
    except Exception as e:
        logging.warning('Pegasys sysBLOCK price lookup failed with error:',exc_info=True)
        return None

    if sysblock_price is None:
        return None

    return float('{:.6f}'.format(amount / sysblock_price))


def get_wsys_amount(amount):
    global wsys_price
    global last_amount_update_time_wsys

    try:
        if last_amount_update_time_wsys is None or (int(time.time()) - 60) > last_amount_update_time_wsys:
            wsys_price = get_price_pegasys(WSYS,sysUSDT)/(10**4)
            last_amount_update_time_wsys = int(time.time())
    except Exception as e:
        logging.warning('WSYS price lookup failed with error:', exc_info=True)
        return None

    if wsys_price is None:
        return None

    return float('{:.6f}'.format(amount / wsys_price))

