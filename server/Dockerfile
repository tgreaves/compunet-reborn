FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY compunet_server.py x25_protocol.py ./

EXPOSE 6400 6403 6502

CMD ["python3", "compunet_server.py"]
