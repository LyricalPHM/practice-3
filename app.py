import os
import time
from datetime import datetime

import clickhouse_connect
from flask import Flask

app = Flask(__name__)

db_initialized = False


def get_clickhouse_client(database=None):
    return clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        username=os.getenv("CLICKHOUSE_USER", "flaskuser"),
        password=os.getenv("CLICKHOUSE_PASSWORD", "flaskpassword"),
        database=database or os.getenv("CLICKHOUSE_DB", "default"),
    )


def init_db():
    db_name = os.getenv("CLICKHOUSE_DB", "flaskdb")
    retries = 20

    while retries > 0:
        try:
            default_client = get_clickhouse_client(database="default")
            default_client.command(f"CREATE DATABASE IF NOT EXISTS {db_name}")

            client = get_clickhouse_client(database=db_name)
            client.command(
                """
                CREATE TABLE IF NOT EXISTS visits
                (
                    id UUID DEFAULT generateUUIDv4(),
                    created_at DateTime
                )
                ENGINE = MergeTree
                ORDER BY created_at
                """
            )

            return

        except Exception as error:
            print(f"ClickHouse is not ready yet: {error}")
            retries -= 1
            time.sleep(2)

    raise RuntimeError("ClickHouse is not available")


def ensure_db_initialized():
    global db_initialized

    if not db_initialized:
        init_db()
        db_initialized = True


@app.route("/")
def home():
    ensure_db_initialized()

    db_name = os.getenv("CLICKHOUSE_DB", "flaskdb")
    client = get_clickhouse_client(database=db_name)

    client.insert(
        "visits",
        [[datetime.now()]],
        column_names=["created_at"],
    )

    result = client.query("SELECT count() FROM visits")
    visits_count = result.result_rows[0][0]

    return f"Hello, Docker, ClickHouse and GitHub Actions! Visits count: {visits_count}"


@app.route("/health")
def health():
    return "OK"


if __name__ == "__main__":
    ensure_db_initialized()
    app.run(host="0.0.0.0", port=5000)
