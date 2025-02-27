# app.py
import os
import logging
import traceback
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Initialize the Flask app
app = Flask(__name__)

# Set a secret key for session management
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", mode="a")
    ]
)
app.logger.info("Parking Dashboard App is starting...")

# Database connection function
def get_db_connection():
    try:
        connection = psycopg2.connect(
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
def data():
    try:
        # Retrieve query parameters (all optional)
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        license_prefix = request.args.get("license_prefix")
        categories = request.args.get("categories")
        colors = request.args.get("colors")
        gates = request.args.get("gates")
        search = request.args.get("search")
        page_size = int(request.args.get("page_size", 10))
        page = int(request.args.get("page", 1))
        offset = (page - 1) * page_size

        query = """
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
        # Parameter count:
        # 2 for start_date/end_date,
        # 2 for license_prefix,
        # 2 for categories,
        # 2 for colors,
        # 2 for gates,
        # 7 for search block,
        # 1 for LIMIT and 1 for OFFSET => Total 19
        params = (
            start_date, end_date,
            license_prefix, license_prefix,
            categories, categories,
            colors, colors,
            gates, gates,
            search, search, search, search, search, search, search,
            page_size, offset
        )
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error in /data endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load data", "details": str(e)}), 500

# ---------------------------------------
# 2. /dashboard/data Endpoint
# ---------------------------------------
@app.route("/dashboard/data", methods=["GET"])
def dashboard_data():
    try:
        search = request.args.get("search")
        page_size = int(request.args.get("page_size", 10))
        page = int(request.args.get("page", 1))
        offset = (page - 1) * page_size

        query = """
            SELECT *
            FROM parking
            WHERE
              %s IS NULL OR
              license_plate ILIKE ('%%' || %s || '%%') OR
              category ILIKE ('%%' || %s || '%%') OR
              color ILIKE ('%%' || %s || '%%') OR
              gate ILIKE ('%%' || %s || '%%') OR
              zone ILIKE ('%%' || %s || '%%') OR
              description ILIKE ('%%' || %s || '%%')
            ORDER BY timestamp DESC
            LIMIT %s
            OFFSET %s;
        """
        # Count placeholders: 1 (check search is NULL) + 6 (for each field) + LIMIT + OFFSET = 9.
        # So we need 7 copies of search for the search block.
        params = (
            search, search, search, search, search, search, search,
            page_size, offset
        )
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error in /dashboard/data endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load dashboard data", "details": str(e)}), 500

# ---------------------------------------
# 3. /stats/category-stats Endpoint
# ---------------------------------------
@app.route("/stats/category-stats", methods=["GET"])
def category_stats():
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        if not start_date or not end_date:
            return jsonify({"error": "start_date and end_date parameters are required"}), 400

        query = """
            SELECT category, COUNT(*) AS count
            FROM parking
            WHERE
              timestamp >= %s::timestamptz
              AND timestamp <= %s::timestamptz
            GROUP BY category;
        """
        params = (start_date, end_date)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error in /stats/category-stats endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load category stats", "details": str(e)}), 500

# ---------------------------------------
# 4. /stats/today-entries Endpoint
# ---------------------------------------
@app.route("/stats/today-entries", methods=["GET"])
def today_entries():
    try:
        query = """
            SELECT COUNT(*) AS count
            FROM parking
            WHERE DATE(timestamp) = CURRENT_DATE
              AND gate ILIKE '%%_in';
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in /stats/today-entries endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load today's entries", "details": str(e)}), 500

# ---------------------------------------
# 5. /stats/recent-entries Endpoint
# ---------------------------------------
@app.route("/stats/recent-entries", methods=["GET"])
def recent_entries():
    try:
        query = """
            SELECT COUNT(*) AS count
            FROM parking
            WHERE timestamp >= NOW() - INTERVAL '10 minutes'
              AND gate ILIKE '%%_in';
        """
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in /stats/recent-entries endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load recent entries", "details": str(e)}), 500

# ---------------------------------------
# 6. /export Endpoint
# ---------------------------------------
@app.route("/export", methods=["GET"])
def export():
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        license_prefix = request.args.get("license_prefix")
        categories = request.args.get("categories")
        colors = request.args.get("colors")
        gates = request.args.get("gates")
        search = request.args.get("search")

        query = """
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
        # Parameter count:
        # 2 for start_date/end_date,
        # 2 for license_prefix,
        # 2 for categories,
        # 2 for colors,
        # 2 for gates,
        # 7 for search block => total 2+2+2+2+2+7 = 17.
        params = (
            start_date, end_date,
            license_prefix, license_prefix,
            categories, categories,
            colors, colors,
            gates, gates,
            search, search, search, search, search, search, search
        )
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error in /export endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not export data", "details": str(e)}), 500

# ---------------------------------------
# 7. /stats/trends Endpoint
# ---------------------------------------
@app.route("/stats/trends", methods=["GET"])
def stats_trends():
    try:
        conn = get_db_connection()
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
        return jsonify({"error": "Could not load trends", "details": str(e)}), 500

# ---------------------------------------
# 8. /stats/duration-stats Endpoint
# ---------------------------------------
@app.route("/stats/duration-stats", methods=["GET"])
def duration_stats():
    try:
        start_time = request.args.get("start_time")
        if not start_time:
            return jsonify({"error": "start_time parameter is required"}), 400

        query = """
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
        params = (start_time,)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error in /stats/duration-stats endpoint: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load duration stats", "details": str(e)}), 500

# ---------------------------------------
# Existing /test Endpoint (unchanged)
# ---------------------------------------
@app.route("/test", methods=["GET"])
def test():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM parking ORDER BY timestamp DESC LIMIT 5;")
        test_entries = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(test_entries)
    except Exception as e:
        app.logger.error(f"Error in /test route: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load test entries", "details": str(e)}), 500

# Start the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
