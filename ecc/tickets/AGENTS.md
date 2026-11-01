# L2 — 티켓과 상태 저장

> L1: 저장소 [AGENTS.md](../../AGENTS.md) · L3: [architecture](../../docs/architecture.md) · L4: [티켓·REST 계약](../../docs/features/rest-api.md)

## 책임

작업 요청, 분류 계획, 승인 및 실행 결과의 데이터 모델과 d94-query API client를 담당합니다. 상태의 실제 저장은 d94-query PostgreSQL입니다.

## 파일과 계약

| 파일 | 책임 |
|---|---|
| `models.py` | `CreateTicket`, `IntentPlan`, `Ticket`, `TicketStatus` |
| `query_client.py` | d94-query create/get/decision/result API 호출 |

## 불변식

- 상태 전이: `CREATED` → `AWAITING_CONFIRM` → `PROCESSING` → `DONE` 또는 `FAILED`; 거절은 `AWAITING_CONFIRM` → `REJECTED`입니다.
- 티켓 상태를 ECC 메모리나 Redis에 복제하지 않습니다.
- 새 상태나 필드의 의미를 바꾸면 L3와 L4, API 응답 계약을 함께 갱신합니다.
- `X-ECC-Service-Token`으로 d94-query에 인증합니다. ECC와 query의 secret 설정값을 일치시킵니다.
- d94-query의 조건부 SQL 상태 전이가 승인 중복을 방지합니다.

