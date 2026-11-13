# L2 — Telegram 인터페이스

> L1: [AGENTS.md](../../AGENTS.md) · L4: [명령·알림](../../docs/features/telegram-approval.md)

`bot.py`: 순수 함수(`parse_run`, `render_notify`, 키보드, 프롬프트 임시 저장, `reply_request_id`, `answer_text`)와 `handle_callback`, `build_dispatcher`, `run_bot`.

- 모든 명령·callback은 `from_user.id`를 allowlist와 대조합니다.
- ayaan 호출은 `ecc/ayaan_client.py`만 사용합니다.
- 답장 답변은 봇 자신의 메시지(`is_bot` + bot id)에 단 답장만 받고, 요청 ID는 원문의 `요청 ID:` 줄에서 읽습니다(ECC는 요청 상태를 저장하지 않음).
- `ayn:ans:` callback의 선택지·요청 상태는 ayaan이 검증합니다. ECC는 숫자 형식만 봅니다.
