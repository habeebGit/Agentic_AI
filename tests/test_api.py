import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_post_and_get_property_minimal():
    payload = {
        "sourceIds": [{"provider": "test", "id": "TEST-1"}],
        "address": {"street": "100 Main St", "city": "Austin", "state": "TX", "zip": "78701"},
        "propertyType": "office",
        "buildingSqFt": 25000
    }
    r = client.post('/api/properties', json=payload)
    assert r.status_code == 200 or r.status_code == 201
    data = r.json()
    assert 'id' in data

    prop_id = data['id']
    r2 = client.get(f'/api/properties/{prop_id}')
    assert r2.status_code == 200
    body = r2.json()
    assert body['propertyType'] == 'office'
    assert body['address']['city'] == 'Austin'
