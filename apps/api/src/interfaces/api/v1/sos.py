from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.api.v1.auth import _get_claims
from src.metrics import metrics_recorder
from src.modules.sos_alerting.service import sos_service

router = APIRouter(prefix="/sos", tags=["sos"])


class TriggerSosRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_user_id: str
    severity: str = Field(default="critical")
    cascade: list[dict] = Field(
        default_factory=lambda: [
            {"target_roles": ["family_member"], "delay_seconds": 0, "max_retries": 1, "retry_delay_seconds": 30},
            {
                "target_roles": ["caregiver", "doctor"],
                "delay_seconds": 60,
                "max_retries": 2,
                "retry_delay_seconds": 30,
                "fallback_roles": ["admin"],
            },
        ]
    )


class ProcessEscalationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    network_outage: bool = False


class ResolveIncidentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = None


class RunSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: str = Field(pattern="^(day|night|network_outage)$")


@router.post("/incidents/trigger")
def trigger_incident(payload: TriggerSosRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "sos:trigger" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: sos:trigger")

    incident = sos_service.trigger_incident(
        subject_user_id=payload.subject_user_id,
        initiated_by_user_id=claims["sub"],
        severity=payload.severity,
        cascade=payload.cascade,
    )
    return incident.model_dump()


@router.post("/incidents/{incident_id}/ack")
def acknowledge_incident(incident_id: str, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "sos:respond" not in permissions and "sos:trigger" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: sos:respond")

    try:
        incident = sos_service.acknowledge(incident_id=incident_id, responder_user_id=claims["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    metrics_recorder.observe_sos_response_time((datetime.now(UTC) - incident.created_at).total_seconds())
    return incident.model_dump()


@router.post("/incidents/{incident_id}/process-escalation")
def process_escalation(incident_id: str, payload: ProcessEscalationRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "sos:respond" not in permissions and "sos:trigger" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: sos:respond")

    try:
        incident = sos_service.process_escalation_tick(
            incident_id=incident_id,
            now=datetime.now(UTC),
            network_outage=payload.network_outage,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return incident.model_dump()


@router.post("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, payload: ResolveIncidentRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "sos:respond" not in permissions and "sos:trigger" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: sos:respond")

    try:
        incident = sos_service.resolve(incident_id=incident_id, resolver_user_id=claims["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    metrics_recorder.observe_sos_response_time((datetime.now(UTC) - incident.created_at).total_seconds())
    return incident.model_dump()


@router.get("/incidents/{incident_id}/timeline")
def get_incident_timeline(incident_id: str, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "sos:respond" not in permissions and "sos:trigger" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: sos:respond")

    try:
        timeline = sos_service.forensic_timeline(incident_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"count": len(timeline), "items": [event.model_dump() for event in timeline]}


@router.post("/simulations/run")
def run_sos_simulation(payload: RunSimulationRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "sos:respond" not in permissions and "sos:trigger" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: sos:respond")

    try:
        result = sos_service.simulate_scenario(payload.scenario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.model_dump()


@router.get("/incidents")
def list_incidents(claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "sos:respond" not in permissions and "sos:trigger" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: sos:respond")

    incidents = sos_service.list_incidents()
    return {"count": len(incidents), "items": [i.model_dump() for i in incidents]}
