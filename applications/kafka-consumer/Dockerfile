FROM python:3.13-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN python -m pip install \
    --no-cache-dir \
    --prefix=/install \
    -r requirements.txt


FROM python:3.13-slim

WORKDIR /app

RUN python -m pip uninstall -y setuptools || true \
    && rm -rf \
       /usr/local/lib/python3.13/site-packages/setuptools* \
       /usr/local/lib/python3.13/site-packages/msgpack*

RUN useradd \
    --uid 10001 \
    --create-home \
    --shell /usr/sbin/nologin \
    appuser

COPY --from=builder /install /usr/local

COPY consumer.py .

USER 10001

CMD ["python", "consumer.py"]
