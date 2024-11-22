from flask import Flask, request, jsonify
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import execute_values
import logging
import sys
import json
import csv
import os

app = Flask(__name__)

# CSV EXPORT OF RAW WEBHOOS FOR DEBUGGING
debug_csv = False  # Enable or disable raw JSON logging to CSV
csv_file_path = "/app/backend/webhook_debug.csv"  # Path to the CSV file, ensuring it's in the backend folder

# PostgreSQL settings
DB_SETTINGS = {
    "host": "db",
    "port": 5432,
    "dbname": "flow",
    "user": "postgres",
    "password": "123---321"
}
POSTGRES_TABLE = "parking"

# In-memory storage for logged IDs
logged_ids = {
    "ganajan_car_in": set(),
    "ganajan_car_out": set(),
    "ganajan_bike_in": set(),
    "ganajan_bike_out": set(),
}

# Configure application and Werkzeug logging
def setup_logging():
    log_format = "%(asctime)s [%(prefix)-8s] %(message)s"
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Customize Werkzeug logs to only show request details
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_handler = logging.StreamHandler(sys.stdout)

    # Custom log formatter for Werkzeug to exclude IP and timestamp
    werkzeug_formatter = logging.Formatter(
        fmt='%(asctime)s [REQ_LOG ] "%(message)s"',
        datefmt="%d%b%y %H:%M"
    )
    werkzeug_handler.setFormatter(werkzeug_formatter)
    werkzeug_logger.handlers = [werkzeug_handler]
    werkzeug_logger.propagate = False

    # Ensure there is at least one handler in the root logger
    if not logging.getLogger().handlers:
        default_handler = logging.StreamHandler(sys.stdout)
        default_handler.setFormatter(ShortTimestampFormatter("%(asctime)s [%(prefix)-8s] %(message)s"))
        logging.getLogger().addHandler(default_handler)
    else:
        # Update the formatter of the first existing handler
        logging.getLogger().handlers[0].setFormatter(ShortTimestampFormatter("%(asctime)s [%(prefix)-8s] %(message)s"))

    # Force stdout to flush immediately
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

# Shortened timestamp formatter
class ShortTimestampFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%d%b%y %H:%M")

setup_logging()

# Utility to log with a specific prefix
def log_with_prefix(level, prefix, message):
    extra = {'prefix': prefix}
    logging.log(level, message, extra=extra)

# Add a custom logging filter to handle prefixes
class PrefixFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'prefix'):
            record.prefix = "GENERAL "  # Default prefix
        return True

logging.getLogger().addFilter(PrefixFilter())

def ensure_csv_file_exists():
    """Ensure the CSV file exists, creating it if necessary."""
    if not os.path.exists(csv_file_path):
        try:
            os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
            with open(csv_file_path, mode="w", newline="") as csvfile:
                csv_writer = csv.writer(csvfile)
                # Write header row
                csv_writer.writerow(["webhook", "raw_json"])
            log_with_prefix(logging.INFO, "CSV_LOG ", f"CSV file created at {csv_file_path}")
        except Exception as e:
            log_with_prefix(logging.ERROR, "CSV_LOG ", f"Failed to create CSV file: {e}")

def write_json_to_csv(webhook_uri, raw_json):
    """Write raw JSON payload to a CSV file."""
    if not debug_csv:
        return

    ensure_csv_file_exists()  # Ensure file exists before writing

    try:
        with open(csv_file_path, mode="a", newline="") as csvfile:
            csv_writer = csv.writer(csvfile)
            # Write one line per webhook: webhook name and raw JSON as a string
            csv_writer.writerow([webhook_uri, json.dumps(raw_json)])
        log_with_prefix(logging.INFO, "CSV_LOG ", f"Raw JSON written to {csv_file_path}")
    except Exception as e:
        log_with_prefix(logging.ERROR, "CSV_LOG ", f"Failed to write JSON to CSV: {e}")

def get_db_connection():
    """Establish a connection to the PostgreSQL database."""
    return psycopg2.connect(**DB_SETTINGS)

def parse_timestamp(timestamp_ms):
    """Convert timestamp from milliseconds to a datetime object with UTC timezone."""
    try:
        return datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(tz=timezone.utc)

