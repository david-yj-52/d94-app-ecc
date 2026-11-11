# Telegram 명령·알림 (L4)

## 입력

`/start`, `/run <이슈키> [tool]`, `/task <프롬프트>`, `/tasks`, `/quota`, `/resume <id>`, `/cancel <id>`.
Callback: `ayn:run:<key>:<tool>`, `ayn:task:<uuid8>`, `ayn:resume:<id>`, `ayn:cancel:<id>`, `ayn:no`.

## 규칙

- `from_user.id`가 allowlist에 없으면 모든 명령·callback 거부.
- `/run`·`/task`는 미리보기 후 [실행] 버튼을 눌러야 ayaan `POST /tasks`를 호출합니다 (`/task`는 projectKey 없이 `{prompt, source:"TELEGRAM"}`).
- `/task` 프롬프트는 메모리에 10분 보관 후 만료.
- 알림은 `POST /api/v1/notify`(X-ECC-Token)로 수신해 전원에게 발송합니다.

## 코드 위치

`ecc/telegram/bot.py`, `ecc/ayaan_client.py`, `ecc/api/app.py`, 테스트 `tests/`.
