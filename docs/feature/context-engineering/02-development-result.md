# AI 컨텍스트 문서 체계 구성 — 개발 결과

| 항목 | 내용 |
|---|---|
| 계획 | [01-development-plan.md](01-development-plan.md) |
| 범위 | L1~L4 컨텍스트 및 한국어 문서 정리 |
| 날짜 | 2026-10-31 |
| 상태 | 완료 |

## 결과 요약

- Python 코드를 `api`, `telegram`, `tickets`, `intent`, `execution`, `config` 기능 폴더로 재배치했습니다.
- L1 [AGENTS.md](../../../AGENTS.md)에 모듈 지도, 서비스 불변식, 변경·문서 동기화 규칙을 작성했습니다.
- 각 기능 폴더에 L2 `AGENTS.md`와 `CLAUDE.md`를 추가했습니다.
- L3 [architecture.md](../../architecture.md)에 요청 흐름, API, 상태, 보안, 환경 설정을 정리했습니다.
- L4 `docs/features/`에 Telegram 승인, REST API, Nano 분류, CLI 실행, 런타임·인프라 계약을 작성했습니다.
- README와 GHCR·Compose 배포 설명을 한국어로 바꿨습니다.
- 기본 Compose는 Eureka 네트워크에 의존하지 않도록 구성하고, 필요할 때 `docker-compose.cloud.yml` overlay를 추가하도록 했습니다.
- ECC의 Redis 의존성과 Redis 컨테이너 설정을 제거했습니다. 요구사항에 따라 d94-query 티켓 API가 제공될 때까지 티켓 상태는 단일 ECC 프로세스 메모리에 임시 저장합니다. ECC 재시작 시 상태가 사라집니다.

## 검증

- `python -m compileall -q ecc`: 통과 (번들 Python 런타임 사용).
- Markdown 상대 링크 대상 검사: 통과.
- `docker compose --env-file .env config --quiet`: 통과 (`.env.example`을 임시 `.env`로 복사해 검증한 뒤 임시 파일 삭제).
- 단위 테스트와 실제 컨테이너 기동은 수행하지 않았습니다.
- d94-query에 ECC 전용 테이블이나 API는 추가하지 않았습니다. 해당 API가 제공되면 ECC를 별도로 갱신해야 합니다.

## 갱신 문서

`AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/deployment.md`, `docs/features/*`, `ecc/**/AGENTS.md`, `ecc/**/CLAUDE.md`, `docs/feature/context-engineering/*`

