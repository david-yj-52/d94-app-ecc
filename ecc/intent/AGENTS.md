# L2 — 의도 분류

> L1: 저장소 [AGENTS.md](../../AGENTS.md) · L3: [architecture](../../docs/architecture.md) · L4: [Nano 분류기 계약](../../docs/features/intent-classification.md)

## 책임

선택적 Jetson Nano HTTP 분류기 호출과 반환 JSON 검증을 처리합니다. endpoint가 설정되지 않으면 요청을 요약으로 사용하는 기본 계획을 반환합니다.

## 파일과 계약

| 파일 | 책임 |
|---|---|
| `classifier.py` | `POST {ECC_NANO_ENDPOINT}/api/v1/classify`, `IntentPlan` 검증 |

## 불변식

- 요청 본문은 `ticket_id`, `raw_prompt`입니다.
- Nano의 `target_cli`는 신뢰할 수 없는 입력입니다. 허용 CLI인지 검사한 후 승인 UI에 표시합니다.
- timeout 또는 응답 검증 실패 시 티켓은 실패로 기록하고 CLI를 실행하지 않습니다.
- Nano에 비밀 토큰이나 CLI 인증정보를 전달하지 않습니다.

