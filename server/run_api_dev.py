#!/usr/bin/env python3
"""Dev launcher for the Binding-B client API + the reference web client.

Serves BOTH on a single origin (http://localhost:6404) so the browser client
has no CORS to deal with:
  - /v1/session, /v1/gateway   -> the client API (api_binding)
  - /                          -> client/web/index.html (+ app.js, assets.json)

This is a DEVELOPMENT convenience only. In production the client API
(api_binding.make_app) runs on its own, and the static client is served
however you deploy web assets. Requires server/cfg/users.json and a staged
content tree under server/data/content (see data.example).

Run:  python server/run_api_dev.py
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compunet_server as s          # noqa: E402
import api_binding as api            # noqa: E402
from aiohttp import web              # noqa: E402

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'client', 'web')
PORT = 6404


async def _index(request):
    return web.FileResponse(os.path.join(WEB, 'index.html'))


async def main():
    app = api.make_app(s)            # /v1/* routes
    app.router.add_get('/', _index)  # client entry point
    app.router.add_static('/', WEB)  # app.js, assets.json, ...
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print('Compunet client API + web client: http://localhost:%d/' % PORT)
    while True:
        await asyncio.sleep(3600)


if __name__ == '__main__':
    asyncio.run(main())
