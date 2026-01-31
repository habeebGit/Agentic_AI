import os
import logging
import uuid
import json
from typing import Dict, Any

from rq import Queue
from redis import Redis

from db import make_engine, make_session, Base
from db.models import ProvenanceEntry, Property, Report

from app.llm import call_llm_safe, record_provenance_stub

# Minimal RQ worker example: enqueue a job that calls the LLM and persists results

def get_redis_queue(redis_url: str = None) -> Queue:
    redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    conn = Redis.from_url(redis_url)
    return Queue('default', connection=conn)


def persist_provenance(db_session, property_id: str, field_path: str, provider: str, raw_reference: str, confidence: float, raw_value: Dict[str, Any]):
    entry = ProvenanceEntry(
        property_id=property_id,
        field_path=field_path,
        provider=provider,
        raw_reference=raw_reference,
        confidence=confidence,
        raw_value=raw_value,
    )
    db_session.add(entry)
    db_session.commit()


def persist_report(db_session, property_id: str, summary: str, sections: Dict[str, Any], confidence: float):
    r = Report(
        property_id=property_id,
        report_id=str(uuid.uuid4()),
        summary=summary,
        sections=sections,
        confidence_overall=confidence,
        generated_at='now()'
    )
    db_session.add(r)
    db_session.commit()


def llm_extraction_job(property_id: str, doc_text: str, sources: Dict[str, str]):
    """
    This function runs in an RQ worker process. It imports the LLM helper and the DB session,
    calls the model, validates and persists provenance and a simple report.
    """
    from app.db import engine, SessionLocal

    session = SessionLocal()
    try:
        # Pass provenance_context so the LLM helper will persist per-field provenance linked to this property
        provenance_ctx_base = {'property_id': property_id, 'provider': os.environ.get('LLM_PROVIDER','openai')}
        parsed = call_llm_safe(
            model=os.environ.get('LLM_MODEL','gpt-4o-mini'),
            doc_text=doc_text,
            sources=sources,
            provenance_context=provenance_ctx_base,
        )

        # Example: write a provenance entry for each field using the centralized hook
        for k, v in parsed.items():
            field_ctx = {**provenance_ctx_base, 'field_path': f"extraction.{k}", 'confidence': 0.9}
            try:
                # use the centralized persistence (records both ProvenanceEntry and/or call-level table)
                record_provenance_stub(prompt=doc_text, response_text=json.dumps({k: v}), model=os.environ.get('LLM_MODEL','gpt-4o-mini'), meta={'attempt':1,'usage':None,'model':os.environ.get('LLM_MODEL','gpt-4o-mini'),'confidence':0.9}, provenance_context=field_ctx)
            except Exception:
                # fallback to legacy DB insert
                persist_provenance(session, property_id, f"{k}", provider='openai', raw_reference='llm', confidence=0.9, raw_value={'value': v})

        # Create a tiny summary/report
        summary = f"Extracted {len(parsed.keys())} fields via LLM"
        sections = {'extraction': parsed}
        persist_report(session, property_id, summary, sections, confidence=0.9)

    finally:
        session.close()


if __name__ == '__main__':
    q = get_redis_queue()
    # Example enqueue
    job = q.enqueue(llm_extraction_job, '00000000-0000-0000-0000-000000000000', 'Sample doc text here', [{'id':'d1','snippet':'Built 1998'}])
    print('Enqueued job', job.id)
