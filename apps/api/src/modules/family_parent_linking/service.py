import secrets
from datetime import UTC, datetime, timedelta
from enum import Enum

from pydantic import BaseModel


class LinkStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"


class RelationshipType(str, Enum):
    parent = "parent"
    spouse = "spouse"
    child = "child"
    sibling = "sibling"
    caregiver = "caregiver"
    doctor = "doctor"


class LinkRequestRecord(BaseModel):
    id: str
    family_user_id: str
    parent_user_id: str
    relationship_type: RelationshipType = RelationshipType.parent
    invitation_token: str
    status: LinkStatus
    created_at: datetime
    expires_at: datetime
    decided_at: datetime | None = None


class FamilyLinkRecord(BaseModel):
    id: str
    family_user_id: str
    parent_user_id: str
    relationship_type: RelationshipType
    request_id: str
    linked_at: datetime


class FamilyLinkService:
    def __init__(self):
        self.requests: dict[str, LinkRequestRecord] = {}
        self.links: dict[str, FamilyLinkRecord] = {}

    def _is_expired(self, request: LinkRequestRecord) -> bool:
        return datetime.now(UTC) > request.expires_at

    def _expire_if_needed(self, request: LinkRequestRecord) -> None:
        if request.status == LinkStatus.pending and self._is_expired(request):
            request.status = LinkStatus.expired
            request.decided_at = datetime.now(UTC)

    def create_link_request(
        self,
        family_user_id: str,
        parent_user_id: str,
        relationship_type: RelationshipType = RelationshipType.parent,
    ) -> LinkRequestRecord:
        existing = [
            req
            for req in self.requests.values()
            if req.family_user_id == family_user_id
            and req.parent_user_id == parent_user_id
            and req.status == LinkStatus.pending
        ]
        if existing and not self._is_expired(existing[0]):
            return existing[0]
        request = LinkRequestRecord(
            id=secrets.token_urlsafe(12),
            family_user_id=family_user_id,
            parent_user_id=parent_user_id,
            relationship_type=relationship_type,
            invitation_token=secrets.token_urlsafe(18),
            status=LinkStatus.pending,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        self.requests[request.id] = request
        return request

    def approve_request(self, request_id: str, parent_user_id: str) -> FamilyLinkRecord:
        request = self.requests.get(request_id)
        if not request:
            raise ValueError("request not found")
        self._expire_if_needed(request)
        if request.parent_user_id != parent_user_id:
            raise ValueError("parent mismatch")
        if request.status != LinkStatus.pending:
            raise ValueError("request already decided")

        request.status = LinkStatus.approved
        request.decided_at = datetime.now(UTC)
        link = FamilyLinkRecord(
            id=secrets.token_urlsafe(12),
            family_user_id=request.family_user_id,
            parent_user_id=request.parent_user_id,
            relationship_type=request.relationship_type,
            request_id=request.id,
            linked_at=datetime.now(UTC),
        )
        self.links[link.id] = link
        return link

    def reject_request(self, request_id: str, parent_user_id: str) -> LinkRequestRecord:
        request = self.requests.get(request_id)
        if not request:
            raise ValueError("request not found")
        self._expire_if_needed(request)
        if request.parent_user_id != parent_user_id:
            raise ValueError("parent mismatch")
        if request.status != LinkStatus.pending:
            raise ValueError("request already decided")

        request.status = LinkStatus.rejected
        request.decided_at = datetime.now(UTC)
        return request

    def unlink(self, family_user_id: str, parent_user_id: str) -> bool:
        for link_id, link in list(self.links.items()):
            if link.family_user_id == family_user_id and link.parent_user_id == parent_user_id:
                del self.links[link_id]
                return True
        return False

    def list_requests_for_user(self, user_id: str) -> list[LinkRequestRecord]:
        for req in self.requests.values():
            self._expire_if_needed(req)
        return [
            req
            for req in self.requests.values()
            if req.family_user_id == user_id or req.parent_user_id == user_id
        ]

    def list_pending_invitations_for_parent(self, parent_user_id: str) -> list[LinkRequestRecord]:
        for req in self.requests.values():
            self._expire_if_needed(req)
        return [
            req
            for req in self.requests.values()
            if req.parent_user_id == parent_user_id and req.status == LinkStatus.pending
        ]

    def list_links_for_user(self, user_id: str) -> list[FamilyLinkRecord]:
        return [
            link
            for link in self.links.values()
            if link.family_user_id == user_id or link.parent_user_id == user_id
        ]


family_link_service = FamilyLinkService()
