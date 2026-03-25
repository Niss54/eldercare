from dataclasses import dataclass


@dataclass(slots=True)
class AiRequest:
    feature: str
    payload: dict


@dataclass(slots=True)
class AiResponse:
    accepted: bool
    reason: str


class AiIntegrationPort:
    def submit(self, request: AiRequest) -> AiResponse:
        raise NotImplementedError


class DisabledAiIntegration(AiIntegrationPort):
    def submit(self, request: AiRequest) -> AiResponse:
        return AiResponse(accepted=False, reason="AI integration is feature-flagged off")


ai_integration_port = DisabledAiIntegration()
