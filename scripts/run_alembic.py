#!/usr/bin/env python3
"""Helper to run alembic with environment variables.

Usage:
  export DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname
  python scripts/run_alembic.py upgrade head

This script sets sqlalchemy.url in alembic config from DATABASE_URL or from .env file.
"""
import os
import sys
from alembic.config import Config
from alembic import command
from pathlib import Path
from dotenv import load_dotenv

# load .env if present
dotenv_path = Path('.') / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)

DB_URL = os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_URL')
if not DB_URL:
    print('Error: set DATABASE_URL or SQLALCHEMY_URL environment variable')
    sys.exit(2)

alembic_ini = Path(__file__).resolve().parents[1] / 'alembic.ini'
config = Config(str(alembic_ini))
config.set_main_option('sqlalchemy.url', DB_URL)
# Ensure alembic script location is absolute (so alembic finds the alembic/ folder regardless of CWD)
config.set_main_option('script_location', str(Path(__file__).resolve().parents[1] / 'alembic'))

# pass through alembic CLI args
if len(sys.argv) < 2:
    print('Usage: run_alembic.py <alembic_command> [args]')
    sys.exit(2)

cmd = sys.argv[1]
args = sys.argv[2:]

if cmd == 'upgrade' and args:
    command.upgrade(config, args[0])
elif cmd == 'downgrade' and args:
    command.downgrade(config, args[0])
elif cmd == 'current':
    command.current(config)
elif cmd == 'history':
    command.history(config)
else:
    # fallback for other commands
    getattr(command, cmd)(config, *args)
