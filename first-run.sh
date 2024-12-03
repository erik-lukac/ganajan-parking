#!/bin/bash
# first-run.sh
# This script sets up a PostgreSQL database container, creates the database, and inserts an initial entry.

### DATABASE CONFIGURATION ###
POSTGRES_HOST="localhost"
POSTGRES_PORT=${DB_PORT:-5444}
POSTGRES_DBNAME=${DB_NAME:-"default_dbname"}
POSTGRES_USER=${DB_USER:-"default_user"}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-"default_password"}
POSTGRES_TABLE=${DB_TABLE:-"default_table"}
CONTAINER_NAME="db"
NETWORK_NAME="shared_network"
DB_FOLDER="db"  # Local folder for database storage

# Export password for non-interactive use
export PGPASSWORD=$POSTGRES_PASSWORD

# Embedded SQL for initial table creation and first entry
EMBEDDED_SQL="
-- Grant permissions to the flowerist user
GRANT ALL ON SCHEMA public TO \"$POSTGRES_USER\";
GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DBNAME TO \"$POSTGRES_USER\";

-- Create the $POSTGRES_TABLE table if it doesn't exist
CREATE TABLE IF NOT EXISTS $POSTGRES_TABLE (
    id SERIAL PRIMARY KEY,
    insertion_id INTEGER NOT NULL,
    license_plate TEXT NOT NULL,
    category TEXT NOT NULL,
    color TEXT,
    \"timestamp\" TIMESTAMP NOT NULL,
    gate TEXT NOT NULL,
    zone INTEGER NOT NULL,
    description TEXT
);

-- Insert the first entry
COPY $POSTGRES_TABLE (id, insertion_id, license_plate, category, color, \"timestamp\", gate, zone, description) FROM stdin;
0	11111	-	vehicle	undefined	2024-11-11 11:11:11.111111	ganajan_bike_in	11	11
\\.
"

echo "Setting up PostgreSQL Docker container..."

# Step 1: Create Docker network if it doesn't exist
if ! docker network ls | grep -q "$NETWORK_NAME"; then
    echo "Creating Docker network: $NETWORK_NAME"
    docker network create "$NETWORK_NAME"
else
    echo "Docker network $NETWORK_NAME already exists."
fi

# Step 2: Ensure DB folder exists locally
if [ ! -d "$DB_FOLDER" ]; then
    echo "Creating local database folder: $DB_FOLDER"
    mkdir -p "$DB_FOLDER"
else
    echo "Database folder $DB_FOLDER already exists."
fi

# Step 3: Start the PostgreSQL Docker container
if ! docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "Creating and starting Docker container: $CONTAINER_NAME"
    docker run -d \
        --name "$CONTAINER_NAME" \
        --network "$NETWORK_NAME" \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        -e PGDATA=/var/lib/postgresql/data/pgdata \
        -v "$(pwd)/$DB_FOLDER:/var/lib/postgresql/data/pgdata" \
        -p "$POSTGRES_PORT:5432" \
        postgres:latest
else
    echo "Docker container $CONTAINER_NAME already exists. Starting it..."
    docker start "$CONTAINER_NAME"
fi

# Wait for the database service to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker exec "$CONTAINER_NAME" pg_isready -U postgres > /dev/null 2>&1; do
    sleep 2
    echo "PostgreSQL is not ready yet. Retrying..."
done
echo "PostgreSQL is ready."

# Step 4: Create the database user if it doesn't exist
echo "Creating database user if it doesn't exist..."
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" psql -U postgres -c "
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$POSTGRES_USER') THEN
      CREATE ROLE \"$POSTGRES_USER\" LOGIN PASSWORD '$POSTGRES_PASSWORD';
   END IF;
END
\$\$;"

# Step 5: Create the database if it doesn't exist
echo "Creating database if it doesn't exist..."
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" psql -U postgres -c "
SELECT 1 FROM pg_database WHERE datname = '$POSTGRES_DBNAME';
" | grep -q 1 || docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" psql -U postgres -c "CREATE DATABASE $POSTGRES_DBNAME;"

# Step 6: Execute embedded SQL to grant permissions, create the table, and insert the first entry
echo "Setting up the $POSTGRES_TABLE table and inserting the first entry..."
docker exec -i "$CONTAINER_NAME" psql -U postgres -d "$POSTGRES_DBNAME" <<< "$EMBEDDED_SQL"

# Step 7: Grant SELECT permissions to flowerist on the $POSTGRES_TABLE table
echo "Granting SELECT permissions on the table..."
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" psql -U postgres -d "$POSTGRES_DBNAME" -c "
GRANT SELECT ON $POSTGRES_TABLE TO \"$POSTGRES_USER\";
"

# Step 8: Verify table creation and first entry
echo "Verifying table creation and first entry..."
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$POSTGRES_DBNAME" -c "SELECT * FROM $POSTGRES_TABLE;"

echo "Database setup and initial entry creation completed!"