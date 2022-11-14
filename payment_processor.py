import logging
import os
import json
import sys
import time
import uuid
import secrets
import datetime
from threading import Thread
from flask import Flask, request, Response, g, jsonify
from database.models import commit, db_session, select, Project, Payment
from util.eth_payments import Web3Helper, coin_names
from util import get_eth_amount, get_wsys_amount, get_avax_amount, get_ablock_amount, get_aablock_amount, get_sysblock_amount, \
                 min_payment_amount_tier1, min_payment_amount_tier2, min_payment_amount_xquery, discount_ablock, discount_aablock, \
                 discount_sysblock, min_api_calls, quote_valid_hours

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(level=LOGLEVEL, stream=sys.stdout,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    datefmt='[%Y-%m-%d:%H:%M:%S]')

web3_helper = Web3Helper()
api_count_cache = dict()

def update_api_counts():
    """Periodically updates the api counts to the db. Should be called
    from a unique thread."""
    while True:
        global api_count_cache
        if api_count_cache:
            try:
                with db_session:
                    for project_id in api_count_cache:
                        proj = Project.get(name=project_id)
                        if not proj:
                            continue
                        count = api_count_cache[project_id]
                        if not count or not isinstance(count, int):
                            count = 0
                        proj.used_api_tokens += count
                        if proj.used_api_tokens >= proj.api_token_count:
                            proj.active = False
                        logging.info('updating {} with {}'.format(proj.name, count))
                api_count_cache = dict()  # clear cache on success
            except Exception as e:
                logging.error(e)
        time.sleep(5)

def on_startup():
    evm_threads = {}
    for evm in coin_names:
        logging.info(f'Starting {evm} blockchain payment processing thread...')
        evm_threads[evm] = Thread(target=web3_helper.evm_start, daemon=True, args=[evm])
        evm_threads[evm].start()
    t = Thread(target=update_api_counts, daemon=True)
    t.start()

def get_min_amounts(auto_activate, xquery_bool, archive_mode_bool, amounts):

    min_amount = {}
    for coin_name in [coin_names[x][y] for x in coin_names for y in [True, False]]:
        if auto_activate:
            min_amount[coin_name] = 0
        elif xquery_bool:
            min_amount[coin_name] = amounts[f'xquery_min_amount_{coin_name}']
        elif archive_mode_bool:
            min_amount[coin_name] = amounts[f'tier2_min_amount_{coin_name}']
        else:
            min_amount[coin_name] = amounts[f'tier1_min_amount_{coin_name}']

    return min_amount

class FlaskWithStartUp(Flask):
    def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
        with self.app_context():
            on_startup()
        super(FlaskWithStartUp, self).run(host=host, port=port, debug=debug, load_dotenv=load_dotenv, **options)



app = FlaskWithStartUp(__name__)



