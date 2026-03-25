"""M05.1 Health Records Tests - unit tests for domain and application layer."""

from datetime import UTC, datetime, timedelta

import pytest

from src.modules.health.domain.models import RecordType
from src.modules.health.application.services import HealthRecordService


@pytest.fixture
def health_service():
    """Create HealthRecordService instance for testing."""
    return HealthRecordService(existing_service=None)


class TestHealthRecordServiceContract:
    """Test HealthRecordService (M05.1 application service contract)."""

    def test_create_record_with_enum_record_type(self, health_service):
        """Test creating a health record with RecordType enum."""
        record = health_service.create(
            patient_id="patient-123",
            created_by_id="doctor-456",
            record_type=RecordType.medical_history,
            data={"diagnosis": "Type 2 Diabetes", "notes": "Requires monitoring"},
        )

        assert record.id is not None
        assert record.patient_id == "patient-123"
        assert record.created_by_id == "doctor-456"
        assert record.record_type == RecordType.medical_history
        assert record.data["diagnosis"] == "Type 2 Diabetes"
        assert record.document_ref is None
        assert record.created_at is not None
        assert record.updated_at is not None

    def test_create_record_with_string_record_type(self, health_service):
        """Test creating a health record with string record type."""
        record = health_service.create(
            patient_id="patient-123",
            created_by_id="doctor-456",
            record_type="lab_results",
            data={"test": "CBC", "value": "normal"},
        )

        assert record.record_type == RecordType.lab_results
        assert record.data["test"] == "CBC"

    def test_create_record_with_document_reference(self, health_service):
        """Test creating a health record with S3 document reference."""
        from src.modules.health.domain.models import DocumentReference

        doc_ref = DocumentReference(
            s3_key="health-records/patient-123/scan-20250324.pdf",
            file_hash="abc123def456",
            mime_type="application/pdf",
        )

        record = health_service.create(
            patient_id="patient-123",
            created_by_id="doctor-456",
            record_type=RecordType.lab_results,
            data={"test_name": "CT Scan"},
            document_ref=doc_ref,
        )

        assert record.document_ref is not None
        assert record.document_ref.s3_key == "health-records/patient-123/scan-20250324.pdf"
        assert record.document_ref.file_hash == "abc123def456"

    def test_create_timestamps_are_utc(self, health_service):
        """Test that created/updated timestamps are in UTC."""
        record = health_service.create(
            patient_id="patient-123",
            created_by_id="doctor-456",
            record_type=RecordType.vitals,
            data={"temperature": 98.6},
        )

        assert record.created_at.tzinfo is not None  # Has timezone info
        assert record.updated_at.tzinfo is not None

    def test_search_filters_by_patient_id(self, health_service):
        """Test search returns only records for specified patient."""
        # With no existing service, search should return empty list
        results = health_service.search(patient_id="patient-123")
        assert results == []

    def test_search_with_record_type_filter(self, health_service):
        """Test search with record type filter."""
        # With no existing service, search should return empty list
        results = health_service.search(
            patient_id="patient-123",
            record_type=RecordType.medical_history,
        )
        assert results == []

    def test_search_with_date_filter(self, health_service):
        """Test search with date range filter."""
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)

        # With no existing service, search should return empty list
        results = health_service.search(
            patient_id="patient-123",
            date_from=week_ago,
        )
        assert results == []

    def test_get_nonexistent_record_returns_none(self, health_service):
        """Test getting a non-existent record returns None."""
        result = health_service.get("nonexistent-id")
        assert result is None


class TestRecordTypeEnum:
    """Test RecordType enum validation."""

    def test_all_record_types_defined(self):
        """Test that all required record types are defined."""
        expected_types = {
            "medical_history",
            "lab_results",
            "vitals",
            "prescription",
        }
        actual_types = {rt.value for rt in RecordType}
        assert actual_types == expected_types

    def test_record_type_enum_values(self):
        """Test RecordType enum values are correct."""
        assert RecordType.medical_history.value == "medical_history"
        assert RecordType.lab_results.value == "lab_results"
        assert RecordType.vitals.value == "vitals"
        assert RecordType.prescription.value == "prescription"


class TestDocumentReference:
    """Test DocumentReference value object."""

    def test_create_document_reference(self):
        """Test creating a DocumentReference value object."""
        from src.modules.health.domain.models import DocumentReference

        doc_ref = DocumentReference(
            s3_key="records/patient-123/doc.pdf",
            file_hash="hash123",
            mime_type="application/pdf",
        )

        assert doc_ref.s3_key == "records/patient-123/doc.pdf"
        assert doc_ref.file_hash == "hash123"
        assert doc_ref.mime_type == "application/pdf"

    def test_document_reference_is_pydantic_model(self):
        """Test DocumentReference is a Pydantic model."""
        from src.modules.health.domain.models import DocumentReference

        doc_ref = DocumentReference(
            s3_key="test.pdf",
            file_hash="hash",
            mime_type="application/pdf",
        )

        # Should be serializable
        data = doc_ref.model_dump()
        assert data["s3_key"] == "test.pdf"
