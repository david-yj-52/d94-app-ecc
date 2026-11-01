# REST 티켓 API (L4)

## API 계약

| 메서드·경로 | 입력·헤더 | 응답 |
|---|---|---|
| `POST /api/v1/tickets` | `X-ECC-Token`, `{ "prompt": "...", "workspace": "/workspace/repo" }` | 201, 생성한 `Ticket` |
| `GET /api/v1/tickets/{ticket_id}` | `X-ECC-Token` | 200, 현재 `Ticket`; 없으면 404 |
| `GET /actuator/health` | 인증 없음 | ECC liveness 상태 200 |

`prompt`는 1~8000자, `workspace`는 1~500자입니다. REST 인증 설정이 비어 있거나 헤더가 틀리면 401입니다. API 포트는 기본 loopback 바인딩입니다.

## 생성 흐름

인증 → workspace 경계 확인 → 티켓 생성 → Nano/대체 분류 → CLI allowlist 확인 → `AWAITING_CONFIRM` 상태로 d94-query 저장 → Telegram 승인 메시지 전송 → 201 응답 순서입니다.

## 데이터 상태

상태 종류는 `CREATED`, `AWAITING_CONFIRM`, `PROCESSING`, `DONE`, `REJECTED`, `FAILED`입니다. 응답에는 프롬프트, workspace, 계획, 실행 결과가 포함될 수 있으므로 API 접근과 d94-query DB 권한을 제한합니다.

## 코드 위치

- `ecc/api/app.py`: 경로·header 인증·HTTP 예외
- `ecc/tickets/models.py`: 요청/응답 형식과 enum
- `ecc/tickets/query_client.py`: d94-query REST 호출
- Telegram 승인 알림: `ecc/telegram/bot.py`

## d94-query 티켓 API

ECC는 `ECC_QUERY_BASE_URL` 아래에 있는 다음 API를 `X-ECC-Service-Token`으로 호출합니다.

- `POST /api/v1/ecc/tickets`
- `GET /api/v1/ecc/tickets/{ticket_id}`
- `POST /api/v1/ecc/tickets/{ticket_id}/decision`
- `PATCH /api/v1/ecc/tickets/{ticket_id}/result`

query는 PostgreSQL에서 승인·거절 상태를 조건부 변경합니다. 승인 경쟁에서 한 요청만 `PROCESSING`으로 전이하고, 나머지는 409를 반환합니다.

