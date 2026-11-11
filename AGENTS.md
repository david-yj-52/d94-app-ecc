# AGENTS.md — d94-app-ecc (ECC)

> 모든 AI 도구가 공유하는 **L1 저장소 가이드**입니다. 세부 구현 규칙은 작업하는 기능 폴더의 L2 `AGENTS.md`를 추가로 읽습니다. 도구별 파일은 같은 폴더의 `CLAUDE.md`에서 AGENTS.md를 불러옵니다.

## 0. 문서 계층 및 지도

| 계층 | 범위 | 문서 | 읽는 시점 |
|---|---|---|---|
| L1 | 저장소 전체 목표·불변식·작업 규칙 | 이 파일 | 항상 |
| L2 | 기능 모듈의 책임·클래스·불변식 | `ecc/**/AGENTS.md` | 해당 모듈을 수정할 때 |
| L3 | 전체 아키텍처·요청 흐름·환경 설정 | [docs/architecture.md](docs/architecture.md) | 경계·흐름·설정을 바꿀 때 |
| L4 | 한 기능의 API·상태·실패·운영 계약 | [docs/features/](docs/features/) | 해당 기능을 변경할 때 |
| 이력 | 계획·결과·설계 결정 | [docs/feature/](docs/feature/) | 변경 이력이 필요할 때 |

```
AGENTS.md (L1)
├── ecc/api/AGENTS.md .............. FastAPI 수명주기·notify
├── ecc/telegram/AGENTS.md ......... Telegram 명령·버튼
├── ecc/intent/AGENTS.md ........... 미사용(보존)
└── ecc/config/AGENTS.md ........... 환경 설정·Eureka
```

현재 흐름은 L3 [architecture](docs/architecture.md), 기능 계약은 L4 [features](docs/features/README.md)에 둡니다. L1/L2에는 작업 때 항상 필요한 요약과 불변식만 남깁니다.

## 1. 서비스 요약

- ECC는 Telegram 전용 채널입니다. ayaan(d94-app-ayaan)의 알림을 `POST /api/v1/notify`로 받아 허용 사용자에게 전달하고, Telegram 명령(`/run /task /tasks /quota /resume /cancel`)을 ayaan API(게이트웨이 경유, `X-AYAAN-Token`)로 전달합니다.
- CLI 실행·티켓 저장은 하지 않습니다. `ecc/intent`는 미사용으로 보존합니다.

## 2. 기술 스택과 명령

| 목적 | 명령 |
|---|---|
| 설치 | `python -m pip install -e '.[dev]'` |
| 테스트·린트 | `pytest -q` · `ruff check .` |
| 로컬 실행 | `uvicorn ecc.api.app:app --host 127.0.0.1 --port 8080` |
| 기동 | `docker compose --env-file .env up -d` |

## 3. 불변식

1. Telegram 명령·callback은 `ECC_TELEGRAM_ALLOWED_USER_IDS`의 숫자 ID만 허용합니다.
2. 봇 토큰과 allowlist가 없으면 기동을 거부합니다.
3. `/actuator/health` 외 REST는 `X-ECC-Token`을 요구합니다.
4. callback_data는 64바이트 이하이며 비밀값을 담지 않습니다.
5. 프롬프트·메시지 원문을 로그에 남기지 않습니다.

## 4. 변경 절차와 문서 동기화

1. 수정할 기능의 L2 가이드와 관련 L4 기능 문서를 먼저 읽습니다.
2. 구현과 같은 변경에서 해당 L2/L4 및 L3 문서를 갱신합니다.
3. 새 모듈을 만들면 L1 지도에 등록하고 모듈 폴더에 `AGENTS.md`와 `CLAUDE.md`를 만듭니다.
4. 새 환경 변수를 추가하면 `.env.example`, L1 환경 변수 지도, L3 아키텍처 또는 배포 문서를 함께 갱신합니다.
5. 흐름·상태·보안 경계를 바꾸면 `docs/architecture.md` 및 관련 L4 계약을 갱신합니다.
6. `pytest -q`와 `ruff check .`를 실행하고 실제 결과를 보고합니다.

## 5. 저장소 문서

| 문서 | 용도 |
|---|---|
| [docs/architecture.md](docs/architecture.md) | L3 시스템 구성, 흐름, 보안 경계, 환경 변수 |
| [docs/features/](docs/features/) | L4 기능별 계약과 구현 위치 |
| [docs/deployment.md](docs/deployment.md) | 로컬 실행 호스트·GHCR·Compose 절차 |
| [docs/feature/](docs/feature/) | 개발 계획·결과 이력 |
