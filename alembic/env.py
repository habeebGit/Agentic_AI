from logging.config import fileConfig
import logging
import os
import sys
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# this is the Alembic Config object, which provides the values from the .ini file in use.
config = context.config

# Interpret the config file for Python logging. If alembic.ini logging sections are incomplete,
# fall back to a simple basicConfig to avoid KeyError during tests or env differences.
try:
    fileConfig(config.config_file_name)
except Exception:
    logging.basicConfig(level=logging.INFO)

# make project root importable and load metadata
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db import Base
from db.models import *  # noqa: F401,F403

target_metadata = Base.metadata


def run_migrations_offline():
    # Allow DATABASE_URL env var to override the alembic.ini value
    url = os.environ.get('DATABASE_URL') or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    # Prefer DATABASE_URL env var if set; otherwise use config section
    url = os.environ.get('DATABASE_URL')
    if url:
        connectable = create_engine(url, poolclass=pool.NullPool)
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
