from flask import Flask, request, jsonify
from datetime import datetime, timezone
from typing import List, Optional
import psycopg2
from psycopg2.extras import execute_values
import logging
import sys
import json
import csv
import os

app = Flask(__name__)

# SETTINGS
# All configuration settings are grouped together under this section.

# Toggle to enable or disable logging of full incoming data
LOG_INCOMING_DATA = False  # Set to True to log incoming JSON data

# CSV EXPORT OF RAW WEBHOOKS FOR DEBUGGING
DEBUG_CSV = False  # Enable or disable raw JSON logging to CSV
CSV_FILE_PATH = "/app/backend/webhook_debug.csv"  # Path to the CSV file, ensuring it's in the backend folder

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
LOGGED_IDS = {
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
    if not os.path.exists(CSV_FILE_PATH):
        try:
            os.makedirs(os.path.dirname(CSV_FILE_PATH), exist_ok=True)
            with open(CSV_FILE_PATH, mode="w", newline="") as csvfile:
                csv_writer = csv.writer(csvfile)
                # Write header row
                csv_writer.writerow(["webhook", "raw_json"])
            log_with_prefix(logging.INFO, "CSV_LOG ", f"CSV file created at {CSV_FILE_PATH}")
        except Exception as e:
            log_with_prefix(logging.ERROR, "CSV_LOG ", f"Failed to create CSV file: {e}")

def write_json_to_csv(webhook_uri, raw_json):
    """Write raw JSON payload to a CSV file."""
    if not DEBUG_CSV:
        return

    ensure_csv_file_exists()  # Ensure file exists before writing

    try:
        with open(CSV_FILE_PATH, mode="a", newline="") as csvfile:
            csv_writer = csv.writer(csvfile)
            # Write one line per webhook: webhook name and raw JSON as a string
            csv_writer.writerow([webhook_uri, json.dumps(raw_json)])
        log_with_prefix(logging.INFO, "CSV_LOG ", f"Raw JSON written to {CSV_FILE_PATH}")
    except Exception as e:
        log_with_prefix(logging.ERROR, "CSV_LOG ", f"Failed to write JSON to CSV: {e}")

def get_db_connection():
    """Establish a connection to the PostgreSQL database."""
    return psycopg2.connect(**DB_SETTINGS)

def parse_timestamp(timestamp_ms: Optional[str]) -> datetime:
    """Convert timestamp from milliseconds to a datetime object with UTC timezone."""
    try:
        log_with_prefix(logging.DEBUG, "DEBUG   ", f"Raw timestamp_ms: {timestamp_ms}")
        # Convert milliseconds to seconds and then to a datetime object
        parsed_time = datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=timezone.utc)
        log_with_prefix(logging.DEBUG, "DEBUG   ", f"Parsed timestamp: {parsed_time}")
        return parsed_time
    except (ValueError, TypeError) as e:
        log_with_prefix(logging.ERROR, "DEBUG   ", f"Timestamp parsing error: {e}")
        # Returning None indicates a failed conversion; the caller can handle this.
        return None

def insert_data_to_db(records: List[tuple]):
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

def log_filtered_data(webhook_name: str, webhook_uri: str, data: dict):
    """Process and store new vehicle data from the webhook."""
    webhook_data = validate_webhook_data(data, webhook_uri)
    if not webhook_data:
        return

    new_entries, inserted_ids = process_new_entries(webhook_data, webhook_uri, webhook_name)
    insert_new_entries(new_entries)

    # Log expanded data
    total_vehicles = len(webhook_data.get('data', {}).get('data', []))
    existing_count = total_vehicles - len(new_entries)
    log_with_prefix(
        logging.DEBUG,
        "DATA_PRO",
        f"{webhook_uri} - Total Vehicles: {total_vehicles}, New: {len(new_entries)}, Existing: {existing_count}. Inserted IDs: {json.dumps(inserted_ids)}"
    )

def validate_webhook_data(data: dict, webhook_uri: str) -> Optional[dict]:
    """Validate and parse incoming webhook data."""
    try:
        if 'data' not in data or 'data' not in data['data']:
            raise ValueError("Missing 'data' key in the incoming JSON data")
        return data
    except Exception as e:
        log_with_prefix(logging.ERROR, "DATA_VAL", f"{webhook_uri} - Data validation failed: {e}")
        return None

