import secrets
from datetime import UTC, datetime

from pydantic import BaseModel


class HealthRecord(BaseModel):
    id: str
    subject_user_id: str
    created_by_user_id: str
    data_type: str
    summary: str
    object_key: str | None = None
    created_at: datetime
    updated_at: datetime


class HealthRecordService:
    def __init__(self):
        self.records: dict[str, HealthRecord] = {}

    def create_record(
        self,
        subject_user_id: str,
        created_by_user_id: str,
        data_type: str,
        summary: str,
        object_key: str | None,
        record_id: str | None = None,
    ) -> HealthRecord:
        now = datetime.now(UTC)
        if record_id is None:
            record_id = secrets.token_urlsafe(12)
        record = HealthRecord(
            id=record_id,
            subject_user_id=subject_user_id,
            created_by_user_id=created_by_user_id,
            data_type=data_type,
            summary=summary,
            object_key=object_key,
            created_at=now,
            updated_at=now,
        )
        self.records[record.id] = record
        return record

    def list_records(self, subject_user_id: str) -> list[HealthRecord]:
        return [record for record in self.records.values() if record.subject_user_id == subject_user_id]

    def get_record(self, record_id: str) -> HealthRecord | None:
        return self.records.get(record_id)


health_record_service = HealthRecordService()
