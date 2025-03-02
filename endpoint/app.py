
# app.py
import os
import logging
import traceback
from typing import Any, Optional, Tuple, Dict
from datetime import datetime,timedelta,timezone  # Added import for datetime
import psycopg2.extras
from flask import Flask, request, jsonify, send_file, make_response  # type: ignore

from psycopg2.extras import RealDictCursor, DictCursor
from psycopg2.extensions import connection as Connection  # type: ignore
from dotenv import load_dotenv
from flask_cors import CORS
import math
import logging
import pandas as pd
import csv 
from io import StringIO, BytesIO
from openpyxl import Workbook
import json

load_dotenv()  # Load environment variables from .env file

# Initialize the Flask app
app: Flask = Flask(__name__)

# CORS allowed origins
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:32212",
    "http://localhost:3000",
    "http://35.208.144.223:32212"
]}})

# Set a secret key for session management; use an env variable or generate one
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# Configure logging: log to both stdout and a file.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", mode="a")
    ]
)
app.logger.info("Parking Dashboard App is starting...")

def get_db_connection() -> Connection:
    """
    Establish a connection to the PostgreSQL database using credentials from environment variables.
    
    Returns:
        A psycopg2 connection object.
    """
    try:
        connection: Connection = psycopg2.connect(
            dbname=os.environ.get("DB_NAME", "flow"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD"),
            host=os.environ.get("DB_HOST", "db"),
            port=os.environ.get("DB_PORT", 5432),
            cursor_factory=RealDictCursor
        )
        app.logger.info("Database connection established successfully.")
        return connection
    except Exception as e:
        app.logger.error(f"Database connection error: {e}")
        raise

# ---------------------------------------
# 1. /data Endpoint
# ---------------------------------------
@app.route("/data", methods=["GET"])
def data() -> Any:
    """
    Endpoint to retrieve parking data with optional filters.
    
    Query parameters include:
    - start_date, end_date: Filter by timestamp range.
    - license_prefix: Filter for license_plate starting with the given prefix.
    - categories, colors, gates: Comma-separated values to filter respective fields.
    - search: Search term to match across several fields.
    - page_size, page: Pagination settings.
    """
    try:
        # Retrieve query parameters (all optional)
        start_date: Optional[str] = request.args.get("start_date")
        end_date: Optional[str] = request.args.get("end_date")
        license_prefix: Optional[str] = request.args.get("license_prefix")
        categories: Optional[str] = request.args.get("categories")
        colors: Optional[str] = request.args.get("colors")
        gates: Optional[str] = request.args.get("gates")
        search: Optional[str] = request.args.get("search")
        page_size: int = int(request.args.get("page_size", 10))
        page: int = int(request.args.get("page", 1))
        offset: int = (page - 1) * page_size

        # SQL query with placeholders for safe parameter substitution.
        query: str = """
            SELECT *
            FROM parking
            WHERE
              (timestamp >= COALESCE(%s::timestamptz, timestamp))
              AND (timestamp <= COALESCE(%s::timestamptz, timestamp))
              AND (%s IS NULL OR license_plate ILIKE (%s || '%%'))
              AND (%s IS NULL OR category IN (SELECT UNNEST(string_to_array(%s, ',')) ))
              AND (%s IS NULL OR color IN (SELECT UNNEST(string_to_array(%s, ',')) ))
              AND (%s IS NULL OR gate IN (SELECT UNNEST(string_to_array(%s, ',')) ))
              AND (
                   %s IS NULL OR 
                   license_plate ILIKE ('%%' || %s || '%%') OR
                   category ILIKE ('%%' || %s || '%%') OR
                   color ILIKE ('%%' || %s || '%%') OR
                   gate ILIKE ('%%' || %s || '%%') OR
                   zone ILIKE ('%%' || %s || '%%') OR
                   description ILIKE ('%%' || %s || '%%')
              )
            ORDER BY timestamp DESC
            LIMIT %s
            OFFSET %s;
        """
        # Prepare parameters tuple
        params: Tuple[Any, ...] = (
            start_date, end_date,
            license_prefix, license_prefix,
            categories, categories,
            colors, colors,
            gates, gates,
            search, search, search, search, search, search, search,
            page_size, offset
        )
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error in /data endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load data", "details": f"{e}"}), 500

# ---------------------------------------
# 2. /dashboard/data Endpoint
# ---------------------------------------
@app.route("/dashboard/data", methods=["GET"])
def dashboard_data() -> Any:
    """
    Endpoint to retrieve parking data for the dashboard with a general search.
    
    Query parameters include:
    - search: Search term to match across several fields.
    - page_size, page: Pagination settings.
    """
    try:
        search: Optional[str] = request.args.get("search")
        page_size: int = int(request.args.get("page_size", 10))
        page: int = int(request.args.get("page", 1))
        offset: int = (page - 1) * page_size

        query: str = """
            SELECT *
            FROM parking
            WHERE (
              %s IS NULL OR
              license_plate ILIKE ('%%' || %s || '%%') OR
              category ILIKE ('%%' || %s || '%%') OR
              color ILIKE ('%%' || %s || '%%') OR
              gate ILIKE ('%%' || %s || '%%') OR
              zone ILIKE ('%%' || %s || '%%') OR
              description ILIKE ('%%' || %s || '%%')
            )
            AND category != 'pedestrian'
            ORDER BY timestamp DESC
            LIMIT %s
            OFFSET %s;
        """
        params: Tuple[Any, ...] = (
            search, search, search, search, search, search, search,
            page_size, offset
        )
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error in /dashboard/data endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load dashboard data", "details": f"{e}"}), 500

# Alias route so both /dashboard/data and /dashboard-data work
@app.route("/dashboard-data", methods=["GET"])
def dashboard_data_alias() -> Any:
    """
    Alias for the dashboard data endpoint.
    """
    return dashboard_data()

# ---------------------------------------
# 3. /stats/category-stats Endpoint
# ---------------------------------------
@app.route("/stats/category-stats", methods=["GET"])
def category_stats() -> Any:
    """
    Endpoint to retrieve statistics of parking categories over a specified time range.
    
    Query parameters:
    - start_date, end_date: Required timestamp range.
    """
    try:
        start_date: Optional[str] = request.args.get("start_date")
        end_date: Optional[str] = request.args.get("end_date")
        if not start_date or not end_date:
            return jsonify({"error": "start_date and end_date parameters are required"}), 400

        query: str = """
            SELECT category, COUNT(*) AS count
            FROM parking
            WHERE
              timestamp >= %s::timestamptz
              AND timestamp <= %s::timestamptz
            GROUP BY category;
        """
        params: Tuple[Any, ...] = (start_date, end_date)
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error in /stats/category-stats endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load category stats", "details": f"{e}"}), 500

# ---------------------------------------
# 4. /stats/today-entries Endpoint
# ---------------------------------------
@app.route("/stats/today-entries", methods=["GET"])
def today_entries() -> Any:
    """
    Endpoint to retrieve the count of today's parking entries.
    """
    try:
        query: str = """
            SELECT COUNT(*) AS count
            FROM parking
            WHERE DATE(timestamp) = CURRENT_DATE
              AND gate ILIKE '%%_in'
              AND category != 'pedestrian';
        """
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in /stats/today-entries endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load today's entries", "details": f"{e}"}), 500

# ---------------------------------------
# 5. /stats/recent-entries Endpoint
# ---------------------------------------
@app.route("/stats/recent-entries", methods=["GET"])
def recent_entries() -> Any:
    """
    Endpoint to retrieve the count of parking entries in the last 10 minutes.
    """
    try:
        query: str = """
            SELECT COUNT(*) AS count
            FROM parking
            WHERE timestamp >= NOW() - INTERVAL '10 minutes'
              AND gate ILIKE '%%_in';
        """
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in /stats/recent-entries endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load recent entries", "details": f"{e}"}), 500

# ---------------------------------------
# 6. /export Endpoint
# ---------------------------------------
@app.route("/export", methods=["GET"])
def export() -> Any:
    """
    Endpoint to export parking data with optional filters as a CSV or XLSX file (excluding pedestrians).

    Query parameters:
    - start_date, end_date, license_prefix, categories, colors, gates, search, file_format (csv or xlsx).
    """
    try:
        # Extract query parameters
        start_date: Optional[str] = request.args.get("start_date")
        end_date: Optional[str] = request.args.get("end_date")
        license_prefix: Optional[str] = request.args.get("license_prefix")
        categories: Optional[str] = request.args.get("categories")
        colors: Optional[str] = request.args.get("colors")
        gates: Optional[str] = request.args.get("gates")
        search: Optional[str] = request.args.get("search")
        file_format: str = request.args.get("file_format", "csv").lower()  # Default to csv

        # Validate file_format
        if file_format not in ["csv", "xlsx"]:
            return jsonify({"error": "Invalid file format. Use 'csv' or 'xlsx'."}), 400

        # SQL query with pedestrian exclusion
        query: str = """
            SELECT *
            FROM parking
            WHERE
              category != 'pedestrian'
              AND (timestamp >= COALESCE(%s::timestamptz, timestamp))
              AND (timestamp <= COALESCE(%s::timestamptz, timestamp))
              AND (%s IS NULL OR license_plate ILIKE (%s || '%%'))
              AND (%s IS NULL OR category IN (SELECT UNNEST(string_to_array(%s, ','))))
              AND (%s IS NULL OR color IN (SELECT UNNEST(string_to_array(%s, ','))))
              AND (%s IS NULL OR gate IN (SELECT UNNEST(string_to_array(%s, ','))))
              AND (
                   %s IS NULL OR
                   license_plate ILIKE ('%%' || %s || '%%') OR
                   category ILIKE ('%%' || %s || '%%') OR
                   color ILIKE ('%%' || %s || '%%') OR
                   gate ILIKE ('%%' || %s || '%%') OR
                   zone ILIKE ('%%' || %s || '%%') OR
                   description ILIKE ('%%' || %s || '%%')
              )
            ORDER BY timestamp DESC;
        """
        params: Tuple[Any, ...] = (
            start_date, end_date,
            license_prefix, license_prefix,
            categories, categories,
            colors, colors,
            gates, gates,
            search, search, search, search, search, search, search
        )

        # Fetch data from the database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()

        # Define column order
        fieldnames = [
            "timestamp", "license_plate", "category", "color",
            "gate", "zone", "description", "insertion_id"
        ]

        # Handle CSV export
        if file_format == "csv":
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow(row)
            output.seek(0)

            response = make_response(output.getvalue())
            response.headers["Content-Disposition"] = "attachment; filename=parking_data.csv"
            response.headers["Content-Type"] = "text/csv"
            return response

        # Handle XLSX export
        elif file_format == "xlsx":
            wb = Workbook()
            ws = wb.active
            ws.title = "Parking Data"

            # Write headers
            ws.append(fieldnames)

            # Write data rows
            for row in results:
                # Convert row dict to list in fieldnames order, handling datetime objects
                row_data = []
                for field in fieldnames:
                    value = row.get(field)
                    if isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    row_data.append(value)
                ws.append(row_data)

            # Save to BytesIO
            output = BytesIO()
            wb.save(output)
            output.seek(0)

            response = make_response(output.getvalue())
            response.headers["Content-Disposition"] = "attachment; filename=parking_data.xlsx"
            response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return response

    except Exception as e:
        app.logger.error(f"Error in /export endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not export data", "details": f"{e}"}), 500

