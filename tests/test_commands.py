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
    assert tg.parse_run("/run CIRA-12 codex") == ("CIRA-12", "CODEX")
    assert tg.parse_run("/run CIRA-12") == ("CIRA-12", None)
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
    assert asked == ["QUEUED", "RUNNING", "PAUSED"]
    assert text.splitlines()[-1] == "P1 - CLAUDE PAUSED 재개 11-11 15:30"


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
