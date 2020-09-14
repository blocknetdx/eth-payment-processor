import json
import asyncio
import uuid
import datetime
from aiohttp import web
from database.models import *
from util.eth_payments import Web3Helper

routes = web.RouteTableDef()
app = web.Application()
web3_helper = Web3Helper()


@db_session
@routes.get("/create_project", name='create_project')
async def create_project(request: web.Request):
    print('Creating new pending project')

    eth_address = await web3_helper.get_eth_address()
    project_name = str(uuid.uuid4())
    start_time = datetime.datetime.now()
    payment_expires = start_time + datetime.timedelta(hours=3, minutes=30)

    error = 0
    try:
        if eth_address is None:
            raise Exception

        project = Project(
            name=project_name,
            api_token_count=10000,
            active=False
        )

        payment = Payment(
            pending=True,
            address=eth_address,
            start_time=start_time,
            project=project
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

        return web.json_response(json.dumps(context))

    context = {
        'result': {
            'project_id': project_name,
            'payment_address': eth_address,
            'expiry_time': payment_expires.strftime("%Y-%m-%d %H:%M:%S")
        },
        'error': error
    }

    print('Successfully created new pending project')

    return web.json_response(json.dumps(context))


async def start_backend(application):
    application['eth_payment_listener'] = asyncio.create_task(web3_helper.start())
    application['eth_accounts_update'] = asyncio.create_task(web3_helper.loop_accounts())


async def init_app() -> web.Application:
    app.add_routes(routes)

    return app


def main():
    print("[server] Starting server on port 8080.")

    app.on_startup.append(start_backend)
    web.run_app(init_app())


if __name__ == '__main__':
    main()
