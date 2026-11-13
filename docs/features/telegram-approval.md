# Telegram 명령·알림 (L4)

## 입력

`/start`, `/run <이슈키> [tool] [dev]`, `/task <프롬프트>`, `/tasks`, `/waiting`, `/answer <요청ID> <답변>`, `/quota`, `/resume <id>`, `/cancel <id>`, ayaan 요청 알림에 대한 **답장**.
Callback: `ayn:run:<key>:<tool>:<PLAN|DEV>`(이전 4단 형식도 받음), `ayn:task:<uuid8>`, `ayn:resume:<id>`, `ayn:cancel:<id>`, `ayn:ans:<요청ID>:<n>`, `ayn:no`.

## 사람 응답 요청 (TSTA-1: 질문·권한·개발 시작)

- ayaan은 `WAITING`·`PLAN_DONE` 알림에 선택지별 `answer` 버튼(`{action:"answer", requestId, choice}`)과 본문 줄 `요청 ID: <id>`를 넣습니다.
- 버튼 → `POST /requests/{id}/answer {choice, answeredBy:"tg:<user_id>"}`. 200이면 원 메시지 끝에 `✔ <선택지> (응답됨)`을 붙여 수정하고 버튼을 없앱니다. 409면 "이미 처리된 요청입니다(누가, 언제)"를 alert로 보여 줍니다(먼저 누른 1건만 유효, CAS는 query).
- callback_data는 신뢰하지 않습니다. 선택지 범위·요청 상태는 ayaan이 다시 검증합니다.
- 자유 답변: 봇 자신의 요청 알림에 답장하거나 `/answer <요청ID> <내용>`. 답장의 요청 ID는 원문의 `요청 ID:` 줄에서 읽으므로 ECC에 상태가 없습니다. 다른 메시지(사용자·다른 봇)에 단 답장은 무시합니다.
- `/waiting`: 열린 요청 목록(`GET /requests?status=OPEN`).
- `/run KEY … dev`: 기획을 건너뛰고 바로 개발(`phase:"DEV"`). 기본은 기획부터.
- 버튼이 4개 이상이면 한 줄에 하나씩 둡니다.

## 규칙

- `from_user.id`가 allowlist에 없으면 모든 명령·callback 거부.
- `/run`·`/task`는 미리보기 후 [실행] 버튼을 눌러야 ayaan `POST /tasks`를 호출합니다 (`/task`는 projectKey 없이 `{prompt, source:"TELEGRAM"}`).
- `/task` 프롬프트는 메모리에 10분 보관 후 만료.
- 알림은 `POST /api/v1/notify`(X-ECC-Token)로 수신해 전원에게 발송합니다.

## 코드 위치

`ecc/telegram/bot.py`, `ecc/ayaan_client.py`, `ecc/api/app.py`, 테스트 `tests/`.
