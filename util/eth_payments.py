import logging
import os
import time
import json
import datetime
import secrets

from web3 import Web3
from web3.middleware import geth_poa_middleware
from database.models import Payment, db_session
from util import get_eth_amount, get_ablock_amount, get_aablock_amount, min_payment_amount_tier1, \
                 min_payment_amount_tier2, discount_ablock, discount_aablock

default_api_calls_count = 6000000

ablock_contract_address = Web3.toChecksumAddress('0xe692c8d72bd4ac7764090d54842a305546dd1de5')
aablock_contract_address = Web3.toChecksumAddress('0xC931f61B1534EB21D8c11B24f3f5Ab2471d4aB50')

with open("util/ablock_abi.json", "r") as file:
    abi = json.load(file)


def calc_api_calls_tiers(payment_amount_wei, tier1_eth_amount_wei, tier2_eth_amount_wei,
                         archival_mode: bool, def_api_calls_count: int) -> int:
    """Calculates the number of api calls for the specified archival mode and tier
    amounts. The [default api call count] * [price multiplier] determines total paid
    api calls. [price multiplier] = [user payment in eth] / [tier required payment in eth]"""
    tier_expected_amount = tier1_eth_amount_wei if not archival_mode else tier2_eth_amount_wei
    multiplier = float(payment_amount_wei) / float(tier_expected_amount)
    logging.info(f"Multiplier {multiplier}")
    api_calls = int(float(def_api_calls_count) * multiplier)
    return api_calls


def calc_api_calls(payment_amount_wei, token, archival_mode: bool, def_api_calls_count: int) -> int:
    """Calculates the number of api calls dynamically based on ETH/USD price."""
    if token == 'eth':
        tier1_amount = Web3.toWei(float(get_eth_amount(min_payment_amount_tier1)),'ether')
        tier2_amount = Web3.toWei(float(get_eth_amount(min_payment_amount_tier2)),'ether')
        return calc_api_calls_tiers(payment_amount_wei, tier1_amount, tier2_amount, archival_mode,
                                    def_api_calls_count)
    elif token == 'ablock':
        tier1_amount = Web3.toWei(float(get_ablock_amount(min_payment_amount_tier1 * discount_ablock)), 'ether')
        tier2_amount = Web3.toWei(float(get_ablock_amount(min_payment_amount_tier2 * discount_ablock)), 'ether')
        return calc_api_calls_tiers(payment_amount_wei, tier1_amount, tier2_amount, archival_mode,
                                    def_api_calls_count)

    elif token == 'aablock':
        tier1_amount = Web3.toWei(float(get_aablock_amount(min_payment_amount_tier1 * discount_aablock)), 'ether')
        tier2_amount = Web3.toWei(float(get_aablock_amount(min_payment_amount_tier2 * discount_aablock)), 'ether')
        return calc_api_calls_tiers(payment_amount_wei, tier1_amount, tier2_amount, archival_mode,
                                    def_api_calls_count)


