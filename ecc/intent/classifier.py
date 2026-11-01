import httpx

from ecc.config.settings import Settings
from ecc.tickets.models import IntentPlan


async def classify(ticket_id: str, prompt: str, settings: Settings) -> IntentPlan:
    if not settings.nano_endpoint:
        if not settings.allowed_clis:
            raise ValueError("ECC_CLI_ALLOWLIST must contain at least one CLI")
        return IntentPlan(
            target_cli=sorted(settings.allowed_clis)[0],
            summary=prompt[:500],
            action_plan=["요청 내용을 검토하고 승인 후 실행합니다."],
        )
    async with httpx.AsyncClient(timeout=settings.nano_timeout_seconds) as client:
        response = await client.post(
            f"{settings.nano_endpoint.rstrip('/')}/api/v1/classify",
            json={"ticket_id": ticket_id, "raw_prompt": prompt},
        )
        response.raise_for_status()
        plan = IntentPlan.model_validate(response.json())
        if plan.target_cli.lower() not in settings.allowed_clis:
            raise ValueError("Nano selected a CLI that is not allowlisted")
        plan.target_cli = plan.target_cli.lower()
        return plan

