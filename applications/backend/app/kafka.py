import json
import os
import uuid
from pathlib import Path

from confluent_kafka import Producer


_producer = None


def _load_kafka_credentials() -> tuple[str, str]:
    credentials_file = os.getenv(
        "KAFKA_CREDENTIALS_FILE",
        "/vault/secrets/kafka.json",
    )

    try:
        credentials = json.loads(Path(credentials_file).read_text())
        username = credentials["username"]
        password = credentials["password"]

        if not all(isinstance(value, str) and value for value in (username, password)):
            raise ValueError()

        return username, password

    except (OSError, ValueError, KeyError, TypeError):
        raise RuntimeError("Kafka credentials are unavailable") from None


def get_producer() -> Producer:
    global _producer

    if _producer is not None:
        return _producer

    username, password = _load_kafka_credentials()

    _producer = Producer(
        {
            "bootstrap.servers": os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS",
                "finops-kafka-kafka-bootstrap.kafka.svc.cluster.local:9092",
            ),
            "security.protocol": "SASL_PLAINTEXT",
            "sasl.mechanism": "SCRAM-SHA-512",
            "sasl.username": username,
            "sasl.password": password,

            "acks": "all",
            "enable.idempotence": True,
            "retries": 10,
        }
    )

    return _producer


def publish_transaction_created(transaction: dict) -> None:
    producer = get_producer()

    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "transaction.created",
        "transaction_id": transaction["id"],
        "user_id": transaction["user_id"],
        "category_id": transaction["category_id"],
        "amount": transaction["amount"],
        "description": transaction["description"],
        "occurred_at": transaction["occurred_at"].isoformat(),
        "created_at": transaction["created_at"].isoformat(),
    }

    producer.produce(
        topic="transactions",
        key=str(transaction["user_id"]),
        value=json.dumps(event).encode(),
    )

    producer.poll(0)
