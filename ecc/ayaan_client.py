import httpx


class AyaanClient:
    """Thin client for the ayaan API (via gateway). Responses are {success, data}; returns data."""

    def __init__(self, settings, transport=None):
        self._http = httpx.AsyncClient(
            base_url=settings.ayaan_base_url.rstrip("/"),
            headers={"X-AYAAN-Token": settings.ayaan_token},
            timeout=15,
            transport=transport,
        )

    async def _call(self, method, path, **kw) -> tuple[int, dict | list | None]:
        r = await self._http.request(method, path, **kw)
        try:
            payload = r.json()
        except ValueError:
            payload = {}
        return r.status_code, payload.get("data") if isinstance(payload, dict) else None

    async def create_task(self, body: dict) -> tuple[int, dict]:
        return await self._call("POST", "/tasks", json=body)

    async def list_tasks(self, status: str | None = None) -> list:
        _, data = await self._call("GET", "/tasks", params={"status": status} if status else None)
        return data or []

    async def quotas(self) -> dict:
        _, data = await self._call("GET", "/quotas")
        return data or {}

    async def resume(self, task_id: str) -> tuple[int, dict]:
        return await self._call("POST", f"/tasks/{task_id}/resume")

    async def cancel(self, task_id: str) -> tuple[int, dict]:
        return await self._call("POST", f"/tasks/{task_id}/cancel")

    async def issue_preview(self, issue_key: str) -> dict | None:
        status, data = await self._call("GET", f"/issues/{issue_key}")
        return data if status == 200 else None

    async def aclose(self):
        await self._http.aclose()
