#!/usr/bin/env bash
set -e

# 1) Load environment variables from .env
if [ -f .env ]; then
    # Export each key=val line (ignoring # comments)
    export $(grep -v '^#' .env | xargs)
fi

# 2) Stop and remove containers/volumes (if any)
docker-compose down -v || true

# 3) Start only the db service in the background
docker-compose up -d db

echo "Waiting 10 seconds for Postgres to start..."
sleep 10

# 4) Create 'parking' table (if not exists)
#    Use -e PGPASSWORD to supply the password non-interactively
docker-compose exec -e PGPASSWORD="$DB_PASSWORD" db \
  psql -U "$DB_USER" -d "$DB_NAME" -c "
  CREATE TABLE IF NOT EXISTS parking (
    insertion_id TEXT PRIMARY KEY,
    license_plate TEXT,
    category TEXT,
    color TEXT,
    timestamp TIMESTAMP WITH TIME ZONE,
    gate TEXT,
    zone TEXT,
    description TEXT
  );
"

echo "Table 'parking' has been ensured in database '$DB_NAME'."