@app.route("/create_project", methods=['POST'])
@app.route("/extend_project/<project_id>", methods=['POST'])
def create_or_extend_project(project_id=None):

    # fetch min payment amounts
    amounts = {}
    for evm in coin_names:
        for native_block_ in [True, False]:
            discount = eval(f'discount_{coin_names[evm][native_block_]}') if not native_block_ else 1
            amounts[f'tier1_min_amount_{coin_names[evm][native_block_]}'] = eval(f'get_{coin_names[evm][native_block_]}_amount(min_payment_amount_tier1*discount)')
            amounts[f'tier2_min_amount_{coin_names[evm][native_block_]}'] = eval(f'get_{coin_names[evm][native_block_]}_amount(min_payment_amount_tier2*discount)')
            amounts[f'xquery_min_amount_{coin_names[evm][native_block_]}'] = eval(f'get_{coin_names[evm][native_block_]}_amount(min_payment_amount_xquery*discount)')

    if len(amounts) - list(amounts.values()).count(None) < 1:
        context = {
            'error': 'Internal Server Error: Failed to get at least 1 payment amount, please try again',
            'amounts':amounts
        }
        return Response(response=json.dumps(context))

     # handle create_project call
    if 'create_project' in request.base_url:
        logging.info('Creating new pending project')
        request_json = request.get_json()
        logging.info(request_json)
        xquery_bool = True
        hydra_bool = False
        archive_mode_bool = False
        if request_json:
            lc_keys_request_json = dict((k.lower(), v) for k, v in request_json[0].items())
            if 'hydra' in lc_keys_request_json.keys() and lc_keys_request_json['hydra'].lower() == 'true':
                if 'xquery' in lc_keys_request_json.keys() and lc_keys_request_json['xquery'].lower() == 'true':
                    context = {
                        'error': 'A single project is not (yet) allowed to be used for both XQuery and Hydra.'
                    }
                    return Response(response=json.dumps(context))
                xquery_bool = False
                hydra_bool = True
                archive_mode_bool = 'tier' in lc_keys_request_json.keys() and lc_keys_request_json['tier'] == 2

        # Prevent client from creating a project for a service not supported on this SNode
        if min_payment_amount_xquery < 0 and xquery_bool:
            context = {
                'error': 'This Service Node does not provide XQuery service.'
                }
            return Response(response=json.dumps(context))
        if min_payment_amount_tier1 < 0 and hydra_bool:
            context = {
                'error': 'This Service Node does not provide Hydra service.'
                }
            return Response(response=json.dumps(context))
        if min_payment_amount_tier2 < 0 and hydra_bool and archive_mode_bool:
            context = {
                'error': 'This Service Node does not provide tier2 Hydra service.'
                }
            return Response(response=json.dumps(context))

        # automatically activate a newly created project if SNode operator is charging 0 (i.e. offering free service)
        auto_activate = min_payment_amount_xquery == 0 if xquery_bool \
                else min_payment_amount_tier2 == 0 if archive_mode_bool \
                else min_payment_amount_tier1 == 0

        # Fetch min amounts to be paid to activate a project
        min_amount = get_min_amounts(auto_activate, xquery_bool, archive_mode_bool, amounts)


        token = secrets.token_hex(32)
        eth_address, eth_privkey = web3_helper.get_evm_address('eth', token)
        avax_address, avax_privkey = web3_helper.get_evm_address('avax', token)
        nevm_address, nevm_privkey = web3_helper.get_evm_address('nevm', token)
        project_id = str(uuid.uuid4())
        api_key = secrets.token_urlsafe(32)

        logging.info(f'Creating project {project_id} with payment amounts: {amounts}')

        if eth_address is None and avax_address is None and nevm_address is None:
            context = {
                'error': 'Internal Server Error: Failed to get at least 1 payment address, please try again'
            }
            return Response(response=json.dumps(context))

        try:
            with db_session:
                project = Project(
                    name=project_id,
                    api_key=api_key,
                    api_token_count=10000 if auto_activate else 0, # keeps track of total api tokens awarded to client
                    used_api_tokens=0, # keeps track of total api tokens used by client
                    active=auto_activate, # keeps track of whether project is currently active
                    activated=auto_activate, # keeps track of whether project was ever activated
                    user_cancelled=False, # to be used later when payment channels are in place to track if project cancelled by user
                    hydra=hydra_bool, # True if this project allows Hydra (/xrs/evm_passthrough) access
                    xquery=xquery_bool, # True if this project allows XQuery (/xrs/xquery) access
                    archive_mode=archive_mode_bool  # True if this project allows Hydra (/xrs/evm_passthrough) access to all ETH blocks, not just most recent 128 blocks
                )

                payment = Payment(
                    pending=not auto_activate,
                    eth_token=token if token!=None else '',
                    eth_address=eth_address if eth_address!=None and not auto_activate else '',
                    eth_privkey=eth_privkey if eth_privkey!=None else '',
                    avax_token=token if token!=None else '',
                    avax_address=avax_address if avax_address!=None and not auto_activate else '',
                    avax_privkey=avax_privkey if avax_privkey!=None else '',
                    nevm_token=token if token!=None else '',
                    nevm_address=nevm_address if nevm_address!=None and not auto_activate else '',
                    nevm_privkey=nevm_privkey if nevm_privkey!=None else '',
                    quote_start_time=datetime.datetime.now(),
                    project=project,
                    min_amount_eth = min_amount['eth'],
                    min_amount_ablock = min_amount['ablock'],
                    min_amount_avax = min_amount['avax'],
                    min_amount_aablock = min_amount['aablock'],
                    min_amount_wsys = min_amount['wsys'],
                    min_amount_sysblock = min_amount['sysblock'],
                    amount_eth=0,
                    amount_ablock=0,
                    amount_avax=0,
                    amount_aablock=0,
                    amount_wsys=0,
                    amount_sysblock=0
                )
                commit()

        except Exception as e:
            logging.critical('Exception while creating Project or Payment', exc_info=True)

            context = {
                'error': 'Exception while creating Project or Payment'
            }

            return Response(response=json.dumps(context))

    # handle extend_project call
    else:
        if project_id is None:
            logging.critical('Extend project requested but no project ID provided in URL.')
            context = {
                'error': 'Extend project requested but no project ID provided in URL.'
            }
            return Response(response=json.dumps(context))

        logging.info(f'Extending project: {project_id}')
        try:
            with db_session:
                project = Project.get(name=project_id)
                payment = Payment.get(project=project_id)
                if not project or not payment:
                    logging.critical('No Project or no Payment record retreived from db', exc_info=True)
                    context = {
                        'error': 'No Project or no Payment record retreived from db'
                    }
                    return Response(response=json.dumps(context))

                # Fetch xquery_bool, archive_mode_bool from db
                xquery_bool, archive_mode_bool = project.xquery, project.archive_mode

                # Don't allow auto_activate (free) API tokens when extending a project
                auto_activate = False

                # Fetch min amounts to be paid to activate a project
                min_amount = get_min_amounts(auto_activate, xquery_bool, archive_mode_bool, amounts)

                # set pending = True so next payment receives full credit as long as quote is valid
                payment.pending = True

                payment.quote_start_time = datetime.datetime.now(),
                payment.min_amount_eth = min_amount['eth'],
                payment.min_amount_ablock = min_amount['ablock'],
                payment.min_amount_avax = min_amount['avax'],
                payment.min_amount_aablock = min_amount['aablock'],
                payment.min_amount_wsys = min_amount['wsys'],
                payment.min_amount_sysblock = min_amount['sysblock'],

                commit()
        except Exception as e:
            logging.critical('Exception while extending Project or Payment', exc_info=True)
            context = {
                'error': 'Exception while extending Project or Payment'
            }
            return Response(response=json.dumps(context))

    try:
        with db_session:
            project = Project.get(name=project_id)
            payment = Payment.get(project=project_id)
            if not project or not payment:
                logging.critical('No Project or no Payment record retreived from db', exc_info=True)
                context = {
                    'error': 'No Project or no Payment record retreived from db'
                }
                return Response(response=json.dumps(context))

            context = {
                'result': {
                    'project_id': project.name,
                    'api_key': project.api_key,
                    'min_amount_eth': payment.min_amount_eth,
                    'min_amount_ablock': payment.min_amount_ablock,
                    'min_amount_avax': payment.min_amount_avax,
                    'min_amount_aablock': payment.min_amount_aablock,
                    'min_amount_wsys': payment.min_amount_wsys,
                    'min_amount_sysblock': payment.min_amount_sysblock,
                    'payment_eth_address': payment.eth_address,
                    'payment_avax_address': payment.avax_address,
                    'payment_nevm_address': payment.nevm_address,
                    'quote_start_time': payment.quote_start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    'quote_expiry_time': (payment.quote_start_time + datetime.timedelta(hours=quote_valid_hours)).strftime("%Y-%m-%d %H:%M:%S UTC")
                }
            }

        logging.info('Successfully created new pending project')

        return Response(response=json.dumps(context))

    except Exception as e:
        logging.critical('Exception while generating response for newly created or extended Project or Payment', exc_info=True)
        context = {
            'error': 'Exception while generating response for newly created or extended Project or Payment'
        }
        return Response(response=json.dumps(context))

#@app.route("/list_projects", methods=['GET'])
#def list_projects():
#    results = []
#    try:
#        with db_session:
#            query = select(p for p in Project)
#
#            results = [{
#                'name': p.name,
#                'api_token_count': p.api_token_count,
#                'used_api_tokens': p.used_api_tokens,
#                'expires': str(p.expires),
#                'active': p.active,
#            } for p in query]
#    except Exception as e:
#        logging.error(e)
#
#    context = {
#        'result': results,
#        'error': 0
#    }
#
#    return Response(response=json.dumps(context))

@app.route("/<project_id>/api_count", methods=['POST'])
def api_count_handler(project_id):
    global api_count_cache
    if project_id:
        if project_id in api_count_cache:
            api_count_cache[project_id] += 1
        else:
            api_count_cache[project_id] = 1
        context = {
            'result': 'updated count {}'.format(api_count_cache[project_id]),
            'error': 0
        }
    else:
        context = {
            'msg': 'no project found with id {}'.format(project_id),
            'error': -1001
        }
    return Response(response=json.dumps(context))

if __name__ == '__main__':
    logging.info("[server] Starting server on port 8080.")
    app.run(host="0.0.0.0", port=8080)
