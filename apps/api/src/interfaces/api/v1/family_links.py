from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.interfaces.api.v1.auth import _get_claims
from src.modules.family_parent_linking.service import RelationshipType, family_link_service
from src.modules.identity_access.models import Role

router = APIRouter(prefix="/family-links", tags=["family-links"])


class LinkRequestCreate(BaseModel):
    parent_user_id: str
    relationship_type: RelationshipType = RelationshipType.parent


@router.post("/requests")
def request_link(payload: LinkRequestCreate, claims: dict = Depends(_get_claims)):
    role = Role(claims["role"])
    if role not in {Role.family_member, Role.admin}:
        raise HTTPException(status_code=403, detail="Only family member or admin can create link requests")

    family_user_id = claims["sub"]
    request = family_link_service.create_link_request(
        family_user_id=family_user_id,
        parent_user_id=payload.parent_user_id,
        relationship_type=payload.relationship_type,
    )
    return request.model_dump()


@router.get("/requests")
def list_requests(claims: dict = Depends(_get_claims)):
    requests = family_link_service.list_requests_for_user(claims["sub"])
    return {"count": len(requests), "items": [r.model_dump() for r in requests]}


@router.get("/invitations/pending")
def list_pending_invitations(claims: dict = Depends(_get_claims)):
    role = Role(claims["role"])
    if role not in {Role.parent, Role.admin}:
        raise HTTPException(status_code=403, detail="Only parent or admin can view pending invitations")

    if role == Role.admin:
        pending = [req for req in family_link_service.requests.values() if req.status.value == "pending"]
    else:
        pending = family_link_service.list_pending_invitations_for_parent(claims["sub"])

    return {"count": len(pending), "items": [req.model_dump() for req in pending]}


@router.post("/requests/{request_id}/approve")
def approve_request(request_id: str, claims: dict = Depends(_get_claims)):
    role = Role(claims["role"])
    if role not in {Role.parent, Role.admin}:
        raise HTTPException(status_code=403, detail="Only parent or admin can approve link requests")
    try:
        parent_user_id = claims["sub"] if role == Role.parent else family_link_service.requests[request_id].parent_user_id
        link = family_link_service.approve_request(request_id, parent_user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Request not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return link.model_dump()


@router.post("/requests/{request_id}/reject")
def reject_request(request_id: str, claims: dict = Depends(_get_claims)):
    role = Role(claims["role"])
    if role not in {Role.parent, Role.admin}:
        raise HTTPException(status_code=403, detail="Only parent or admin can reject link requests")
    try:
        parent_user_id = claims["sub"] if role == Role.parent else family_link_service.requests[request_id].parent_user_id
        req = family_link_service.reject_request(request_id, parent_user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Request not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return req.model_dump()


@router.get("/links/me")
def list_my_links(claims: dict = Depends(_get_claims)):
    links = family_link_service.list_links_for_user(claims["sub"])
    return {"count": len(links), "items": [l.model_dump() for l in links]}


@router.get("/network")
def family_network(claims: dict = Depends(_get_claims)):
    links = family_link_service.list_links_for_user(claims["sub"])
    return {
        "user_id": claims["sub"],
        "count": len(links),
        "items": [l.model_dump() for l in links],
    }


@router.delete("/links/{family_user_id}/{parent_user_id}")
def unlink(family_user_id: str, parent_user_id: str, claims: dict = Depends(_get_claims)):
    role = Role(claims["role"])
    actor_id = claims["sub"]

    if role not in {Role.family_member, Role.parent, Role.admin}:
        raise HTTPException(status_code=403, detail="Role cannot unlink")
    if role == Role.family_member and actor_id != family_user_id:
        raise HTTPException(status_code=403, detail="Family member can only unlink own relationships")
    if role == Role.parent and actor_id != parent_user_id:
        raise HTTPException(status_code=403, detail="Parent can only unlink own relationships")

    removed = family_link_service.unlink(family_user_id=family_user_id, parent_user_id=parent_user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"status": "unlinked", "family_user_id": family_user_id, "parent_user_id": parent_user_id}
