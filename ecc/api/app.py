import asyncio
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from ecc.config.settings import get_settings
from ecc.execution.runner import CliExecutor
from ecc.intent.classifier import classify
from ecc.telegram.bot import run_bot
from ecc.tickets.models import CreateTicket, Ticket, TicketStatus
from ecc.tickets.query_client import D94QueryClient

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.telegram_bot_token or not settings.allowed_user_ids:
        raise RuntimeError("ECC_TELEGRAM_BOT_TOKEN and ECC_TELEGRAM_ALLOWED_USER_IDS are required")
    if not settings.query_base_url or not settings.query_service_token:
        raise RuntimeError("ECC_QUERY_BASE_URL and ECC_QUERY_SERVICE_TOKEN are required")
    executor = CliExecutor(settings)
    await executor.start()
    app.state.query_client = D94QueryClient(settings)
    app.state.executor = executor
    bot_task = None
    eureka_client = None
    if settings.telegram_bot_token:
        bot_task = asyncio.create_task(run_bot(app), name="ecc-telegram-bot")
    if settings.eureka_enabled:
        from py_eureka_client import eureka_client as eureka

        eureka_client = eureka
        eureka.init(
            eureka_server=settings.eureka_url,
            app_name=settings.service_name,
            instance_host=settings.eureka_instance_host,
            instance_port=settings.eureka_instance_port,
            **({"instance_ip": settings.eureka_instance_ip} if settings.eureka_instance_ip else {}),
        )
    try:
        yield
    finally:
        await executor.stop()
        if bot_task:
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
        if eureka_client:
            eureka_client.stop()


app = FastAPI(title="D94 External Communication Channel", version="0.1.0", lifespan=lifespan)


async def require_api_token(x_ecc_token: str = Header(default="")):
    if not settings.api_token or not secrets.compare_digest(x_ecc_token, settings.api_token):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/actuator/health")
async def health(request: Request):
    return {"status": "UP", "service": settings.service_name}


@app.post("/api/v1/tickets", response_model=Ticket, status_code=status.HTTP_201_CREATED)
async def create_ticket(body: CreateTicket, request: Request, _auth: None = Depends(require_api_token)):
    try:
        request.app.state.executor.resolve_workspace(body.workspace)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ticket = Ticket(prompt=body.prompt, workspace=body.workspace)
    try:
        plan = await classify(ticket.ticket_id, ticket.prompt, settings)
        ticket.intent = plan.intent
        ticket.target_cli = plan.target_cli.lower()
        ticket.summary = plan.summary
        ticket.action_plan = plan.action_plan
        ticket.status = TicketStatus.AWAITING_CONFIRM
    except Exception:
        ticket.status = TicketStatus.FAILED
        ticket.summary = "요청 분류에 실패했습니다."
        ticket.result = "Intent classification failed"

    try:
        ticket = await request.app.state.query_client.create(ticket)
        if ticket.status == TicketStatus.AWAITING_CONFIRM:
            from ecc.telegram.bot import notify_approval

            await notify_approval(ticket)
        return ticket
    except Exception as exc:
        raise HTTPException(status_code=502, detail="d94-query ticket operation failed") from exc


@app.get("/api/v1/tickets/{ticket_id}", response_model=Ticket)
async def get_ticket(ticket_id: str, request: Request, _auth: None = Depends(require_api_token)):
    ticket = await request.app.state.query_client.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

