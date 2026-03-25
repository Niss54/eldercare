from src.modules.family.application.services import FamilyLinkService
from src.modules.family.domain.models import FamilyLinkStatus, RelationshipType
from src.modules.family_parent_linking.service import FamilyLinkService as ParentLinkingService


def _build_service() -> FamilyLinkService:
    return FamilyLinkService(ParentLinkingService())


def test_family_application_service_invite_and_list_pending():
    service = _build_service()

    invited = service.invite(
        family_user_id="u_family",
        parent_user_id="u_parent",
        relationship_type=RelationshipType.parent,
    )

    assert invited.family_user_id == "u_family"
    assert invited.parent_user_id == "u_parent"
    assert invited.relationship_type == RelationshipType.parent
    assert invited.status == FamilyLinkStatus.invited

    pending = service.list_pending_for_parent("u_parent")
    assert len(pending) == 1
    assert pending[0].id == invited.id


def test_family_application_service_accept_and_reject():
    service = _build_service()

    first = service.invite(
        family_user_id="u_family",
        parent_user_id="u_parent",
        relationship_type=RelationshipType.spouse,
    )
    accepted = service.accept(first.id, "u_parent")
    assert accepted.status == FamilyLinkStatus.accepted
    assert accepted.relationship_type == RelationshipType.spouse

    second = service.invite(
        family_user_id="u_family",
        parent_user_id="u_parent",
        relationship_type=RelationshipType.child,
    )
    rejected = service.reject(second.id, "u_parent")
    assert rejected.status == FamilyLinkStatus.rejected
    assert rejected.relationship_type == RelationshipType.child
