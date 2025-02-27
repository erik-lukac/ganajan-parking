# webhooks.py
from flask import Flask, request, jsonify
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
import psycopg2
from psycopg2.extras import execute_values
import logging
import sys
import json
import csv
import os

from dotenv import load_dotenv
load_dotenv()

app: Flask = Flask(__name__)

# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------
LOG_INCOMING_DATA: bool = False           # Log full incoming JSON data if needed.
DEBUG_CSV: bool = False                   # Enable/disable CSV logging for raw webhook data.
CSV_FILE_PATH: str = "/app/backend/webhook_debug.csv"  # CSV file path

DB_SETTINGS: Dict[str, Any] = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "flow"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "")
}
POSTGRES_TABLE: str = os.getenv("DB_TABLE", "parking")

# TIMESTAMP_MODE determines how we log the source timestamp:
#   "vehicle" - use each vehicle's "Trajectory end" for logging reference.
#   "top"     - use the top-level "data_end_timestamp" for logging reference.
#   "system"  - ignore webhook timestamps and log as "SYSTEM".
# The actual DB insertion always uses the current system UTC timestamp.
TIMESTAMP_MODE: str = os.getenv("TIMESTAMP_MODE", "system").lower()

# In-memory storage for logged IDs to avoid duplicate processing.
LOGGED_IDS: Dict[str, set] = {
    "ganajan_car_in": set(),
    "ganajan_car_out": set(),
    "ganajan_bike_in": set(),
    "ganajan_bike_out": set(),
}

# ---------------------------------------------------------------------
# LOGGING CONFIGURATION
# ---------------------------------------------------------------------
def setup_logging() -> None:
    """Configure logging for the application and Werkzeug."""
    log_format: str = "%(asctime)s [%(prefix)-8s] %(message)s"
    logging.basicConfig(
        level=logging.INFO,  # Use INFO level to reduce verbosity.
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    # Customize Werkzeug logs.
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_handler = logging.StreamHandler(sys.stdout)
    werkzeug_formatter = logging.Formatter(
        fmt='%(asctime)s [REQ_LOG ] "%(message)s"',
        datefmt="%d%b%y %H:%M"
    )
    werkzeug_handler.setFormatter(werkzeug_formatter)
    werkzeug_logger.handlers = [werkzeug_handler]
    werkzeug_logger.propagate = False

    # Ensure the root logger uses our custom formatter.
    if not logging.getLogger().handlers:
        default_handler = logging.StreamHandler(sys.stdout)
        default_handler.setFormatter(ShortTimestampFormatter("%(asctime)s [%(prefix)-8s] %(message)s"))
        logging.getLogger().addHandler(default_handler)
    else:
        logging.getLogger().handlers[0].setFormatter(
            ShortTimestampFormatter("%(asctime)s [%(prefix)-8s] %(message)s")
        )

    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

class ShortTimestampFormatter(logging.Formatter):
    """Custom logging formatter with a shortened timestamp."""
    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%d%b%y %H:%M")

setup_logging()

def log_with_prefix(level: int, prefix: str, message: str) -> None:
    """Log a message with a given prefix using f-string formatting."""
    extra = {'prefix': prefix}
    logging.log(level, f"{message}", extra=extra)

class PrefixFilter(logging.Filter):
    """Ensure every log record has a prefix."""
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'prefix'):
            record.prefix = "GENERAL "
        return True

logging.getLogger().addFilter(PrefixFilter())

# ---------------------------------------------------------------------
# CSV DEBUG LOGGING
# ---------------------------------------------------------------------
def ensure_csv_file_exists() -> None:
    """Ensure the CSV file exists, creating it with a header if necessary."""
    if not os.path.exists(CSV_FILE_PATH):
        try:
            os.makedirs(os.path.dirname(CSV_FILE_PATH), exist_ok=True)
            with open(CSV_FILE_PATH, mode="w", newline="") as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(["webhook", "raw_json"])
            log_with_prefix(logging.INFO, "CSV_LOG", f"CSV file created at {CSV_FILE_PATH}")
        except Exception as e:
            log_with_prefix(logging.ERROR, "CSV_LOG", f"Failed to create CSV file: {e}")

def write_json_to_csv(webhook_uri: str, raw_json: Dict[str, Any]) -> None:
    """Write raw JSON payload to a CSV file if debugging is enabled."""
    if not DEBUG_CSV:
        return
    ensure_csv_file_exists()
    try:
        with open(CSV_FILE_PATH, mode="a", newline="") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow([webhook_uri, json.dumps(raw_json)])
        log_with_prefix(logging.INFO, "CSV_LOG", f"Raw JSON written to {CSV_FILE_PATH}")
    except Exception as e:
        log_with_prefix(logging.ERROR, "CSV_LOG", f"Failed to write JSON to CSV: {e}")

# ---------------------------------------------------------------------
# DATABASE FUNCTIONS
# ---------------------------------------------------------------------
def get_db_connection() -> psycopg2.extensions.connection:
    """Establish a connection to the PostgreSQL database."""
    return psycopg2.connect(**DB_SETTINGS)

