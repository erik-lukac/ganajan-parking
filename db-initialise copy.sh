docker-compose down -v
docker stop db
docker rm db#!/usr/bin/env bash
set -euo pipefail

### DATABASE CONFIGURATION ###
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-"default_password"}
DB_USER=${DB_USER:-"default_user"}
DB_NAME=${DB_NAME:-"default_dbname"}
DB_PORT=${DB_PORT:-5444}
DB_TABLE=${DB_TABLE:-"default_table"}

# Create .env file with the configuration
cat > .env << EOL
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DB_USER=$DB_USER
DB_NAME=$DB_NAME
DB_PORT=$DB_PORT
DB_PASSWORD=$POSTGRES_PASSWORD
EOL

CONTAINER_NAME="db"
NETWORK_NAME="shared_network"
DB_FOLDER="db"  # Local folder for database storage

# Embedded SQL for initial table creation and first entry
EMBEDDED_SQL="
-- Grant permissions to the user
GRANT ALL ON SCHEMA public TO \"$DB_USER\";
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO \"$DB_USER\";

-- Create the $DB_TABLE table if it doesn't exist
CREATE TABLE IF NOT EXISTS $DB_TABLE (
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
COPY $DB_TABLE (id, insertion_id, license_plate, category, color, \"timestamp\", gate, zone, description) FROM stdin;
0   11111   -   vehicle undefined    2024-11-11 11:11:11.111111 ganajan_bike_in  11  11
\\.
"

echo "Preparing environment..."

# Install Docker if not available
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    sudo apt-get update -y
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    # Add Docker’s official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    # Set up the Docker stable repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
      https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
    echo "Docker is already installed."
fi

# Ensure Docker is running
echo "Ensuring Docker is running..."
sudo systemctl enable docker
sudo systemctl start docker
echo "Docker is running."

# Create Docker network if it doesn't exist
if ! sudo docker network ls | grep -q "$NETWORK_NAME"; then
    echo "Creating Docker network: $NETWORK_NAME"
    sudo docker network create "$NETWORK_NAME"
else
    echo "Docker network $NETWORK_NAME already exists."
fi

# Ensure DB folder exists locally
if [ ! -d "$DB_FOLDER" ]; then
    echo "Creating local database folder: $DB_FOLDER"
    mkdir -p "$DB_FOLDER"
else
    echo "Database folder $DB_FOLDER already exists."
fi

# If an old container exists, remove it
if sudo docker ps -a --format '{{.Names}}' | grep -qw "$CONTAINER_NAME"; then
    echo "Removing old container named $CONTAINER_NAME..."
    sudo docker stop "$CONTAINER_NAME" || true
    sudo docker rm "$CONTAINER_NAME"
fi

echo "Creating and starting Docker container: $CONTAINER_NAME"
sudo docker run -d \
    --name "$CONTAINER_NAME" \
    --network "$NETWORK_NAME" \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    -e PGDATA=/var/lib/postgresql/data/pgdata \
    -v "$(pwd)/$DB_FOLDER:/var/lib/postgresql/data/pgdata" \
    -p "$DB_PORT:5432" \
    postgres:latest

echo "Waiting for PostgreSQL to be ready..."
until sudo docker exec "$CONTAINER_NAME" pg_isready -U postgres > /dev/null 2>&1; do
    sleep 2
    echo "PostgreSQL is not ready yet. Retrying..."
done
echo "PostgreSQL is ready."

echo "Creating database user if not exists..."
sudo docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" psql -U postgres -c "
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
      CREATE ROLE \"$DB_USER\" LOGIN PASSWORD '$POSTGRES_PASSWORD';
   END IF;
END
\$\$;"

echo "Creating database if not exists..."
sudo docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" psql -U postgres -c "
SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';
" | grep -q 1 || sudo docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" psql -U postgres -c "CREATE DATABASE $DB_NAME;"

echo "Setting up the $DB_TABLE table and inserting the first entry..."
echo "$EMBEDDED_SQL" | sudo docker exec -i "$CONTAINER_NAME" psql -U postgres -d "$DB_NAME"

echo "Granting SELECT permissions on the table..."
sudo docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" psql -U postgres -d "$DB_NAME" -c "
GRANT SELECT ON $DB_TABLE TO \"$DB_USER\";
"

echo "Verifying table creation and first entry..."
sudo docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT * FROM $DB_TABLE;"

echo "Database setup and initial entry creation completed!"
echo "Note: The DB container is running. Other services are not started yet."
echo "You can now start other services later using: docker-compose -f docker-compose.yml up -d"
