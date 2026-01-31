from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Date, Text, JSON, ForeignKey, Boolean, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, DOUBLE_PRECISION
from sqlalchemy.orm import relationship
from . import Base
import sqlalchemy.sql as sql

# Constants
_UUID_GEN = sql.text('gen_random_uuid()')
_NOW = sql.text('now()')
_PROPERTIES_FK = 'properties.id'
_USERS_FK = 'users.id'
_CASCADE_DELETE = 'all, delete-orphan'
_ONDELETE_SET_NULL = 'SET NULL'


class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    email = Column(Text, nullable=False, unique=True)
    full_name = Column(Text)
    role = Column(Text, nullable=False, default='analyst')
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)


class Property(Base):
    __tablename__ = 'properties'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    title = Column(Text)
    property_type = Column(Text, nullable=False)
    building_sqft = Column(Numeric)
    lot_sqft = Column(Numeric)
    year_built = Column(Integer)
    stories = Column(Integer)
    address_street = Column(Text, nullable=False)
    address_city = Column(Text, nullable=False)
    address_state = Column(Text, nullable=False)
    address_zip = Column(Text, nullable=False)
    address_country = Column(Text, nullable=False, server_default='US')
    lat = Column(DOUBLE_PRECISION)
    lon = Column(DOUBLE_PRECISION)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)
    last_synced_at = Column(TIMESTAMP(timezone=True))

    source_ids = relationship('PropertySourceID', back_populates='property', cascade=_CASCADE_DELETE)
    provenance_entries = relationship('ProvenanceEntry', back_populates='property', cascade=_CASCADE_DELETE)
    financial_last12mo = relationship('FinancialsLast12Mo', uselist=False, back_populates='property', cascade=_CASCADE_DELETE)
    leases = relationship('Lease', back_populates='property', cascade=_CASCADE_DELETE)
    documents = relationship('Document', back_populates='property', cascade=_CASCADE_DELETE)
    comps = relationship('Comp', back_populates='property', cascade=_CASCADE_DELETE)
    valuation_models = relationship('ValuationModel', back_populates='property', cascade=_CASCADE_DELETE)
    risk_scores = relationship('RiskScore', back_populates='property', cascade=_CASCADE_DELETE)
    agent_tasks = relationship('AgentTask', back_populates='property')
    reports = relationship('Report', back_populates='property')


class PropertySourceID(Base):
    __tablename__ = 'property_source_ids'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    provider = Column(Text, nullable=False)
    provider_id = Column(Text, nullable=False)
    raw_payload = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    property = relationship('Property', back_populates='source_ids')


class ProvenanceEntry(Base):
    __tablename__ = 'provenance_entries'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    field_path = Column(Text, nullable=False)
    provider = Column(Text, nullable=False)
    raw_reference = Column(Text)
    fetched_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)
    confidence = Column(Numeric, nullable=False)
    raw_value = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    property = relationship('Property', back_populates='provenance_entries')


class LLMCallProvenance(Base):
    __tablename__ = 'llm_call_provenance'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    request_id = Column(Text, nullable=True)
    model = Column(Text, nullable=False)
    provider = Column(Text, nullable=True)
    prompt = Column(Text)
    response = Column(Text)
    usage = Column(JSON)
    property_id = Column(UUID(as_uuid=True), ForeignKey(_PROPERTIES_FK, ondelete=_ONDELETE_SET_NULL), nullable=True)
    field_path = Column(Text, nullable=True)
    confidence = Column(Numeric, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    # optional relationship back to property for convenience
    property = relationship('Property')


class FinancialsLast12Mo(Base):
    __tablename__ = 'financials_last12mo'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    gross_income = Column(Numeric)
    net_operating_income = Column(Numeric)
    total_expenses = Column(Numeric)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    property = relationship('Property', back_populates='financial_last12mo')


class FinancialsHistory(Base):
    __tablename__ = 'financials_history'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    year = Column(Integer, nullable=False)
    noi = Column(Numeric)
    gross = Column(Numeric)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    property = relationship('Property')


class Lease(Base):
    __tablename__ = 'leases'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    tenant_name = Column(Text)
    leased_sqft = Column(Numeric)
    lease_start = Column(Date)
    lease_end = Column(Date)
    rent_psf = Column(Numeric)
    source = Column(Text)
    raw_payload = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    property = relationship('Property', back_populates='leases')


class Document(Base):
    __tablename__ = 'documents'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    url = Column(Text)
    mime_type = Column(Text)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    raw_metadata = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    property = relationship('Property', back_populates='documents')
    uploader = relationship('User')


class Comp(Base):
    __tablename__ = 'comps'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    provider = Column(Text)
    sale_date = Column(Date)
    sale_price = Column(Numeric)
    distance_meters = Column(Integer)
    similarity_score = Column(Numeric)
    raw_payload = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    property = relationship('Property', back_populates='comps')


class ValuationModel(Base):
    __tablename__ = 'valuation_models'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    model_name = Column(Text, nullable=False)
    model_version = Column(Text)
    inputs = Column(JSON)
    outputs = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    property = relationship('Property', back_populates='valuation_models')


class RiskScore(Base):
    __tablename__ = 'risk_scores'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    title_risk = Column(Numeric)
    flood_risk = Column(Numeric)
    market_risk = Column(Numeric)
    overall_confidence = Column(Numeric)
    details = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    property = relationship('Property', back_populates='risk_scores')


class AgentTask(Base):
    __tablename__ = 'agent_tasks'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    task_id = Column(Text, nullable=False, unique=True)
    agent_name = Column(Text, nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='SET NULL'))
    run_mode = Column(Text)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    status = Column(Text, nullable=False)
    log = Column(JSON)
    report_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'))
    request_id = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    property = relationship('Property', back_populates='agent_tasks')
    user = relationship('User')


class Report(Base):
    __tablename__ = 'reports'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='SET NULL'))
    report_id = Column(Text, nullable=False, unique=True)
    summary = Column(Text)
    sections = Column(JSON)
    confidence_overall = Column(Numeric)
    generated_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    property = relationship('Property', back_populates='reports')


class Approval(Base):
    __tablename__ = 'approvals'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_GEN)
    report_id = Column(UUID(as_uuid=True), ForeignKey('reports.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    decision = Column(Text, nullable=False)
    notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)

    report = relationship('Report')
    user = relationship('User')


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(BigInteger, primary_key=True)
    event_time = Column(TIMESTAMP(timezone=True), server_default=_NOW, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    event_type = Column(Text, nullable=False)
    payload = Column(JSON)

    user = relationship('User')
