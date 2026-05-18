FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir websockets

COPY compunet_server.py x25_protocol.py ./

EXPOSE 6400 6502

CMD ["python3", "compunet_server.py"]
