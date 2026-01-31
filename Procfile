web: ./scripts/wait_for_db.sh db 5432 60 && uvicorn app.main:app --host 0.0.0.0 --port 8000
worker: ./scripts/wait_for_db.sh db 5432 60 && rq worker default
