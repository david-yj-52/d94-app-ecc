# ECC 아키텍처 (L3)

이 문서는 코드 기준 현재 동작을 설명합니다. 기능별 상세 계약은 [L4 기능 색인](features/README.md), 실행 절차는 [배포 가이드](deployment.md)를 봅니다.

## 1. 구성과 책임

```text
Telegram ──long polling──▶ ECC FastAPI 서비스 ──▶ Jetson Nano (선택)
                                  │
                                  ├── 프로세스 메모리: 임시 티켓·승인 상태
                                  ├── Eureka: 선택 등록
                                  └── 단일 asyncio 큐 ──▶ AI CLI ──▶ 허용된 작업공간
```

| 모듈 | 책임 |
|---|---|
| `ecc/api` | FastAPI 수명주기, REST 인증·요청·응답, health |
| `ecc/telegram` | Telegram 명령·버튼, 사용자 allowlist, 결과 알림 |
| `ecc/tickets` | Pydantic 데이터 형식과 임시 메모리 저장소 |
| `ecc/intent` | Jetson Nano 분류 요청과 응답 검증, 미설정 시 기본 계획 |
| `ecc/execution` | 작업공간 경계 확인, 직렬 CLI 실행, timeout |
| `ecc/config` | `ECC_` 환경 변수 파싱 |

## 2. Telegram 요청에서 실행까지

1. 허용된 사용자가 `/task <요청>`을 보냅니다. 작업 디렉터리는 `ECC_TELEGRAM_DEFAULT_WORKSPACE`입니다.
2. API 요청은 `POST /api/v1/tickets`에 프롬프트와 workspace를 전달합니다. 이 REST 경로는 `X-ECC-Token` 인증이 필요합니다.
3. workspace 경로를 정규화하고 `ECC_CLI_WORKSPACES` 경계 안인지 확인합니다.
4. `ECC_NANO_ENDPOINT`가 설정되면 `POST /api/v1/classify`에 `{ticket_id, raw_prompt}`를 전달합니다. 설정하지 않으면 기본 요약/계획을 만듭니다.
5. Nano 응답을 `IntentPlan`으로 검증하고 `target_cli`가 허용 목록에 있는지 확인합니다.
6. 티켓을 ECC 프로세스 메모리에 `AWAITING_CONFIRM`으로 저장하고 Telegram 승인·거절 버튼을 전송합니다.
7. 허용 사용자 callback은 메모리 저장소의 잠금 안에서 상태를 변경합니다. 거절은 `REJECTED`, 승인은 `PROCESSING`으로 변경합니다.
8. 승인은 `PROCESSING` 상태로 저장한 후 단일 asyncio queue에 넣습니다. CLI 결과에 따라 `DONE` 또는 `FAILED`로 저장하고 Telegram에 결과를 보냅니다.

## 3. REST API와 health

| 메서드 | 경로 | 인증 | 동작 |
|---|---|---|---|
| GET | `/actuator/health` | 없음 | ECC 프로세스 liveness 반환 |
| POST | `/api/v1/tickets` | `X-ECC-Token` | 티켓 생성, 분류, Telegram 승인 알림 |
| GET | `/api/v1/tickets/{ticket_id}` | `X-ECC-Token` | 티켓 상태 조회 |

FastAPI 상세 `/docs`는 현재 별도로 비활성화하지 않았습니다. API 포트는 Compose에서 기본 loopback에만 바인딩합니다.

## 4. 티켓 상태와 임시 저장

```text
CREATED → AWAITING_CONFIRM → PROCESSING → DONE
                   │              └────→ FAILED
                   └───────────────→ REJECTED
```

현재 티켓은 ECC 프로세스 메모리에만 존재하며 재시작하면 사라집니다. asyncio lock으로 한 인스턴스 안에서만 중복 승인·거절을 방지합니다. ECC는 하나의 인스턴스로 실행해야 합니다. d94-query가 티켓 API를 제공하면 저장소를 해당 API로 갱신할 예정이며, 현재 d94-query에는 ECC 티켓 테이블이나 API를 추가하지 않습니다.

## 5. 보안 경계

- Telegram은 서버가 ECC에 먼저 요청하는 webhook 구조가 아니라 ECC의 polling 구조입니다. ECC 호스트에 Telegram용 인바운드 포트가 필요하지 않습니다.
- REST 토큰과 Telegram 사용자 ID는 별도 인증 수단입니다. `/actuator/health`만 공개 인증 예외입니다.
- CLI는 셸을 통하지 않고, 허용된 실행 파일을 절대 경로로 호출합니다. 사용자 지정 실행 파일이나 임의 인자를 받지 않습니다.
- workspace는 정규화한 경로로 허용 root 포함 여부를 검사합니다.
- 컨테이너 내부에 AI CLI 및 인증정보를 설치해야 합니다. Docker 호스트의 CLI 프로세스/자격 증명과 자동 공유되지 않습니다.
- Nano 분류 계획은 안내 자료입니다. 실제 실행 대상은 승인된 티켓의 prompt이며 CLI 실행을 승인하는 행위는 해당 prompt의 수행을 허가합니다.

## 6. 설정 변수

전체 예시는 저장소 `.env.example`이 기준입니다.

| 변수 | 기본값 | 용도 |
|---|---|---|
| `ECC_SERVICE_NAME` | `d94-ecc` | 서비스 이름 |
| `ECC_API_TOKEN` | 빈 값 | REST 인증 토큰. 비어 있으면 REST 보호 경로는 모두 401 |
| `ECC_TELEGRAM_BOT_TOKEN` | 빈 값 | 필수 Telegram bot token |
| `ECC_TELEGRAM_ALLOWED_USER_IDS` | 빈 값 | 필수 쉼표 구분 사용자 ID |
| `ECC_TELEGRAM_DEFAULT_WORKSPACE` | `/workspace` | Telegram 작업 기본 경로 |
| `ECC_NANO_ENDPOINT` | 빈 값 | 선택 분류기 base URL |
| `ECC_NANO_TIMEOUT_SECONDS` | `30` | Nano HTTP timeout |
| `ECC_EUREKA_ENABLED` | `false` | 서비스 등록 on/off |
| `ECC_EUREKA_URL` | `http://eureka:8761/eureka/` | Eureka base URL |
| `ECC_EUREKA_INSTANCE_HOST` | `d94-ecc` | Eureka 등록 hostname |
| `ECC_EUREKA_INSTANCE_IP` | 빈 값 | 필요할 때 등록 IP 명시 |
| `ECC_EUREKA_INSTANCE_PORT` | `8080` | Eureka 등록 포트 |
| `ECC_CLI_ALLOWLIST` | `claude,gemini,codex` | 허용 CLI 이름 |
| `ECC_CLI_EXECUTABLES` | 빈 값 | `cli=/absolute/path` 쌍을 쉼표로 지정 |
| `ECC_CLI_TIMEOUT_SECONDS` | `1800` | CLI 실행 최대 시간 |
| `ECC_CLI_WORKSPACES` | `/workspace` | 쉼표 구분 허용 root |
| `APP_BIND`, `APP_PORT` | `127.0.0.1`, `8085` | Compose 호스트 bind 주소·포트 |
| `WORKSPACE_HOST_PATH` | `./workspace` | 호스트 디렉터리 bind mount |
| `CLI_AUTH_HOST_PATH` | `./cli-auth` | 컨테이너 홈 bind mount |
| `CLOUD_NETWORK_NAME` | `befw-cloud-network` | Eureka compose overlay가 사용할 external 네트워크 |

