#!/usr/bin/env python3
"""Seed the database with example commercial properties.

Usage:
  source .venv/bin/activate
  export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_ai
  python scripts/seed_properties.py
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Make sure project root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from db.models import Property, PropertySourceID, ProvenanceEntry

DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_URL') or 'postgresql+psycopg2://postgres:postgres@127.0.0.1:15432/agentic_ai'

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

SAMPLES = [
    {
        'source': {'provider': 'seed', 'id': 'SEED-001'},
        'title': 'Sunset Office Park',
        'address': {'street': '100 Sunset Blvd', 'city': 'Austin', 'state': 'TX', 'zip': '78701', 'country': 'US', 'lat':30.268, 'lon':-97.743},
        'propertyType': 'office',
        'buildingSqFt': 32000,
        'financials': {'last12Mo': {'grossIncome': 920000, 'netOperatingIncome': 400000, 'totalExpenses': 520000}},
        'provenance': [
            {'fieldPath': 'financials.last12Mo.noi', 'provider': 'seed', 'rawReference': 'seed://doc/001', 'confidence': 0.95, 'rawValue': {'noi': 400000}}
        ]
    },
    {
        'source': {'provider': 'seed', 'id': 'SEED-002'},
        'title': 'Riverside Industrial',
        'address': {'street': '250 Riverside Ave', 'city': 'Dallas', 'state': 'TX', 'zip': '75201', 'country': 'US', 'lat':32.7767, 'lon':-96.7970},
        'propertyType': 'industrial',
        'buildingSqFt': 85000,
        'financials': {'last12Mo': {'grossIncome': 1500000, 'netOperatingIncome': 900000, 'totalExpenses': 600000}},
        'provenance': [
            {'fieldPath': 'buildingSqFt', 'provider': 'seed', 'rawReference': 'seed://doc/002', 'confidence': 0.9, 'rawValue': {'buildingSqFt':85000}}
        ]
    },
    {
        'source': {'provider': 'seed', 'id': 'SEED-003'},
        'title': 'Harbor Retail Center',
        'address': {'street': '5 Harbor Way', 'city': 'San Diego', 'state': 'CA', 'zip': '92101', 'country': 'US', 'lat':32.7157, 'lon':-117.1611},
        'propertyType': 'retail',
        'buildingSqFt': 54000,
        'financials': {'last12Mo': {'grossIncome': 1100000, 'netOperatingIncome': 600000, 'totalExpenses': 500000}},
        'provenance': [
            {'fieldPath': 'address', 'provider': 'seed', 'rawReference': 'seed://doc/003', 'confidence': 0.92, 'rawValue': {'address':'verified'}}
        ]
    }
]


def seed():
    session = SessionLocal()
    try:
        for s in SAMPLES:
            provider = s['source']['provider']
            provider_id = s['source']['id']
            existing = session.query(PropertySourceID).filter_by(provider=provider, provider_id=provider_id).first()
            if existing:
                print(f"Skipping existing sample: {provider}/{provider_id} (property_id={existing.property_id})")
                continue

            prop = Property(
                title=s.get('title'),
                property_type=s.get('propertyType'),
                building_sqft=s.get('buildingSqFt'),
                address_street=s['address']['street'],
                address_city=s['address']['city'],
                address_state=s['address']['state'],
                address_zip=s['address']['zip'],
                address_country=s['address'].get('country','US'),
                lat=s['address'].get('lat'),
                lon=s['address'].get('lon')
            )
            session.add(prop)
            session.flush()

            psi = PropertySourceID(property_id=prop.id, provider=provider, provider_id=provider_id, raw_payload=s['source'])
            session.add(psi)

            # financials via raw SQL upsert
            last12 = s.get('financials', {}).get('last12Mo')
            if last12:
                session.execute(
                    text(
                        """
                        INSERT INTO financials_last12mo (property_id, gross_income, net_operating_income, total_expenses)
                        VALUES (:pid, :g, :n, :t)
                        ON CONFLICT (property_id) DO UPDATE
                          SET gross_income = EXCLUDED.gross_income,
                              net_operating_income = EXCLUDED.net_operating_income,
                              total_expenses = EXCLUDED.total_expenses
                        """
                    ),
                    {'pid': str(prop.id), 'g': last12.get('grossIncome'), 'n': last12.get('netOperatingIncome'), 't': last12.get('totalExpenses')}
                )

            # provenance
            for p in s.get('provenance', []):
                pe = ProvenanceEntry(property_id=prop.id, field_path=p['fieldPath'], provider=p['provider'], raw_reference=p.get('rawReference'), confidence=p.get('confidence', 0.5), raw_value=p.get('rawValue'))
                session.add(pe)

            session.commit()
            print(f"Inserted sample property {provider}/{provider_id} -> id={prop.id}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    seed()
