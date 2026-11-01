# Jetson Nano 의도 분류 (L4)

## 요청·응답

ECC는 `ECC_NANO_ENDPOINT`가 설정된 경우 다음 요청을 보냅니다.

```json
{"ticket_id":"TCK-...","raw_prompt":"사용자 요청"}
```

응답은 `IntentPlan`으로 검증합니다.

```json
{"intent":"code_generation","target_cli":"claude","summary":"작업 요약","action_plan":["단계 1"]}
```

요청 경로는 `{ECC_NANO_ENDPOINT}/api/v1/classify`, timeout은 `ECC_NANO_TIMEOUT_SECONDS`입니다.

## 대체 동작·검증

- Nano endpoint가 비어 있으면 `intent=code_generation`, `summary=prompt 앞 500자`, 기본 안내 action plan을 생성하고 허용 CLI 이름의 사전순 첫 항목을 선택합니다.
- Nano의 `target_cli`는 `ECC_CLI_ALLOWLIST`에 포함되어야 합니다.
- HTTP 오류, timeout, 응답 검증 실패, 허용되지 않은 CLI는 실행 없이 분류 실패로 종료합니다.
- Nano 계획은 승인 메시지에 제시합니다. 실제 CLI 명령/인자 결정은 ECC 고정 설정에서 나옵니다.

## 코드 위치

- `ecc/intent/classifier.py`: httpx 호출 및 `IntentPlan` 생성
- `ecc/tickets/models.py`: `IntentPlan`
- `ecc/api/app.py`, `ecc/telegram/bot.py`: 분류 결과 적용 및 실패 처리

