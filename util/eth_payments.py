import logging
import os
import time
import json
import datetime
import secrets

from web3 import Web3
from web3.middleware import geth_poa_middleware
from database.models import Payment, db_session, commit
from util import get_eth_amount, get_sys_amount, \
                 get_ablock_amount, get_aablock_amount, get_sysblock_amount, \
                 min_payment_amount_tier1, min_payment_amount_tier2, \
                 discount_ablock, discount_aablock, discount_sysblock 

default_api_calls_count = 6000000

ablock_contract_address = Web3.toChecksumAddress('0xe692c8d72bd4ac7764090d54842a305546dd1de5')
aablock_contract_address = Web3.toChecksumAddress('0xC931f61B1534EB21D8c11B24f3f5Ab2471d4aB50')
sysblock_contract_address = Web3.toChecksumAddress('0xtbd')

with open("util/ablock_abi.json", "r") as file:
    abi = json.load(file)


def calc_api_calls_tiers(payment_amount_wei, tier1_eth_amount_wei, tier2_eth_amount_wei,
                         archival_mode: bool, def_api_calls_count: int) -> int:
    """Calculates the number of api calls for the specified archival mode and tier
    amounts. The [default api call count] * [price multiplier] determines total paid
    api calls. [price multiplier] = [user payment in eth] / [tier required payment in eth]"""
    if isinstance(tier1_eth_amount_wei, tuple):
        tier1_eth_amount_wei = tier1_eth_amount_wei[0]
    if isinstance(tier2_eth_amount_wei, tuple):
        tier2_eth_amount_wei = tier2_eth_amount_wei[0]
    tier_expected_amount = tier1_eth_amount_wei if not archival_mode else tier2_eth_amount_wei
    multiplier = float(payment_amount_wei) / float(tier_expected_amount)
    logging.info(f"Multiplier {multiplier}")
    api_calls = int(float(def_api_calls_count) * multiplier)
    return api_calls


