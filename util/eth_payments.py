import logging
import os
import time
import datetime

from web3 import Web3
from database.models import Payment, db_session
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
    """Calculates the number of api calls dynamically based on ETH/USD price."""
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

    def start(self):
        latest = self.w3.eth.filter('latest')

        while True:
            try:
                events = latest.get_new_entries()
                if len(events) > 0:  # fetch latest account info
                    self.fetch_accounts()
                self.handle_events(events)
            except Exception as e:
                logging.error('error handling event {}'.format(e))
            time.sleep(1)

    @db_session
    def fetch_accounts(self):
        query = Payment.select(lambda payment: payment.start_time is not None and payment.address is not None)
        accounts = [payment.address for payment in query]
        if len(accounts) > 0:
            self.accounts = accounts

    async def get_eth_address(self):
        try:
            return self.w3_accounts.geth.personal.new_account('')
        except Exception as e:
            logging.error(e)

            return None

    @db_session
    def handle_events(self, events):
        for event in events:
            self.handle_event(event)

    def handle_event(self, event):
        block_hash = Web3.toHex(event)
        if not block_hash:
            return
        block = self.w3.eth.getBlock(block_hash, full_transactions=True)
        if 'transactions' not in block:
            logging.warning('no transactions in eth block {}'.format(block_hash))
            return
        logging.info('processing eth block {}'.format(block_hash))
        transactions = block['transactions']

        for tx in transactions:
            tx_hash = tx['hash'].hex()
            to_address = tx['to']
            value = tx['value']
            if value <= 0:
                continue

            if to_address in self.accounts:
                payment_obj = Payment.get(address=to_address)
                if not payment_obj or not payment_obj.project:
                    logging.warning('payment received for unknown project'.format(tx_hash, to_address, value))
                    continue

                tx_ids = set(payment_obj.tx_hash.split(','))
                if tx_hash in tx_ids:
                    continue  # payment already received

                logging.info('payment received for project: {} {} {}'.format(payment_obj.project.name, tx_hash,
                                                                             to_address, value))

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
                    # If initial payment offering has expired
                    if datetime.datetime.now() >= payment_obj.start_time + datetime.timedelta(hours=3, minutes=30):
                        # Expired time requires obtaining new payment tier calcs
                        tier2_expected_amount = get_eth_amount(min_payment_amount_tier2)
                        payment_obj.project.archive_mode = value >= Web3.toWei(tier2_expected_amount, 'ether')
                        # Note set the api calls here since first time payment (do not append)
                        payment_obj.project.api_token_count = calc_api_calls(value, payment_obj.project.archive_mode,
                                                                             default_api_calls_count)
                    else:
                        # Non-expired payment calcs should use the db payment tiers
                        payment_obj.project.archive_mode = value >= Web3.toWei(payment_obj.tier2_expected_amount, 'ether')
                        # Note set the api calls here since first time payment (do not append)
                        payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                   payment_obj.tier1_expected_amount,
                                                                                   payment_obj.tier2_expected_amount,
                                                                                   payment_obj.project.archive_mode,
                                                                                   default_api_calls_count)
                else:
                    # Append api calls because this is a top-up payment (first payment already received)
                    payment_obj.project.api_token_count += calc_api_calls(value, payment_obj.project.archive_mode,
                                                                          default_api_calls_count)

                payment_obj.pending = False

                # If the user has overage don't allow them to use the api until they've
                # paid for the overage. Only set the project to active if they have
                # more api tokens available than used api tokens.
                if payment_obj.project.api_token_count > payment_obj.project.used_api_tokens \
                        or (payment_obj.project.api_token_count > 0 and payment_obj.project.used_api_tokens is None):
                    payment_obj.project.active = True

                if not payment_obj.amount:
                    payment_obj.amount = float(Web3.fromWei(value, 'ether'))
                else:
                    payment_obj.amount += float(Web3.fromWei(value, 'ether'))

                if not payment_obj.tx_hash:
                    payment_obj.tx_hash = tx_hash
                else:
                    payment_obj.tx_hash += ',' + tx_hash

                payment_obj.project.expires = datetime.datetime.now() + datetime.timedelta(days=30)
