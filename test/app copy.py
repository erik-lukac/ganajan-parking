from flask import Flask, request, jsonify
from datetime import datetime

# Constants for better readability
TOP_LEVEL_FIELDS = ["analytic_id", "block_name", "cube_id"]
ENTRY_FIELDS = ["id", "license_plate", "type", "status", "timestamp"]

def create_app():
    """
    Factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True  # Optional: pretty-print JSON responses
    app.logger.setLevel("DEBUG")  # Set log level for Flask logger
    app.logger.info("STARTING WEBHOOK LISTENER")
    
    # Register routes
    register_routes(app)

    return app

def register_routes(app):
    """
    Register all application routes.
    """
    @app.route('/webhooks/ganajan_bike_in', methods=['POST'])
    def handle_webhook():
        """
        Handles incoming POST requests to the /webhooks/ganajan_bike_in endpoint.
        """
        data = request.get_json()

        if not data:
            app.logger.warning("No JSON payload received or incorrect Content-Type")
            return jsonify({"message": "No JSON payload received"}), 400

        # Process the payload
        response = process_payload(data)

        if not response["first_entry"]:
            app.logger.info("No valid entries found in the payload")

        app.logger.debug("Response being sent: %s", response)
        return jsonify(response), 200

def extract_top_level_data(data):
    """
    Extracts top-level fields from the incoming JSON data.
    """
    return {field: data.get(field) for field in TOP_LEVEL_FIELDS}

def extract_first_valid_entry(entries):
    """
    Extracts the first valid entry from the provided list of entries.
    An entry is valid if it has at least 5 fields and the license plate is not '-'.
    Converts the timestamp from Unix time (milliseconds) to UTC without seconds.
    """
    for entry in entries:
        if len(entry) >= 5 and entry[1] != '-':
            # Convert timestamp to UTC format without seconds
            timestamp_ms = int(entry[4])  # Ensure it's an integer
            timestamp_utc = datetime.utcfromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M')
            entry_dict = dict(zip(ENTRY_FIELDS, entry))
            entry_dict["timestamp"] = timestamp_utc
            return entry_dict
    return {}

def process_payload(data):
    """
    Processes the payload to extract top-level fields and the first valid entry.
    """
    top_level_data = extract_top_level_data(data)
    entries = data.get('data', {}).get('data', [])
    first_valid_entry = extract_first_valid_entry(entries)
    return {**top_level_data, "first_entry": first_valid_entry}

if __name__ == "__main__":
    # Create and run the app
    app = create_app()
    app.run(host="0.0.0.0", port=5003)