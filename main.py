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
from util.eth_payments import Web3Helper
from util import get_eth_amount, get_ablock_amount, get_aablock_amount, \
                 min_payment_amount_tier1, min_payment_amount_tier2, discount_ablock, discount_aablock

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
    t1 = Thread(target=web3_helper.eth_start, daemon=True)
    t1.start()
    t2 = Thread(target=web3_helper.avax_start, daemon=True)
    t2.start()
    t3 = Thread(target=web3_helper.eth_start_back, daemon=True)
    t3.start()
    t4 = Thread(target=web3_helper.avax_star_back, daemon=True)
    t4.start()
    t5 = Thread(target=update_api_counts, daemon=True)
    t5.start()

class FlaskWithStartUp(Flask):
    def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
        with self.app_context():
            on_startup()
        super(FlaskWithStartUp, self).run(host=host, port=port, debug=debug, load_dotenv=load_dotenv, **options)



app = FlaskWithStartUp(__name__)



@app.route("/create_project", methods=['GET'])
def create_project():
    logging.info('Creating new pending project')
    # fetch eth
    tier1_expected_amount = get_eth_amount(min_payment_amount_tier1)
    tier2_expected_amount = get_eth_amount(min_payment_amount_tier2)
    tier1_expected_amount_ablock = get_ablock_amount(min_payment_amount_tier1 * discount_ablock)
    tier2_expected_amount_ablock = get_ablock_amount(min_payment_amount_tier2 * discount_ablock)
    tier1_expected_amount_aablock = get_aablock_amount(min_payment_amount_tier1 * discount_aablock)
    tier2_expected_amount_aablock = get_aablock_amount(min_payment_amount_tier2 * discount_aablock)

    amounts = {
    "eth_tier1":tier1_expected_amount,
    "eth_tier2":tier2_expected_amount,
    "ablock_tier1":tier1_expected_amount_ablock,
    "ablock_tier2":tier2_expected_amount_ablock,
    "aablock_tier1":tier1_expected_amount_aablock,
    "aablock_tier2":tier2_expected_amount_aablock
    }
    if list(amounts.values()).count(None)>=5:
        context = {
            'error': 'Internal Server Error: Failed to get at least 2 amounts, please try again',
            'amounts':amounts
        }
        return Response(response=json.dumps(context))

    eth_token, eth_address, eth_privkey = web3_helper.get_eth_address()
    avax_token, avax_address, avax_privkey = web3_helper.get_avax_address()
    project_name = str(uuid.uuid4())
    start_time = datetime.datetime.now()
    payment_expires = start_time + datetime.timedelta(hours=3, minutes=30)
    api_key = secrets.token_urlsafe(32)

    logging.info(f'Creating project {project_name} with payment amounts: {amounts}')

    if tier1_expected_amount is None and tier2_expected_amount is None and tier1_expected_amount_ablock is None and tier2_expected_amount_ablock is None:
        eth_address = None

    try:
        if eth_address is None and avax_address is None:
            context = {
                'error': 'Internal Server Error: Failed to get at least 1 payment address, please try again'
            }
            return Response(response=json.dumps(context))

        with db_session:
            project = Project(
                name=project_name,
                api_key=api_key,
                api_token_count=6000000,
                used_api_tokens=0,
                active=False
            )

            payment = Payment(
                pending=True,
                eth_token=eth_token if eth_token!=None else '',
                eth_address=eth_address if eth_address!=None else '',
                eth_privkey=eth_privkey if eth_privkey!=None else '',
                avax_token=avax_token if avax_token!=None else '',
                avax_address=avax_address if avax_address!=None else '',
                avax_privkey=avax_privkey if avax_privkey!=None else '',
                start_time=start_time,
                project=project,
                tier1_expected_amount=tier1_expected_amount if tier1_expected_amount!=None else -1,
                tier2_expected_amount=tier2_expected_amount if tier2_expected_amount!=None else -1,
                tier1_expected_amount_ablock=tier1_expected_amount_ablock if tier1_expected_amount_ablock!=None else -1,
                tier2_expected_amount_ablock=tier2_expected_amount_ablock if tier2_expected_amount_ablock!=None else -1,
                tier1_expected_amount_aablock=tier1_expected_amount_aablock if tier1_expected_amount_aablock!=None else -1,
                tier2_expected_amount_aablock=tier2_expected_amount_aablock if tier2_expected_amount_aablock!=None else -1,
                amount_aablock=0,
                amount_ablock=0
            )

            commit()
    except Exception as e:
        logging.critical('Exception while creating Project or Payment', exc_info=True)
        
        context = { 
            'error': 'Exception while creating Project or Payment'
        }

        return Response(response=json.dumps(context))

    context = {
        'result': {
            'project_id': project_name,
            'api_key': api_key,
            'payment_eth_address': eth_address,
            'payment_avax_address': avax_address,
            'payment_amount_tier1_eth': tier1_expected_amount,
            'payment_amount_tier2_eth': tier2_expected_amount,
            'payment_amount_tier1_ablock': tier1_expected_amount_ablock,
            'payment_amount_tier2_ablock': tier2_expected_amount_ablock,
            'payment_amount_tier1_aablock': tier1_expected_amount_aablock,
            'payment_amount_tier2_aablock': tier2_expected_amount_aablock,
            'expiry_time': payment_expires.strftime("%Y-%m-%d %H:%M:%S EST")
        }
    }

    logging.info('Successfully created new pending project')

    return Response(response=json.dumps(context))


@app.route("/list_projects", methods=['GET'])
def list_projects():
    results = []
    try:
        with db_session:
            query = select(p for p in Project)

            results = [{
                'name': p.name,
                'api_token_count': p.api_token_count,
                'used_api_tokens': p.used_api_tokens,
                'expires': str(p.expires),
                'active': p.active,
            } for p in query]
    except Exception as e:
        logging.error(e)

    context = {
        'result': results,
        'error': 0
    }

    return Response(response=json.dumps(context))


@app.route("/<project_id>/api_count", methods=['POST'])
def api_count_handler(project_id):
    global api_count_cache
    project_id = request.form['project_id']
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