# ---------------------------------------
# 7. /stats/trends Endpoint
# ---------------------------------------
@app.route("/stats/trends", methods=["GET"])
def stats_trends() -> Any:
    """
    Endpoint to retrieve trends including today's and yesterday's entries and exits.
    """
    try:
        conn: Connection = get_db_connection()
        cur = conn.cursor()

        # Today's entries
        cur.execute("""
            SELECT COUNT(*) AS count
            FROM parking
            WHERE DATE(timestamp) = CURRENT_DATE
              AND gate ILIKE '%%_in';
        """)
        todays_entries = cur.fetchone()

        # Today's exits
        cur.execute("""
            SELECT COUNT(*) AS count
            FROM parking
            WHERE DATE(timestamp) = CURRENT_DATE
              AND gate ILIKE '%%_out';
        """)
        todays_exits = cur.fetchone()

        # Yesterday's entries
        cur.execute("""
            SELECT COUNT(*) AS count
            FROM parking
            WHERE DATE(timestamp) = CURRENT_DATE - INTERVAL '1 day'
              AND gate ILIKE '%%_in';
        """)
        yesterdays_entries = cur.fetchone()

        # Yesterday's exits
        cur.execute("""
            SELECT COUNT(*) AS count
            FROM parking
            WHERE DATE(timestamp) = CURRENT_DATE - INTERVAL '1 day'
              AND gate ILIKE '%%_out';
        """)
        yesterdays_exits = cur.fetchone()

        cur.close()
        conn.close()

        return jsonify({
            "todays_entries": todays_entries,
            "todays_exits": todays_exits,
            "yesterdays_entries": yesterdays_entries,
            "yesterdays_exits": yesterdays_exits
        })
    except Exception as e:
        app.logger.error(f"Error in /stats/trends endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load trends", "details": f"{e}"}), 500
