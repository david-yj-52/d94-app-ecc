# d94-app-ecc

ECC(External Communication Channel)는 **Telegram 전용 채널**입니다. CLI 실행·티켓 관리는 d94-app-ayaan이 맡고, ECC는 (1) ayaan이 보내는 알림을 허용된 Telegram 사용자에게 전달하고 (2) Telegram 명령·버튼을 ayaan API(게이트웨이 경유)로 전달합니다.

## 기능

- `POST /api/v1/notify` (`X-ECC-Token`): `{event, title, body, buttons?}`를 허용 사용자 전원에게 발송, `{sent: n}` 반환
- Telegram 명령: `/run <이슈키> [tool]`, `/task <프롬프트>`, `/tasks`, `/quota`, `/resume <id>`, `/cancel <id>`
- 버튼 callback_data: `ayn:<action>:<taskId>` (resume/cancel), `ayn:run:<이슈키>:<tool>`, `ayn:task:<id>`
- Eureka 등록, GHCR 이미지 + Docker Compose 배포

문서: [AGENTS.md](AGENTS.md) → [아키텍처](docs/architecture.md) → [기능 계약](docs/features/README.md) · [배포](docs/deployment.md)

테스트: `pip install -e '.[dev]' && pytest -q && ruff check .`
