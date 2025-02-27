# app.py
import os
import re
import logging
import traceback
from flask import Flask, render_template, request, session
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Initialize the Flask app
app = Flask(__name__, template_folder='templates')

# Set a secret key for session management
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler("app.log", mode='a')  # Log to file
    ]
)
app.logger.info("Parking Dashboard App is starting...")

# Database connection function
def get_db_connection():
    try:
        connection = psycopg2.connect(
            dbname=os.environ.get("DB_NAME", "flow"),         # Fetch database name from environment variable
            user=os.environ.get("DB_USER", "postgres"),       # Fetch database user from environment variable
            password=os.environ.get("DB_PASSWORD"),           # Fetch password from environment variable
            host=os.environ.get("DB_HOST", "db"),             # Assuming PostgreSQL is running on localhost or Docker network
            port=os.environ.get("DB_PORT", 5432),             # Fetch port from environment variable
            cursor_factory=RealDictCursor  # This will return results as dictionaries
        )
        app.logger.info("Database connection established successfully.")
        return connection
    except Exception as e:
        app.logger.error(f"Database connection error: {e}")
        raise

# Input validation function
def is_valid_license_plate(license_plate):
    """Validate the license plate format."""
    if license_plate is None:
        app.logger.warning("License plate is None.")
        return False
    valid = bool(re.match(r"^[A-Za-z0-9-]{1,10}$", license_plate))
    if not valid:
        app.logger.warning(f"Invalid license plate format: {license_plate}")
    return valid

