FROM python:3.12-slim

WORKDIR /app

COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ⚠ Every module compunet_server imports at RUNTIME must be listed here. It
# imports api_binding to serve Binding B (§1.8) on 6404 — omitting it did not
# disable the JSON API, it killed the whole server at startup, C64 service
# included. api_binding needs only stdlib + aiohttp (already in requirements)
# and partyline, both of which are present.
#
# ⚠ THIS HAS NOW HAPPENED TWICE. 1.3.0 added header_frame and header_preview and
# did not add them here; the image built cleanly, then crash-looped on
# `ModuleNotFoundError: No module named 'header_frame'`. A source checkout cannot
# catch it — the modules are right there — so nothing fails until deployment.
# Adding an import to compunet_server.py means adding the file to this list.
# The current runtime set is: x25_protocol, partyline, terminal, api_binding,
# header_frame, header_preview (partyline and terminal import compunet_server
# back; api_binding pulls in partyline).
COPY server/compunet_server.py server/x25_protocol.py server/partyline.py \
     server/terminal.py server/api_binding.py \
     server/header_frame.py server/header_preview.py ./
# ⚠ The web client ships INSIDE the server image so the client API can serve it
# from its own origin (see make_app's web_client_dir). One hostname through the
# tunnel, nothing for the user to type, no CORS. It also means the hosted client
# is always the build that matches this server.
COPY client/web/index.html client/web/assets.json ./web/
COPY client/web/dist/app.bundle.js ./web/dist/

COPY VERSION ./

EXPOSE 6400 6401 6403 6404

CMD ["python3", "compunet_server.py"]