class Web3Helper:
    def __init__(self):
        self.AVAX_HOST = os.environ.get('AVAX_HOST','')
        self.AVAX_PORT = os.environ.get('AVAX_PORT','')
        self.AVAX_HOST_TYPE = os.environ.get('AVAX_HOST_TYPE','')
        self.ETH_HOST = os.environ.get('ETH_HOST', '')
        self.ETH_PORT = os.environ.get('ETH_PORT', '')
        self.ETH_HOST_TYPE = os.environ.get('ETH_HOST_TYPE','')

        if self.AVAX_HOST_TYPE in ['http', 'https'] and self.AVAX_HOST!='':
            self.w3_avax = Web3(Web3.HTTPProvider(f'{self.AVAX_HOST_TYPE}://{self.AVAX_HOST}:{self.AVAX_PORT}/ext/bc/C/rpc'))
            self.w3_avax_back = Web3(Web3.HTTPProvider(f'{self.AVAX_HOST_TYPE}://{self.AVAX_HOST}:{self.AVAX_PORT}/ext/bc/C/rpc'))
            self.w3_avax_accounts = Web3(Web3.HTTPProvider(f'{self.AVAX_HOST_TYPE}://{self.AVAX_HOST}:{self.AVAX_PORT}/ext/bc/C/rpc'))
            self.w3_avax.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_avax_accounts.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_avax_back.middleware_onion.inject(geth_poa_middleware, layer=0)
        elif self.AVAX_HOST_TYPE in ['ws', 'wss'] and self.AVAX_HOST!='':
            self.w3_avax = Web3(Web3.WebsocketProvider(f'{self.AVAX_HOST_TYPE}://{self.AVAX_HOST}:{self.AVAX_PORT}/ext/bc/C/rpc'))
            self.w3_avax_back = Web3(Web3.WebsocketProvider(f'{self.AVAX_HOST_TYPE}://{self.AVAX_HOST}:{self.AVAX_PORT}/ext/bc/C/rpc'))
            self.w3_avax_accounts = Web3(Web3.WebsocketProvider(f'{self.AVAX_HOST_TYPE}://{self.AVAX_HOST}:{Aself.VAX_PORT}/ext/bc/C/rpc'))
            self.w3_avax.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_avax_accounts.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_avax_back.middleware_onion.inject(geth_poa_middleware, layer=0)
        if self.ETH_HOST_TYPE in ['http','https'] and self.ETH_HOST!='':
            self.w3 = Web3(Web3.HTTPProvider(f'{self.ETH_HOST_TYPE}://{self.ETH_HOST}:{self.ETH_PORT}'))
            self.w3_back = Web3(Web3.HTTPProvider(f'{self.ETH_HOST_TYPE}://{self.ETH_HOST}:{self.ETH_PORT}'))
            self.w3_accounts = Web3(Web3.HTTPProvider(f'{self.ETH_HOST_TYPE}://{self.ETH_HOST}:{self.ETH_PORT}'))
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_accounts.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_back.middleware_onion.inject(geth_poa_middleware, layer=0)
        elif self.ETH_HOST_TYPE in ['ws','wss'] and self.ETH_HOST!='':
            self.w3 = Web3(Web3.WebsocketProvider(f'{self.ETH_HOST_TYPE}://{self.ETH_HOST}:{self.ETH_PORT}'))
            self.w3_back = Web3(Web3.WebsocketProvider(f'{self.ETH_HOST_TYPE}://{self.ETH_HOST}:{self.ETH_PORT}'))
            self.w3_accounts = Web3(Web3.WebsocketProvider(f'{self.ETH_HOST_TYPE}://{self.ETH_HOST}:{self.ETH_PORT}'))
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_accounts.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_back.middleware_onion.inject(geth_poa_middleware, layer=0)
        if self.ETH_HOST_TYPE!='':
            self.contract_ablock = self.w3.eth.contract(address=ablock_contract_address, abi=abi)
        if self.AVAX_HOST_TYPE!='':
            self.contract_aablock = self.w3_avax.eth.contract(address=aablock_contract_address, abi=abi)
        self.eth_accounts = []
        self.avax_accounts = []

    def eth_start(self):
        if self.ETH_HOST_TYPE!='':
            latest = self.w3.eth.filter({'toBlock': 'latest'})
            while True:
                try:
                    events = latest.get_new_entries()
                    if len(events) > 0:  # fetch latest account info
                        self.fetch_eth_accounts()
                    self.handle_eth_events(events)
                except Exception as e:
                    latest = self.w3.eth.filter({'toBlock': 'latest'})
                    logging.critical('error handling eth event', exc_info=True)
                time.sleep(1)

    def avax_start(self):
        if self.AVAX_HOST_TYPE!='':
            latest = self.w3_avax.eth.filter({'toBlock': 'latest'})
            while True:
                try:
                    events = latest.get_new_entries()
                    if len(events) > 0:  # fetch latest account info
                        self.fetch_avax_accounts()
                    self.handle_avax_events(events)
                except Exception as e:
                    latest = self.w3_avax.eth.filter({'toBlock': 'latest'})
                    logging.critical('error handling avax event', exc_info=True)
                time.sleep(1)

    def eth_start_back(self):
        if self.AVAX_HOST_TYPE!='':
            LATEST_BLOCK = int(self.w3_back.eth.getBlock('latest').number)
            CURRENT_BLOCK = LATEST_BLOCK
            while True:
                try:
                    backward_filter = self.w3_back.eth.filter({
                                'fromBlock': hex(int(CURRENT_BLOCK)-1),
                                'toBlock': hex(int(CURRENT_BLOCK)),
                            })
                    events = backward_filter.get_all_entries()
                    if len(events) > 0:  # fetch latest account info
                        self.fetch_eth_accounts()
                    self.handle_eth_events(events)
                    if LATEST_BLOCK - CURRENT_BLOCK >= 1000:
                        CURRENT_BLOCK = LATEST_BLOCK + 1000
                    else:
                        CURRENT_BLOCK = CURRENT_BLOCK-2
                except Exception as e:
                    logging.critical('error handling eth back event', exc_info=True)
                time.sleep(1)

    def avax_start_back(self):
        if self.AVAX_HOST_TYPE!='':
            LATEST_BLOCK = int(self.w3_avax_back.eth.getBlock('latest').number)
            CURRENT_BLOCK = LATEST_BLOCK
            while True:
                try:
                    backward_filter = self.w3_avax_back.eth.filter({
                                'fromBlock': hex(int(CURRENT_BLOCK)-1),
                                'toBlock': hex(int(CURRENT_BLOCK)),
                            })
                    events = backward_filter.get_all_entries()
                    if len(events) > 0:  # fetch latest account info
                        self.fetch_avax_accounts()
                    self.handle_avax_events(events)
                    if LATEST_BLOCK - CURRENT_BLOCK >= 1000:
                        CURRENT_BLOCK = LATEST_BLOCK + 1000
                    else:
                        CURRENT_BLOCK = CURRENT_BLOCK-2
                except Exception as e:
                    logging.critical('error handling avax back event', exc_info=True)
                time.sleep(1)

    @db_session(optimistic=False)
    def fetch_eth_accounts(self):
        query = Payment.select(lambda payment: payment.start_time is not None and payment.eth_address is not None)
        accounts = [payment.eth_address for payment in query]
        if len(accounts) > 0:
            self.eth_accounts = accounts

    @db_session(optimistic=False)
    def fetch_avax_accounts(self):
        query = Payment.select(lambda payment: payment.start_time is not None and payment.avax_address is not None)
        accounts = [payment.avax_address for payment in query]
        if len(accounts) > 0:
            self.avax_accounts = accounts

    def get_eth_address(self):
        try:
            token = secrets.token_hex(32)
            acc = self.w3_accounts.eth.account.create(token)
            address = acc.address
            privkey = acc.privateKey.hex()
            return [token, address, privkey]
        except Exception as e:
            logging.critical("get eth address exception", exc_info=True)
            return [None, None, None]

    def get_avax_address(self):
        try:
            token = secrets.token_hex(32)
            acc = self.w3_avax.eth.account.create(token)
            address = acc.address
            privkey = acc.privateKey.hex()
            return [token, address, privkey]
        except Exception as e:
            logging.critical("get avax address exception", exc_info=True)
            return [None, None, None]

    @db_session(optimistic=False)
    def handle_eth_events(self, events):
        for event in events:
            self.handle_eth_event(event)

    @db_session(optimistic=False)
    def handle_avax_events(self, events):
        for event in events:
            self.handle_avax_event(event)

    def check_aablock_balance(self):
        paid = {}
        for contract_address in self.avax_accounts:
            balance_contract = self.contract_aablock.functions.balanceOf(Web3.toChecksumAddress(contract_address)).call()
            payment_obj = Payment.get(avax_address=contract_address)
            amount_aablock = balance_contract*10**10 - Web3.toWei(payment_obj.amount_aablock, 'ether')
            if amount_aablock > 0:
                paid[contract_address] = amount_aablock
        return paid

    def check_ablock_balance(self):
        paid = {}
        for contract_address in self.eth_accounts:
            balance_contract = self.contract_ablock.functions.balanceOf(contract_address).call()
            payment_obj = Payment.get(eth_address=contract_address)
            amount_ablock = balance_contract*10**10 - Web3.toWei(payment_obj.amount_ablock, 'ether')
            if amount_ablock > 0:
                paid[contract_address] = amount_ablock
        return paid

    def handle_eth_event(self, event):
        block_number = event['blockNumber']
        if not block_number:
            return
        block = self.w3.eth.get_block(block_number, full_transactions=True)
        if 'transactions' not in block:
            logging.warning('no transactions in eth block {}'.format(block_number))
            return
        logging.info('processing eth block {}'.format(block_number))
        transactions = block['transactions']
        ablock_accounts = self.check_ablock_balance()

        for tx in transactions:
            tx_hash = tx['hash'].hex()
            to_address = tx['to']
            value = tx['value']
            if value <= 0:
                continue

            if to_address in self.eth_accounts:
                payment_obj = Payment.get(eth_address=to_address)
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
                # from partial payments. If the initial price has expired, u    se the current price of eth to
                # determine how many calls the user receives. First time partial payments default to non-archival
                # api access. In order for users to obtain archival access their first payment must be greater
                # than or equal to the minimum payment amount for archival access.
                #
                # Make sure db supports large enough integer to track used_api_tokens (i.e. int64)

                # If the project has never been activated (payment is pending) allow the user to set the archival mode.
                # Activated projects cannot change the archival state.
                if payment_obj.pending:
                    # If initial payment offering has expired
                    if datetime.datetime.now() >= payment_obj.start_time + datetime.timedelta(hours=12):
                        # Expired time requires obtaining new payment tier calcs
                        tier2_expected_amount = get_eth_amount(min_payment_amount_tier2)
                        payment_obj.project.archive_mode = value >= Web3.toWei(tier2_expected_amount, 'ether')
                        # Note set the api calls here since first time payment (do not append)
                        payment_obj.project.api_token_count = calc_api_calls(value, 'eth',
                                                                             payment_obj.project.archive_mode,
                                                                             default_api_calls_count)
                    else:
                        # Non-expired payment calcs should use the db payment tiers
                        payment_obj.project.archive_mode = value >= Web3.toWei(payment_obj.tier2_expected_amount, 'ether')
                        # Note set the api calls here since first time payment (do not append)
                        payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                   Web3.toWei(payment_obj.tier1_expected_amount,'ether'),
                                                                                   Web3.toWei(payment_obj.tier2_expected_amount,'ether'),
                                                                                   payment_obj.project.archive_mode,
                                                                                   default_api_calls_count)
                else:
                    # Append api calls because this is a top-up payment (first payment already received)
                    payment_obj.project.api_token_count += calc_api_calls(value, 'eth',
                                                                          payment_obj.project.archive_mode,
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

        if ablock_accounts:
            for to_address in ablock_accounts:
                payment_obj = Payment.get(eth_address=to_address)
                value = ablock_accounts[to_address]
                if payment_obj.pending:
                    if datetime.datetime.now() >= payment_obj.start_time + datetime.timedelta(hours=12):
                        tier2_expected_amount_ablock = get_ablock_amount(min_payment_amount_tier2 * discount)
                        payment_obj.project.archive_mode = value >= (tier2_expected_amount_ablock - tier1_expected_amount_ablock)
                        payment_obj.project.api_token_count = calc_api_calls(Web3.toWei(value, 'ether'), 'ablock',
                                                                             payment_obj.project.archive_mode,
                                                                             default_api_calls_count)//(10**8)
                    else:
                        tier2_expected_amount_ablock = get_ablock_amount(min_payment_amount_tier2 * discount)
                        payment_obj.project.archive_mode = value >= (tier2_expected_amount_ablock - tier1_expected_amount_ablock)
                        payment_obj.project.api_token_count = calc_api_calls_tiers(Web3.toWei(value, 'ether'),
                                                                                   Web3.toWei(payment_obj.tier1_expected_amount_ablock,'ether'),
                                                                                   Web3.toWei(payment_obj.tier2_expected_amount_ablock,'ether'),
                                                                                   payment_obj.project.archive_mode,
                                                                                   default_api_calls_count)//(10**8)
                else:
                    payment_obj.project.api_token_count += calc_api_calls(Web3.toWei(value, 'ether'), 'ablock',
                                                                          payment_obj.project.archive_mode,
                                                                          default_api_calls_count)//(10**8)

                payment_obj.pending = False

                if payment_obj.project.api_token_count > payment_obj.project.used_api_tokens \
                        or (payment_obj.project.api_token_count > 0 and payment_obj.project.used_api_tokens is None):
                    payment_obj.project.active = True

                if not payment_obj.amount:
                    payment_obj.amount_ablock = float(value)/(10**8)
                else:
                    payment_obj.amount_ablock += float(value)/(10**8)

                payment_obj.project.expires = datetime.datetime.now() + datetime.timedelta(days=30)

    def handle_avax_event(self, event):
        block_number = event['blockNumber']
        if not block_number:
            return
        block = self.w3_avax.eth.get_block(block_number, full_transactions=True)
        if 'transactions' not in block:
            logging.warning('no transactions in avax block {}'.format(block_number))
            return
        logging.info('processing avax block {}'.format(block_number))
        transactions = block['transactions']
        aablock_accounts = self.check_aablock_balance()

        if aablock_accounts:
            for to_address in aablock_accounts:
                payment_obj = Payment.get(avax_address=to_address)
                value = aablock_accounts[to_address]
                if payment_obj.pending:
                    if datetime.datetime.now() >= payment_obj.start_time + datetime.timedelta(hours=12):
                        tier2_expected_amount_aablock = get_aablock_amount(min_payment_amount_tier2 * discount_aablock)
                        payment_obj.project.archive_mode = value >= (tier2_expected_amount_aablock - tier1_expected_amount_aablock)
                        payment_obj.project.api_token_count = calc_api_calls(Web3.toWei(value, 'ether'), 'aablock',
                                                                             payment_obj.project.archive_mode,
                                                                             default_api_calls_count)//(10**8)
                    else:
                        tier2_expected_amount_aablock = get_aablock_amount(min_payment_amount_tier2 * discount_aablock)
                        payment_obj.project.archive_mode = value >= (tier2_expected_amount_aablock - tier1_expected_amount_aablock)
                        payment_obj.project.api_token_count = calc_api_calls_tiers(Web3.toWei(value, 'ether'),
                                                                                   Web3.toWei(payment_obj.tier1_expected_amount_aablock,'ether'),
                                                                                   Web3.toWei(payment_obj.tier2_expected_amount_aablock,'ether'),
                                                                                   payment_obj.project.archive_mode,
                                                                                   default_api_calls_count)//(10**8)
                else:
                    payment_obj.project.api_token_count += calc_api_calls(Web3.toWei(value, 'ether'), 'aablock',
                                                                          payment_obj.project.archive_mode,
                                                                          default_api_calls_count)//(10**8)

                payment_obj.pending = False

                if payment_obj.project.api_token_count > payment_obj.project.used_api_tokens \
                        or (payment_obj.project.api_token_count > 0 and payment_obj.project.used_api_tokens is None):
                    payment_obj.project.active = True

                if not payment_obj.amount:
                    payment_obj.amount_aablock = float(value)/(10**8)
                else:
                    payment_obj.amount_aablock += float(value)/(10**8)

                payment_obj.project.expires = datetime.datetime.now() + datetime.timedelta(days=30)
