from datetime import UTC, datetime

from src.modules.family.domain.models import FamilyLink, FamilyLinkStatus, RelationshipType
from src.modules.family_parent_linking.service import (
    FamilyLinkRecord,
    FamilyLinkService as ParentLinkingService,
    LinkRequestRecord,
)


def _status_from_invitation_status(status: str) -> FamilyLinkStatus:
    if status == "pending":
        return FamilyLinkStatus.invited
    if status == "approved":
        return FamilyLinkStatus.accepted
    if status == "rejected":
        return FamilyLinkStatus.rejected
    if status == "expired":
        return FamilyLinkStatus.expired
    return FamilyLinkStatus.revoked


class FamilyLinkService:
    """Application-facing family linking service for M03.1 domain workflows."""

    def __init__(self, linking_service: ParentLinkingService) -> None:
        self._linking_service = linking_service

    def send_invitation(
        self,
        *,
        family_user_id: str,
        parent_user_id: str,
        relationship_type: RelationshipType,
    ) -> FamilyLink:
        invitation = self._linking_service.create_link_request(
            family_user_id=family_user_id,
            parent_user_id=parent_user_id,
            relationship_type=relationship_type,
        )
        return self._to_domain_link(invitation)

    def invite(
        self,
        *,
        family_user_id: str,
        parent_user_id: str,
        relationship_type: RelationshipType,
    ) -> FamilyLink:
        return self.send_invitation(
            family_user_id=family_user_id,
            parent_user_id=parent_user_id,
            relationship_type=relationship_type,
        )

    def accept_invitation(self, invite_id: str, parent_user_id: str) -> FamilyLink:
        link = self._linking_service.approve_request(
            request_id=invite_id,
            parent_user_id=parent_user_id,
        )
        return self._from_approved_link(link)

    def accept(self, request_id: str, parent_user_id: str) -> FamilyLink:
        return self.accept_invitation(invite_id=request_id, parent_user_id=parent_user_id)

    def reject(self, request_id: str, parent_user_id: str) -> FamilyLink:
        invitation = self._linking_service.reject_request(
            request_id=request_id,
            parent_user_id=parent_user_id,
        )
        return self._to_domain_link(invitation)

    def list_pending_for_parent(self, parent_user_id: str) -> list[FamilyLink]:
        invitations = self._linking_service.list_pending_invitations_for_parent(
            parent_user_id=parent_user_id
        )
        return [self._to_domain_link(invitation) for invitation in invitations]

    def unlink(self, *, family_user_id: str, parent_user_id: str) -> bool:
        return self._linking_service.unlink(
            family_user_id=family_user_id,
            parent_user_id=parent_user_id,
        )

    def _to_domain_link(self, invitation: LinkRequestRecord) -> FamilyLink:
        relationship = invitation.relationship_type
        relationship_type = (
            relationship
            if isinstance(relationship, RelationshipType)
            else RelationshipType(str(relationship.value if hasattr(relationship, "value") else relationship))
        )
        status = _status_from_invitation_status(invitation.status.value)
        decided_at = (
            datetime.now(UTC)
            if status in {FamilyLinkStatus.accepted, FamilyLinkStatus.rejected}
            else None
        )
        return FamilyLink(
            id=invitation.id,
            family_user_id=invitation.family_user_id,
            parent_user_id=invitation.parent_user_id,
            relationship_type=relationship_type,
            status=status,
            invited_at=invitation.created_at,
            decided_at=decided_at,
        )

    def _from_approved_link(self, link: FamilyLinkRecord) -> FamilyLink:
        relationship = link.relationship_type
        relationship_type = (
            relationship
            if isinstance(relationship, RelationshipType)
            else RelationshipType(str(relationship.value if hasattr(relationship, "value") else relationship))
        )
        return FamilyLink(
            id=link.id,
            family_user_id=link.family_user_id,
            parent_user_id=link.parent_user_id,
            relationship_type=relationship_type,
            status=FamilyLinkStatus.accepted,
            invited_at=link.linked_at,
            decided_at=link.linked_at,
        )
