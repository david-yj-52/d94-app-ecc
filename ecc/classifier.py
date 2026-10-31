import httpx

from ecc.config import Settings
from ecc.models import IntentPlan


async def classify(ticket_id: str, prompt: str, settings: Settings) -> IntentPlan:
    if not settings.nano_endpoint:
        return IntentPlan(summary=prompt[:500], action_plan=["요청 내용을 검토하고 승인 후 실행합니다."])
    async with httpx.AsyncClient(timeout=settings.nano_timeout_seconds) as client:
        response = await client.post(
            f"{settings.nano_endpoint.rstrip('/')}/api/v1/classify",
            json={"ticket_id": ticket_id, "raw_prompt": prompt},
        )
        response.raise_for_status()
        return IntentPlan.model_validate(response.json())