# ---------------------------------------
# 8. /stats/duration-stats Endpoint
# ---------------------------------------
@app.route("/stats/duration-stats", methods=["GET"])
def duration_stats() -> Any:
    """
    Endpoint to retrieve duration statistics for parking entries.
    
    Query parameters:
    - start_time: Required start time for filtering.
    """
    try:
        start_time: Optional[str] = request.args.get("start_time")
        if not start_time:
            return jsonify({"error": "start_time parameter is required"}), 400

        query: str = """
            SELECT
                e.insertion_id AS entry_id,
                e.license_plate,
                e.timestamp AS entry_timestamp,
                x.timestamp AS exit_timestamp,
                EXTRACT(EPOCH FROM (x.timestamp - e.timestamp)) AS duration
            FROM parking e
            LEFT JOIN LATERAL (
                SELECT *
                FROM parking x
                WHERE x.license_plate = e.license_plate
                  AND x.gate ILIKE '%%_out'
                  AND x.timestamp > e.timestamp
                ORDER BY x.timestamp ASC
                LIMIT 1
            ) x ON true
            WHERE e.gate ILIKE '%%_in'
              AND e.timestamp >= %s::timestamptz;
        """
        params: Tuple[Any, ...] = (start_time,)
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error in /stats/duration-stats endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load duration stats", "details": f"{e}"}), 500

