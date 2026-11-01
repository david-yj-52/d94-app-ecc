# Telegram 요청·승인·결과 알림 (L4)

## 입력

- `/start`: allowlist에 등록된 사용자는 사용법 안내를 받습니다.
- `/task <요청>`: allowlist 사용자가 요청합니다. 인수는 비어 있지 않아야 하며 최대 길이는 `CreateTicket.prompt` 검증을 따릅니다.
- Callback data: `approve:{ticket_id}` 또는 `reject:{ticket_id}`.

## 처리 규칙

| 단계 | 동작 |
|---|---|
| 사용자 확인 | `from_user.id`가 `ECC_TELEGRAM_ALLOWED_USER_IDS`에 없으면 거부 |
| 작업 디렉터리 | `ECC_TELEGRAM_DEFAULT_WORKSPACE`를 runner에서 확인 |
| 분류 | `ecc.intent.classifier.classify` 호출 |
| 승인 메시지 | ticket ID, intent, CLI, summary, action plan 표시 |
| 승인/거절 | d94-query에서 상태가 `AWAITING_CONFIRM`인 티켓을 조건부 갱신 |
| 결과 | 실행 완료/실패를 티켓에 저장하고 Telegram 메시지로 회신 |

## 실패와 경계

- 미허용 사용자는 티켓 생성·승인·거절을 할 수 없습니다.
- 분류 실패는 `FAILED` 티켓으로 저장하고 실행하지 않습니다.
- d94-query 상태 변경이 충돌하거나 실패하면 실행하지 않습니다.
- 현재 Telegram polling은 ECC 프로세스 수명주기에 종속됩니다. ECC가 꺼져 있으면 업데이트를 처리하지 않습니다.

## 코드 위치

- `ecc/telegram/bot.py`: aiogram router, `/task`, callback, 알림
- `ecc/api/app.py`: polling task 시작·종료 및 REST 생성 티켓 알림
- `ecc/tickets/models.py`: 사용자에게 노출되는 상태·요약 모델

