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
├── ecc/api/AGENTS.md .............. FastAPI 수명주기·REST 경로
├── ecc/telegram/AGENTS.md ......... Telegram 입력·승인 콜백
├── ecc/tickets/AGENTS.md .......... 티켓 모델·임시 저장소
├── ecc/intent/AGENTS.md ........... Nano 분류기·대체 계획
├── ecc/execution/AGENTS.md ........ 허용 CLI·작업 큐·작업공간
└── ecc/config/AGENTS.md ........... 환경 설정·Eureka
```

현재 흐름은 L3 [architecture](docs/architecture.md), 기능 계약은 L4 [features](docs/features/README.md)에 둡니다. L1/L2에는 작업 때 항상 필요한 요약과 불변식만 남깁니다.

## 1. 서비스 요약

- ECC(External Communication Channel)는 Telegram 또는 인증된 REST 요청을 티켓으로 만들고, 선택적으로 Jetson Nano에 의도 분류를 요청한 뒤 Telegram의 명시적 승인을 기다립니다.
- 승인된 CLI 작업은 ECC 프로세스 안의 단일 큐에서 차례로 실행됩니다.
- 현재 티켓·승인·실행 결과는 ECC 프로세스 메모리에만 저장합니다. d94-query의 티켓 API가 제공되면 ECC 저장 경계를 그 API로 갱신합니다.
- FastAPI와 CLI 실행기는 **같은 컨테이너 안에서 실행**됩니다. Docker 호스트의 CLI는 컨테이너에서 자동으로 보이지 않습니다. 실행 호스트에 CLI를 설치한 파생 이미지를 준비해야 합니다.
- 서비스 탐색(Eureka)은 선택 기능입니다. Config Server에서 설정을 자동으로 읽지는 않습니다.

## 2. 기술 스택과 명령

| 영역 | 기술 |
|---|---|
| 런타임·API | Python 3.12, FastAPI, Uvicorn |
| Telegram | aiogram 3, long polling (ECC에서 Telegram으로 아웃바운드 연결) |
| 티켓 상태 | 임시 단일 프로세스 메모리 저장소 (d94-query API 제공 후 연동 예정) |
| 연동 | httpx, 선택적 py-eureka-client |
| 배포 | Docker 이미지, GitHub Actions → GHCR, 수동 Docker Compose |

| 목적 | 명령 |
|---|---|
| 개발 의존성 설치 | `python -m pip install .` |
| 로컬 API 실행 | `uvicorn ecc.api.app:app --reload --host 127.0.0.1 --port 8080` |
| 문법 확인 | `python -m compileall -q ecc` |
| 이미지 빌드 | `docker build -t d94-app-ecc .` |
| 기동 | `docker compose --env-file .env up -d` |

## 3. 불변식

1. Telegram 요청·승인 콜백은 `ECC_TELEGRAM_ALLOWED_USER_IDS`의 숫자 사용자 ID만 허용합니다.
2. 봇 토큰과 사용자 ID allowlist가 없으면 서비스 기동을 거부합니다. 토큰은 소스·문서·이미지에 넣지 않습니다.
3. `/actuator/health`를 제외한 ECC REST 경로는 `X-ECC-Token` 인증을 요구합니다. 운영에서는 포트를 loopback 또는 신뢰된 내부망에만 공개합니다.
4. 티켓 상태는 현재 ECC 단일 프로세스에만 존재하며, 재시작 후 복구되지 않습니다.
5. Nano가 고른 CLI도 `ECC_CLI_ALLOWLIST`에 없으면 실행하지 않습니다. 허용 CLI 집합이 비었으면 실행할 대상이 없습니다.
6. 작업공간은 `ECC_CLI_WORKSPACES` 아래의 디렉터리만 허용합니다. 요청 경로를 정규화한 뒤 검사합니다.
7. Redis를 사용하지 않습니다. 임시 저장소의 잠금으로 ECC 한 인스턴스 안의 승인 중복을 막습니다.
8. 승인 전에는 CLI를 실행하지 않습니다. d94-query 티켓 API 제공 시 상태 저장과 원자적 승인 처리를 해당 API로 옮깁니다.
9. CLI는 셸 문자열로 실행하지 않습니다. `create_subprocess_exec`에 고정된 인자 형식으로 전달하고, 단일 작업 큐에서 실행합니다.
10. CLI 작업 큐는 프로세스 내부 메모리입니다. ECC는 한 인스턴스만 운영합니다.
11. 작업 프롬프트와 CLI 결과는 민감 정보를 포함할 수 있습니다. 로그에 원문을 남기지 말고 CLI 인증 디렉터리를 보호합니다.
12. 배포 workflow는 이미지를 GHCR에 올립니다. 서버 배포는 운영자가 Compose `pull`/`up -d`로 수행합니다.

## 4. 변경 절차와 문서 동기화

1. 수정할 기능의 L2 가이드와 관련 L4 기능 문서를 먼저 읽습니다.
2. 구현과 같은 변경에서 해당 L2/L4 및 L3 문서를 갱신합니다.
3. 새 모듈을 만들면 L1 지도에 등록하고 모듈 폴더에 `AGENTS.md`와 `CLAUDE.md`를 만듭니다.
4. 새 환경 변수를 추가하면 `.env.example`, L1 환경 변수 지도, L3 아키텍처 또는 배포 문서를 함께 갱신합니다.
5. 흐름·상태·보안 경계를 바꾸면 `docs/architecture.md` 및 관련 L4 계약을 갱신합니다.
6. 검증을 요청받았으면 `python -m compileall -q ecc`, Docker 빌드, 동작 확인을 수행하고 각각의 실제 결과를 구분해 보고합니다. 검증을 요청받지 않은 경우 테스트는 임의로 추가·실행하지 않습니다.

## 5. 저장소 문서

| 문서 | 용도 |
|---|---|
| [docs/architecture.md](docs/architecture.md) | L3 시스템 구성, 흐름, 보안 경계, 환경 변수 |
| [docs/features/](docs/features/) | L4 기능별 계약과 구현 위치 |
| [docs/deployment.md](docs/deployment.md) | 로컬 실행 호스트·GHCR·Compose 절차 |
| [docs/feature/](docs/feature/) | 개발 계획·결과 이력 |
