# app.py
import os
import logging
import traceback
from typing import Any, Optional, Tuple
from datetime import datetime  # Added import for datetime

from flask import Flask, request, jsonify  # type: ignore
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as Connection  # type: ignore
from dotenv import load_dotenv
from flask_cors import CORS

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
    Endpoint to export parking data with optional filters.
    
    Query parameters:
    - start_date, end_date, license_prefix, categories, colors, gates, search.
    """
    try:
        start_date: Optional[str] = request.args.get("start_date")
        end_date: Optional[str] = request.args.get("end_date")
        license_prefix: Optional[str] = request.args.get("license_prefix")
        categories: Optional[str] = request.args.get("categories")
        colors: Optional[str] = request.args.get("colors")
        gates: Optional[str] = request.args.get("gates")
        search: Optional[str] = request.args.get("search")

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
        conn: Connection = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(results)
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
def parse_timestamp(ts: str) -> datetime:
    """Parse the timestamp from 'Fri, 28 Feb 2025 13:46:16 GMT' format"""
    return datetime.strptime(ts, "%a, %d %b %Y %H:%M:%S %Z")

@app.route("/data1", methods=["GET"])
def data1() -> Any:
    """
    Endpoint to retrieve parking data with optional filters and proper entry/exit mapping.
    """
    try:
        # Retrieve query parameters
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

        # Enhanced query with proper entry/exit mapping using a CTE
        query = """
            WITH entries AS (
                SELECT *
                FROM parking
                WHERE gate LIKE '%_in'
                    AND (timestamp >= COALESCE(%s::timestamptz, timestamp))
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
            ),
            exits AS (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY license_plate 
                           ORDER BY timestamp
                       ) as exit_num
                FROM parking
                WHERE gate LIKE '%_out'
            ),
            matched_records AS (
                SELECT 
                    e.insertion_id AS entry_id,
                    e.license_plate,
                    e.category,
                    e.color,
                    e.timestamp AS entry_timestamp,
                    e.gate AS entry_gate,
                    e.zone,
                    e.description,
                    ex.insertion_id AS exit_id,
                    ex.timestamp AS exit_timestamp,
                    ex.gate AS exit_gate,
                    EXTRACT(EPOCH FROM (ex.timestamp - e.timestamp)) AS duration,
                    ROW_NUMBER() OVER (
                        PARTITION BY e.insertion_id 
                        ORDER BY ex.timestamp
                    ) as match_num
                FROM entries e
                LEFT JOIN exits ex
                    ON e.license_plate = ex.license_plate
                    AND ex.timestamp > e.timestamp
                    AND ex.exit_num = 1
            )
            SELECT *
            FROM matched_records
            WHERE match_num = 1
            ORDER BY entry_timestamp DESC
            LIMIT %s
            OFFSET %s;
        """

        # Prepare parameters for the main query (without pagination in count)
        main_params = (
            parse_timestamp(start_date) if start_date else None,
            parse_timestamp(end_date) if end_date else None,
            license_prefix, license_prefix,
            categories, categories,
            colors, colors,
            gates, gates,
            search, search, search, search, search, search, search,
            page_size, offset
        )

        # Execute main query
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, main_params)
        results = cur.fetchall()
        
        # For total count, reuse the same CTE without LIMIT/OFFSET
        count_query = """
            WITH entries AS (
                SELECT *
                FROM parking
                WHERE gate LIKE '%_in'
                    AND (timestamp >= COALESCE(%s::timestamptz, timestamp))
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
            ),
            exits AS (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY license_plate 
                           ORDER BY timestamp
                       ) as exit_num
                FROM parking
                WHERE gate LIKE '%_out'
            ),
            matched_records AS (
                SELECT 
                    e.insertion_id AS entry_id,
                    e.license_plate,
                    e.category,
                    e.color,
                    e.timestamp AS entry_timestamp,
                    e.gate AS entry_gate,
                    e.zone,
                    e.description,
                    ex.insertion_id AS exit_id,
                    ex.timestamp AS exit_timestamp,
                    ex.gate AS exit_gate,
                    EXTRACT(EPOCH FROM (ex.timestamp - e.timestamp)) AS duration,
                    ROW_NUMBER() OVER (
                        PARTITION BY e.insertion_id 
                        ORDER BY ex.timestamp
                    ) as match_num
                FROM entries e
                LEFT JOIN exits ex
                    ON e.license_plate = ex.license_plate
                    AND ex.timestamp > e.timestamp
                    AND ex.exit_num = 1
            )
            SELECT COUNT(*) FROM matched_records WHERE match_num = 1;
        """
        # Parameters for count query (same as main, but without pagination)
        count_params = (
            parse_timestamp(start_date) if start_date else None,
            parse_timestamp(end_date) if end_date else None,
            license_prefix, license_prefix,
            categories, categories,
            colors, colors,
            gates, gates,
            search, search, search, search, search, search, search
        )
        cur.execute(count_query, count_params)
        total_records = cur.fetchone()[0]
        
        cur.close()
        conn.close()

        # Format results
        formatted_results = []
        for row in results:
            formatted_results.append({
                "entry_id": row[0],
                "license_plate": row[1],
                "category": row[2],
                "color": row[3],
                "entry_timestamp": row[4].strftime("%a, %d %b %Y %H:%M:%S %Z"),
                "entry_gate": row[5],
                "zone": row[6],
                "description": row[7],
                "exit_id": row[8],
                "exit_timestamp": row[9].strftime("%a, %d %b %Y %H:%M:%S %Z") if row[9] else None,
                "exit_gate": row[10],
                "duration": row[11]
            })

        return jsonify({
            "data": formatted_results,
            "total_pages": (total_records + page_size - 1) // page_size,
            "current_page": page,
            "total_records": total_records
        })

    except Exception as e:
        app.logger.error(f"Error in /data1 endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load data", "details": str(e)}), 500

# Start the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
