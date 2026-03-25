from dataclasses import dataclass


@dataclass(slots=True)
class DeviceEvent:
    device_id: str
    event_type: str
    payload: dict


class IotIntegrationPort:
    def ingest(self, event: DeviceEvent) -> dict:
        raise NotImplementedError


class DisabledIotIntegration(IotIntegrationPort):
    def ingest(self, event: DeviceEvent) -> dict:
        return {
            "accepted": False,
            "reason": "IoT integration is feature-flagged off",
            "device_id": event.device_id,
        }


iot_integration_port = DisabledIotIntegration()
