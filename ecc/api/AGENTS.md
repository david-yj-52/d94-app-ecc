# L2 — API 진입점

> L1: 저장소 [AGENTS.md](../../AGENTS.md) · L3: [architecture](../../docs/architecture.md) · L4: [REST 티켓 API](../../docs/features/rest-api.md)

## 책임

FastAPI 앱 수명주기, d94-query client·CLI worker·Telegram polling·Eureka 초기화, liveness health check와 REST 티켓 경로를 조립합니다. 요청 검증과 응답의 HTTP 상태는 이 모듈에서 관리합니다.

## 파일과 계약

| 파일 | 책임 |
|---|---|
| `app.py` | lifespan, `GET /actuator/health`, `POST /api/v1/tickets`, `GET /api/v1/tickets/{ticket_id}` |

## 불변식

- health 외 경로는 `X-ECC-Token`을 검증합니다.
- 수명주기에서 worker·Telegram polling·Eureka를 시작했다면 종료 시 정리합니다.
- 티켓의 생성·조회·승인·실행 결과 저장은 d94-query API를 통해 수행합니다.
- API 티켓은 Telegram 승인 요청까지 연결되어야 합니다. 승인 메시지를 보내지 못한 요청을 성공으로 가장하지 않습니다.
- HTTP 계층은 CLI 프로세스를 직접 실행하지 않습니다. `execution` 모듈의 경계를 사용합니다.

