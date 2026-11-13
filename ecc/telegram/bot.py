import functools
import re
import time
import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ecc.config.settings import get_settings

settings = get_settings()

_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9]*-\d+$")
_PROMPT_TTL = 600
KST = ZoneInfo("Asia/Seoul")
ACTIVE = ("QUEUED", "RUNNING", "PAUSED", "WAITING")
# ayaan puts this line in every request notification; a reply to it is a free-text answer
_REQ_ID = re.compile(r"요청 ID: ([0-9A-Za-z-]{1,64})")
MAX_TEXT = 4000
# ponytail: in-memory, single instance; prompts are lost on restart (callback then says expired)
_prompts: dict[str, tuple[str, float]] = {}


def guard_ayaan(fn):
    """Reply (message) or answer (callback) when ayaan is unreachable, so nothing hangs."""

    @functools.wraps(fn)
    async def wrapper(event, *args, **kwargs):
        try:
            return await fn(event, *args, **kwargs)
        except httpx.HTTPError:
            await event.answer("ayaan 연결 실패")

    return wrapper


def _authorized(user_id: int) -> bool:
    return user_id in settings.allowed_user_ids


def parse_run(text: str) -> tuple[str, str | None, str]:
    """-> (issue key, tool or None, phase). A trailing `dev` skips planning (PLAN is default)."""
    parts = (text or "").split()[1:]
    phase = "DEV" if parts and parts[-1].lower() == "dev" else "PLAN"
    if phase == "DEV":
        parts.pop()
    if not 1 <= len(parts) <= 2 or not _KEY.match(parts[0]):
        raise ValueError("사용법: /run <이슈키> [tool] [dev]")
    return parts[0], parts[1].upper() if len(parts) == 2 else None, phase


def store_prompt(prompt: str) -> str:
    now = time.monotonic()
    for k in [k for k, (_, exp) in _prompts.items() if exp < now]:
        del _prompts[k]
    key = f"ayn:task:{uuid.uuid4().hex[:8]}"
    _prompts[key] = (prompt, now + _PROMPT_TTL)
    return key


def take_prompt(key: str) -> str | None:
    item = _prompts.pop(key, None)
    return item[0] if item and item[1] >= time.monotonic() else None


def render_notify(event: str, title: str, body: str) -> str:
    return f"[{event}] {title}\n\n{body}"


def _callback_data(b: dict) -> str:
    if b["action"] == "answer":
        return f"ayn:ans:{b['requestId']}:{b['choice']}"
    return f"ayn:{b['action']}:{b['taskId']}"


def notify_keyboard(buttons) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    keys = [InlineKeyboardButton(text=b["label"], callback_data=_callback_data(b)) for b in buttons]
    # long choice labels do not fit side by side: more than 3 buttons go one per row
    return InlineKeyboardMarkup(inline_keyboard=[keys] if len(keys) <= 3 else [[k] for k in keys])


def reply_request_id(message, bot_id: int | None) -> str | None:
    """Request id from the bot's own notification this message replies to, else None."""
    src = message.reply_to_message
    author = getattr(src, "from_user", None)
    if not author or not author.is_bot or author.id != bot_id:
        return None
    m = _REQ_ID.search(src.text or "")
    return m[1] if m else None


def confirm_keyboard(run_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="실행", callback_data=run_data),
        InlineKeyboardButton(text="취소", callback_data="ayn:no"),
    ]])


def kst(ts: str | None) -> str | None:
    """ayaan timestamps are naive UTC (or carry an offset): show them as KST MM-DD HH:MM."""
    if not ts:
        return None
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
    return dt.astimezone(KST).strftime("%m-%d %H:%M")


def _task_line(t: dict) -> str:
    extra = f" 재개 {kst(t['resumeAt'])}" if t.get("resumeAt") else ""
    return f"{t.get('id')} {t.get('issueKey') or '-'} {t.get('toolCd')} {t.get('status')}{extra}"


def join_capped(lines: list[str], limit: int = MAX_TEXT) -> str:
    """Join lines under Telegram's 4096-char cap, ending with '… 외 N건' when cut."""
    out: list[str] = []
    for i, line in enumerate(lines):
        rest = len(lines) - i
        if len("\n".join([*out, line, f"… 외 {rest}건"])) >= limit:
            return "\n".join([*out, f"… 외 {rest}건"])
        out.append(line)
    return "\n".join(out)


