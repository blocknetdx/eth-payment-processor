import logging
import os
import time
import json
import datetime
import secrets

from web3 import Web3
from web3.middleware import geth_poa_middleware
from database.models import Payment, db_session, commit
from util import get_eth_amount, get_wsys_amount, \
                 get_ablock_amount, get_aablock_amount, get_sysblock_amount, \
                 min_payment_amount_tier1, min_payment_amount_tier2, min_payment_amount_xquery, \
                 discount_ablock, discount_aablock, discount_sysblock, quote_valid_hours

# create nested dict of names of EVM native coins (coin_names[evm][True]) and block token names (coin_names[evm][False])
coin_names = {
        'eth': {
            True:'eth',
            False:'ablock'
            },
        'avax': {
            True:'avax',
            False:'aablock'
            },
        'nevm': {
            True:'wsys',
            False:'sysblock'
            }
        }
block_contract_address = {}
block_contract_address['eth'] = Web3.toChecksumAddress('0xe692c8d72bd4ac7764090d54842a305546dd1de5') # ablock_contract_address 
block_contract_address['avax'] = Web3.toChecksumAddress('0xC931f61B1534EB21D8c11B24f3f5Ab2471d4aB50') # aablock_contract_address 
block_contract_address['nevm'] = Web3.toChecksumAddress('0x1CcCA1cE62c62F7Be95d4A67722a8fDbed6EEcb4') # sysblock_contract_address 
#block_contract['nevm'] = Web3.toChecksumAddress('0xe18c200a70908c89ffa18c628fe1b83ac0065ea4') # This was a placeholder sysblock_contract_address before sysblock was created

with open("util/ablock_abi.json", "r") as file:
    abi = json.load(file)


