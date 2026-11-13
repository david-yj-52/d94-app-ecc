import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Literal

from aiogram import Bot
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, model_validator

from ecc.ayaan_client import AyaanClient
from ecc.config.settings import get_settings
from ecc.telegram.bot import notify_keyboard, render_notify, run_bot

settings = get_settings()
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.telegram_bot_token or not settings.allowed_user_ids:
        raise RuntimeError("ECC_TELEGRAM_BOT_TOKEN and ECC_TELEGRAM_ALLOWED_USER_IDS are required")
    bot = Bot(settings.telegram_bot_token)
    ayaan = AyaanClient(settings)
    app.state.bot = bot
    bot_task = asyncio.create_task(run_bot(bot, ayaan), name="ecc-telegram-bot")
    bot_task.add_done_callback(
        lambda t: not t.cancelled()
        and t.exception()
        and log.error("telegram polling died", exc_info=t.exception())
    )
    eureka_client = None
    if settings.eureka_enabled:
        from py_eureka_client import eureka_client as eureka

        eureka_client = eureka
        await eureka.init_async(  # sync init() fails inside a running event loop
            eureka_server=settings.eureka_url,
            app_name=settings.service_name,
            instance_host=settings.eureka_instance_host,
            instance_port=settings.eureka_instance_port,
            **({"instance_ip": settings.eureka_instance_ip} if settings.eureka_instance_ip else {}),
        )
    try:
        yield
    finally:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        if eureka_client:
            await eureka_client.stop_async()
        await ayaan.aclose()
        await bot.session.close()


app = FastAPI(title="D94 External Communication Channel", version="0.2.0", lifespan=lifespan)


async def require_api_token(x_ecc_token: str = Header(default="")):
    expected = settings.api_token.encode()
    if not expected or not secrets.compare_digest(x_ecc_token.encode(), expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


class NotifyButton(BaseModel):
    label: str
    action: Literal["resume", "cancel", "answer"]
    taskId: str | None = None
    requestId: str | None = None
    choice: int | None = None

    @model_validator(mode="after")
    def _target(self):
        if self.action == "answer":
            if not self.requestId or self.choice is None or not 0 <= self.choice <= 9:
                raise ValueError("answer needs requestId and choice 0~9")
        elif not self.taskId:
            raise ValueError(f"{self.action} needs taskId")
        return self


class NotifyBody(BaseModel):
    event: str
    title: str
    body: str
    buttons: list[NotifyButton] | None = None


@app.get("/actuator/health")
async def health():
    return {"status": "UP", "service": settings.service_name}


@app.post("/api/v1/notify")
async def notify(body: NotifyBody, request: Request, _auth: None = Depends(require_api_token)):
    text = render_notify(body.event, body.title, body.body)
    markup = notify_keyboard([b.model_dump() for b in body.buttons or []])
    sent = 0
    for uid in sorted(settings.allowed_user_ids):
        try:
            await request.app.state.bot.send_message(uid, text, reply_markup=markup)
            sent += 1
        except Exception:
            # one blocked user must not stop the rest; caller sees the count
            log.warning("notify send failed for user %s", uid, exc_info=True)
    if sent == 0 and settings.allowed_user_ids:
        return JSONResponse({"sent": 0}, status_code=502)  # nobody got it: let ayaan retry
    return {"sent": sent}