def process_new_entries(webhook_data: dict, webhook_uri: str, webhook_name: str) -> (List[tuple], List[str]):
    """Process new vehicle entries and prepare them for database insertion."""
    new_entries = []
    inserted_ids_with_timestamps = []
    cube_id = webhook_data.get('cube_id', 'N/A')
    name = webhook_data.get('name', webhook_name)

    headers = webhook_data['data'].get('header', [])
    rows = webhook_data['data'].get('data', [])

    for row in rows:
        vehicle = dict(zip(headers, row))
        insertion_id = vehicle.get('ID', 'N/A')

        if insertion_id not in LOGGED_IDS[webhook_uri]:
            LOGGED_IDS[webhook_uri].add(insertion_id)

            # Debug: Log raw vehicle data
            log_with_prefix(logging.DEBUG, "DEBUG   ", f"Processing vehicle: {vehicle}")

            license_plate = vehicle.get('License plate', '-')
            category = vehicle.get('Category', 'N/A')
            color = vehicle.get('Color', 'N/A')
            timestamp_ms = vehicle.get('Trajectory end', None)

            # Parse and verify the timestamp
            timestamp = parse_timestamp(timestamp_ms)
            if not timestamp:
                continue  # Skip this entry if the timestamp is invalid

            # Format the parsed timestamp as 'ddMMM HH:MM'
            formatted_timestamp = timestamp.strftime("%d%b %H:%M")

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

            # Append the formatted timestamp to the ID for logging
            inserted_ids_with_timestamps.append(f"{insertion_id} {formatted_timestamp}")

    return new_entries, inserted_ids_with_timestamps

def insert_new_entries(new_entries: List[tuple]):
    """Insert new entries into the database if any."""
    if new_entries:
        insert_data_to_db(new_entries)

# Webhook endpoints

import pprint  # Import pprint for pretty-printing JSON data

@app.route('/webhooks/ganajan_bike_in', methods=['POST'])
def ganajan_bike_in():
    data = request.get_json()
    if data is None:
        log_with_prefix(logging.ERROR, "WEBHOOK ", "No JSON data received")
        return jsonify({"status": "error", "message": "No JSON data received"}), 400

    vehicles_count = len(data.get('data', {}).get('data', []))
    log_with_prefix(logging.DEBUG, "WEBHOOK ", f"ganajan_bike_in endpoint called with {vehicles_count} vehicles")

    # Log the incoming data only if LOG_INCOMING_DATA is enabled
    if LOG_INCOMING_DATA:
        import pprint
        log_with_prefix(logging.DEBUG, "WEBHOOK ", f"Incoming data:\n{pprint.pformat(data)}")

    write_json_to_csv("ganajan_bike_in", data)  # Write raw JSON to CSV
    log_filtered_data("Bike In", "ganajan_bike_in", data)
    return jsonify({"status": "bike_in_received"}), 200

@app.route('/webhooks/ganajan_car_in', methods=['POST'])
def ganajan_car_in():
    data = request.get_json()
    if data is None:
        log_with_prefix(logging.ERROR, "WEBHOOK ", "No JSON data received")
        return jsonify({"status": "error", "message": "No JSON data received"}), 400

    vehicles_count = len(data.get('data', {}).get('data', []))
    log_with_prefix(logging.DEBUG, "WEBHOOK ", f"ganajan_car_in endpoint called with {vehicles_count} vehicles")

    write_json_to_csv("ganajan_car_in", data)  # Write raw JSON to CSV
    log_filtered_data("Car In", "ganajan_car_in", data)
    return jsonify({"status": "car_in_received"}), 200

@app.route('/webhooks/ganajan_car_out', methods=['POST'])
def ganajan_car_out():
    data = request.get_json()
    if data is None:
        log_with_prefix(logging.ERROR, "WEBHOOK ", "No JSON data received")
        return jsonify({"status": "error", "message": "No JSON data received"}), 400

    vehicles_count = len(data.get('data', {}).get('data', []))
    log_with_prefix(logging.DEBUG, "WEBHOOK ", f"ganajan_car_out endpoint called with {vehicles_count} vehicles")

    write_json_to_csv("ganajan_car_out", data)  # Write raw JSON to CSV
    log_filtered_data("Car Out", "ganajan_car_out", data)
    return jsonify({"status": "car_out_received"}), 200

@app.route('/webhooks/ganajan_bike_out', methods=['POST'])
def ganajan_bike_out():
    data = request.get_json()
    if data is None:
        log_with_prefix(logging.ERROR, "WEBHOOK ", "No JSON data received")
        return jsonify({"status": "error", "message": "No JSON data received"}), 400

    vehicles_count = len(data.get('data', {}).get('data', []))
    log_with_prefix(logging.DEBUG, "WEBHOOK ", f"ganajan_bike_out endpoint called with {vehicles_count} vehicles")

    write_json_to_csv("ganajan_bike_out", data)  # Write raw JSON to CSV
    log_filtered_data("Bike Out", "ganajan_bike_out", data)
    return jsonify({"status": "bike_out_received"}), 200

if __name__ == '__main__':
    ensure_csv_file_exists()  # Ensure CSV file exists at startup
    log_with_prefix(logging.INFO, "STARTUP ", "Flask app starting on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)