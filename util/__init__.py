import logging
import os
import time
import json
from web3 import Web3
from web3.middleware import geth_poa_middleware
from util.price_aablock import get_price_aablock
from util.price_sysblock import get_price_sysblock

min_payment_amount_tier1 = float(os.environ.get('PAYMENT_AMOUNT_TIER1', 35))
min_payment_amount_tier2 = float(os.environ.get('PAYMENT_AMOUNT_TIER2', 200))
discount_ablock = float((100 - int(os.environ.get('DISCOUNT_ABLOCK', 20)))/100)
discount_aablock = float((100 - int(os.environ.get('DISCOUNT_AABLOCK', 0)))/100)
discount_sysblock = float((100 - int(os.environ.get('DISCOUNT_SYSBLOCK', 10)))/100)

aBlock = Web3.toChecksumAddress('0xe692c8d72bd4ac7764090d54842a305546dd1de5')
USDT = Web3.toChecksumAddress('0xdac17f958d2ee523a2206206994597c13d831ec7')
WETH = Web3.toChecksumAddress('0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2')

last_amount_update_time_eth = None
last_amount_update_time_ablock = None
last_amount_update_time_aablock = None
last_amount_update_time_sys = None
last_amount_update_time_sysblock = None
eth_price = None
ablock_price = None
aablock_price = None
sys_price = None
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
with open("util/uniswap_router_abi.json", 'r') as file:
    UniswapRouterABI = json.load(file)


def get_price(address1, address2):
    router = w3_conn.eth.contract(address=UniswapRouterABI['contractAddress'], abi=UniswapRouterABI['abi'])
    token = w3_conn.toWei(1, 'Ether')

    price = router.functions.getAmountsOut(token, [address1, address2]).call()
    price = price[1] / (10 ** 2)
    return price


def get_eth_amount(amount):
    global eth_price
    global last_amount_update_time_eth

    try:
        if last_amount_update_time_eth is None or (int(time.time()) - 60) > last_amount_update_time_eth:
            eth_price = get_price(WETH,USDT)/(10**4)
            last_amount_update_time_eth = int(time.time())
    except Exception as e:
        logging.critical('Geth eth price lookup failed with error:', exc_info=True)
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
        logging.critical('Uniswap ablock price lookup failed with error:',exc_info=True)
        return None

    if ablock_price is None:
        return None

    return float('{:.6f}'.format(amount / ablock_price))



