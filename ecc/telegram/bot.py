from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ecc.config.settings import get_settings
from ecc.intent.classifier import classify
from ecc.tickets.models import Ticket, TicketStatus

settings = get_settings()


def _authorized(user_id: int) -> bool:
    return user_id in settings.allowed_user_ids


def _approval_keyboard(ticket_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ 승인", callback_data=f"approve:{ticket_id}"),
        InlineKeyboardButton(text="❌ 거절", callback_data=f"reject:{ticket_id}"),
    ]])


async def notify_approval(ticket) -> None:
    if not settings.telegram_bot_token or not settings.allowed_user_ids:
        return
    bot = Bot(settings.telegram_bot_token)
    plan_text = "\n".join(f"{i}. {item}" for i, item in enumerate(ticket.action_plan, 1))
    try:
        await bot.send_message(
            min(settings.allowed_user_ids),
            f"[작업 승인 요청]\n티켓: {ticket.ticket_id}\n의도: {ticket.intent}\nCLI: {ticket.target_cli}\n"
            f"요약: {ticket.summary}\n\n[계획]\n{plan_text}\n\n승인 후 CLI가 실행됩니다.",
            reply_markup=_approval_keyboard(ticket.ticket_id),
        )
    finally:
        await bot.session.close()


async def run_bot(app) -> None:
    bot = Bot(settings.telegram_bot_token)
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def start(message: Message):
        if not message.from_user or not _authorized(message.from_user.id):
            return await message.answer("허용되지 않은 사용자입니다.")
        await message.answer("ECC 작업 요청: /task <요청 내용>")

    @dispatcher.message(Command("task"))
    async def task(message: Message):
        if not message.from_user or not _authorized(message.from_user.id):
            return await message.answer("허용되지 않은 사용자입니다.")
        prompt = (message.text or "").partition(" ")[2].strip()
        if not prompt:
            return await message.answer("사용법: /task <요청 내용>")
        try:
            app.state.executor.resolve_workspace(settings.telegram_default_workspace)
        except (OSError, ValueError) as exc:
            return await message.answer(f"작업공간 설정 오류: {exc}")
        ticket = Ticket(
            prompt=prompt, workspace=settings.telegram_default_workspace
        )
        try:
            plan = await classify(ticket.ticket_id, ticket.prompt, settings)
            ticket.intent, ticket.target_cli = plan.intent, plan.target_cli.lower()
            ticket.summary, ticket.action_plan = plan.summary, plan.action_plan
            ticket.status = TicketStatus.AWAITING_CONFIRM
        except Exception:
            ticket.status = TicketStatus.FAILED
            ticket.result = "Intent classification failed"
            ticket.summary = "요청 분류에 실패했습니다."
            ticket = await app.state.query_client.create(ticket)
            return await message.answer(f"분류 실패: {ticket.ticket_id}")
        ticket = await app.state.query_client.create(ticket)
        await message.answer(
            f"[작업 승인 요청]\n티켓: {ticket.ticket_id}\n의도: {ticket.intent}\nCLI: {ticket.target_cli}\n"
            f"요약: {ticket.summary}\n\n[계획]\n" + "\n".join(
                f"{i}. {item}" for i, item in enumerate(ticket.action_plan, 1)
            ) + "\n\n승인 후 CLI가 실행됩니다.",
            reply_markup=_approval_keyboard(ticket.ticket_id),
        )

    @dispatcher.callback_query(F.data.startswith(("approve:", "reject:")))
    async def decide(query: CallbackQuery):
        if not query.from_user or not _authorized(query.from_user.id):
            return await query.answer("허용되지 않은 사용자입니다.", show_alert=True)
        action, ticket_id = (query.data or "").split(":", 1)
        try:
            ticket = await app.state.query_client.decide(ticket_id, action, query.from_user.id)
        except Exception:
            return await query.answer("이미 처리되었거나 query 서버에 연결할 수 없습니다.", show_alert=True)
        if action == "reject":
            if query.message:
                await query.message.edit_text(f"티켓 {ticket_id} 거절됨")
            return await query.answer("거절했습니다.")
        if query.message:
            await query.message.edit_text(f"티켓 {ticket_id} 실행 중…")
        await query.answer("승인했습니다.")
        try:
            result = await app.state.executor.execute(ticket.target_cli, ticket.workspace, ticket.prompt)
            ticket = await app.state.query_client.finish(ticket_id, TicketStatus.DONE, result)
        except Exception as exc:
            ticket = await app.state.query_client.finish(ticket_id, TicketStatus.FAILED, str(exc)[:12000])
        await bot.send_message(query.from_user.id, f"[{ticket.status}] {ticket_id}\n\n{(ticket.result or '')[-3500:]}")

    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await bot.session.close()

