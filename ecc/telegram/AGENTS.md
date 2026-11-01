# L2 — Telegram 인터페이스

> L1: 저장소 [AGENTS.md](../../AGENTS.md) · L3: [architecture](../../docs/architecture.md) · L4: [승인 흐름](../../docs/features/telegram-approval.md)

## 책임

aiogram long polling으로 `/task` 입력, 승인/거절 callback, 작업 결과 알림을 처리합니다. ECC가 Telegram API를 향해 아웃바운드 연결을 여므로 Telegram webhook이나 공개 인바운드 포트는 필요하지 않습니다.

## 파일과 계약

| 파일 | 책임 |
|---|---|
| `bot.py` | 사용자 allowlist, 작업 티켓 생성, 승인 키보드, CLI 실행 결과 회신 |

## 불변식

- 명령과 callback 모두 실제 숫자 `from_user.id`를 allowlist와 대조합니다.
- 승인 버튼은 d94-query의 조건부 상태 전이 요청이 성공한 경우에만 실행합니다.
- 거절은 상태만 `REJECTED`로 바꾸고 실행하지 않습니다.
- 사용자 메시지·CLI 출력 원문을 운영 로그에 기록하지 않습니다.
- callback_data는 티켓 식별자와 동작만 담습니다. 비밀값을 넣지 않습니다.

