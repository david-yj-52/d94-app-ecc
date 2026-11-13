# ECC 아키텍처 (L3)

```text
Telegram ◀──polling──▶ ECC ──X-AYAAN-Token──▶ gateway ──▶ d94-app-ayaan
                        ▲
        POST /api/v1/notify (X-ECC-Token) ◀── ayaan
```

| 모듈 | 책임 |
|---|---|
| `ecc/api` | FastAPI 수명주기, `/actuator/health`, `POST /api/v1/notify` |
| `ecc/telegram` | 명령·버튼, 사용자 allowlist, 순수 함수(`parse_run`, `render_notify`, 키보드) |
| `ecc/ayaan_client.py` | ayaan REST 클라이언트(`{success,data}`에서 data 추출) |
| `ecc/config` | `ECC_` 환경 변수 |
| `ecc/intent` | 현재 사용하지 않음(보존) |

## Notify

요청 `{event, title, body, buttons?: [{label, action: "resume"|"cancel", taskId} | {label, action: "answer", requestId, choice}]}` → 메시지 `[{event}] {title}\n\n{body}`, 버튼은 `ayn:{action}:{taskId}` 또는 `ayn:ans:{requestId}:{choice}`(응답은 ayaan `POST /requests/{id}/answer`, 상세는 L4 telegram-approval). `ECC_TELEGRAM_ALLOWED_USER_IDS` 전원에게 보내며 개별 전송 실패는 건너뛰고 성공 수를 `{sent}`로 반환합니다. 토큰이 틀리면 401.

## Telegram 명령

- `/run KEY [tool] [dev]`: ayaan `GET /issues/KEY` 미리보기 + [실행]/[취소] → `POST /tasks {issueKey, tool, source:"TELEGRAM", phase?}` (기본 기획부터, `dev`면 바로 개발)
- 답변: 요청 알림의 버튼·답장·`/answer` → ayaan `POST /requests/{id}/answer {choice|answer, answeredBy:"tg:<id>"}`, `/waiting` → `GET /requests?status=OPEN`
- `/task <프롬프트>`: 미리보기 + [실행]. 프롬프트는 callback_data 64바이트 제한 때문에 메모리 dict에 10분간 보관(`ayn:task:<uuid8>`), 재시작·만료 시 재요청 필요.
- `/tasks`, `/quota`, `/resume <id>`, `/cancel <id>`: ayaan 조회·제어.
- 생성 응답 409는 "이미 진행 중" 안내로 처리합니다.

## 보안

- 명령·callback 모두 `from_user.id`를 allowlist와 대조합니다.
- `X-ECC-Token`은 ayaan → ECC, `X-AYAAN-Token`은 ECC → ayaan 방향 인증입니다.
- ECC는 CLI를 실행하지 않고 작업 상태를 저장하지 않습니다(프롬프트 임시 보관 제외).

## 설정

| 변수 | 기본값 | 용도 |
|---|---|---|
| `ECC_API_TOKEN` | 빈 값 | notify 인증. 비면 항상 401 |
| `ECC_TELEGRAM_BOT_TOKEN` / `ECC_TELEGRAM_ALLOWED_USER_IDS` | 빈 값 | 필수 |
| `ECC_AYAAN_BASE_URL` | `http://gateway-cloud-gateway-1:10001/tsh/api/v1/ayaan` | ayaan API |
| `ECC_AYAAN_TOKEN` | 빈 값 | `X-AYAAN-Token` |
| `ECC_EUREKA_*` | compose에서 enabled | Eureka 등록 |
| `CLOUD_NETWORK_NAME` | `befw-cloud-network` | external Docker 네트워크 |
