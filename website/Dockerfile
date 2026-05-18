FROM python:3.12-slim

WORKDIR /app

COPY website/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY website/ ./
COPY VERSION ./

EXPOSE 6464

CMD ["python3", "app.py"]
