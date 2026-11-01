import httpx

from ecc.config.settings import Settings
from ecc.tickets.models import Ticket


class D94QueryClient:
    def __init__(self, settings: Settings):
        self.base_url = settings.query_base_url.rstrip("/")
        self.token = settings.query_service_token
        self.timeout = httpx.Timeout(20.0)

    async def create(self, ticket: Ticket) -> Ticket:
        payload = ticket.model_dump(mode="json", exclude={"created_at", "approved_by"})
        data = await self._request("POST", "/api/v1/ecc/tickets", json=payload)
        return Ticket.model_validate(data)

    async def get(self, ticket_id: str) -> Ticket | None:
        try:
            data = await self._request("GET", f"/api/v1/ecc/tickets/{ticket_id}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        return Ticket.model_validate(data)

    async def decide(self, ticket_id: str, action: str, actor_id: int) -> Ticket:
        data = await self._request(
            "POST",
            f"/api/v1/ecc/tickets/{ticket_id}/decision",
            json={"action": action, "actor_id": str(actor_id)},
        )
        return Ticket.model_validate(data)

    async def finish(self, ticket_id: str, status: str, result: str) -> Ticket:
        data = await self._request(
            "PATCH",
            f"/api/v1/ecc/tickets/{ticket_id}/result",
            json={"status": status, "result": result},
        )
        return Ticket.model_validate(data)

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        if not self.token:
            raise RuntimeError("ECC_QUERY_SERVICE_TOKEN is required")
        headers = {"X-ECC-Service-Token": self.token}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, self.base_url + path, headers=headers, **kwargs)
        response.raise_for_status()
        envelope = response.json()
        if not envelope.get("success") or not isinstance(envelope.get("data"), dict):
            raise RuntimeError("d94-query returned an invalid ECC ticket response")
        return envelope["data"]
