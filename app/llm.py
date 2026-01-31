import os
import json
import time
import logging
from typing import List, Dict, Any, Optional

import openai
import jsonschema
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from dotenv import load_dotenv
from db.models import ProvenanceEntry, LLMCallProvenance
from app.db import SessionLocal

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
logger = logging.getLogger(__name__)

# Minimal extractor schema (extend for your use case)
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "property_id": {"type": "string"},
        "year_built": {"type": ["integer", "null"]},
        "gross_floor_area_sf": {"type": ["number", "null"]},
        "leases_count": {"type": "integer"}
    },
    "required": ["property_id", "leases_count"],
    "additionalProperties": False,
}


def _extract_provenance_values(provenance_context: Optional[Dict[str, str]], meta: Dict[str, Any], model: str):
    """Extracts and normalizes provenance-related values from context and meta."""
    property_id = provenance_context.get('property_id') if provenance_context else None
    field_path = provenance_context.get('field_path') if provenance_context and provenance_context.get('field_path') else 'llm_call'
    provider = provenance_context.get('provider') if provenance_context and provenance_context.get('provider') else model
    raw_reference = provenance_context.get('raw_reference') if provenance_context and provenance_context.get('raw_reference') else 'llm'
    confidence = float(meta.get('confidence', 0.5))
    return property_id, field_path, provider, raw_reference, confidence


def _get_db_session():
    """Return a DB session and a flag indicating whether we created it here.

    This handles the two possible shapes of SessionLocal used in the repo (callable sessionmaker or session instance).
    """
    created = False
    try:
        if callable(SessionLocal):
            session = SessionLocal()
            created = True
        else:
            session = SessionLocal
    except Exception:
        # Fallback: assume SessionLocal itself is a session
        session = SessionLocal
    return session, created


def _persist_provenance_entry(
    session,
    created_session: bool,
    property_id: str,
    field_path: str,
    provider: str,
    raw_reference: str,
    confidence: float,
    raw_value: Dict[str, Any],
):
    """Create and commit a ProvenanceEntry, handling rollback and optional session closing."""
    try:
        entry = ProvenanceEntry(
            property_id=property_id,
            field_path=field_path,
            provider=provider,
            raw_reference=raw_reference,
            confidence=confidence,
            raw_value=raw_value,
        )
        session.add(entry)
        session.commit()
        logger.debug("Persisted provenance entry id=%s for property=%s field=%s", getattr(entry, 'id', None), property_id, field_path)
    except Exception as e:
        logger.exception("Failed to persist provenance entry: %s", e)
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        if created_session:
            try:
                session.close()
            except Exception:
                pass


def record_provenance_stub(
    prompt: str,
    response_text: str,
    model: str,
    meta: Dict[str, Any],
    provenance_context: Optional[Dict[str, str]] = None,
):
    """
    Persist a provenance entry to the DB with richer metadata where possible.
    provenance_context (optional): {'property_id': '<uuid>', 'field_path': 'field.name', 'provider': 'openai'}

    If property_id is not provided we skip DB insert to avoid violating NOT NULL constraint on
    ProvenanceEntry.property_id. This keeps the function safe to call when only call-level
    provenance is desired.
    """
    logger.info("LLM call: model=%s attempt=%s tokens=%s", model, meta.get("attempt"), meta.get("usage"))

    property_id, field_path, provider, raw_reference, confidence = _extract_provenance_values(provenance_context, meta, model)

    raw_value = {
        'prompt': prompt,
        'response': response_text,
        'meta': meta,
    }

    # If we don't have a property_id, write a call-level provenance record to llm_call_provenance
    if not property_id:
        try:
            # prefer a lightweight insert using a new session
            session, created = _get_db_session()
            stmt = insert(LLMCallProvenance).values(
                request_id=meta.get('request_id'),
                model=model,
                provider=provider,
                prompt=prompt,
                response=response_text,
                usage=meta.get('usage'),
                property_id=None,
                field_path=field_path,
                confidence=confidence,
            )
            session.execute(stmt)
            session.commit()
            logger.debug("Inserted call-level llm_call_provenance entry for model=%s", model)
        except Exception as e:
            logger.exception("Failed to persist call-level provenance: %s", e)
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            if created:
                try:
                    session.close()
                except Exception:
                    pass
        return

    session, created = _get_db_session()
    _persist_provenance_entry(
        session=session,
        created_session=created,
        property_id=property_id,
        field_path=field_path,
        provider=provider,
        raw_reference=raw_reference,
        confidence=confidence,
        raw_value=raw_value,
    )


def call_llm_safe(
    model: str,
    doc_text: str,
    sources: List[Dict[str, str]],
    schema: Dict = EXTRACTION_SCHEMA,
    retries: int = 3,
    max_tokens: int = 600,
    temperature: float = 0.0,
    provenance_context: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Call an LLM safely for structured extraction.
    Returns parsed JSON that validates against `schema` or raises an error.
    """
    grounding = "\n\n".join(f"[{s.get('id','src')}]: {s.get('snippet','')}" for s in sources[:5])

    system = (
        "You are a strict JSON extractor. Reply ONLY with a single JSON object that matches the schema provided. "
        "Do not include any explanation, markdown, or backticks."
    )

    user = (
        f"Document text:\n{doc_text}\n\n"
        f"Grounding sources:\n{grounding}\n\n"
        "Return JSON matching this schema exactly:\n"
        f"{json.dumps(schema)}\n\n"
        "If a value is not present, use null."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    attempt = 0
    last_exception: Optional[Exception] = None
    while attempt < retries:
        attempt += 1
        try:
            resp = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp["choices"][0]["message"]["content"].strip()

            meta = {"attempt": attempt, "usage": resp.get("usage"), "model": model}

            # Persist LLM call provenance (full response + tokens etc.)
            try:
                record_provenance_stub(prompt=user, response_text=content, model=model, meta=meta, provenance_context=provenance_context)
            except Exception:
                logger.exception("Failed to record provenance for LLM call")

            parsed = json.loads(content)
            jsonschema.validate(instance=parsed, schema=schema)
            return parsed

        except json.JSONDecodeError as e:
            logger.warning("LLM returned invalid JSON (attempt %d): %s", attempt, e)
            # Give the assistant one chance to correct using its previous output
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": "Your previous reply was not valid JSON. Reply again with only the JSON object that matches the schema provided earlier."
            })
            time.sleep(1 * attempt)
            last_exception = e
            continue

        except jsonschema.ValidationError as e:
            logger.error("LLM output failed schema validation: %s", e)
            # Do not retry endlessly for validation errors; escalate
            raise

        except Exception as e:
            logger.exception("Unexpected error calling LLM (attempt %d): %s", attempt, e)
            last_exception = e
            time.sleep(2 * attempt)
            continue

    raise RuntimeError("LLM extraction failed") from last_exception
