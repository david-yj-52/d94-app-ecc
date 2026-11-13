from fastapi.testclient import TestClient

from ecc.api import app as api


class FakeBot:
    def __init__(self):
        self.calls = []

    async def send_message(self, chat_id, text, reply_markup=None):
        self.calls.append((chat_id, text, reply_markup))


def _client(monkeypatch):
    bot = FakeBot()
    monkeypatch.setattr(api.settings, "api_token", "t0ken")
    monkeypatch.setattr(api.settings, "telegram_allowed_user_ids", "1,2")
    api.app.state.bot = bot
    return TestClient(api.app), bot  # no context manager: lifespan not run


BODY = {
    "event": "RATE_LIMITED",
    "title": "CIRA-12 paused",
    "body": "resume at 15:00",
    "buttons": [{"label": "Resume", "action": "resume", "taskId": "abc"}],
}


def test_notify_requires_token(monkeypatch):
    client, bot = _client(monkeypatch)
    assert client.post("/api/v1/notify", json=BODY).status_code == 401
    assert client.post("/api/v1/notify", json=BODY, headers={"X-ECC-Token": "x"}).status_code == 401
    assert bot.calls == []


def test_notify_sends_to_all_allowed_users(monkeypatch):
    client, bot = _client(monkeypatch)
    r = client.post("/api/v1/notify", json=BODY, headers={"X-ECC-Token": "t0ken"})
    assert r.status_code == 200 and r.json() == {"sent": 2}
    assert sorted(c[0] for c in bot.calls) == [1, 2]
    assert bot.calls[0][1] == "[RATE_LIMITED] CIRA-12 paused\n\nresume at 15:00"
    assert bot.calls[0][2].inline_keyboard[0][0].callback_data == "ayn:resume:abc"


def test_notify_non_ascii_token_is_401(monkeypatch):
    client, _ = _client(monkeypatch)
    r = client.post("/api/v1/notify", json=BODY, headers={"X-ECC-Token": "토큰".encode()})
    assert r.status_code == 401


def test_notify_502_when_nobody_received(monkeypatch):
    client, bot = _client(monkeypatch)

    async def boom(*a, **k):
        raise RuntimeError("blocked")

    bot.send_message = boom
    r = client.post("/api/v1/notify", json=BODY, headers={"X-ECC-Token": "t0ken"})
    assert r.status_code == 502 and r.json() == {"sent": 0}


def test_lifespan_eureka_uses_async_api(monkeypatch):
    import asyncio

    from py_eureka_client import eureka_client

    calls = []

    async def init_async(**kw):
        calls.append("init")

    async def stop_async():
        calls.append("stop")

    def sync(*a, **k):
        raise AssertionError("sync eureka call inside the event loop")

    async def idle_bot(bot, ayaan):
        await asyncio.Event().wait()

    for name, fn in (("init_async", init_async), ("stop_async", stop_async),
                     ("init", sync), ("stop", sync)):
        monkeypatch.setattr(eureka_client, name, fn)
    monkeypatch.setattr(api, "run_bot", idle_bot)
    monkeypatch.setattr(api.settings, "telegram_bot_token", "123456:ABCdef")
    monkeypatch.setattr(api.settings, "telegram_allowed_user_ids", "1")
    monkeypatch.setattr(api.settings, "eureka_enabled", True)
    with TestClient(api.app):
        pass
    assert calls == ["init", "stop"]


def test_notify_answer_button_validation(monkeypatch):
    client, bot = _client(monkeypatch)
    h = {"X-ECC-Token": "t0ken"}
    ok = {**BODY, "buttons": [{"label": "A", "action": "answer", "requestId": "r1", "choice": 0}]}
    assert client.post("/api/v1/notify", json=ok, headers=h).status_code == 200
    assert bot.calls[0][2].inline_keyboard[0][0].callback_data == "ayn:ans:r1:0"
    for bad in ({"label": "A", "action": "answer", "requestId": "r1"},
                {"label": "A", "action": "answer", "choice": 0},
                {"label": "A", "action": "resume"}):
        r = client.post("/api/v1/notify", json={**BODY, "buttons": [bad]}, headers=h)
        assert r.status_code == 422
