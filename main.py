import json
import asyncio
from aiohttp import web
from database.models import *
from util.eth_payments import Web3Helper

routes = web.RouteTableDef()
app = web.Application()
web3_helper = Web3Helper()


@db_session
@routes.get("/request_eth_address", name='request_eth_address')
async def request_eth_address(request: web.Request):
    eth_address = await web3_helper.get_eth_address()

    error = 0
    if eth_address is None:
        error = 'Unexpected Error!'

    context = {
        'result': eth_address if error is None else '',
        'error': error
    }

    print('Received ping request')

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