async def answer_text(ayaan, request_id: str, body: dict) -> str:
    status, data = await ayaan.answer(request_id, body)
    data = data if isinstance(data, dict) else {}
    if status == 200:
        return f"✔ {data.get('answer') or ''} (응답됨)"
    if status == 409:
        by, at = data.get("answeredBy") or "-", kst(data.get("answeredAt")) or "-"
        return f"이미 처리된 요청입니다 ({by}, {at})"
    if status == 404:
        return "요청을 찾을 수 없습니다."
    return f"응답 실패 ({status})"


async def waiting_text(ayaan) -> str:
    lines = [
        f"{r.get('id')} [{r.get('kind')}] {(r.get('question') or '-')[:80]}"
        f" (작업 {r.get('taskId')})"
        for r in await ayaan.waiting()
    ]
    return join_capped(lines) or "응답 대기 중인 요청이 없습니다."


async def active_tasks_text(ayaan) -> str:
    items = [t for s in ACTIVE for t in await ayaan.list_tasks(s)]
    return join_capped([_task_line(t) for t in items]) or "작업이 없습니다."


@guard_ayaan
async def handle_callback(query: CallbackQuery, ayaan) -> None:
    if not query.from_user or not _authorized(query.from_user.id):
        return await query.answer("허용되지 않은 사용자입니다.", show_alert=True)
    data = query.data or ""
    parts = data.split(":")
    if data == "ayn:no":
        text = "취소했습니다."
    elif parts[:2] == ["ayn", "ans"] and len(parts) == 4 and parts[3].isdigit():
        # callback_data is untrusted: ayaan re-checks the request is OPEN and choice in range
        body = {"choice": int(parts[3]), "answeredBy": f"tg:{query.from_user.id}"}
        result = await answer_text(ayaan, parts[2], body)
        if not result.startswith("✔"):
            return await query.answer(result, show_alert=True)
        await query.answer()
        if query.message:  # editing without reply_markup also removes the buttons
            await query.message.edit_text(f"{query.message.text or ''}\n\n{result}")
        return
    elif parts[:2] == ["ayn", "run"] and len(parts) in (4, 5):
        body = {"issueKey": parts[2], "source": "TELEGRAM"}
        if parts[3] and parts[3] != "-":
            body["tool"] = parts[3]
        if len(parts) == 5 and parts[4] == "DEV":  # 4 parts: messages sent before TSTA-2
            body["phase"] = "DEV"
        status, task = await ayaan.create_task(body)
        text = _created_text(status, task)
    elif parts[:2] == ["ayn", "task"] and len(parts) == 3:
        prompt = take_prompt(data)
        if prompt is None:
            text = "요청이 만료되었습니다. /task를 다시 보내세요."
        else:
            text = _created_text(*await ayaan.create_task({"prompt": prompt, "source": "TELEGRAM"}))
    elif parts[:2] in (["ayn", "resume"], ["ayn", "cancel"]) and len(parts) == 3:
        call = ayaan.resume if parts[1] == "resume" else ayaan.cancel
        status, _ = await call(parts[2])
        text = f"{parts[1]} 요청 완료" if status < 300 else f"{parts[1]} 실패 ({status})"
    else:
        return await query.answer("알 수 없는 동작입니다.")
    await query.answer()
    if query.message:
        await query.message.edit_text(text)


def _created_text(status: int, task) -> str:
    task = task if isinstance(task, dict) else {}
    if status == 201:
        return f"작업 생성됨: {task.get('id')} ({task.get('issueKey') or 'prompt'})"
    if status == 409:
        return f"이미 진행 중인 작업이 있습니다: {task.get('id')} ({task.get('status')})"
    return f"작업 생성 실패 ({status})"


