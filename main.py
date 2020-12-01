import logging
import os
import sys
import uuid
import secrets
import datetime
from threading import Thread
from aiohttp import web
from database.models import commit, db_session, select, Project, Payment
from util.eth_payments import Web3Helper
from util import get_eth_amount, min_payment_amount_tier1, min_payment_amount_tier2

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(level=LOGLEVEL, stream=sys.stdout,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    datefmt='[%Y-%m-%d:%H:%M:%S]')

routes = web.RouteTableDef()
app = web.Application()
web3_helper = Web3Helper()


@routes.get("/create_project", name='create_project')
async def create_project(request: web.Request):
    logging.info('Creating new pending project')

    eth_address = await web3_helper.get_eth_address()
    project_name = str(uuid.uuid4())
    start_time = datetime.datetime.now()
    payment_expires = start_time + datetime.timedelta(hours=3, minutes=30)
    api_key = secrets.token_urlsafe(32)
    tier1_expected_amount = get_eth_amount(min_payment_amount_tier1),
    tier2_expected_amount = get_eth_amount(min_payment_amount_tier2),

    logging.info(tier1_expected_amount[0], tier2_expected_amount[0])

    error = 0 if tier1_expected_amount is not None and tier2_expected_amount is not None else -1099
    try:
        if eth_address is None:
            raise Exception

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
                address=eth_address,
                start_time=start_time,
                project=project,
                tier1_expected_amount=tier1_expected_amount[0],
                tier2_expected_amount=tier2_expected_amount[0],
            )

            commit()
    except Exception as e:
        logging.error(e)
        error = -9091

    if eth_address is None or error != 0:
        error = -1000

        context = {
            'result': error,
            'error': error
        }

        return web.json_response(context)

    context = {
        'result': {
            'project_id': project_name,
            'api_key': api_key,
            'payment_address': eth_address,
            'payment_amount_tier1': tier1_expected_amount[0],
            'payment_amount_tier2': tier2_expected_amount[0],
            'expiry_time': payment_expires.strftime("%Y-%m-%d %H:%M:%S EST")
        },
        'error': error
    }

    logging.info('Successfully created new pending project')

    return web.json_response(context)


@routes.get("/list_projects", name='list_projects')
async def list_projects(request: web.Request):
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

    return web.json_response(context)


async def on_startup(application):
    t1 = Thread(target=web3_helper.start, daemon=True)
    t1.start()


async def init_app() -> web.Application:
    app.add_routes(routes)

    return app


def main():
    logging.info("[server] Starting server on port 8080.")

    app.on_startup.append(on_startup)
    web.run_app(init_app())


if __name__ == '__main__':
    main()
