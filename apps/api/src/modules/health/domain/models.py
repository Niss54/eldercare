"""M05.1 Health Records Domain Models - DDD aggregates for clinical data storage."""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class RecordType(str, Enum):
    """Health record type enumeration for M05.1."""

    medical_history = "medical_history"
    lab_results = "lab_results"
    vitals = "vitals"
    prescription = "prescription"


class DocumentReference(BaseModel):
    """Value object representing an S3-stored document reference."""

    s3_key: str = Field(description="S3 object key for the document")
    file_hash: str = Field(description="SHA256 hash of the file content")
    mime_type: str = Field(description="MIME type of the document")


class HealthRecord(BaseModel):
    """HealthRecord aggregate for M05.1 - clinical and wellness data storage.
    
    - id: Unique identifier for the record
    - patient_id: User ID of the record subject
    - created_by_id: User ID of the record creator
    - record_type: RecordType enum value
    - data: JSONB data containing clinical information
    - document_ref: Optional reference to S3-stored document
    - created_at: Timestamp of record creation (UTC)
    - updated_at: Timestamp of last update (UTC)
    """

    id: str
    patient_id: str
    created_by_id: str
    record_type: RecordType
    data: dict
    document_ref: DocumentReference | None = None
    created_at: datetime
    updated_at: datetime
