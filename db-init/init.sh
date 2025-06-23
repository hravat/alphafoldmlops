#!/bin/bash

#set -o allexport
#source /docker-entrypoint-initdb.d/.env
#set +o allexport

DB_NAME="chembl_db"
DB_USER="postgres"
DUMP_FILE="data/chembl_35/chembl_35_postgresql/chembl_ml_dataset.dump"

# Create the database (if it doesn't already exist)
echo "Creating database $DB_NAME if it doesn't exist..."
#psql -U "$DB_USER" -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
psql -U "$DB_USER" -c "CREATE DATABASE $DB_NAME"
echo "Database $DB_NAME created or already exists."


# Restore the table from the dump file
echo "Restoring the table chembl_ml_dataset from $DUMP_FILE..."
pg_restore -U "$DB_USER" -d "$DB_NAME" --table=chembl_ml_dataset "$DUMP_FILE"
echo "Table chembl_ml_dataset restored successfully."

# Database 2: mage_db (for Mage)
MAGE_DB="mage_db"
MAGE_USER="mage"
MAGE_PASSWORD="mage"


echo "Creating user $MAGE_USER..."
psql -U "$DB_USER" -tc "SELECT 1 FROM pg_roles WHERE rolname='$MAGE_USER'" | grep -q 1 || \
psql -U "$DB_USER" -c "CREATE USER $MAGE_USER WITH PASSWORD '$MAGE_PASSWORD';"

echo "Creating database $MAGE_DB..."
psql -U "$DB_USER" -c "CREATE DATABASE $MAGE_DB OWNER $MAGE_USER;" || echo "$MAGE_DB already exists."

echo "Granting privileges on $MAGE_DB to $MAGE_USER..."
psql -U "$DB_USER" -d "$MAGE_DB" -c "GRANT ALL PRIVILEGES ON DATABASE $MAGE_DB TO $MAGE_USER;"

echo "Creating schema 'mage' in database $MAGE_DB..."
psql -U "$DB_USER" -d "$MAGE_DB" -c "CREATE SCHEMA IF NOT EXISTS mage AUTHORIZATION $MAGE_USER;"

echo "Granting privileges on schema 'mage' to $MAGE_USER..."
psql -U "$DB_USER" -d "$MAGE_DB" -c "GRANT ALL ON SCHEMA mage TO $MAGE_USER;"

# Database 3: mlflow_db (for MLflow)
MLFLOW_DB="mlflow_db"
MLFLOW_USER="mlflow"
MLFLOW_PASSWORD="mlflow"
MLFLOW_SCHEMA="mlflow"

echo "Creating user $MLFLOW_USER..."
psql -U "$DB_USER" -tc "SELECT 1 FROM pg_roles WHERE rolname='$MLFLOW_USER'" | grep -q 1 || \
psql -U "$DB_USER" -c "CREATE USER $MLFLOW_USER WITH PASSWORD '$MLFLOW_PASSWORD';"

echo "Creating database $MLFLOW_DB..."
psql -U "$DB_USER" -c "CREATE DATABASE $MLFLOW_DB OWNER $MLFLOW_USER;" || echo "$MLFLOW_DB already exists."

echo "Granting privileges on $MLFLOW_DB to $MLFLOW_USER..."
psql -U "$DB_USER" -d "$MLFLOW_DB" -c "GRANT ALL PRIVILEGES ON DATABASE $MLFLOW_DB TO $MLFLOW_USER;"



echo "Creating schema 'mlflow' in database $MLFLOW_DB..."
psql -U "$DB_USER" -d "$MLFLOW_DB" -c "CREATE SCHEMA IF NOT EXISTS mlflow AUTHORIZATION $MLFLOW_USER;"

# Create schema "mlflow" in mlflow_db and grant ownership to MLFLOW_USER
echo "Creating schema 'mlflow' in database $MLFLOW_DB..."
psql -U "$DB_USER" -d "$MLFLOW_DB" -c "CREATE SCHEMA IF NOT EXISTS mlflow AUTHORIZATION $MLFLOW_USER;"

echo "Granting privileges on schema 'mlflow' to $MLFLOW_USER..."
psql -U "$DB_USER" -d "$MLFLOW_DB" -c "GRANT ALL ON SCHEMA $MLFLOW_SCHEMA TO $MLFLOW_USER;"


# Prefect DB setup
PREFECT_DB="prefect"
PREFECT_USER="prefect"
PREFECT_PASSWORD="prefect"
PREFECT_SCHEMA="prefect"

echo "Creating user $PREFECT_USER if not exists..."
psql -U "$DB_USER" -tc "SELECT 1 FROM pg_roles WHERE rolname='$PREFECT_USER'" | grep -q 1 || \
psql -U "$DB_USER" -c "CREATE USER $PREFECT_USER WITH PASSWORD '$PREFECT_PASSWORD';"

echo "Creating database $PREFECT_DB..."
psql -U "$DB_USER" -tc "SELECT 1 FROM pg_database WHERE datname = '$PREFECT_DB'" | grep -q 1 || \
psql -U "$DB_USER" -c "CREATE DATABASE $PREFECT_DB OWNER $PREFECT_USER;"

echo "Granting privileges on $PREFECT_DB to $PREFECT_USER..."
psql -U "$DB_USER" -d "$PREFECT_DB" -c "GRANT ALL PRIVILEGES ON DATABASE $PREFECT_DB TO $PREFECT_USER;"

echo "Creating schema '$PREFECT_SCHEMA' in database $PREFECT_DB..."
psql -U "$DB_USER" -d "$PREFECT_DB" -c "CREATE SCHEMA IF NOT EXISTS $PREFECT_SCHEMA AUTHORIZATION $PREFECT_USER;"

echo "Granting privileges on schema '$PREFECT_SCHEMA' to $PREFECT_USER..."
psql -U "$DB_USER" -d "$PREFECT_DB" -c "GRANT ALL ON SCHEMA $PREFECT_SCHEMA TO $PREFECT_USER;"

# (Optional) Create sb schema in prefect_db as well
echo "Creating schema 'sb' in database $PREFECT_DB..."
psql -U "$DB_USER" -d "$PREFECT_DB" -c "CREATE SCHEMA IF NOT EXISTS sb AUTHORIZATION $PREFECT_USER;"
echo "Granting privileges on schema 'sb' to $PREFECT_USER..."
psql -U "$DB_USER" -d "$PREFECT_DB" -c "GRANT ALL ON SCHEMA sb TO $PREFECT_USER;"



psql -U "postgres" -d chembl_db <<EOF
CREATE TABLE public.chembl_ml_dataset_shuffled AS
SELECT *,
       ROW_NUMBER() OVER (ORDER BY RANDOM()) AS rownum
FROM public.chembl_ml_dataset;

-- Optional: Drop original table if not needed
DROP TABLE public.chembl_ml_dataset;

-- Optional: Rename new table to original name
ALTER TABLE public.chembl_ml_dataset_shuffled RENAME TO chembl_ml_dataset;
EOF