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
    provider_nevm = Web3(Web3.WebsocketProvider(f'{NEVM_HOST_TYPE}://{NEVM_HOST}:{NEVM_PORT}'))
    provider_nevm.middleware_onion.inject(geth_poa_middleware, layer=0)
else:
    provider_nevm = None

with open("util/pegasys_router_abi.json", 'r') as file:
    PegasysRouterABI = json.load(file)
    
usdtContract_address = '0x0df7d92a4db09d3828a725d039b89fdc8dfc96a6' # USDT/WSYS pair
sysblockContract_address = '0x1a7400f4dfe299dbac8034bd2bb0b3b17fca9342' # Use PSYS/WSYS as proxy for sysBLOCK

def get_price_pegasys(address1, address2):
    router = provider_nevm.eth.contract(address=PegasysRouterABI['contractAddress'], abi=PegasysRouterABI['abi'])
    token = provider_nevm.toWei(1, 'Ether')

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

    if provider_nevm is None:
        return None

    usdtContract = provider_nevm.eth.contract(address=provider_nevm.toChecksumAddress(usdtContract_address), abi=poolABI)
    sysblockContract = provider_nevm.eth.contract(address=provider_nevm.toChecksumAddress(sysblockContract_address), abi=poolABI)

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
