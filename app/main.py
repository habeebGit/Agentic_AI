from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
from uuid import UUID
from typing import List, Optional
from pathlib import Path
import os
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_db
from sqlalchemy.orm import Session
from db.models import Property, PropertySourceID, ProvenanceEntry, Report
import sqlalchemy

app = FastAPI(title="Commercial Due-Diligence Agent API", openapi_url="/openapi.json")

# CORS configuration for dashboard and local development
cors_env = os.environ.get('CORS_ORIGINS')
if cors_env:
    origins = [o.strip() for o in cors_env.split(',') if o.strip()]
else:
    origins = ["http://localhost:8000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for the dashboard (resolve relative to this file)
static_dir = Path(__file__).resolve().parent / "static"
if not static_dir.exists():
    static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class AddressIn(BaseModel):
    street: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)
    zip: str = Field(..., min_length=3)
    country: Optional[str] = 'US'
    lat: Optional[float] = None
    lon: Optional[float] = None


class FinancialsLast12MoIn(BaseModel):
    grossIncome: Optional[float]
    netOperatingIncome: Optional[float]
    totalExpenses: Optional[float]


class ProvenanceIn(BaseModel):
    fieldPath: str
    provider: str
    rawReference: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    rawValue: Optional[dict] = None


class PropertyCreate(BaseModel):
    sourceIds: List[dict] = Field(..., min_items=1)
    address: AddressIn
    propertyType: str
    buildingSqFt: Optional[float] = None
    financials: Optional[dict] = None
    provenance: Optional[List[ProvenanceIn]] = None


@app.post('/api/properties', response_model=dict)
def upsert_property(payload: PropertyCreate, db: Session = Depends(get_db)):
    try:
        # validate payload (pydantic already validated)
        pass
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())

    # Try upsert by source id: if any sourceId exists, update that property, else create new
    prop = None
    for s in payload.sourceIds:
        provider = s.get('provider')
        provider_id = s.get('id') or s.get('providerId') or s.get('externalId')
        if not provider or not provider_id:
            continue
        existing = db.query(PropertySourceID).filter_by(provider=provider, provider_id=provider_id).first()
        if existing:
            prop = db.query(Property).get(existing.property_id)
            break

    if not prop:
        prop = Property(
            property_type=payload.propertyType,
            address_street=payload.address.street,
            address_city=payload.address.city,
            address_state=payload.address.state,
            address_zip=payload.address.zip,
            address_country=payload.address.country,
            building_sqft=payload.buildingSqFt
        )
        db.add(prop)
        db.flush()

    # attach source ids
    for s in payload.sourceIds:
        provider = s.get('provider')
        provider_id = s.get('id') or s.get('providerId') or s.get('externalId')
        if not provider or not provider_id:
            continue
        # upsert property_source_ids
        existing = db.query(PropertySourceID).filter_by(property_id=prop.id, provider=provider, provider_id=provider_id).first()
        if not existing:
            psi = PropertySourceID(property_id=prop.id, provider=provider, provider_id=provider_id, raw_payload=s)
            db.add(psi)

    # financials
    if payload.financials:
        last12 = payload.financials.get('last12Mo') if isinstance(payload.financials, dict) else None
        if last12:
            try:
                db.execute(sqlalchemy.text("INSERT INTO financials_last12mo (property_id, gross_income, net_operating_income, total_expenses) VALUES (:pid, :g, :n, :t) ON CONFLICT (property_id) DO UPDATE SET gross_income = EXCLUDED.gross_income, net_operating_income = EXCLUDED.net_operating_income, total_expenses = EXCLUDED.total_expenses"), {'pid': str(prop.id), 'g': last12.get('grossIncome'), 'n': last12.get('netOperatingIncome'), 't': last12.get('totalExpenses')})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"DB error writing financials: {e}")

    # provenance
    if payload.provenance:
        for p in payload.provenance:
            pe = ProvenanceEntry(property_id=prop.id, field_path=p.fieldPath, provider=p.provider, raw_reference=p.rawReference, confidence=p.confidence, raw_value=p.rawValue)
            db.add(pe)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB commit failed: {e}")

    return { 'id': str(prop.id), 'status': 'ingested', 'normalized': True }


@app.get('/api/properties/{prop_id}', response_model=dict)
def get_property(prop_id: UUID, db: Session = Depends(get_db)):
    prop = db.query(Property).get(prop_id)
    if not prop:
        raise HTTPException(status_code=404, detail='Property not found')

    # assemble response
    source_ids = [ { 'provider': s.provider, 'id': s.provider_id } for s in prop.source_ids ]
    address = {
        'street': prop.address_street,
        'city': prop.address_city,
        'state': prop.address_state,
        'zip': prop.address_zip,
        'country': prop.address_country,
        'lat': prop.lat,
        'lon': prop.lon
    }
    return {
        'id': str(prop.id),
        'sourceIds': source_ids,
        'address': address,
        'propertyType': prop.property_type,
        'buildingSqFt': float(prop.building_sqft) if prop.building_sqft else None
    }


# New endpoints for dashboard
@app.get('/api/reports')
def list_reports(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(Report).order_by(Report.generated_at.desc()).limit(limit).all()
    result = []
    for r in rows:
        result.append({
            'id': str(r.id),
            'reportId': r.report_id,
            'propertyId': str(r.property_id) if r.property_id else None,
            'summary': r.summary,
            'generatedAt': r.generated_at.isoformat() if r.generated_at else None,
            'confidenceOverall': float(r.confidence_overall) if r.confidence_overall is not None else None
        })
    return JSONResponse(content=result)


@app.get('/api/properties/{prop_id}/provenance')
def get_provenance(prop_id: UUID, db: Session = Depends(get_db)):
    rows = db.query(ProvenanceEntry).filter_by(property_id=prop_id).order_by(ProvenanceEntry.fetched_at.desc()).all()
    result = []
    for p in rows:
        result.append({
            'id': str(p.id),
            'fieldPath': p.field_path,
            'provider': p.provider,
            'rawReference': p.raw_reference,
            'fetchedAt': p.fetched_at.isoformat() if p.fetched_at else None,
            'confidence': float(p.confidence),
            'rawValue': p.raw_value
        })
    return JSONResponse(content=result)


@app.get('/dashboard')
def dashboard():
    return FileResponse('app/static/dashboard.html')


@app.get('/')
def root():
    """Serve the dashboard at the site root for convenience."""
    return FileResponse('app/static/dashboard.html')


@app.get('/api/properties')
def list_properties(page: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    if page < 1:
        page = 1
    if limit < 1 or limit > 500:
        limit = 50
    offset = (page - 1) * limit
    rows = db.query(Property).order_by(Property.updated_at.desc()).offset(offset).limit(limit).all()
    result = []
    for p in rows:
        result.append({
            'id': str(p.id),
            'address': {
                'street': p.address_street,
                'city': p.address_city,
                'state': p.address_state,
                'zip': p.address_zip,
                'country': p.address_country
            },
            'propertyType': p.property_type,
            'buildingSqFt': float(p.building_sqft) if p.building_sqft is not None else None,
            'lastSyncedAt': p.last_synced_at.isoformat() if p.last_synced_at else None,
            'updatedAt': p.updated_at.isoformat() if p.updated_at else None
        })
    return JSONResponse(content={'page': page, 'limit': limit, 'items': result})
