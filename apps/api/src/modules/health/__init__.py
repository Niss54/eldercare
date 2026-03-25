"""M05.1 Health Records Module - DDD module for clinical data storage."""

from src.modules.health.application.services import health_record_service_m05
from src.modules.health.domain.models import DocumentReference, HealthRecord, RecordType
from src.modules.health.infrastructure.s3_provider import AwsS3Provider, LocalS3Provider, S3Provider, get_s3_provider

__all__ = [
    # Domain
    "HealthRecord",
    "RecordType",
    "DocumentReference",
    # Application
    "health_record_service_m05",
    # Infrastructure
    "S3Provider",
    "AwsS3Provider",
    "LocalS3Provider",
    "get_s3_provider",
]