# ---------------------------------------
# NEW: /stats/today-exits Endpoint
# ---------------------------------------
@app.route("/stats/today-exits", methods=["GET"])
def today_exits() -> Any:
    """
    Endpoint to retrieve the count of today's parking exits.
    """
    try:
        query: str = """
            SELECT COUNT(*) AS count
            FROM parking
            WHERE DATE(timestamp) = CURRENT_DATE
              AND gate ILIKE '%%_out'
              AND category != 'pedestrian';
        """
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in /stats/today-exits endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load today's exits", "details": f"{e}"}), 500

# ---------------------------------------
# Existing /test Endpoint (unchanged)
# ---------------------------------------
@app.route("/test", methods=["GET"])
def test() -> Any:
    """
    Test endpoint to retrieve the 5 most recent parking entries.
    """
    try:
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM parking ORDER BY timestamp DESC LIMIT 5;")
        test_entries = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(test_entries)
    except Exception as e:
        app.logger.error(f"Error in /test route: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load test entries", "details": f"{e}"}), 500

#---------------------------------------
# testing endpoint for mapping vehicles (/data1)
#---------------------------------------
def parse_timestamp_utc(ts: str) -> datetime:
    """Parse timestamp from 'Sat, 01 Mar 2025 13:02:55 UTC' or 'Fri, 28 Feb 2025 13:46:16 GMT'"""
    app.logger.info(f"Attempting to parse timestamp: '{ts}'")
    formats = [
        "%a, %d %b %Y %H:%M:%S UTC",  # Primary format for database
        "%a, %d %b %Y %H:%M:%S GMT"   # Fallback for older data
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(ts, fmt)
            app.logger.info(f"Successfully parsed with format '{fmt}': {dt}")
            return dt
        except ValueError as e:
            app.logger.info(f"Failed parsing with format '{fmt}': {str(e)}")
            continue
    raise ValueError(f"Invalid timestamp format: {ts}")



@app.route("/data1", methods=["GET"])
def data1():
    """
    Flask endpoint to retrieve parking data with entry/exit mapping.

    Features:
    - Maps vehicle entries (_in) to exits (_out) by license plate (no time limit).
    - Handles timestamp format: 'Sat, 01 Mar 2025 13:02:55 UTC' or 'Fri, 28 Feb 2025 13:46:16 GMT'.
    - Excludes pedestrians and vehicles without license plates.
    - Supports filters: date range, license prefix, categories, colors, gates, search term.
    - Implements pagination.
    - Sorts by most recent entry time.
    - Fetches all data if no date range specified.

    Returns:
    - JSON response with parking data, pagination info, or error details.
    """
    try:
        app.logger.info("Endpoint /data1 accessed")

        # Extract query parameters
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        license_prefix = request.args.get("license_prefix")
        categories = request.args.get("categories") or request.args.get("category")
        colors = request.args.get("colors") or request.args.get("color")
        gates = request.args.get("gates") or request.args.get("gate")
        search = request.args.get("search")
        page_size_str = request.args.get("page_size", "10")
        page_str = request.args.get("page", "1")

        app.logger.info(f"Raw parameters: {request.args}")

        now = datetime.utcnow()

        # Parse dates using the renamed function
        start_date = parse_timestamp_utc(start_date_str) if start_date_str else None
        end_date = parse_timestamp_utc(end_date_str) if end_date_str else None

        # Log parsed timestamps
        app.logger.info(f"Parsed start_date: {start_date}")
        app.logger.info(f"Parsed end_date: {end_date}")

        # Validate date range
        if start_date and end_date and start_date > end_date:
            app.logger.error("Start date is after end date")
            return jsonify({"error": "Invalid date range", "details": "start_date must be before end_date"}), 400

        # Convert to string format for query (use UTC to match database)
        start_date_str = start_date.strftime('%a, %d %b %Y %H:%M:%S UTC') if start_date else None
        end_date_str = end_date.strftime('%a, %d %b %Y %H:%M:%S UTC') if end_date else None

        page_size = int(page_size_str)
        page = int(page_str)
        offset = (page - 1) * page_size

        app.logger.info(f"Processed parameters: start_date={start_date_str}, end_date={end_date_str}, "
                        f"license_prefix={license_prefix}, categories={categories}, colors={colors}, "
                        f"gates={gates}, search={search}, page={page}, page_size={page_size}")

        # Build WHERE clauses for entries
        where_clauses = [
            "gate LIKE '%_in'",
            "category != 'pedestrian'",
            "license_plate != '-'"
        ]

        if start_date_str and end_date_str:
            where_clauses.append(f"timestamp BETWEEN '{start_date_str}' AND '{end_date_str}'")
            app.logger.info(f"Applied date filter: timestamp BETWEEN '{start_date_str}' AND '{end_date_str}'")
        else:
            app.logger.info("No date filter applied; fetching all data")

        if license_prefix:
            where_clauses.append(f"license_plate ILIKE '{license_prefix}%'")
        if categories and categories.lower() != "undefined":
            categories_list = ",".join(f"'{cat.strip()}'" for cat in categories.split(','))
            where_clauses.append(f"category IN ({categories_list})")
        if colors and colors.lower() != "undefined":
            colors_list = ",".join(f"'{col.strip()}'" for cat in categories.split(','))
            where_clauses.append(f"color IN ({colors_list})")
        if gates and colors.lower() != "undefined":
            gates_list = ",".join(f"'{gate.strip()}'" for cat in categories.split(','))
            where_clauses.append(f"gate IN ({gates_list})")
        if search:
            search_pattern = f'%{search}%'
            where_clauses.append(f"""(
                license_plate ILIKE '{search_pattern}' OR
                category ILIKE '{search_pattern}' OR
                color ILIKE '{search_pattern}' OR
                gate ILIKE '{search_pattern}' OR
                zone::TEXT ILIKE '{search_pattern}' OR
                description ILIKE '{search_pattern}'
            )""")

        # Construct the query
        query = f"""
            WITH entries AS (
                SELECT
                    insertion_id,
                    license_plate,
                    category,
                    color,
                    gate AS entry_gate,
                    timestamp AS entry_time,
                    zone,
                    description
                FROM parking
                WHERE {' AND '.join(where_clauses)}
            ),
            exits AS (
                SELECT
                    license_plate,
                    gate AS exit_gate,
                    timestamp AS exit_time
                FROM parking
                WHERE gate LIKE '%_out'
                {f"AND timestamp <= '{end_date_str}'" if end_date_str else ""}
            ),
            matched_exits AS (
                SELECT
                    e.insertion_id,
                    e.license_plate,
                    e.entry_time,
                    MIN(x.exit_time) AS exit_time
                FROM entries e
                LEFT JOIN exits x
                    ON e.license_plate = x.license_plate
                    AND x.exit_time > e.entry_time
                GROUP BY e.insertion_id, e.license_plate, e.entry_time
            )
            SELECT
                e.insertion_id,
                e.license_plate,
                e.category,
                e.color,
                e.entry_gate,
                TO_CHAR(e.entry_time, 'Dy, DD Mon YYYY HH24:MI:SS TZ') AS entry_time,
                COALESCE(x.exit_gate, 'Not Exited') AS exit_gate,
                TO_CHAR(m.exit_time, 'Dy, DD Mon YYYY HH24:MI:SS TZ') AS exit_time,
                e.zone,
                e.description,
                CASE
                    WHEN m.exit_time IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (m.exit_time - e.entry_time))
                    ELSE -1
                END AS duration
            FROM entries e
            LEFT JOIN matched_exits m
                ON e.insertion_id = m.insertion_id
                AND e.license_plate = m.license_plate
                AND e.entry_time = m.entry_time
            LEFT JOIN exits x
                ON m.license_plate = x.license_plate
                AND m.exit_time = x.exit_time
            ORDER BY e.entry_time DESC
            LIMIT {page_size} OFFSET {offset}
        """

        count_query = f"""
            WITH entries AS (
                SELECT insertion_id
                FROM parking
                WHERE {' AND '.join(where_clauses)}
            )
            SELECT COUNT(*) AS total FROM entries
        """

        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                app.logger.info(f"Executing query: {query}")
                cur.execute(query)
                results = cur.fetchall()
                results_list = [dict(row) for row in results]

                app.logger.info(f"Executing count query: {count_query}")
                cur.execute(count_query)
                total_records = cur.fetchone()['total']

            app.logger.info(f"Returning {len(results_list)} records, total={total_records}")
            return jsonify({
                "data": results_list,
                "page": page,
                "page_size": page_size,
                "total_records": total_records,
                "total_pages": math.ceil(total_records / page_size)
            })

        finally:
            conn.close()

    except ValueError as ve:
        app.logger.error(f"Input validation error: {str(ve)}")
        return jsonify({"error": "Invalid input", "details": str(ve)}), 400
    except psycopg2.Error as pe:
        app.logger.error(f"Database error: {str(pe)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Database error", "details": str(pe)}), 500
    except Exception as e:
        app.logger.error(f"Error in /data1 endpoint: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load data", "details": str(e)}), 500


