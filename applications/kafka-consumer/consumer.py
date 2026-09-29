import json
import logging
import os
import signal
from pathlib import Path

import psycopg
from confluent_kafka import Consumer, KafkaException


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger("finops-kafka-consumer")

running = True


def shutdown_handler(signum, frame):
    global running
    running = False


signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)


def load_credentials(path: str) -> tuple[str, str]:
    try:
        data = json.loads(Path(path).read_text())
        username = data["username"]
        password = data["password"]

        if not all(isinstance(value, str) and value for value in (username, password)):
            raise ValueError()

        return username, password

    except (OSError, ValueError, KeyError, TypeError):
        raise RuntimeError(f"Credentials unavailable: {path}") from None


def get_db_connection():
    username, password = load_credentials(
        os.getenv(
            "POSTGRES_CREDENTIALS_FILE",
            "/vault/secrets/database.json",
        )
    )

    return psycopg.connect(
        host=os.getenv(
            "POSTGRES_HOST",
            "postgres.finops.svc.cluster.local",
        ),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "finops"),
        user=username,
        password=password,
        connect_timeout=5,
    )


def get_consumer() -> Consumer:
    username, password = load_credentials(
        os.getenv(
            "KAFKA_CREDENTIALS_FILE",
            "/vault/secrets/kafka.json",
        )
    )

    return Consumer(
        {
            "bootstrap.servers": os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS",
                "finops-kafka-kafka-bootstrap.kafka.svc.cluster.local:9092",
            ),
            "group.id": "finops-analytics",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "security.protocol": "SASL_PLAINTEXT",
            "sasl.mechanism": "SCRAM-SHA-512",
            "sasl.username": username,
            "sasl.password": password,
        }
    )


def process_event(conn, event: dict) -> bool:
    event_id = event.get("event_id")

    if not event_id:
        raise ValueError("Kafka event has no event_id")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO processed_kafka_events (event_id)
            VALUES (%s)
            ON CONFLICT (event_id) DO NOTHING
            RETURNING event_id
            """,
            (event_id,),
        )

        inserted = cur.fetchone()

    if inserted is None:
        logger.info("Duplicate ignored event_id=%s", event_id)
        return False

    logger.info(
        "Processed event_id=%s type=%s transaction_id=%s user_id=%s amount=%s",
        event_id,
        event.get("event_type"),
        event.get("transaction_id"),
        event.get("user_id"),
        event.get("amount"),
    )

    return True


def main():
    consumer = get_consumer()
    consumer.subscribe(["transactions"])

    logger.info("Consumer started group=finops-analytics")

    try:
        while running:
            msg = consumer.poll(1.0)

            if msg is None:
                continue

            if msg.error():
                raise KafkaException(msg.error())

            try:
                event = json.loads(msg.value().decode("utf-8"))

                with get_db_connection() as conn:
                    process_event(conn, event)
                    conn.commit()

                consumer.commit(
                    message=msg,
                    asynchronous=False,
                )

            except Exception:
                logger.exception(
                    "Event processing failed topic=%s partition=%s offset=%s",
                    msg.topic(),
                    msg.partition(),
                    msg.offset(),
                )

    finally:
        consumer.close()
        logger.info("Consumer stopped")


if __name__ == "__main__":
    main()

