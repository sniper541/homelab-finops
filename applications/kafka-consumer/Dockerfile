FROM python:3.13-slim

WORKDIR /app

RUN useradd \
    --uid 10001 \
    --create-home \
    --shell /usr/sbin/nologin \
    appuser

COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    -r requirements.txt

COPY consumer.py .

USER 10001

CMD ["python", "consumer.py"]
