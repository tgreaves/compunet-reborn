FROM python:3.12-slim

WORKDIR /app

COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY server/compunet_server.py server/x25_protocol.py ./
COPY VERSION ./

EXPOSE 6400 6403 6502

CMD ["python3", "compunet_server.py"]