class Web3Helper:
    def __init__(self):

        self.HOST = {}
        self.PORT = {}
        self.HOST_TYPE = {}
        self.w3 = {}
        #self.w3_accounts = {}
        self.contract = {}
        self.accounts = {}
        for evm in coin_names:
            self.HOST[evm] = os.environ.get(f'{evm.upper()}_HOST','')
            self.PORT[evm] = os.environ.get(f'{evm.upper()}_PORT','')
            self.HOST_TYPE[evm] = os.environ.get(f'{evm.upper()}_HOST_TYPE','')
            self.w3[evm] = None
            #self.w3_accounts[evm] = None
            url_ext = '/ext/bc/C/rpc' if evm == 'AVAX' else ''
            if self.HOST_TYPE[evm] in ['http', 'https'] and self.HOST[evm]!='':
                self.w3[evm] = Web3(Web3.HTTPProvider(f'{self.HOST_TYPE[evm]}://{self.HOST[evm]}:{self.PORT[evm]}{url_ext}'))
                #self.w3_accounts[evm] = Web3(Web3.HTTPProvider(f'{self.HOST_TYPE[evm]}://{self.HOST[evm]}:{self.PORT[evm]}{url_ext}'))
            elif self.HOST_TYPE[evm] in ['ws', 'wss'] and self.HOST[evm]!='':
                self.w3[evm] = Web3(Web3.WebsocketProvider(f'{self.HOST_TYPE[evm]}://{self.HOST[evm]}:{self.PORT[evm]}{url_ext}'))
                #self.w3_accounts[evm] = Web3(Web3.WebsocketProvider(f'{self.HOST_TYPE[evm]}://{self.HOST[evm]}:{self.PORT[evm]}{url_ext}'))
            self.w3[evm].middleware_onion.inject(geth_poa_middleware, layer=0)
            #self.w3_accounts[evm].middleware_onion.inject(geth_poa_middleware, layer=0)
            if self.HOST_TYPE[evm]!='':
                self.contract[evm] = self.w3[evm].eth.contract(address=block_contract_address[evm], abi=abi)
            self.accounts[evm] = []

    def evm_start(self, evm):
        if self.HOST_TYPE[evm]=='': return # this saves CPU cycle
        logging.info(f'{evm.upper()} loop starting in 2s')
        time.sleep(2) # I have no idea why this is here - Conan
        while True:
            try:
                self.fetch_evm_accounts(evm) #  sets self.accounts[evm] to list of all evm addresses which have been created via create_project
                self.handle_evm_event(evm)
            except Exception as e:
                logging.critical(f'error handling {evm}', exc_info=True)
            logging.info(f'processing {evm} projects in 20s...')
            time.sleep(20)

    @db_session()
    def fetch_evm_accounts(self, evm):
        query = Payment.select(eval(f'lambda payment: payment.quote_start_time is not None and payment.{evm}_address is not None and payment.{evm}_address!=""'))
        accounts = eval(f'[payment.{evm}_address for payment in query]')
        if len(accounts) > 0:
                self.accounts[evm] = accounts

    def get_evm_address(self, evm, token):
        if self.w3[evm] is None:
            return [None, None]
        try:
            acc = self.w3[evm].eth.account.create(token)
            address = acc.address
            privkey = acc.privateKey.hex()
            return [address, privkey]
        except Exception as e:
            logging.critical(f'get {evm.upper()} address exception', exc_info=True)
            return [None, None]

    # returns dict of addr => addr_value
    def check_balance(self, evm, evm_coin_block_token_):
        # evm_coin_block_token_ = True if checking balance of evm coin, False if checking balance of block token on evm
        paid = {}
        for address in self.accounts[evm]:
            if evm_coin_block_token_:
                balance = self.w3[evm].eth.getBalance(Web3.toChecksumAddress(address))
                amount = float(Web3.fromWei(balance, 'ether'))
            else:
                balance_contract = self.contract[evm].functions.balanceOf(Web3.toChecksumAddress(address)).call()
                amount = float(Web3.fromWei(balance_contract*10**10, 'ether'))
            if amount > 0:
                paid[address] = amount
        return paid

    @db_session()
    def handle_evm_event(self, evm):

        def update_db_amount(coin_name, payment_obj, value):
            if coin_name == 'avax':
                payment_obj.amount_avax = float(value)
            elif coin_name == 'aablock':
                payment_obj.amount_aablock = float(value)
            elif coin_name == 'wsys':
                payment_obj.amount_wsys = float(value)
            elif coin_name == 'sysblock':
                payment_obj.amount_sysblock = float(value)
            elif coin_name == 'eth':
                payment_obj.amount_eth = float(value)
            elif coin_name == 'ablock':
                payment_obj.amount_ablock = float(value)

        # evm_coin_block_token_ = True if checking balance of evm native coin, False if checking balance of block token on evm
        for evm_coin_block_token_ in [True, False]:
            accounts = self.check_balance(evm, evm_coin_block_token_) # stores dict of addr => addr_value in accounts var
            coin_name = coin_names[evm][evm_coin_block_token_]
            logging.info(f'processing {coin_name} payments...')
            for to_address in accounts:
                payment_obj = eval(f'Payment.get({evm}_address=to_address)')
                min_amount = eval(f'payment_obj.min_amount_{coin_name}')
                if min_amount <= 0:
                    continue # SNode op may have set min_amount to 0 to allow free access; this continue prevents division by 0 below

                if payment_obj.pending and datetime.datetime.now() > payment_obj.quote_start_time + datetime.timedelta(hours=quote_valid_hours):
                    payment_obj.pending = False # set pending = False if quote time expired

                value = accounts[to_address]
                value_added = value - eval(f'payment_obj.amount_{coin_name}')
                if value_added >= min_amount:
                    logging.info('{} {} payment received for project: {} at address: {}'.format(value_added, coin_name, payment_obj.project.name,
                                                                                 to_address))

                    # If payment quote still valid/pending, add to api_token_count according to amount paid
                    if payment_obj.pending:
                        payment_obj.project.api_token_count += int(value_added * min_api_calls / min_amount)
                    # If payment quote NOT still valid/pending, add half of quoted api calls to api_token_count, according to amount paid / 2
                    else:
                        payment_obj.project.api_token_count += int(value_added * min_api_calls / min_amount / 2)

                    # Only set the project to active if the user has
                    # more api tokens available than used api tokens.
                    if payment_obj.project.api_token_count > payment_obj.project.used_api_tokens:
                        payment_obj.project.active = True
                        payment_obj.project.activated = True

                    update_db_amount(coin_name, payment_obj, value)

                elif value_added > 0:
                    logging.info('{} {} payment received for project: {} at address: {} was too low'.format(value_added, coin_name, payment_obj.project.name,
                                                                                 to_address))
                    logging.info('min {} payment for project: {} is {} but only {} was received'.format(coin_name, payment_obj.project.name,
                                                                                     min_amount, value_added))
                elif value_added < 0:
                    logging.info('{} {} withdrawn from project: {} address: {} by SNode operator'.format(abs(value_added), coin_name, payment_obj.project.name,
                                                                                 to_address))
                    update_db_amount(coin_name, payment_obj, value)
