from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import os

with open("util/pool.json") as poolFile :
    poolABI = json.load(poolFile )
with open("util/ERC20.json") as erc20File:
    ERC20ABI = json.load(erc20File)

NEVM_HOST = os.environ.get('NEVM_HOST','')
NEVM_PORT = os.environ.get('NEVM_PORT','')
NEVM_HOST_TYPE = os.environ.get('NEVM_HOST_TYPE','')

if NEVM_HOST_TYPE in ['http','https']:
    provider_nevm = Web3(Web3.HTTPProvider(f'{NEVM_HOST_TYPE}://{NEVM_HOST}:{NEVM_PORT}'))
    provider_nevm.middleware_onion.inject(geth_poa_middleware, layer=0)
elif NEVM_HOST_TYPE in ['ws','wss']:
    provider_avax = Web3(Web3.WebsocketProvider(f'{NEVM_HOST_TYPE}://{NEVM_HOST}:{NEVM_PORT}'))
    provider_avax.middleware_onion.inject(geth_poa_middleware, layer=0)
with open("util/pegasys_router_abi.json", 'r') as file:
    PegasysRouterABI = json.load(file)
    
usdtContract_address = '0x922D641a426DcFFaeF11680e5358F34d97d112E1'
sysblockContract_address = '0xtbd'


def get_price_pegasys(address1, address2):
    router = w3_conn.eth.contract(address=PegasysRouterABI['contractAddress'], abi=PegasysRouterABI['abi'])
    token = w3_conn.toWei(1, 'Ether')

    price = router.functions.getAmountsOut(token, [address1, address2]).call()
    price = price[1] / (10 ** 2)
    return price



def get_price_sysblock():

    def price(reserveToken0, reserveToken1, token0Address, token1Address):

        token0 = provider_nevm.eth.contract(address=provider_nevm.toChecksumAddress(token0Address), abi=ERC20ABI)
        token1 = provider_nevm.eth.contract(address=provider_nevm.toChecksumAddress(token1Address), abi=ERC20ABI)

        token0Symbol = token0.functions.symbol().call()
        token0Decimals = token0.functions.decimals().call()

        token1Decimals = token1.functions.decimals().call()

        if token0Symbol == "WSYS":
            price_token = (reserveToken1 / 10 ** token1Decimals) / (reserveToken0 / 10 ** token0Decimals)
        else:
            price_token = (reserveToken0 / 10 ** token0Decimals) / (reserveToken1 / 10 ** token1Decimals)

        return price_token

    usdtContract = provider_nevm.eth.contract(address=provider_nevm.toChecksumAddress(usdtContract_address), abi=poolABI)
    sysblockContract = provider_avax.eth.contract(address=provider_nevm.toChecksumAddress(sysblockContract_address), abi=poolABI)

    reserves_usdt = usdtContract.functions.getReserves().call()
    reserveToken0 = reserves_usdt[0]
    reserveToken1 = reserves_usdt[1]

    token0Address = usdtContract.functions.token0().call()
    token1Address = usdtContract.functions.token1().call()

    price_usdt = price(reserveToken0, reserveToken1, token0Address, token1Address)

    reserves_sysblock = sysblockContract.functions.getReserves().call()
    reserveToken0 = reserves_sysblock[0]
    reserveToken1 = reserves_sysblock[1]

    token0Address = sysblockContract.functions.token0().call()
    token1Address = sysblockContract.functions.token1().call()

    price_sysblock = price(reserveToken0, reserveToken1, token0Address, token1Address)

    return price_usdt / price_sysblock


def get_sysblock_amount(amount):
    global sysblock_price
    global last_amount_update_time_sysblock

    try:
        if last_amount_update_time_sysblock is None or (int(time.time()) - 60) > last_amount_update_time_sysblock:
            sysblock_price = get_price_sysblock()
            last_amount_update_time_sysblock = int(time.time())
    except Exception as e:
        logging.critical('Pegasys sysblock price lookup failed with error:',exc_info=True)
        return None

    if sysblock_price is None:
        return None

    return float('{:.6f}'.format(amount / sysblock_price))


def get_sys_amount(amount):
    global sys_price
    global last_amount_update_time_sys

    try:
        if last_amount_update_time_sys is None or (int(time.time()) - 60) > last_amount_update_time_sys:
            sys_price = get_price_pegasys(WSYS,USDT)/(10**4)
            last_amount_update_time_sys = int(time.time())
    except Exception as e:
        logging.critical('Sys price lookup failed with error:', exc_info=True)
        return None

    if sys_price is None:
        return None

    return float('{:.6f}'.format(amount / sys_price))