def calc_api_calls(payment_amount_wei, token, archival_mode: bool, def_api_calls_count: int) -> int:
    """Calculates the number of api calls dynamically based on ETH/USD price."""
    if token == 'eth':
        tier1_amount = float(get_eth_amount(min_payment_amount_tier1))
        tier2_amount = float(get_eth_amount(min_payment_amount_tier2))
        return calc_api_calls_tiers(payment_amount_wei, tier1_amount, tier2_amount, archival_mode,
                                    def_api_calls_count)
    elif token == 'ablock':
        tier1_amount = float(get_ablock_amount(min_payment_amount_tier1 * discount_ablock))
        tier2_amount = float(get_ablock_amount(min_payment_amount_tier2 * discount_ablock)),
        return calc_api_calls_tiers(payment_amount_wei, tier1_amount, tier2_amount, archival_mode,
                                    def_api_calls_count)

    elif token == 'aablock':
        tier1_amount = float(get_aablock_amount(min_payment_amount_tier1 * discount_aablock))
        tier2_amount = float(get_aablock_amount(min_payment_amount_tier2 * discount_aablock))
        return calc_api_calls_tiers(payment_amount_wei, tier1_amount, tier2_amount, archival_mode,
                                    def_api_calls_count)

    elif token == 'sysblock':
        tier1_amount = float(get_sysblock_amount(min_payment_amount_tier1 * discount_sysblock))
        tier2_amount = float(get_sysblock_amount(min_payment_amount_tier2 * discount_sysblock))
        return calc_api_calls_tiers(payment_amount_wei, tier1_amount, tier2_amount, archival_mode,
                                    def_api_calls_count)

    elif token == 'sys':
        tier1_amount = float(get_sys_amount(min_payment_amount_tier1))
        tier2_amount = float(get_sys_amount(min_payment_amount_tier2))
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
        self.NEVM_HOST = os.environ.get('NEVM_HOST','')
        self.NEVM_PORT = os.environ.get('NEVM_PORT','')
        self.NEVM_HOST_TYPE = os.environ.get('NEVM_HOST_TYPE','')

        if self.AVAX_HOST_TYPE in ['http', 'https'] and self.AVAX_HOST!='':
            self.w3_avax = Web3(Web3.HTTPProvider(f'{self.AVAX_HOST_TYPE}://{self.AVAX_HOST}:{self.AVAX_PORT}/ext/bc/C/rpc'))
            self.w3_avax_accounts = Web3(Web3.HTTPProvider(f'{self.AVAX_HOST_TYPE}://{self.AVAX_HOST}:{self.AVAX_PORT}/ext/bc/C/rpc'))
            self.w3_avax.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_avax_accounts.middleware_onion.inject(geth_poa_middleware, layer=0)
        elif self.AVAX_HOST_TYPE in ['ws', 'wss'] and self.AVAX_HOST!='':
            self.w3_avax = Web3(Web3.WebsocketProvider(f'{self.AVAX_HOST_TYPE}://{self.AVAX_HOST}:{self.AVAX_PORT}/ext/bc/C/rpc'))
            self.w3_avax_accounts = Web3(Web3.WebsocketProvider(f'{self.AVAX_HOST_TYPE}://{self.AVAX_HOST}:{Aself.VAX_PORT}/ext/bc/C/rpc'))
            self.w3_avax.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_avax_accounts.middleware_onion.inject(geth_poa_middleware, layer=0)
        if self.ETH_HOST_TYPE in ['http','https'] and self.ETH_HOST!='':
            self.w3 = Web3(Web3.HTTPProvider(f'{self.ETH_HOST_TYPE}://{self.ETH_HOST}:{self.ETH_PORT}'))
            self.w3_accounts = Web3(Web3.HTTPProvider(f'{self.ETH_HOST_TYPE}://{self.ETH_HOST}:{self.ETH_PORT}'))
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_accounts.middleware_onion.inject(geth_poa_middleware, layer=0)
        elif self.ETH_HOST_TYPE in ['ws','wss'] and self.ETH_HOST!='':
            self.w3 = Web3(Web3.WebsocketProvider(f'{self.ETH_HOST_TYPE}://{self.ETH_HOST}:{self.ETH_PORT}'))
            self.w3_accounts = Web3(Web3.WebsocketProvider(f'{self.ETH_HOST_TYPE}://{self.ETH_HOST}:{self.ETH_PORT}'))
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_accounts.middleware_onion.inject(geth_poa_middleware, layer=0)
        if self.NEVM_HOST_TYPE in ['http','https'] and self.NEVM_HOST!='':
            self.w3 = Web3(Web3.HTTPProvider(f'{self.NEVM_HOST_TYPE}://{self.NEVM_HOST}:{self.NEVM_PORT}'))
            self.w3_accounts = Web3(Web3.HTTPProvider(f'{self.NEVM_HOST_TYPE}://{self.NEVM_HOST}:{self.NEVM_PORT}'))
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_accounts.middleware_onion.inject(geth_poa_middleware, layer=0)
        elif self.NEVM_HOST_TYPE in ['ws','wss'] and self.NEVM_HOST!='':
            self.w3 = Web3(Web3.WebsocketProvider(f'{self.NEVM_HOST_TYPE}://{self.NEVM_HOST}:{self.NEVM_PORT}'))
            self.w3_accounts = Web3(Web3.WebsocketProvider(f'{self.NEVM_HOST_TYPE}://{self.NEVM_HOST}:{self.NEVM_PORT}'))
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.w3_accounts.middleware_onion.inject(geth_poa_middleware, layer=0)
        if self.ETH_HOST_TYPE!='':
            self.contract_ablock = self.w3.eth.contract(address=ablock_contract_address, abi=abi)
        if self.AVAX_HOST_TYPE!='':
            self.contract_aablock = self.w3_avax.eth.contract(address=aablock_contract_address, abi=abi)
        if self.NEVM_HOST_TYPE!='':
            self.contract_sysblock = self.w3_avax.eth.contract(address=sysblock_contract_address, abi=abi)
        self.eth_accounts = []
        self.avax_accounts = []
        self.nevm_accounts = []

    def eth_start(self):
        logging.info('ETH loop starting in 2s')
        time.sleep(2)
        while True:
            try:    
                if self.ETH_HOST_TYPE!='':
                    while True:
                        try:
                            self.fetch_eth_accounts()
                            self.handle_eth_event()
                        except Exception as e:
                            logging.critical('error handling eth', exc_info=True)
                        logging.info('processing eth projects in 30s...')
                        time.sleep(30)
            except Exception as e:
                logging.info('ETH node error....Retying in 30s')
                self.__init__()
                time.sleep(30)

    def avax_start(self):
        logging.info('AVAX loop starting in 2s')
        time.sleep(2)
        while True:
            try:
                if self.AVAX_HOST_TYPE!='':
                    while True:
                        try:
                            self.fetch_avax_accounts()
                            self.handle_avax_event()
                        except Exception as e:
                            logging.critical('error handling avax', exc_info=True)
                        logging.info('processing avax projects in 30s...')
                        time.sleep(30)
            except Exception as e:
                logging.info('AVAX node error....Retying in 30s')
                self.__init__()
                time.sleep(30)

    def nevm_start(self):
        logging.info('NEVM loop starting in 2s')
        time.sleep(2)
        while True:
            try:
                if self.NEVM_HOST_TYPE!='':
                    while True:
                        try:
                            self.fetch_nevm_accounts()
                            self.handle_nevm_event()
                        except Exception as e:
                            logging.critical('error handling nevm', exc_info=True)
                        logging.info('processing nevm projects in 30s...')
                        time.sleep(30)
            except Exception as e:
                logging.info('NEVM node error....Retying in 30s')
                self.__init__()
                time.sleep(30)

    @db_session()
    def fetch_eth_accounts(self):
        query = Payment.select(lambda payment: payment.start_time is not None and payment.eth_address is not None and payment.eth_address!='')
        accounts = [payment.eth_address for payment in query]
        if len(accounts) > 0:
            self.eth_accounts = accounts

    @db_session()
    def fetch_avax_accounts(self):
        query = Payment.select(lambda payment: payment.start_time is not None and payment.avax_address is not None and payment.avax_address!='')
        accounts = [payment.avax_address for payment in query]
        if len(accounts) > 0:
            self.avax_accounts = accounts

    @db_session()
    def fetch_nevm_accounts(self):
        query = Payment.select(lambda payment: payment.start_time is not None and payment.nevm_address is not None and payment.nevm_address!='')
        accounts = [payment.nevm_address for payment in query]
        if len(accounts) > 0:
            self.nevm_accounts = a

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

    def get_nevm_address(self):
        try:
            token = secrets.token_hex(32)
            acc = self.w3_nevm.eth.account.create(token)
            address = acc.address
            privkey = acc.privateKey.hex()
            return [token, address, privkey]
        except Exception as e:
            logging.critical("get nevm address exception", exc_info=True)
            return [None, None, None]

    def check_aablock_balance(self):
        paid = {}
        for contract_address in self.avax_accounts:
            balance_contract = self.contract_aablock.functions.balanceOf(Web3.toChecksumAddress(contract_address)).call()
            amount_aablock = float(Web3.fromWei(balance_contract*10**10, 'ether'))
            if amount_aablock > 0:
                paid[contract_address] = amount_aablock
        return paid

    def check_ablock_balance(self):
        paid = {}
        for contract_address in self.eth_accounts:
            balance_contract = self.contract_ablock.functions.balanceOf(Web3.toChecksumAddress(contract_address)).call()
            amount_ablock = float(Web3.fromWei(balance_contract*10**10, 'ether'))
            if amount_ablock > 0:
                paid[contract_address] = amount_ablock
        return paid

    def check_sysblock_balance(self):
        paid = {}
        for contract_address in self.nevm_accounts:
            balance_contract = self.contract_sysblock.functions.balanceOf(Web3.toChecksumAddress(contract_address)).call()
            amount_sysblock = float(Web3.fromWei(balance_contract*10**10, 'ether'))
            if amount_sysblock > 0:
                paid[contract_address] = amount_sysblock
        return paid

    def check_eth_balance(self):
        paid = {}
        for address in self.eth_accounts:
            balance = self.w3.eth.getBalance(Web3.toChecksumAddress(address))
            amount_eth = float(Web3.fromWei(balance, 'ether'))
            if amount_eth > 0:
                paid[address] = amount_eth
        return paid

    def check_sys_balance(self):
        paid = {}
        for address in self.nevm_accounts:
            balance = self.w3.eth.getBalance(Web3.toChecksumAddress(address))
            amount_sys = float(Web3.fromWei(balance, 'sys'))
            if amount_sys > 0:
                paid[address] = amount_sys
        return paid    

    @db_session()
    def handle_eth_event(self):
        logging.info('processing eth ablock projects')
        ablock_accounts = self.check_ablock_balance()
        eth_accounts = self.check_eth_balance()

        if eth_accounts:
            for to_address in eth_accounts:
                payment_obj = Payment.get(eth_address=to_address)
                value = eth_accounts[to_address]
                if value >= payment_obj.tier1_expected_amount:
                    logging.info('eth payment received for project: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))

                    if payment_obj.pending:
                        # If initial payment offering has expired
                        logging.info('eth processing payment for project: {} {} {}'.format(payment_obj.project.name,
                                                         to_address, value))
                        if datetime.datetime.now() >= payment_obj.start_time + datetime.timedelta(hours=1):
                            payment_obj.project.archive_mode = False
                            payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                       payment_obj.tier1_expected_amount,
                                                                                       payment_obj.tier2_expected_amount,
                                                                                       payment_obj.project.archive_mode,
                                                                                       default_api_calls_count/2)    
                        else:
                            # Non-expired payment calcs should use the db payment tiers
                            payment_obj.project.archive_mode = value >= payment_obj.tier2_expected_amount
                            # Note set the api calls here since first time payment (do not append)
                            payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                       payment_obj.tier1_expected_amount,
                                                                                       payment_obj.tier2_expected_amount,
                                                                                       payment_obj.project.archive_mode,
                                                                                       default_api_calls_count)            
                        payment_obj.pending = False

                        # If the user has overage don't allow them to use the api until they've
                        # paid for the overage. Only set the project to active if they have
                        # more api tokens available than used api tokens.
                        if payment_obj.project.api_token_count > payment_obj.project.used_api_tokens \
                                or (payment_obj.project.api_token_count > 0 and payment_obj.project.used_api_tokens is None):
                            payment_obj.project.active = True

                        payment_obj.amount = float(value)

                        payment_obj.project.expires = datetime.datetime.now() + datetime.timedelta(days=30)
                else:
                    logging.info('eth payment received for project too low: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))

        if ablock_accounts:
            for to_address in ablock_accounts:
                payment_obj = Payment.get(eth_address=to_address)
                value = ablock_accounts[to_address]
                if value >= payment_obj.tier1_expected_amount_ablock:
                    logging.info('ablock payment received for project: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))
                    if payment_obj.pending:
                        logging.info('ablock processing payment for project: {} {} {}'.format(payment_obj.project.name,
                                                         to_address, value))
                        if datetime.datetime.now() >= payment_obj.start_time + datetime.timedelta(hours=1):
                            payment_obj.project.archive_mode = False
                            payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                       payment_obj.tier1_expected_amount_ablock,
                                                                                       payment_obj.tier2_expected_amount_ablock,
                                                                                       payment_obj.project.archive_mode,
                                                                                       default_api_calls_count/2)
                        else:
                            payment_obj.project.archive_mode = value >= payment_obj.tier2_expected_amount_ablock
                            payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                       payment_obj.tier1_expected_amount_ablock,
                                                                                       payment_obj.tier2_expected_amount_ablock,
                                                                                       payment_obj.project.archive_mode,
                                                                                       default_api_calls_count)

                        payment_obj.pending = False

                        if payment_obj.project.api_token_count > payment_obj.project.used_api_tokens \
                                or (payment_obj.project.api_token_count > 0 and payment_obj.project.used_api_tokens is None):
                            payment_obj.project.active = True

                        payment_obj.amount_ablock = float(value)

                        payment_obj.project.expires = datetime.datetime.now() + datetime.timedelta(days=30)
                else:
                    logging.info('ablock payment received for project too low: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))

    @db_session()
    def handle_avax_event(self):
        logging.info('processing avax projects')
        aablock_accounts = self.check_aablock_balance()

        if aablock_accounts:
            for to_address in aablock_accounts:
                payment_obj = Payment.get(avax_address=to_address)
                value = aablock_accounts[to_address]
                if value >= payment_obj.tier1_expected_amount_aablock:
                    logging.info('aablock payment received for project: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))
                    if payment_obj.pending:
                        logging.info('aablock processing payment for project: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))
                        if datetime.datetime.now() >= payment_obj.start_time + datetime.timedelta(hours=1):
                            payment_obj.project.archive_mode = False
                            payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                       payment_obj.tier1_expected_amount_aablock,
                                                                                       payment_obj.tier2_expected_amount_aablock,
                                                                                       payment_obj.project.archive_mode,
                                                                                       default_api_calls_count/2)
                        else:
                            payment_obj.project.archive_mode = value >= payment_obj.tier2_expected_amount_aablock
                            payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                       payment_obj.tier1_expected_amount_aablock,
                                                                                       payment_obj.tier2_expected_amount_aablock,
                                                                                       payment_obj.project.archive_mode,
                                                                                       default_api_calls_count)

                        payment_obj.pending = False

                        if payment_obj.project.api_token_count > payment_obj.project.used_api_tokens \
                                or (payment_obj.project.api_token_count > 0 and payment_obj.project.used_api_tokens is None):
                            payment_obj.project.active = True

                        payment_obj.amount_aablock = float(value)

                        payment_obj.project.expires = datetime.datetime.now() + datetime.timedelta(days=30)
                else:
                    logging.info('aablock payment received for project too low: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))

    @db_session()
    def handle_nevm_event(self):
        logging.info('processing sys sysblock projects')
        sys_accounts = self.check_sys_balance()
        sysblock_accounts = self.check_sysblock_balance()

        if sys_accounts:
            for to_address in sys_accounts:
                payment_obj = Payment.get(sys_address=to_address)
                value = sys_accounts[to_address]
                if value >= payment_obj.tier1_expected_amount:
                    logging.info('sys payment received for project: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))

                    if payment_obj.pending:
                        # If initial payment offering has expired
                        logging.info('sys processing payment for project: {} {} {}'.format(payment_obj.project.name,
                                                         to_address, value))
                        if datetime.datetime.now() >= payment_obj.start_time + datetime.timedelta(hours=1):
                            payment_obj.project.archive_mode = False
                            payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                       payment_obj.tier1_expected_amount,
                                                                                       payment_obj.tier2_expected_amount,
                                                                                       payment_obj.project.archive_mode,
                                                                                       default_api_calls_count/2)    
                        else:
                            # Non-expired payment calcs should use the db payment tiers
                            payment_obj.project.archive_mode = value >= payment_obj.tier2_expected_amount
                            # Note set the api calls here since first time payment (do not append)
                            payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                       payment_obj.tier1_expected_amount,
                                                                                       payment_obj.tier2_expected_amount,
                                                                                       payment_obj.project.archive_mode,
                                                                                       default_api_calls_count)            
                        payment_obj.pending = False

                        # If the user has overage don't allow them to use the api until they've
                        # paid for the overage. Only set the project to active if they have
                        # more api tokens available than used api tokens.
                        if payment_obj.project.api_token_count > payment_obj.project.used_api_tokens \
                                or (payment_obj.project.api_token_count > 0 and payment_obj.project.used_api_tokens is None):
                            payment_obj.project.active = True

                        payment_obj.amount = float(value)

                        payment_obj.project.expires = datetime.datetime.now() + datetime.timedelta(days=30)
                else:
                    logging.info('sys payment received for project too low: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))

        if sysblock_accounts:
            for to_address in sysblock_accounts:
                payment_obj = Payment.get(nevm_address=to_address)
                value = sysblock_accounts[to_address]
                if value >= payment_obj.tier1_expected_amount_sysblock:
                    logging.info('sysblock payment received for project: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))
                    if payment_obj.pending:
                        logging.info('sysblock processing payment for project: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))
                        if datetime.datetime.now() >= payment_obj.start_time + datetime.timedelta(hours=1):
                            payment_obj.project.archive_mode = False
                            payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                       payment_obj.tier1_expected_amount_sysblock,
                                                                                       payment_obj.tier2_expected_amount_sysblock,
                                                                                       payment_obj.project.archive_mode,
                                                                                       default_api_calls_count/2)
                        else:
                            payment_obj.project.archive_mode = value >= payment_obj.tier2_expected_amount_sysblock
                            payment_obj.project.api_token_count = calc_api_calls_tiers(value,
                                                                                       payment_obj.tier1_expected_amount_sysblock,
                                                                                       payment_obj.tier2_expected_amount_sysblock,
                                                                                       payment_obj.project.archive_mode,
                                                                                       default_api_calls_count)

                        payment_obj.pending = False

                        if payment_obj.project.api_token_count > payment_obj.project.used_api_tokens \
                                or (payment_obj.project.api_token_count > 0 and payment_obj.project.used_api_tokens is None):
                            payment_obj.project.active = True

                        payment_obj.amount_aablock = float(value)

                        payment_obj.project.expires = datetime.datetime.now() + datetime.timedelta(days=30)
                else:
                    logging.info('sysblock payment received for project too low: {} {} {}'.format(payment_obj.project.name,
                                                                                 to_address, value))
