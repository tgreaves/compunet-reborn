FROM python:3.12-slim

WORKDIR /app

COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ⚠ Every module compunet_server imports at RUNTIME must be listed here. It
# imports api_binding to serve Binding B (§1.8) on 6404 — omitting it did not
# disable the JSON API, it killed the whole server at startup, C64 service
# included. api_binding needs only stdlib + aiohttp (already in requirements)
# and partyline, both of which are present.
COPY server/compunet_server.py server/x25_protocol.py server/partyline.py \
     server/terminal.py server/api_binding.py ./
COPY VERSION ./

EXPOSE 6400 6401 6403 6404

CMD ["python3", "compunet_server.py"]
