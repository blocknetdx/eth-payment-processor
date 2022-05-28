from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import os

with open("util/pool.json") as poolFile :
    poolABI = json.load(poolFile )
with open("util/ERC20.json") as erc20File:
    ERC20ABI = json.load(erc20File)

AVAX_HOST = os.environ.get('AVAX_HOST','')
AVAX_PORT = os.environ.get('AVAX_PORT','')
AVAX_HOST_TYPE = os.environ.get('AVAX_HOST_TYPE','')

if AVAX_HOST_TYPE in ['http','https']:
    provider_avax = Web3(Web3.HTTPProvider(f'{AVAX_HOST_TYPE}://{AVAX_HOST}:{AVAX_PORT}/ext/bc/C/rpc'))
    provider_avax.middleware_onion.inject(geth_poa_middleware, layer=0)
elif AVAX_HOST_TYPE in ['ws','wss']:
    provider_avax = Web3(Web3.WebsocketProvider(f'{AVAX_HOST_TYPE}://{AVAX_HOST}:{AVAX_PORT}/ext/bc/C/rpc'))
    provider_avax.middleware_onion.inject(geth_poa_middleware, layer=0)
    
usdtContract_address = '0x9ee0a4e21bd333a6bb2ab298194320b8daa26516'
aablockContract_address = '0xfFc53c9d889B4C0bfC1ba7B9E253C615300d9fFD'


def get_price_aablock():

    def price(reserveToken0, reserveToken1, token0Address, token1Address):

        token0 = provider_avax.eth.contract(address=provider_avax.toChecksumAddress(token0Address), abi=ERC20ABI)
        token1 = provider_avax.eth.contract(address=provider_avax.toChecksumAddress(token1Address), abi=ERC20ABI)

        token0Symbol = token0.functions.symbol().call()
        token0Decimals = token0.functions.decimals().call()

        token1Decimals = token1.functions.decimals().call()

        if token0Symbol == "WAVAX":
            price_token = (reserveToken1 / 10 ** token1Decimals) / (reserveToken0 / 10 ** token0Decimals)
        else:
            price_token = (reserveToken0 / 10 ** token0Decimals) / (reserveToken1 / 10 ** token1Decimals)

        return price_token

    usdtContract = provider_avax.eth.contract(address=provider_avax.toChecksumAddress(usdtContract_address), abi=poolABI)
    aablockContract = provider_avax.eth.contract(address=provider_avax.toChecksumAddress(aablockContract_address), abi=poolABI)


    reserves_usdt = usdtContract.functions.getReserves().call()
    reserveToken0 = reserves_usdt[0]
    reserveToken1 = reserves_usdt[1]

    token0Address = usdtContract.functions.token0().call()
    token1Address = usdtContract.functions.token1().call()

    price_usdt = price(reserveToken0, reserveToken1, token0Address, token1Address)

    reserves_aablock = aablockContract.functions.getReserves().call()
    reserveToken0 = reserves_aablock[0]
    reserveToken1 = reserves_aablock[1]

    token0Address = aablockContract.functions.token0().call()
    token1Address = aablockContract.functions.token1().call()

    price_aablock = price(reserveToken0, reserveToken1, token0Address, token1Address)

    return price_usdt / price_aablock


def get_aablock_amount(amount):
    global aablock_price
    global last_amount_update_time_aablock

    try:
        if last_amount_update_time_aablock is None or (int(time.time()) - 60) > last_amount_update_time_aablock:
            aablock_price = get_price_aablock()
            last_amount_update_time_aablock = int(time.time())
    except Exception as e:
        logging.critical('Pangolin aablock price lookup failed with error:', exc_info=True)
        return None

    if aablock_price is None:
        return None

    return float('{:.6f}'.format(amount / aablock_price))
