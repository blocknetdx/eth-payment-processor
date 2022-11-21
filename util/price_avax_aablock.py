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
else:
    provider_avax = None
    
contract_address = {'usdt':'0x9ee0a4e21bd333a6bb2ab298194320b8daa26516','aablock':'0xfFc53c9d889B4C0bfC1ba7B9E253C615300d9fFD'}

# param avax_aablock_ == True returns usdt price of avax; avax_aablock_ == False returns usdt price of aablock
def get_price_avax_aablock(avax_aablock_):

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

    if provider_avax is None:
        return None

    price_in_wavax = {}
    for token in ['usdt', 'aablock']:
        contract = provider_avax.eth.contract(address=provider_avax.toChecksumAddress(contract_address[token]), abi=poolABI)
        reserves = contract.functions.getReserves().call()
        token0Address = contract.functions.token0().call()
        token1Address = contract.functions.token1().call()
        price_in_wavax[token] = price(reserves[0], reserves[1], token0Address, token1Address)

    return price_in_wavax['usdt'] if avax_aablock_ else price_in_wavax['usdt'] / price_in_wavax['aablock']
