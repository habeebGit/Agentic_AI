# Using prepared SQL with SQLAlchemy

This folder contains prepared, parameterized SQL queries (queries.sql) intended to be executed via SQLAlchemy's text() API or connection.execute(). Use named parameters as shown in the SQL (e.g. :property_id, :title).

Example usage (Python):

from sqlalchemy import create_engine, text

eng = create_engine("postgresql+psycopg2://user:pass@localhost/dbname")
with eng.begin() as conn:
    sql = open('db/sqlalchemy/queries.sql').read()
    # Extract the single query you want or load the file and execute specific statement using text()
    conn.execute(text("SELECT property_id FROM property_source_ids WHERE provider = :provider AND provider_id = :provider_id LIMIT 1"), {"provider":"county_records","provider_id":"CR-123"})

For multi-statement transactions use conn.begin() context manager and execute each prepared statement separately.

Note: For large applications consider embedding these queries in a proper repository layer or using an ORM model layer with SQLAlchemy Core/ORM for type-safe operations.
