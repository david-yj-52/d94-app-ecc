# REST 티켓 API (L4)

## API 계약

| 메서드·경로 | 입력·헤더 | 응답 |
|---|---|---|
| `POST /api/v1/tickets` | `X-ECC-Token`, `{ "prompt": "...", "workspace": "/workspace/repo" }` | 201, 생성한 `Ticket` |
| `GET /api/v1/tickets/{ticket_id}` | `X-ECC-Token` | 200, 현재 `Ticket`; 없으면 404 |
| `GET /actuator/health` | 인증 없음 | ECC liveness 상태 200 |

`prompt`는 1~8000자, `workspace`는 1~500자입니다. REST 인증 설정이 비어 있거나 헤더가 틀리면 401입니다. API 포트는 기본 loopback 바인딩입니다.

## 생성 흐름

인증 → workspace 경계 확인 → 티켓 생성 → Nano/대체 분류 → CLI allowlist 확인 → `AWAITING_CONFIRM` 상태로 임시 메모리 저장 → Telegram 승인 메시지 전송 → 201 응답 순서입니다.

## 데이터 상태

상태 종류는 `CREATED`, `AWAITING_CONFIRM`, `PROCESSING`, `DONE`, `REJECTED`, `FAILED`입니다. 응답에는 프롬프트, workspace, 계획, 실행 결과가 포함될 수 있으므로 API 접근을 제한합니다. 상태는 ECC 재시작 시 사라집니다.

## 코드 위치

- `ecc/api/app.py`: 경로·header 인증·HTTP 예외
- `ecc/tickets/models.py`: 요청/응답 형식과 enum
- `ecc/tickets/store.py`: 임시 단일 프로세스 저장소와 승인 상태 전이
- Telegram 승인 알림: `ecc/telegram/bot.py`

## d94-query 연동 예정

현재 d94-query에는 ECC 티켓 API가 없습니다. API가 제공되면 저장소 생성·조회·상태 전이 경계를 그 API로 교체합니다. 그때까지 ECC의 상태는 한 프로세스 메모리에만 존재합니다.

