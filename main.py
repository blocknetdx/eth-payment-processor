import os
import time
import uuid
import secrets
import datetime
import ccxt
from threading import Thread
from aiohttp import web
from database.models import commit, db_session, select, Project, Payment
from util.eth_payments import Web3Helper

routes = web.RouteTableDef()
app = web.Application()
web3_helper = Web3Helper()


min_payment_amount_tier1 = float(os.environ.get('PAYMENT_AMOUNT_TIER1', 35))
min_payment_amount_tier2 = float(os.environ.get('PAYMENT_AMOUNT_TIER2', 200))

coinbase = ccxt.coinbasepro()
last_amount_update_time = None
eth_price = None


def get_eth_amount(amount):
    global eth_price
    global last_amount_update_time

    if last_amount_update_time is None or (int(time.time()) - 60) > last_amount_update_time:
        eth_price = coinbase.fetch_ticker('ETH/USD')['close']
        last_amount_update_time = int(time.time())

    if eth_price is None:
        return None

    return float('{:.6f}'.format(amount / eth_price))


@routes.get("/create_project", name='create_project')
async def create_project(request: web.Request):
    print('Creating new pending project')

    eth_address = await web3_helper.get_eth_address()
    project_name = str(uuid.uuid4())
    start_time = datetime.datetime.now()
    payment_expires = start_time + datetime.timedelta(hours=3, minutes=30)
    api_key = secrets.token_urlsafe(32)
    tier1_expected_amount = get_eth_amount(min_payment_amount_tier1),
    tier2_expected_amount = get_eth_amount(min_payment_amount_tier2),

    print(tier1_expected_amount[0], tier2_expected_amount[0])

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
        print(e)
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

    print('Successfully created new pending project')

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
        print(e)

    context = {
        'result': results,
        'error': 0
    }

    return web.json_response(context)


async def on_startup(application):
    t1 = Thread(target=web3_helper.start)
    t2 = Thread(target=web3_helper.loop_accounts)
    t1.start()
    t2.start()


async def init_app() -> web.Application:
    app.add_routes(routes)

    return app


def main():
    print("[server] Starting server on port 8080.")

    app.on_startup.append(on_startup)
    web.run_app(init_app())


if __name__ == '__main__':
    main()
