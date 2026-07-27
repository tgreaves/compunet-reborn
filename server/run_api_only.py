#!/usr/bin/env python3
"""Binding-B client API with NO static file serving.

`run_api_dev.py` also serves client/web on the same origin, which is convenient
for developing the reference client but makes it unusable for clean-room
validation: an isolated builder pointed at that port can fetch our own
implementation (index.html, dist/app.bundle.js, even src/) and the run is void.

This launcher exposes only the /v1/* API, so the builder has the protocol and
nothing else.

Run:  python server/run_api_only.py          (default port 6414)
      CLIENT_API_PORT=6404 python server/run_api_only.py
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compunet_server as s          # noqa: E402
import api_binding as api            # noqa: E402
from aiohttp import web              # noqa: E402

PORT = int(os.environ.get('CLIENT_API_PORT', '6414'))


async def main():
    app = api.make_app(s)            # /v1/* only — no static routes
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print('Compunet client API (no static files): http://localhost:%d/v1/' % PORT)
    while True:
        await asyncio.sleep(3600)


if __name__ == '__main__':
    asyncio.run(main())
