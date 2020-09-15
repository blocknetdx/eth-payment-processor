import os
import time
import datetime
from web3 import Web3
from database.models import commit, db_session, select, Payment


class Web3Helper:
    def __init__(self):
        self.ETH_HOST = os.environ.get('ETH_HOST', 'eth-mainnet-service.cc-dev.svc.cluster.local')
        self.ETH_PORT = os.environ.get('ETH_PORT', 8546)
        self.w3 = Web3(Web3.WebsocketProvider('ws://{}:{}'.format(self.ETH_HOST, self.ETH_PORT)))
        self.w3_accounts = Web3(Web3.WebsocketProvider('ws://{}:{}'.format(self.ETH_HOST, self.ETH_PORT)))

        self.min_payment_amount = self.w3.toWei(os.environ.get('PAYMENT_AMOUNT', 0.01), 'ether')

        self.accounts = []

    @db_session
    def start(self):
        latest = self.w3.eth.filter('latest')

        while True:
            for event in latest.get_new_entries():
                self.handle_event(event)

    @db_session
    def loop_accounts(self):
        while True:
            query = select(p for p in Payment if p.pending is True
                           and p.start_time < (datetime.datetime.now() + datetime.timedelta(hours=4)))

            query2 = query.filter(lambda payment: payment.address is not None)

            self.accounts = [payment.address for payment in query2]

            time.sleep(1)

    async def get_eth_address(self):
        try:
            return self.w3_accounts.geth.personal.new_account('')
        except Exception as e:
            print(e)

            return None

    def handle_event(self, event):
        block_hash = event.hex()
        block = self.w3.eth.getBlock(block_hash, full_transactions=True)
        transactions = block['transactions']

        for tx in transactions:
            tx_hash = tx['hash'].hex()
            to_address = tx['to']
            value = tx['value']

            if to_address in self.accounts:
                print('payment received: {} {} {}'.format(tx_hash, to_address, value))

                payment_obj = Payment.get(address=to_address)

                if value < self.min_payment_amount:
                    payment_obj.project.active = False
                else:
                    payment_obj.project.active = True

                payment_obj.pending = False
                payment_obj.amount = value
                payment_obj.tx_hash = tx_hash
                payment_obj.project.expires = datetime.datetime.now() + datetime.timedelta(days=30)

                commit()
