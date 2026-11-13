from types import SimpleNamespace

import httpx
import pytest

from ecc.ayaan_client import AyaanClient
from ecc.telegram import bot as tg


class FakeAyaan:
    def __init__(self):
        self.calls = []

    async def create_task(self, body):
        self.calls.append(("create", body))
        return 201, {"id": "t1", "issueKey": body.get("issueKey")}

    async def resume(self, id):
        self.calls.append(("resume", id))
        return 200, {}

    async def cancel(self, id):
        self.calls.append(("cancel", id))
        return 200, {}


class FakeQuery:
    def __init__(self, data, user_id=1):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.answers = []
        self.message = SimpleNamespace(edit_text=self._edit)
        self.edits = []

    async def _edit(self, text, **kw):
        self.edits.append(text)

    async def answer(self, text="", **kw):
        self.answers.append(text)


@pytest.fixture(autouse=True)
def allowed(monkeypatch):
    monkeypatch.setattr(tg.settings, "telegram_allowed_user_ids", "1")


def test_parse_run_command():
    assert tg.parse_run("/run CIRA-12 codex") == ("CIRA-12", "CODEX", "PLAN")
    assert tg.parse_run("/run CIRA-12") == ("CIRA-12", None, "PLAN")
    assert tg.parse_run("/run CIRA-12 dev") == ("CIRA-12", None, "DEV")
    assert tg.parse_run("/run CIRA-12 codex DEV") == ("CIRA-12", "CODEX", "DEV")
    with pytest.raises(ValueError):
        tg.parse_run("/run")
    with pytest.raises(ValueError):
        tg.parse_run("/run bad key")


async def test_run_confirm_callback_creates_task():
    ayaan, q = FakeAyaan(), FakeQuery("ayn:run:CIRA-12:CODEX")
    await tg.handle_callback(q, ayaan)
    body = {"issueKey": "CIRA-12", "tool": "CODEX", "source": "TELEGRAM"}
    assert ayaan.calls == [("create", body)]


async def test_task_callback_uses_stored_prompt():
    key = tg.store_prompt("do the thing")
    assert len(key.encode()) <= 64
    ayaan, q = FakeAyaan(), FakeQuery(key)
    await tg.handle_callback(q, ayaan)
    assert ayaan.calls == [("create", {"prompt": "do the thing", "source": "TELEGRAM"})]


async def test_resume_button_calls_ayaan():
    ayaan, q = FakeAyaan(), FakeQuery("ayn:resume:abc")
    await tg.handle_callback(q, ayaan)
    assert ayaan.calls == [("resume", "abc")]


async def test_unauthorized_user_ignored():
    ayaan, q = FakeAyaan(), FakeQuery("ayn:resume:abc", user_id=99)
    await tg.handle_callback(q, ayaan)
    assert ayaan.calls == []


async def test_ayaan_client_sends_token_and_unwraps():
    seen = {}

    def handler(req: httpx.Request):
        seen["tok"] = req.headers["X-AYAAN-Token"]
        seen["path"] = req.url.path
        return httpx.Response(409, json={"success": False, "data": {"id": "old"}})

    s = SimpleNamespace(ayaan_base_url="http://x/ayaan", ayaan_token="tk")
    c = AyaanClient(s, transport=httpx.MockTransport(handler))
    assert await c.create_task({"prompt": "p"}) == (409, {"id": "old"})
    assert seen == {"tok": "tk", "path": "/ayaan/tasks"}


async def test_callback_answers_when_ayaan_down():
    class Down(FakeAyaan):
        async def resume(self, id):
            raise httpx.ConnectError("down")

    q = FakeQuery("ayn:resume:abc")
    await tg.handle_callback(q, Down())
    assert q.answers == ["ayaan 연결 실패"]


async def test_tasks_lists_only_active_statuses_in_kst():
    asked = []

    class Lister:
        async def list_tasks(self, status=None):
            asked.append(status)
            return [{"id": f"{status[0]}1", "toolCd": "CLAUDE", "status": status,
                     "resumeAt": "2026-11-11T06:30:00" if status == "PAUSED" else None}]

    text = await tg.active_tasks_text(Lister())
    assert asked == ["QUEUED", "RUNNING", "PAUSED", "WAITING"]
    assert text.splitlines()[-2] == "P1 - CLAUDE PAUSED 재개 11-11 15:30"