#----------------------------------
#endpoint for Analytics page
#-----------------------------------
def parse_timestamp(timestamp_str):
    """Parse GMT timestamp into a GMT-formatted string."""
    try:
        dt = datetime.strptime(timestamp_str, '%a, %d %b %Y %H:%M:%S GMT')
        return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
    except ValueError:
        raise ValueError(f"Unsupported timestamp format: {timestamp_str}")

@app.route("/stats/enhanced-stats", methods=["GET"])
def get_enhanced_stats():
    try:
        app.logger.info("Endpoint /stats/enhanced-stats accessed")

        # Extract query parameters
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        time_range = request.args.get("time_range", "custom")

        # Current UTC time
        now = datetime.utcnow()

        # Parse dates or set defaults
        start_date = parse_timestamp(start_date_str) if start_date_str else (now - timedelta(days=30)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        end_date = parse_timestamp(end_date_str) if end_date_str else now.strftime('%a, %d %b %Y %H:%M:%S GMT')

        # Adjust dates based on time_range if no explicit dates provided
        if not start_date_str and not end_date_str:
            if time_range == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%a, %d %b %Y %H:%M:%S GMT')
                end_date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
            elif time_range == 'week':
                start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).strftime('%a, %d %b %Y %H:%M:%S GMT')
                end_date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
            elif time_range == 'month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime('%a, %d %b %Y %H:%M:%S GMT')
                end_date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')

        app.logger.info(f"Fetching stats from {start_date} to {end_date}")

        # Calculate previous period
        prev_start_date, prev_end_date = calculate_previous_period(start_date, end_date, time_range)

        # Connect to the database
        conn = get_db_connection()
        try:
            # Helper function to execute queries
            def execute_query(cur, query):
                app.logger.info(f"Executing query: {query}")
                cur.execute(query)

            # Get entry/exit counts (exclude pedestrians)
            entry_count = 0
            exit_count = 0
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT
                        SUM(CASE WHEN gate LIKE '%_in' THEN 1 ELSE 0 END) AS entry_count,
                        SUM(CASE WHEN gate LIKE '%_out' THEN 1 ELSE 0 END) AS exit_count
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                """
                execute_query(cur, query)
                result = cur.fetchone()
                if result:
                    entry_count = result.get('entry_count', 0) or 0
                    exit_count = result.get('exit_count', 0) or 0

            # Get zone activity timeline (hourly, exclude pedestrians)
            zone_activity_timeline = []
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT
                        timestamp AS time,
                        COUNT(*) AS activity
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                    GROUP BY timestamp
                    ORDER BY timestamp
                """
                execute_query(cur, query)
                results = cur.fetchall()
                for row in results:
                    if row:
                        time_str = row['time'].strftime('%a, %d %b %Y %H:%M:%S GMT') if isinstance(row['time'], datetime) else str(row['time'])
                        zone_activity_timeline.append({
                            "time": time_str,
                            "activity": row['activity']
                        })

            # Get total events (exclude pedestrians)
            total_events = 0
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT COUNT(*) AS total_events
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                """
                execute_query(cur, query)
                result = cur.fetchone()
                if result:
                    total_events = result.get('total_events', 0) or 0

            # Get busiest hour (exclude pedestrians)
            busiest_hour = None
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT
                        EXTRACT(HOUR FROM timestamp::TIMESTAMP) AS hour,
                        COUNT(*) AS count
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                    GROUP BY hour
                    ORDER BY count DESC
                    LIMIT 1
                """
                execute_query(cur, query)
                result = cur.fetchone()
                if result:
                    busiest_hour = int(result['hour'])

            # Get category counts (exclude pedestrians)
            category_counts = {}
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT category, COUNT(*) AS count
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                    GROUP BY category
                """
                execute_query(cur, query)
                results = cur.fetchall()
                for row in results:
                    if row:
                        category_counts[row['category']] = row['count']

            # Get gate usage (exclude pedestrians)
            gate_usage = {}
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT gate, COUNT(*) AS count
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                    GROUP BY gate
                """
                execute_query(cur, query)
                results = cur.fetchall()
                for row in results:
                    if row:
                        gate_usage[row['gate']] = row['count']

            # Get hourly trend (exclude pedestrians)
            hourly_trend = {}
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT
                        EXTRACT(HOUR FROM timestamp::TIMESTAMP) AS hour,
                        COUNT(*) AS count
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                    GROUP BY hour
                    ORDER BY hour
                """
                execute_query(cur, query)
                results = cur.fetchall()
                for row in results:
                    if row:
                        hourly_trend[int(row['hour'])] = row['count']

            # Get color distribution (exclude pedestrians)
            color_distribution = {}
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT color, COUNT(*) AS count
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                    GROUP BY color
                """
                execute_query(cur, query)
                results = cur.fetchall()
                for row in results:
                    if row:
                        color_distribution[row['color']] = row['count']

            # Get zone counts (exclude pedestrians)
            zone_counts = {}
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT zone, COUNT(*) AS count
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                    GROUP BY zone
                """
                execute_query(cur, query)
                results = cur.fetchall()
                for row in results:
                    if row:
                        zone_counts[row['zone']] = row['count']

            # Get entry/exit by category (exclude pedestrians)
            entry_exit_by_category = {}
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT
                        category,
                        SUM(CASE WHEN gate LIKE '%_in' THEN 1 ELSE 0 END) AS entry,
                        SUM(CASE WHEN gate LIKE '%_out' THEN 1 ELSE 0 END) AS exit
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                    GROUP BY category
                """
                execute_query(cur, query)
                results = cur.fetchall()
                for row in results:
                    if row:
                        entry_exit_by_category[row['category']] = {
                            "entry": row['entry'] if row['entry'] is not None else 0,
                            "exit": row['exit'] if row['exit'] is not None else 0
                        }

            # Get daily trend (exclude pedestrians)
            daily_trend = {}
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT
                        DATE(timestamp) AS day,
                        COUNT(*) AS count
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                    GROUP BY day
                    ORDER BY day
                """
                execute_query(cur, query)
                results = cur.fetchall()
                for row in results:
                    if row:
                        day_str = row['day'].strftime('%Y-%m-%d') if isinstance(row['day'], datetime) else str(row['day'])
                        daily_trend[day_str] = row['count']

            # Get heatmap data (exclude pedestrians)
            heatmap_data = []
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT
                        EXTRACT(DOW FROM timestamp::TIMESTAMP) AS day_of_week,
                        EXTRACT(HOUR FROM timestamp::TIMESTAMP) AS hour,
                        COUNT(*) AS count
                    FROM parking
                    WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
                    AND category != 'pedestrian'
                    GROUP BY day_of_week, hour
                    ORDER BY day_of_week, hour
                """
                execute_query(cur, query)
                results = cur.fetchall()
                for row in results:
                    if row:
                        heatmap_data.append({
                            "day_of_week": int(row['day_of_week']),
                            "hour": int(row['hour']),
                            "count": row['count']
                        })

            # Get previous period category counts (exclude pedestrians)
            previous_counts = {}
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                    SELECT category, COUNT(*) AS count
                    FROM parking
                    WHERE timestamp BETWEEN '{prev_start_date}' AND '{prev_end_date}'
                    AND category != 'pedestrian'
                    GROUP BY category
                """
                execute_query(cur, query)
                results = cur.fetchall()
                for row in results:
                    if row:
                        previous_counts[row['category']] = row['count']

            # Calculate percentage changes
            percentage_changes = calculate_percentage_changes(category_counts, previous_counts)

            # Build response
            stats = {
                "entry_exit_counts": {"entry": entry_count, "exit": exit_count},
                "zone_activity_timeline": zone_activity_timeline,
                "total_events": total_events,
                "busiest_hour": busiest_hour,
                "category_counts": category_counts,
                "gate_usage": gate_usage,
                "hourly_trend": hourly_trend,
                "color_distribution": color_distribution,
                "zone_counts": zone_counts,
                "entry_exit_by_category": entry_exit_by_category,
                "daily_trend": daily_trend,
                "heatmap_data": heatmap_data
            }

            return jsonify({
                "stats": stats,
                "percentage_changes": percentage_changes,
                "time_period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "time_range": time_range
                }
            })

        finally:
            conn.close()

    except Exception as e:
        app.logger.error(f"Error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "Could not load stats", "details": str(e)}), 500
# Helper functions remain unchanged
def calculate_previous_period(start_date, end_date, time_range):
    try:
        start = datetime.strptime(start_date, '%a, %d %b %Y %H:%M:%S GMT')
        end = datetime.strptime(end_date, '%a, %d %b %Y %H:%M:%S GMT')

        if time_range == 'today':
            delta = end - start
            prev_start = start - delta
            prev_end = end - delta
        elif time_range == 'week':
            prev_start = start - timedelta(weeks=1)
            prev_end = end - timedelta(weeks=1)
        elif time_range == 'month':
            prev_start = start.replace(month=start.month-1 if start.month > 1 else 12, year=start.year-1 if start.month == 1 else start.year)
            prev_end = end.replace(month=end.month-1 if end.month > 1 else 12, year=end.year-1 if end.month == 1 else end.year)
        else:  # custom
            delta = end - start
            prev_start = start - delta
            prev_end = end - delta

        return prev_start.strftime('%a, %d %b %Y %H:%M:%S GMT'), prev_end.strftime('%a, %d %b %Y %H:%M:%S GMT')
    except ValueError as e:
        app.logger.error(f"Date parsing error: {str(e)}")
        now = datetime.utcnow()
        default_start = now - timedelta(days=30)
        return default_start.strftime('%a, %d %b %Y %H:%M:%S GMT'), now.strftime('%a, %d %b %Y %H:%M:%S GMT')

def calculate_percentage_changes(current_counts, previous_counts):
    percentage_changes = {}
    all_categories = set(list(current_counts.keys()) + list(previous_counts.keys()))

    for category in all_categories:
        current = current_counts.get(category, 0)
        previous = previous_counts.get(category, 0)
        if previous == 0:
            change = 0 if current == 0 else 100
        else:
            change = ((current - previous) / previous) * 100
        percentage_changes[category] = round(change, 2)

    return percentage_changes



#----------------------------------------
#endpoints for fetching the filters data
#----------------------------------------


@app.route("/filters/colors", methods=["GET"])
def get_colors_filter() -> Any:
    """
    Endpoint to match frontend expectations for color filters.
    """
    try:
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT color FROM parking WHERE color IS NOT NULL;")
        colors_tuples = cur.fetchall()
        
        # Debug the result structure
        app.logger.debug(f"Colors query result type: {type(colors_tuples)}")
        app.logger.debug(f"First result item type: {type(colors_tuples[0]) if colors_tuples else 'N/A'}")
        
        # Handle different result formats
        colors = []
        for item in colors_tuples:
            if isinstance(item, dict):
                colors.append(item['color'])
            elif isinstance(item, (list, tuple)):
                colors.append(item[0])
            else:
                # If it's directly the value
                colors.append(item)
        
        cur.close()
        conn.close()
        return jsonify({"colors": colors})
    except Exception as e:
        app.logger.error(f"Error in /filters/colors route: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load colors", "details": f"{e}"}), 500


@app.route("/filters/categories", methods=["GET"])
def get_categories_filter() -> Any:
    """
    Endpoint to match frontend expectations for category filters.
    """
    try:
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM parking WHERE category IS NOT NULL;")
        categories_tuples = cur.fetchall()
        
        # Handle different result formats
        categories = []
        for item in categories_tuples:
            if isinstance(item, dict):
                categories.append(item['category'])
            elif isinstance(item, (list, tuple)):
                categories.append(item[0])
            else:
                categories.append(item)
        
        cur.close()
        conn.close()
        return jsonify({"categories": categories})
    except Exception as e:
        app.logger.error(f"Error in /filters/categories route: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load categories", "details": f"{e}"}), 500

@app.route("/filters/gates", methods=["GET"])
def get_gates_filter() -> Any:
    """
    Endpoint to get unique gate names from database.
    """
    try:
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT gate FROM parking WHERE gate IS NOT NULL;")
        gates_tuples = cur.fetchall()
        
        # Handle different result formats
        gates = []
        for item in gates_tuples:
            if isinstance(item, dict):
                gates.append(item['gate'])
            elif isinstance(item, (list, tuple)):
                gates.append(item[0])
            else:
                gates.append(item)
        
        cur.close()
        conn.close()
        return jsonify({"gates": gates})
    except Exception as e:
        app.logger.error(f"Error in /filters/gates route: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load gates", "details": f"{e}"}), 500



#--------------------------------------
# endpoint to fetch and log the exports
#--------------------------------------
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'export_logs.json')

# Ensure the log file exists initially
if not os.path.exists(LOG_FILE_PATH):
    with open(LOG_FILE_PATH, 'w') as f:
        json.dump([], f)

def load_logs():
    """Read the current logs from the file."""
    try:
        with open(LOG_FILE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_logs(logs):
    """Write logs back to the file."""
    with open(LOG_FILE_PATH, 'w') as f:
        json.dump(logs, f, indent=2)

@app.route('/log-export', methods=['POST'])
def log_export():
    """Log an export event to the file with rotation."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Prepare the new log entry
    new_log = {
        'id': None,  # ID will be assigned after rotation
        'fileName': data.get('fileName'),
        'format': data.get('format'),
        'exportType': data.get('exportType'),
        'filters': data.get('filters'),
        'recordCount': data.get('recordCount'),
        'user': data.get('user'),
        'timestamp': data.get('timestamp', datetime.utcnow().isoformat())
    }

    # Load existing logs
    logs = load_logs()

    # Log rotation logic
    if len(logs) >= 10:
        # Remove the oldest log (first entry) and shift IDs
        logs = logs[1:]  # Keep logs from index 1 to end
        # Reassign IDs from 1 to 9 for the remaining logs
        for i, log in enumerate(logs, start=1):
            log['id'] = i

    # Assign the next ID to the new log (max 10)
    new_log['id'] = min(len(logs) + 1, 10)
    logs.append(new_log)

    # Save updated logs
    save_logs(logs)

    return jsonify({'message': 'Export logged successfully', 'log': new_log}), 200

@app.route('/export-logs', methods=['GET'])
def get_export_logs():
    """Return the current logs."""
    logs = load_logs()
    return jsonify(logs)



#Start the app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
