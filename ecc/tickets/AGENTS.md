# L2 — 티켓과 상태 저장

> L1: 저장소 [AGENTS.md](../../AGENTS.md) · L3: [architecture](../../docs/architecture.md) · L4: [티켓·REST 계약](../../docs/features/rest-api.md)

## 책임

작업 요청, 분류 계획, 승인 및 실행 결과의 데이터 모델과 임시 단일 프로세스 저장소를 담당합니다. d94-query 티켓 API가 제공되면 이 저장 경계를 API client로 교체합니다.

## 파일과 계약

| 파일 | 책임 |
|---|---|
| `models.py` | `CreateTicket`, `IntentPlan`, `Ticket`, `TicketStatus` |
| `store.py` | 임시 티켓 생성·조회·상태 전이. 프로세스 재시작 시 상태는 사라짐 |

## 불변식

- 상태 전이: `CREATED` → `AWAITING_CONFIRM` → `PROCESSING` → `DONE` 또는 `FAILED`; 거절은 `AWAITING_CONFIRM` → `REJECTED`입니다.
- Redis를 사용하지 않습니다. 현재 상태는 프로세스 메모리에만 있으며 재시작 시 사라집니다.
- d94-query 티켓 API가 아직 없으므로, 해당 API가 제공되면 이 모듈을 연결해 영속화합니다.
- 새 상태나 필드의 의미를 바꾸면 L3와 L4, API 응답 계약을 함께 갱신합니다.
- asyncio lock으로 한 ECC 프로세스 안에서 중복 승인·거절을 방지합니다.