def test_join_capped_truncates_under_4000():
    lines = [f"line-{i:04d} " + "x" * 90 for i in range(100)]
    text = tg.join_capped(lines)
    assert len(text) < 4000 and text.endswith("건")
    shown = len(text.splitlines()) - 1
    assert text.splitlines()[-1] == f"… 외 {100 - shown}건"
    assert tg.join_capped(["a", "b"]) == "a\nb"


def test_kst_quota_reset():
    assert tg.kst("2026-11-10T23:00:00Z") == "11-11 08:00"
    assert tg.kst(None) is None


class AnswerAyaan(FakeAyaan):
    def __init__(self, status=200):
        super().__init__()
        self.status = status

    async def answer(self, rid, body):
        self.calls.append(("answer", rid, body))
        if self.status == 409:
            return 409, {"answer": "A", "answeredBy": "tg:2", "answeredAt": "2026-11-13T03:00:00"}
        return self.status, {"answer": "B안"}

    async def waiting(self):
        return [{"id": "r1", "kind": "QUESTION", "question": "A or B?", "taskId": "t1"}]


async def test_answer_button_records_user_and_removes_buttons():
    ayaan, q = AnswerAyaan(), FakeQuery("ayn:ans:r-1:1")
    q.message.text = "[WAITING] 질문\n\n요청 ID: r-1"
    await tg.handle_callback(q, ayaan)
    assert ayaan.calls == [("answer", "r-1", {"choice": 1, "answeredBy": "tg:1"})]
    assert q.edits == ["[WAITING] 질문\n\n요청 ID: r-1\n\n✔ B안 (응답됨)"]


async def test_answer_button_already_handled_alerts():
    ayaan, q = AnswerAyaan(409), FakeQuery("ayn:ans:r-1:0")
    await tg.handle_callback(q, ayaan)
    assert q.edits == [] and q.answers[-1].startswith("이미 처리된 요청입니다 (tg:2, 11-13 12:00)")


async def test_answer_callback_rejects_bad_choice_and_stranger():
    ayaan = AnswerAyaan()
    q = FakeQuery("ayn:ans:r-1:x")
    await tg.handle_callback(q, ayaan)
    assert ayaan.calls == [] and q.answers == ["알 수 없는 동작입니다."]
    q = FakeQuery("ayn:ans:r-1:0", user_id=99)
    await tg.handle_callback(q, ayaan)
    assert ayaan.calls == []


async def test_run_dev_callback_and_legacy_4_part_data():
    ayaan = FakeAyaan()
    await tg.handle_callback(FakeQuery("ayn:run:CIRA-1:-:DEV"), ayaan)
    await tg.handle_callback(FakeQuery("ayn:run:CIRA-1:-:PLAN"), ayaan)
    await tg.handle_callback(FakeQuery("ayn:run:CIRA-1:-"), ayaan)
    phases = [c[1].get("phase") for c in ayaan.calls]
    assert phases == ["DEV", None, None]


def test_answer_keyboard_and_size_limit():
    rid = "123e4567-e89b-12d3-a456-426614174000"  # query OBJ_ID is a uuid
    btns = [{"label": f"선택 {i}", "action": "answer", "requestId": rid, "choice": i}
            for i in range(5)]
    kb = tg.notify_keyboard(btns)
    assert len(kb.inline_keyboard) == 5  # >3 buttons: one per row
    data = kb.inline_keyboard[4][0].callback_data
    assert data == f"ayn:ans:{rid}:4" and len(data.encode()) <= 64
    two = tg.notify_keyboard(btns[:2] + [{"label": "취소", "action": "cancel", "taskId": "t"}])
    assert len(two.inline_keyboard) == 1
    assert two.inline_keyboard[0][2].callback_data == "ayn:cancel:t"


def _reply(text, author_id=42, is_bot=True):
    author = SimpleNamespace(id=author_id, is_bot=is_bot)
    return SimpleNamespace(reply_to_message=SimpleNamespace(from_user=author, text=text))


def test_reply_request_id_only_from_own_bot():
    note = "[WAITING] x\n요청 ID: abc-123"
    assert tg.reply_request_id(_reply(note), 42) == "abc-123"
    assert tg.reply_request_id(_reply(note, author_id=7), 42) is None  # another bot
    assert tg.reply_request_id(_reply(note, is_bot=False), 42) is None  # a user's message
    assert tg.reply_request_id(_reply("no id here"), 42) is None


async def test_waiting_text():
    assert "r1 [QUESTION] A or B? (작업 t1)" in await tg.waiting_text(AnswerAyaan())