def insert_data_to_db(records):
    """Insert records into the PostgreSQL database."""
    query = f"""
    INSERT INTO {POSTGRES_TABLE}
    (insertion_id, license_plate, category, color, timestamp, gate, zone, description)
    VALUES %s
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, query, records)
                conn.commit()
        log_with_prefix(logging.INFO, "DB_HAND ", "Data inserted successfully.")
    except Exception as e:
        log_with_prefix(logging.ERROR, "DB_HAND ", f"Database insertion failed: {e}")

def log_filtered_data(webhook_name, webhook_uri, data):
    """Extract, log, and store only new IDs from the received webhook data."""
    new_count = 0
    already_received_count = 0
    rows = data.get('data', {}).get('data', [])
    headers = data.get('data', {}).get('header', [])
    cube_id = data.get('cube_id', 'N/A')
    name = data.get('name', webhook_name)

    records = [dict(zip(headers, row)) for row in rows if len(row) >= len(headers)]
    new_entries = []
    inserted_ids = []  # Collect inserted IDs for log expansion

    for record in records:
        insertion_id = record.get("ID", "N/A")
        if insertion_id not in logged_ids[webhook_uri]:
            logged_ids[webhook_uri].add(insertion_id)
            license_plate = record.get("License plate", "-")
            category = record.get("Category", "N/A")
            color = record.get("Color", "N/A")
            timestamp_ms = record.get("Trajectory end", None)
            timestamp = parse_timestamp(timestamp_ms)
            gate = webhook_uri
            zone = cube_id
            description = name
            new_entries.append((
                insertion_id,
                license_plate,
                category,
                color,
                timestamp,
                gate,
                zone,
                description
            ))
            inserted_ids.append(insertion_id)
            new_count += 1
        else:
            already_received_count += 1

    if new_entries:
        insert_data_to_db(new_entries)

    # Log expanded data
    log_with_prefix(
        logging.DEBUG,
        "DATA_PRO",
        f"{webhook_uri} - New: {new_count}, Existing: {already_received_count}. Inserted IDs: {json.dumps(inserted_ids)}"
    )

@app.route('/webhooks/ganajan_car_in', methods=['POST'])
def ganajan_car_in():
    log_with_prefix(logging.DEBUG, "WEBHOOK ", "ganajan_car_in endpoint called")
    write_json_to_csv("ganajan_car_in", request.json)  # Write raw JSON to CSV
    log_filtered_data("Car In", "ganajan_car_in", request.json)
    return jsonify({"status": "car_in_received"}), 200

@app.route('/webhooks/ganajan_car_out', methods=['POST'])
def ganajan_car_out():
    log_with_prefix(logging.DEBUG, "WEBHOOK ", "ganajan_car_out endpoint called")
    write_json_to_csv("ganajan_car_out", request.json)  # Write raw JSON to CSV
    log_filtered_data("Car Out", "ganajan_car_out", request.json)
    return jsonify({"status": "car_out_received"}), 200

@app.route('/webhooks/ganajan_bike_in', methods=['POST'])
def ganajan_bike_in():
    log_with_prefix(logging.DEBUG, "WEBHOOK ", "ganajan_bike_in endpoint called")
    write_json_to_csv("ganajan_bike_in", request.json)  # Write raw JSON to CSV
    log_filtered_data("Bike In", "ganajan_bike_in", request.json)
    return jsonify({"status": "bike_in_received"}), 200

@app.route('/webhooks/ganajan_bike_out', methods=['POST'])
def ganajan_bike_out():
    log_with_prefix(logging.DEBUG, "WEBHOOK ", "ganajan_bike_out endpoint called")
    write_json_to_csv("ganajan_bike_out", request.json)  # Write raw JSON to CSV
    log_filtered_data("Bike Out", "ganajan_bike_out", request.json)
    return jsonify({"status": "bike_out_received"}), 200

if __name__ == '__main__':
    ensure_csv_file_exists()  # Ensure CSV file exists at startup
    log_with_prefix(logging.INFO, "STARTUP ", "Flask app starting on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