def build_dispatcher(ayaan) -> Dispatcher:
    dp = Dispatcher()

    def deny(message: Message) -> bool:
        return not message.from_user or not _authorized(message.from_user.id)

    @dp.message(CommandStart())
    async def start(message: Message):
        if deny(message):
            return await message.answer("허용되지 않은 사용자입니다.")
        await message.answer(
            "/run <이슈키> [tool] [dev]\n/task <프롬프트>\n/tasks\n/waiting\n"
            "/answer <요청ID> <답변>\n/quota\n/resume <id>\n/cancel <id>\n"
            "질문 알림에 답장하면 자유 답변으로 전달됩니다."
        )

    @dp.message(Command("run"))
    @guard_ayaan
    async def run(message: Message):
        if deny(message):
            return await message.answer("허용되지 않은 사용자입니다.")
        try:
            key, tool, phase = parse_run(message.text or "")
        except ValueError as exc:
            return await message.answer(str(exc))
        issue = await ayaan.issue_preview(key)
        if issue is None:
            return await message.answer(f"이슈를 찾을 수 없습니다: {key}")
        tool = tool or issue.get("defaultTool") or "-"
        await message.answer(
            f"{key} {issue.get('title')}\n프로젝트: {issue.get('projectKey')}\n"
            f"경로: {issue.get('workspacePath')}\n도구: {tool}\n"
            f"단계: {'바로 개발' if phase == 'DEV' else '기획부터'}",
            reply_markup=confirm_keyboard(f"ayn:run:{key}:{tool}:{phase}"),
        )

    @dp.message(Command("task"))
    @guard_ayaan
    async def task(message: Message):
        if deny(message):
            return await message.answer("허용되지 않은 사용자입니다.")
        prompt = (message.text or "").partition(" ")[2].strip()
        if not prompt:
            return await message.answer("사용법: /task <프롬프트>")
        await message.answer(
            f"다음 프롬프트로 작업을 실행할까요?\n\n{prompt[:1000]}",
            reply_markup=confirm_keyboard(store_prompt(prompt)),
        )

    @dp.message(Command("tasks"))
    @guard_ayaan
    async def tasks(message: Message):
        if deny(message):
            return await message.answer("허용되지 않은 사용자입니다.")
        await message.answer(await active_tasks_text(ayaan))

    @dp.message(Command("quota"))
    @guard_ayaan
    async def quota(message: Message):
        if deny(message):
            return await message.answer("허용되지 않은 사용자입니다.")
        d = await ayaan.quotas()
        lines = [
            f"{q.get('toolCd')} {q.get('windowCd')} {q.get('usedPct')}% "
            f"reset={kst(q.get('resetsAt')) or '-'} {q.get('status')}"
            for q in d.get("quotas", [])
        ] + [f"! {w}" for w in d.get("warnings", [])]
        await message.answer(join_capped(lines) or "쿼터 정보가 없습니다.")

    for name in ("resume", "cancel"):
        @dp.message(Command(name))
        @guard_ayaan
        async def act(message: Message, _n=name):
            if deny(message):
                return await message.answer("허용되지 않은 사용자입니다.")
            tid = (message.text or "").partition(" ")[2].strip()
            if not tid:
                return await message.answer(f"사용법: /{_n} <id>")
            call = ayaan.resume if _n == "resume" else ayaan.cancel
            status, _ = await call(tid)
            await message.answer(f"{_n} 완료" if status < 300 else f"{_n} 실패 ({status})")

    @dp.message(Command("waiting"))
    @guard_ayaan
    async def waiting(message: Message):
        if deny(message):
            return await message.answer("허용되지 않은 사용자입니다.")
        await message.answer(await waiting_text(ayaan))

    @dp.message(Command("answer"))
    @guard_ayaan
    async def answer(message: Message):
        if deny(message):
            return await message.answer("허용되지 않은 사용자입니다.")
        _, req_id, text = ((message.text or "").split(maxsplit=2) + ["", ""])[:3]
        if not req_id or not text.strip():
            return await message.answer("사용법: /answer <요청ID> <답변>")
        body = {"answer": text.strip(), "answeredBy": f"tg:{message.from_user.id}"}
        await message.answer(await answer_text(ayaan, req_id, body))

    @dp.message(F.reply_to_message, F.text, ~F.text.startswith("/"))
    @guard_ayaan
    async def reply_answer(message: Message):
        if deny(message):
            return await message.answer("허용되지 않은 사용자입니다.")
        req_id = reply_request_id(message, message.bot.id if message.bot else None)
        if req_id is None:
            return  # a reply to anything but our request notification is ignored
        body = {"answer": message.text.strip(), "answeredBy": f"tg:{message.from_user.id}"}
        await message.answer(await answer_text(ayaan, req_id, body))

    @dp.callback_query(F.data.startswith("ayn:"))
    async def cb(query: CallbackQuery):
        await handle_callback(query, ayaan)

    return dp


async def run_bot(bot: Bot, ayaan) -> None:
    dp = build_dispatcher(ayaan)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
