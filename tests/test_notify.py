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
