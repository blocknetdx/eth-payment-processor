import os
import asyncio
import datetime
from web3 import Web3
from database.models import commit, db_session, select, Payment


class Web3Helper:
    def __init__(self):
        # self.ETH_HOST = os.environ.get('ETH_HOST', '127.0.0.1')
        # self.ETH_PORT = os.environ.get('ETH_PORT', 8546)
        self.w3 = Web3(Web3.WebsocketProvider('wss://mainnet.infura.io/ws/v3/fff43894c8fc487abd57e215cd38c1a6'))

        self.accounts = []

    @db_session
    async def start(self):
        latest = self.w3.eth.filter('latest')

        while True:
            for event in latest.get_new_entries():
                await self.handle_event(event)

    async def loop_accounts(self):
        while True:
            query = select(p for p in Payment if p.pending is True
                           and p.start_time < (datetime.datetime.now() + datetime.timedelta(hours=4)))

            self.accounts = [address for address in query.address]

            await asyncio.sleep(1)

    async def get_eth_address(self):
        try:
            return self.w3.geth.personal.new_account()
        except Exception as e:
            print(e)

            return None

    async def handle_event(self, event):
        block_hash = event.hex()
        block = self.w3.eth.getBlock(block_hash, full_transactions=True)
        transactions = block['transactions']
        print('===== Block Number: ', block['number'])
        for tx in transactions:
            tx_hash = tx['hash']
            to_address = tx['to']
            value = tx['value']
            print('   TX Hash: ', tx_hash)
            print('   To wallet: ', to_address)
            print('   Value ETH: ', value)

            if tx['to'] in self.accounts:
                payment_obj = Payment.get(address=to_address)
                payment_obj.pending = False
                payment_obj.amount = value
                payment_obj.tx_hash = tx_hash
                payment_obj.project.expires = datetime.datetime.now() + datetime.timedelta(days=30)
                payment_obj.project.active = True

                commit()
