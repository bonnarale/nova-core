#!/bin/sh
set -eu

psql \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --variable n8n_user="$N8N_POSTGRES_USER" \
  --variable n8n_password="$N8N_POSTGRES_PASSWORD" <<-'EOSQL'
  SELECT format('CREATE USER %I WITH PASSWORD %L', :'n8n_user', :'n8n_password')
  WHERE NOT EXISTS (
    SELECT FROM pg_catalog.pg_roles WHERE rolname = :'n8n_user'
  )\gexec
EOSQL

database_exists="$(psql \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --tuples-only \
  --no-align \
  --variable n8n_db="$N8N_POSTGRES_DB" <<-'EOSQL'
  SELECT 1 FROM pg_database WHERE datname = :'n8n_db';
EOSQL
)"

if [ "$database_exists" != "1" ]; then
  createdb --username "$POSTGRES_USER" --owner "$N8N_POSTGRES_USER" "$N8N_POSTGRES_DB"
fi

psql \
  --username "$POSTGRES_USER" \
  --dbname "$N8N_POSTGRES_DB" \
  --variable n8n_db="$N8N_POSTGRES_DB" \
  --variable n8n_user="$N8N_POSTGRES_USER" <<-'EOSQL'
  GRANT ALL PRIVILEGES ON DATABASE :"n8n_db" TO :"n8n_user";
  GRANT ALL ON SCHEMA public TO :"n8n_user";
EOSQL
