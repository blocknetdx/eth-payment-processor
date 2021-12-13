from web3 import Web3
import json

with open("util/pool.json") as poolFile :
    poolABI = json.load(poolFile )
with open("util/ERC20.json") as erc20File:
    ERC20ABI = json.load(erc20File)

AVAX_HOST = os.environ.get('AVAX_HOST','')
AVAX_PORT = os.environ.get('AVAX_PORT','')
AVAX_HOST_TYPE = os.environ.get('AVAX_HOST_TYPE','http')

if AVAX_HOST_TYPE == 'http':
    provider_avax = Web3(Web3.HTTPProvider(f'https://{AVAX_HOST}:{AVAX_PORT}/ext/bc/C/rpc'))
elif AVAX_HOST_TYPE == 'ws':
    provider_avax = Web3(Web3.WebsocketProvider(f'ws://{AVAX_HOST}:{AVAX_PORT}/ext/bc/C/rpc'))

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

    price_ablock = price(reserveToken0, reserveToken1, token0Address, token1Address)

    return price_usdt / price_ablock
