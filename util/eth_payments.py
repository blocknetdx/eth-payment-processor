import os
import time
import datetime
from web3 import Web3
from database.models import commit, db_session, select, Payment
from util import get_eth_amount, min_payment_amount_tier1, min_payment_amount_tier2

default_api_calls_count = 6000000


def calc_api_calls_tiers(payment_amount_wei, tier1_eth_amount, tier2_eth_amount,
                         archival_mode: bool, def_api_calls_count: int) -> int:
    """Calculates the number of api calls for the specified archival mode and tier
    amounts. The [default api call count] * [price multiplier] determines total paid
    api calls. [price multiplier] = [user payment in eth] / [tier required payment in eth]"""
    tier_expected_amount = tier1_eth_amount if not archival_mode else tier2_eth_amount
    multiplier = float(Web3.fromWei(payment_amount_wei, 'ether')) / float(tier_expected_amount)
    api_calls = int(float(def_api_calls_count) * multiplier)
    return api_calls


def calc_api_calls(payment_amount_wei, archival_mode: bool, def_api_calls_count: int) -> int:
    tier1_eth_amount = get_eth_amount(min_payment_amount_tier1)
    tier2_eth_amount = get_eth_amount(min_payment_amount_tier2)
    return calc_api_calls_tiers(payment_amount_wei, tier1_eth_amount, tier2_eth_amount, archival_mode,
                                def_api_calls_count)


class Web3Helper:
    def __init__(self):
        self.ETH_HOST = os.environ.get('ETH_HOST', 'localhost')
        self.ETH_PORT = os.environ.get('ETH_PORT', 8546)
        self.w3 = Web3(Web3.WebsocketProvider('ws://{}:{}'.format(self.ETH_HOST, self.ETH_PORT)))
        self.w3_accounts = Web3(Web3.WebsocketProvider('ws://{}:{}'.format(self.ETH_HOST, self.ETH_PORT)))

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
            query = select(p for p in Payment if p.start_time is not None)

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
        print('processing eth block {}'.format(block_hash))
        block = self.w3.eth.getBlock(block_hash, full_transactions=True)
        transactions = block['transactions']

        for tx in transactions:
            tx_hash = tx['hash'].hex()
            to_address = tx['to']
            value = tx['value']
            if value <= 0:
                continue

            if to_address in self.accounts:
                print('payment received: {} {} {}'.format(tx_hash, to_address, value))

                payment_obj = Payment.get(address=to_address)

                # Supporting partial payments and handling expired payments:
                # If initial price for default 6M calls is not expired use that to calculate number of calls
                # from partial payments. If the initial price has expired, use the current price of eth to
                # determine how many calls the user receives. First time partial payments default to non-archival
                # api access. In order for users to obtain archival access their first payment must be greater
                # than or equal to the minimum payment amount for archival access.
                #
                # Make sure db supports large enough integer to track used_api_tokens (i.e. int64)

                # If the project has never been activated (payment is pending) allow the user to set the archival mode.
                # Activated projects cannot change the archival state.
                if payment_obj.pending:
                    # Check if initial payment offering has expired
                    if datetime.datetime.now() >= payment_obj.start_time + datetime.timedelta(hours=3, minutes=30):
                        # Expired time requires obtaining new payment tier calcs
                        tier2_expected_amount = get_eth_amount(min_payment_amount_tier2)
                        payment_obj.project.archive_mode = value >= tier2_expected_amount
                        # Note set the api calls here since first time payment (do not append)
                        payment_obj.project.api_token_count = calc_api_calls(value, payment_obj.project.archive_mode,
                                                                             default_api_calls_count)
                    else:
                        # Non-expired payment calcs should use the db payment tiers
                        payment_obj.project.archive_mode = value >= payment_obj.tier2_expected_amount
                        # Note set the api calls here since first time payment (do not append)
                        payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                   payment_obj.project.archive_mode,
                                                                                   default_api_calls_count,
                                                                                   payment_obj.tier1_expected_amount,
                                                                                   payment_obj.tier2_expected_amount)
                else:
                    # Append api calls because this is a top-up payment (first payment already received)
                    payment_obj.project.api_token_count += calc_api_calls(value, payment_obj.project.archive_mode,
                                                                          default_api_calls_count)

                payment_obj.project.active = True
                payment_obj.pending = False
                if not payment_obj.amount:
                    payment_obj.amount = value
                else:
                    payment_obj.amount += value
                if not payment_obj.tx_hash:
                    payment_obj.tx_hash = tx_hash
                else:
                    payment_obj.tx_hash += ',' + tx_hash
                payment_obj.project.expires = datetime.datetime.now() + datetime.timedelta(days=30)

                commit()