# Overview Route
@app.route("/", methods=["GET", "POST"])
def overview():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Initialize dates from session or None
        start_date = session.get("start_date")
        end_date = session.get("end_date")
        
        # Initialize data structures
        last_5_car_in = []
        last_5_car_out = []
        last_5_bike_in = []
        last_5_bike_out = []

        if request.method == "POST":
            # Update dates based on user input
            start_date = request.form.get("start_date")
            end_date = request.form.get("end_date")
            session['start_date'] = start_date
            session['end_date'] = end_date

        # Function to fetch last N entries based on gate pattern and category
        def fetch_last_n(gate_pattern, category, limit=5):
            if start_date and end_date:
                cursor.execute(
                    """
                    SELECT id, license_plate, category, color, timestamp 
                    FROM parking 
                    WHERE category = %s AND gate LIKE %s AND timestamp BETWEEN %s AND %s
                    ORDER BY timestamp DESC 
                    LIMIT %s;
                    """,
                    (category, f"%{gate_pattern}", start_date, end_date, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, license_plate, category, color, timestamp 
                    FROM parking 
                    WHERE category = %s AND gate LIKE %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s;
                    """,
                    (category, f"%{gate_pattern}", limit)
                )
            return cursor.fetchall()

        # Fetch last 5 car entries (car_in)
        last_5_car_in = fetch_last_n('car_in', 'car', 5)

        # Fetch last 5 car exits (car_out)
        last_5_car_out = fetch_last_n('car_out', 'car', 5)

        # Fetch last 5 bike entries (bike_in) - assuming category is 'motorcycle'
        last_5_bike_in = fetch_last_n('bike_in', 'motorcycle', 5)

        # Fetch last 5 bike exits (bike_out) - assuming category is 'motorcycle'
        last_5_bike_out = fetch_last_n('bike_out', 'motorcycle', 5)

        cursor.close()
        connection.close()

        return render_template(
            "dashboard.html",
            view="overview",
            last_5_car_in=last_5_car_in,
            last_5_car_out=last_5_car_out,
            last_5_bike_in=last_5_bike_in,
            last_5_bike_out=last_5_bike_out,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        app.logger.error(f"Error in overview route: {e}")
        app.logger.error(traceback.format_exc())
        return render_template(
            "dashboard.html", 
            view="overview", 
            error_message="Could not load data.", 
            start_date=session.get("start_date"), 
            end_date=session.get("end_date")
        ), 500

# Search Route
@app.route("/search", methods=["GET", "POST"])
def search():
    try:
        if request.method == "POST":
            license_plate = request.form.get("license_plate")
            
            if not license_plate:
                app.logger.warning("No license plate provided in search.")
                return render_template(
                    "dashboard.html", 
                    view="search", 
                    error_message="Please provide a license plate to search.", 
                    start_date=session.get("start_date"), 
                    end_date=session.get("end_date")
                )

            if not is_valid_license_plate(license_plate):
                return render_template(
                    "dashboard.html", 
                    view="search", 
                    error_message="Invalid license plate format.", 
                    start_date=session.get("start_date"), 
                    end_date=session.get("end_date")
                )

            connection = get_db_connection()
            cursor = connection.cursor()

            # Search by license plate
            cursor.execute(
                """
                SELECT id, license_plate, category, color, timestamp 
                FROM parking 
                WHERE license_plate LIKE %s 
                ORDER BY timestamp DESC 
                LIMIT 10;
                """,
                (f"%{license_plate}%",)
            )
            search_results = cursor.fetchall()
            app.logger.info(f"Search results for {license_plate}: {search_results}")

            cursor.close()
            connection.close()
            return render_template(
                "dashboard.html", 
                view="search", 
                search_results=search_results, 
                start_date=session.get("start_date"), 
                end_date=session.get("end_date")
            )
        else:
            # For GET request, simply render the search page with existing date selections
            return render_template(
                "dashboard.html", 
                view="search", 
                start_date=session.get("start_date"), 
                end_date=session.get("end_date")
            )
    except Exception as e:
        app.logger.error(f"Error during license plate search: {e}")
        app.logger.error(traceback.format_exc())
        return render_template(
            "dashboard.html", 
            view="search", 
            error_message="An error occurred while searching.", 
            start_date=session.get("start_date"), 
            end_date=session.get("end_date")
        ), 500

# Statistics Route
@app.route("/statistics", methods=["GET", "POST"])
def statistics():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Initialize dates from session or None
        start_date = session.get("start_date")
        end_date = session.get("end_date")
        statistics_data_pie = []
        statistics_data_bar_vehicles = []
        statistics_data_hourly_average = []

        if request.method == "POST":
            # Update dates based on user input
            start_date = request.form.get("start_date")
            end_date = request.form.get("end_date")
            session['start_date'] = start_date
            session['end_date'] = end_date

        if start_date and end_date:
            # Pie Chart Data: Categories Count
            cursor.execute(
                """
                SELECT category, COUNT(*) as count 
                FROM parking 
                WHERE timestamp BETWEEN %s AND %s 
                GROUP BY category;
                """,
                (start_date, end_date)
            )
            statistics_data_pie = cursor.fetchall()

            # Bar Chart Data: Sum of Vehicles per Day
            cursor.execute(
                """
                SELECT DATE(timestamp) as day, COUNT(*) as total_vehicles
                FROM parking
                WHERE timestamp BETWEEN %s AND %s
                GROUP BY day
                ORDER BY day;
                """,
                (start_date, end_date)
            )
            statistics_data_bar_vehicles = cursor.fetchall()

            # Hourly Average Data
            cursor.execute(
                """
                SELECT hour, AVG(vehicle_count) AS average_vehicle_count FROM (
                    SELECT DATE(timestamp) AS date, EXTRACT(HOUR FROM timestamp) AS hour, COUNT(*) AS vehicle_count
                    FROM parking
                    WHERE timestamp BETWEEN %s AND %s
                    GROUP BY date, hour
                ) sub
                GROUP BY hour
                ORDER BY hour;
                """,
                (start_date, end_date)
            )
            statistics_data_hourly_average = cursor.fetchall()

            app.logger.info(f"Fetched statistics from {start_date} to {end_date}")
        else:
            # Default statistics (e.g., for the last month)
            cursor.execute(
                """
                SELECT category, COUNT(*) as count 
                FROM parking 
                GROUP BY category;
                """
            )
            statistics_data_pie = cursor.fetchall()

            cursor.execute(
                """
                SELECT DATE(timestamp) as day, COUNT(*) as total_vehicles
                FROM parking
                GROUP BY day
                ORDER BY day;
                """
            )
            statistics_data_bar_vehicles = cursor.fetchall()

            # Hourly Average Data
            cursor.execute(
                """
                SELECT hour, AVG(vehicle_count) AS average_vehicle_count FROM (
                    SELECT DATE(timestamp) AS date, EXTRACT(HOUR FROM timestamp) AS hour, COUNT(*) AS vehicle_count
                    FROM parking
                    GROUP BY date, hour
                ) sub
                GROUP BY hour
                ORDER BY hour;
                """
            )
            statistics_data_hourly_average = cursor.fetchall()

            app.logger.info(f"Fetched default statistics")

        cursor.close()
        connection.close()

        # Prepare data for Chart.js
        pie_labels = [row['category'] for row in statistics_data_pie]
        pie_values = [row['count'] for row in statistics_data_pie]

        bar_labels = [row['day'].strftime('%Y-%m-%d') for row in statistics_data_bar_vehicles]
        bar_total_vehicles = [row['total_vehicles'] for row in statistics_data_bar_vehicles]

        hourly_labels = [int(row['hour']) for row in statistics_data_hourly_average]
        hourly_averages = [row['average_vehicle_count'] for row in statistics_data_hourly_average]

        return render_template(
            "dashboard.html",
            view="statistics",
            pie_labels=pie_labels,
            pie_values=pie_values,
            bar_labels=bar_labels,
            bar_total_vehicles=bar_total_vehicles,
            hourly_labels=hourly_labels,
            hourly_averages=hourly_averages,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        app.logger.error(f"Error in statistics route: {e}")
        app.logger.error(traceback.format_exc())
        return render_template(
            "dashboard.html", 
            view="statistics", 
            error_message="Could not load statistics data.", 
            start_date=session.get("start_date"), 
            end_date=session.get("end_date")
        ), 500

# Error Handling
@app.errorhandler(404)
def page_not_found(e):
    app.logger.warning("Page not found: 404 error")
    return render_template(
        "dashboard.html", 
        view="overview", 
        error_message="Page not found.", 
        start_date=session.get("start_date"), 
        end_date=session.get("end_date")
    ), 404

@app.errorhandler(500)
def internal_error(e):
    app.logger.error(f"Internal server error: {e}")
    app.logger.error(traceback.format_exc())
    return render_template(
        "dashboard.html", 
        view="overview", 
        error_message="An unexpected error occurred.", 
        start_date=session.get("start_date"), 
        end_date=session.get("end_date")
    ), 500

# Start the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
