import os
import asyncio
from web3 import Web3


class Web3Helper:
    def __init__(self):
        # self.ETH_HOST = os.environ.get('ETH_HOST', '127.0.0.1')
        # self.ETH_PORT = os.environ.get('ETH_PORT', 8546)
        self.w3 = Web3(Web3.WebsocketProvider('wss://mainnet.infura.io/ws/v3/fff43894c8fc487abd57e215cd38c1a6'))

        self.accounts = []

    async def start(self):
        latest = self.w3.eth.filter('latest')

        while True:
            for event in latest.get_new_entries():
                await self.handle_event(event)

    async def loop_accounts(self):
        while True:
            self.accounts = self.w3.geth.personal.list_accounts()

            await asyncio.sleep(1)

    async def get_eth_address(self):
        try:
            return self.w3.geth.personal.new_account()
        except Exception as e:
            print(e)

            return None

    async def handle_event(self, event):
        print('===== Block hash:  ', event.hex())
        block_hash = event.hex()
        block = self.w3.eth.getBlock(block_hash, full_transactions=True)
        transactions = block['transactions']
        print('===== Block Number: ', block['number'])
        for tx in transactions:
            print('   TX Hash: ', tx['hash'])
            print('   To wallet: ', tx['to'])
            print('   Value ETH: ', tx['value'])
