# L2 — API 진입점

> L1: [AGENTS.md](../../AGENTS.md) · L3: [architecture](../../docs/architecture.md)

`app.py`: lifespan(Bot·AyaanClient·polling·Eureka), `GET /actuator/health`, `POST /api/v1/notify`.

- notify는 `X-ECC-Token` 필수. `app.state.bot.send_message`로 allowlist 전원에게 발송, `{sent: n}`.
- lifespan에서 시작한 polling·클라이언트는 종료 시 정리합니다.
