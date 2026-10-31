import asyncio
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from redis.asyncio import Redis

from ecc.classifier import classify
from ecc.config import get_settings
from ecc.executor import CliExecutor
from ecc.models import CreateTicket, Ticket, TicketStatus
from ecc.store import TicketStore
from ecc.telegram_bot import run_bot

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.telegram_bot_token or not settings.allowed_user_ids:
        raise RuntimeError("ECC_TELEGRAM_BOT_TOKEN and ECC_TELEGRAM_ALLOWED_USER_IDS are required")
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    executor = CliExecutor(settings)
    await executor.start()
    app.state.redis = redis
    app.state.store = TicketStore(redis, settings)
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
        await redis.aclose()


app = FastAPI(title="D94 External Communication Channel", version="0.1.0", lifespan=lifespan)


async def require_api_token(x_ecc_token: str = Header(default="")):
    if not settings.api_token or not secrets.compare_digest(x_ecc_token, settings.api_token):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/actuator/health")
async def health(request: Request):
    try:
        await request.app.state.redis.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc
    return {"status": "UP", "service": settings.service_name}


@app.post("/api/v1/tickets", response_model=Ticket, status_code=status.HTTP_201_CREATED)
async def create_ticket(body: CreateTicket, request: Request, _auth: None = Depends(require_api_token)):
    try:
        request.app.state.executor.resolve_workspace(body.workspace)
        ticket = Ticket(prompt=body.prompt, workspace=body.workspace)
        plan = await classify(ticket.ticket_id, ticket.prompt, settings)
        if plan.target_cli.lower() not in settings.allowed_clis:
            plan.target_cli = "claude" if "claude" in settings.allowed_clis else sorted(settings.allowed_clis)[0]
        ticket.intent = plan.intent
        ticket.target_cli = plan.target_cli.lower()
        ticket.summary = plan.summary
        ticket.action_plan = plan.action_plan
        ticket.status = TicketStatus.AWAITING_CONFIRM
        await request.app.state.store.save(ticket)
        if settings.telegram_bot_token:
            from ecc.telegram_bot import notify_approval

            await notify_approval(ticket)
        return ticket
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Intent classifier unavailable") from exc


@app.get("/api/v1/tickets/{ticket_id}", response_model=Ticket)
async def get_ticket(ticket_id: str, request: Request, _auth: None = Depends(require_api_token)):
    ticket = await request.app.state.store.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

