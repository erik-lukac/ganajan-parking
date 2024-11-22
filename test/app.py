from flask import Flask, request, jsonify
from datetime import datetime

# Constants for readability
TOP_LEVEL_FIELDS = ["analytic_id", "block_name", "cube_id"]
ENTRY_FIELDS = ["id", "license_plate", "type", "status", "timestamp", "original_timestamp"]

print("APP STARTS 7", flush=True)  # Print initial message

def create_app():
    """
    Factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True  # Pretty-print JSON responses
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
        Processes data and prints the table.
        """
        data = request.get_json()

        if not data:
            app.logger.warning("No JSON payload received or incorrect Content-Type")
            return jsonify({"message": "No JSON payload received"}), 400

        # Process the payload
        response = process_payload(data)

        if not response["entries"]:
            app.logger.info("No valid entries found in the payload")
        else:
            # Print the table
            print_table(response["entries"])

        return jsonify(response), 200

def process_payload(data):
    """
    Processes the payload to extract top-level fields and all valid entries.
    """
    top_level_data = extract_top_level_data(data)
    entries = data.get('data', {}).get('data', [])
    valid_entries = extract_all_valid_entries(entries)

    return {**top_level_data, "entries": valid_entries}

def extract_top_level_data(data):
    """
    Extracts top-level fields from the incoming JSON data.
    """
    return {field: data.get(field) for field in TOP_LEVEL_FIELDS}

def extract_all_valid_entries(entries):
    """
    Extracts all valid entries from the provided list of entries.
    An entry is valid if it has at least 5 fields and the license plate is not '-'.
    Converts the timestamp from Unix time (milliseconds) to UTC without seconds.
    """
    valid_entries = []

    for entry in entries:
        if len(entry) >= 5 and entry[1] != '-':
            # Convert timestamp to UTC format without seconds
            timestamp_ms = int(entry[4])  # Ensure it's an integer
            timestamp_utc = datetime.utcfromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M')
            entry_dict = dict(zip(ENTRY_FIELDS[:-1], entry))  # Exclude "original_timestamp" for now
            entry_dict["timestamp"] = timestamp_utc
            entry_dict["original_timestamp"] = entry[4]  # Add the original timestamp
            valid_entries.append(entry_dict)

    return valid_entries

def print_table(entries):
    """
    Prints the list of entries as a table.
    """
    print("\nTable of Valid Entries:\n")
    print(f"{'ID':<10} {'License Plate':<15} {'Type':<10} {'Status':<10} {'Converted Timestamp':<20} {'Original Timestamp':<15}")
    print("-" * 85)
    for entry in entries:
        print(f"{entry['id']:<10} {entry['license_plate']:<15} {entry['type']:<10} {entry['status']:<10} {entry['timestamp']:<20} {entry['original_timestamp']:<15}")
    print("\n")

if __name__ == "__main__":
    # Create and run the app
    app = create_app()
    app.run(host="0.0.0.0", port=5003)