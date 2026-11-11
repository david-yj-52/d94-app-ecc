# L2 — Telegram 인터페이스

> L1: [AGENTS.md](../../AGENTS.md) · L4: [명령·알림](../../docs/features/telegram-approval.md)

`bot.py`: 순수 함수(`parse_run`, `render_notify`, 키보드, 프롬프트 임시 저장)와 `handle_callback`, `build_dispatcher`, `run_bot`.

- 모든 명령·callback은 `from_user.id`를 allowlist와 대조합니다.
- ayaan 호출은 `ecc/ayaan_client.py`만 사용합니다.
