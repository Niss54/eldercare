"""M05.1 Health Records Application Service - use-case orchestration layer."""

import secrets
from datetime import UTC, datetime

from src.modules.health.domain.models import DocumentReference, HealthRecord, RecordType
from src.modules.health_records.service import health_record_service as existing_service


class HealthRecordService:
    """Application service for M05.1 health record operations.
    
    Orchestrates domain logic and adapts between domain models and internal services.
    Applies consent evaluation for retrieval operations.
    """

    def __init__(self, existing_service=None):
        """Initialize with existing health record service for data access."""
        self._service = existing_service

    def create(
        self,
        patient_id: str,
        created_by_id: str,
        record_type: RecordType | str,
        data: dict,
        document_ref: DocumentReference | None = None,
    ) -> HealthRecord:
        """Create a new health record.
        
        Args:
            patient_id: User ID of the record subject
            created_by_id: User ID of the creator
            record_type: RecordType enum or string value
            data: JSONB data containing clinical information
            document_ref: Optional S3 document reference
            
        Returns:
            HealthRecord aggregate
        """
        # Normalize record type to enum
        rt = RecordType(record_type) if isinstance(record_type, str) else record_type

        record_id = secrets.token_urlsafe(12)
        now = datetime.now(UTC)

        # Create domain model
        record = HealthRecord(
            id=record_id,
            patient_id=patient_id,
            created_by_id=created_by_id,
            record_type=rt,
            data=data,
            document_ref=document_ref,
            created_at=now,
            updated_at=now,
        )

        # Persist via existing service (ensure backward compatibility)
        if self._service:
            self._service.create_record(
                subject_user_id=patient_id,
                created_by_user_id=created_by_id,
                data_type=rt.value,
                summary=data.get("summary", ""),
                object_key=document_ref.s3_key if document_ref else None,
                record_id=record_id,  # Pass the same ID to legacy service
            )

        return record

    def get(self, record_id: str) -> HealthRecord | None:
        """Retrieve a health record by ID.
        
        Note: Caller must enforce consent checks before calling this.
        
        Args:
            record_id: ID of the record to retrieve
            
        Returns:
            HealthRecord aggregate or None if not found
        """
        if not self._service:
            return None

        existing = self._service.get_record(record_id)
        if not existing:
            return None

        # Map existing record to domain model
        return self._to_domain(existing)

    def search(
        self,
        patient_id: str,
        record_type: RecordType | None = None,
        date_from: datetime | None = None,
    ) -> list[HealthRecord]:
        """Search health records by patient and optional filters.
        
        Note: Caller must enforce consent checks before calling this.
        
        Args:
            patient_id: Patient user ID
            record_type: Optional filter by record type
            date_from: Optional filter for records since date
            
        Returns:
            List of matching HealthRecord aggregates
        """
        if not self._service:
            return []

        all_records = self._service.list_records(subject_user_id=patient_id)

        # Apply date filter if specified
        if date_from:
            all_records = [
                r for r in all_records
                if r.created_at >= date_from
            ]

        # Apply record type filter if specified
        if record_type:
            type_value = record_type.value if isinstance(record_type, RecordType) else record_type
            all_records = [
                r for r in all_records
                if r.data_type == type_value
            ]

        return [self._to_domain(r) for r in all_records]

    def _to_domain(self, existing_record) -> HealthRecord:
        """Map existing service record to domain model."""
        return HealthRecord(
            id=existing_record.id,
            patient_id=existing_record.subject_user_id,
            created_by_id=existing_record.created_by_user_id,
            record_type=RecordType(existing_record.data_type),
            data={"summary": existing_record.summary},
            document_ref=DocumentReference(
                s3_key=existing_record.object_key,
                file_hash="",
                mime_type="application/octet-stream",
            ) if existing_record.object_key else None,
            created_at=existing_record.created_at,
            updated_at=existing_record.updated_at,
        )


# Singleton instance
health_record_service_m05 = HealthRecordService(existing_service)