def insert_data_to_db(records: List[Tuple[str, str, str, str, datetime, str, str, str]]) -> None:
    """
    Insert records into the PostgreSQL database.
    
    Each record is:
      (insertion_id, license_plate, category, color, timestamp, gate, zone, description)
    """
    query: str = f"""
    INSERT INTO {POSTGRES_TABLE}
    (insertion_id, license_plate, category, color, timestamp, gate, zone, description)
    VALUES %s
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, query, records)
                conn.commit()
        log_with_prefix(logging.INFO, "DB_HAND", "Data inserted successfully.")
    except Exception as e:
        log_with_prefix(logging.ERROR, "DB_HAND", f"Database insertion failed: {e}")

# ---------------------------------------------------------------------
# TIMESTAMP PROCESSING (for logging/reference only)
# ---------------------------------------------------------------------
def parse_timestamp(timestamp_ms: Optional[str]) -> Optional[datetime]:
    """
    Convert a millisecond epoch string to a UTC datetime.
    
    Returns None if parsing fails.
    (This is used only for logging or debugging; the DB always gets the system time.)
    """
    try:
        parsed_time: datetime = datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=timezone.utc)
        return parsed_time
    except (ValueError, TypeError) as e:
        log_with_prefix(logging.ERROR, "TIMESTMP", f"Timestamp parsing error: {e}")
        return None

# ---------------------------------------------------------------------
# WEBHOOK DATA PROCESSING
# ---------------------------------------------------------------------
def validate_webhook_data(data: Dict[str, Any], webhook_uri: str) -> Optional[Dict[str, Any]]:
    """
    Validate the incoming webhook JSON data structure.
    Must have data['data']['data'] for the vehicle rows.
    """
    try:
        if 'data' not in data or 'data' not in data['data']:
            raise ValueError("Missing 'data' key in the incoming JSON data")
        return data
    except Exception as e:
        log_with_prefix(logging.ERROR, "DATA_VAL", f"{webhook_uri} - Data validation failed: {e}")
        return None

def process_new_entries(
    webhook_data: Dict[str, Any],
    webhook_uri: str,
    webhook_name: str
) -> Tuple[List[Tuple[str, str, str, str, datetime, str, str, str]], List[str]]:
    """
    Process the vehicle rows and prepare them for DB insertion.
    
    Returns:
      - A list of record tuples for DB insertion.
      - A list of log strings with insertion_id and timestamps.
      
    The actual timestamp inserted into the DB is always generated as the current system UTC time.
    TIMESTAMP_MODE only affects the "source" string shown in logs.
    """
    new_entries: List[Tuple[str, str, str, str, datetime, str, str, str]] = []
    inserted_ids_with_timestamps: List[str] = []

    headers: List[str] = webhook_data['data'].get('header', [])
    rows: List[List[str]] = webhook_data['data'].get('data', [])

    cube_id: str = webhook_data.get('cube_id', 'N/A')
    name: str = webhook_data.get('name', webhook_name)

    for row in rows:
        vehicle: Dict[str, str] = dict(zip(headers, row))
        insertion_id: str = vehicle.get('ID', 'N/A')

        if insertion_id in LOGGED_IDS[webhook_uri]:
            continue

        LOGGED_IDS[webhook_uri].add(insertion_id)
        log_with_prefix(logging.DEBUG, "PROCESS", f"Processing vehicle: {vehicle}")

        # Prepare a "source" timestamp for logging based on TIMESTAMP_MODE.
        if TIMESTAMP_MODE == "vehicle":
            raw_ts: Optional[str] = vehicle.get('Trajectory end')
            parsed_ts = parse_timestamp(raw_ts)
            source_str: str = parsed_ts.strftime("%d%b %H:%M") if parsed_ts else "INVALID"
        elif TIMESTAMP_MODE == "top":
            top_ts_str: Optional[str] = webhook_data.get("data_end_timestamp")
            parsed_ts = parse_timestamp(top_ts_str)
            source_str: str = parsed_ts.strftime("%d%b %H:%M") if parsed_ts else "INVALID"
        else:
            source_str = "SYSTEM"

        # Always use the current system UTC time for DB insertion.
        db_timestamp: datetime = datetime.now(timezone.utc)
        formatted_db_ts: str = db_timestamp.strftime("%d%b %H:%M")

        license_plate: str = vehicle.get('License plate', '-')
        category: str = vehicle.get('Category', 'N/A')
        color: str = vehicle.get('Color', 'N/A')
        gate: str = webhook_uri
        zone: str = cube_id
        description: str = name

        new_entries.append((
            insertion_id,
            license_plate,
            category,
            color,
            db_timestamp,   # Always system UTC timestamp.
            gate,
            zone,
            description
        ))
        inserted_ids_with_timestamps.append(f"{insertion_id} {formatted_db_ts} (SRC={source_str})")

    return new_entries, inserted_ids_with_timestamps

def insert_new_entries(new_entries: List[Tuple[str, str, str, str, datetime, str, str, str]]) -> None:
    """Insert new vehicle entries into the database if any exist."""
    if new_entries:
        insert_data_to_db(new_entries)

def log_filtered_data(webhook_name: str, webhook_uri: str, data: Dict[str, Any]) -> None:
    """
    Validate and process the webhook data, logging distinct phases:
      1. Webhook Reception
      2. Parsing/Preparation
      3. DB Insertion
    """
    log_with_prefix(logging.INFO, "WEBHOOK", f"==== Received webhook: {webhook_uri} ====")
    webhook_data: Optional[Dict[str, Any]] = validate_webhook_data(data, webhook_uri)
    if not webhook_data:
        return

    log_with_prefix(logging.INFO, "PARSING", "---- Parsing Data ----")
    new_entries, inserted_ids = process_new_entries(webhook_data, webhook_uri, webhook_name)
    log_with_prefix(logging.INFO, "PARSING", "---- Parsing Data Completed ----")

    insert_new_entries(new_entries)
    log_with_prefix(logging.INFO, "DB", "==== Insertion into DB Completed ====")

    total_vehicles: int = len(webhook_data.get('data', {}).get('data', []))
    existing_count: int = total_vehicles - len(new_entries)
    log_with_prefix(
        logging.INFO,
        "SUMMARY",
        f"{webhook_uri} - Total Vehicles: {total_vehicles}, New: {len(new_entries)}, "
        f"Existing: {existing_count}. Inserted IDs: {json.dumps(inserted_ids)}"
    )

# ---------------------------------------------------------------------
# WEBHOOK ENDPOINTS
# ---------------------------------------------------------------------
import pprint

@app.route('/webhooks/ganajan_bike_in', methods=['POST'])
def ganajan_bike_in() -> Any:
    """Endpoint to process 'bike_in' webhooks."""
    data: Optional[Dict[str, Any]] = request.get_json()
    if data is None:
        log_with_prefix(logging.ERROR, "WEBHOOK", "No JSON data received")
        return jsonify({"status": "error", "message": "No JSON data received"}), 400

    vehicles_count: int = len(data.get('data', {}).get('data', []))
    log_with_prefix(logging.INFO, "WEBHOOK", f"==== Received webhook: ganajan_bike_in with {vehicles_count} vehicles ====")

    if LOG_INCOMING_DATA:
        log_with_prefix(logging.INFO, "WEBHOOK", f"Incoming data:\n{pprint.pformat(data)}")

    write_json_to_csv("ganajan_bike_in", data)
    log_filtered_data("Bike In", "ganajan_bike_in", data)
    return jsonify({"status": "bike_in_received"}), 200

@app.route('/webhooks/ganajan_car_in', methods=['POST'])
def ganajan_car_in() -> Any:
    """Endpoint to process 'car_in' webhooks."""
    data: Optional[Dict[str, Any]] = request.get_json()
    if data is None:
        log_with_prefix(logging.ERROR, "WEBHOOK", "No JSON data received")
        return jsonify({"status": "error", "message": "No JSON data received"}), 400

    vehicles_count: int = len(data.get('data', {}).get('data', []))
    log_with_prefix(logging.INFO, "WEBHOOK", f"==== Received webhook: ganajan_car_in with {vehicles_count} vehicles ====")

    write_json_to_csv("ganajan_car_in", data)
    log_filtered_data("Car In", "ganajan_car_in", data)
    return jsonify({"status": "car_in_received"}), 200

@app.route('/webhooks/ganajan_car_out', methods=['POST'])
def ganajan_car_out() -> Any:
    """Endpoint to process 'car_out' webhooks."""
    data: Optional[Dict[str, Any]] = request.get_json()
    if data is None:
        log_with_prefix(logging.ERROR, "WEBHOOK", "No JSON data received")
        return jsonify({"status": "error", "message": "No JSON data received"}), 400

    vehicles_count: int = len(data.get('data', {}).get('data', []))
    log_with_prefix(logging.INFO, "WEBHOOK", f"==== Received webhook: ganajan_car_out with {vehicles_count} vehicles ====")

    write_json_to_csv("ganajan_car_out", data)
    log_filtered_data("Car Out", "ganajan_car_out", data)
    return jsonify({"status": "car_out_received"}), 200

@app.route('/webhooks/ganajan_bike_out', methods=['POST'])
def ganajan_bike_out() -> Any:
    """Endpoint to process 'bike_out' webhooks."""
    data: Optional[Dict[str, Any]] = request.get_json()
    if data is None:
        log_with_prefix(logging.ERROR, "WEBHOOK", "No JSON data received")
        return jsonify({"status": "error", "message": "No JSON data received"}), 400

    vehicles_count: int = len(data.get('data', {}).get('data', []))
    log_with_prefix(logging.INFO, "WEBHOOK", f"==== Received webhook: ganajan_bike_out with {vehicles_count} vehicles ====")

    write_json_to_csv("ganajan_bike_out", data)
    log_filtered_data("Bike Out", "ganajan_bike_out", data)
    return jsonify({"status": "bike_out_received"}), 200

# ---------------------------------------------------------------------
# MAIN ENTRYPOINT
# ---------------------------------------------------------------------
if __name__ == '__main__':
    ensure_csv_file_exists()  # Ensure the CSV file is created if needed.
    log_with_prefix(logging.INFO, "STARTUP", "Flask app starting on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
