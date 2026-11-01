# ECC 배포 가이드 — GHCR + Docker Compose

## 배포 구조

GitHub Actions는 Python 패키지 검증과 컨테이너 이미지 빌드·게시까지 수행합니다. d94-query·UMD처럼 서버에 SSH 접속하거나 컨테이너를 자동 재시작하지 않습니다. 게시된 태그를 대상 호스트에서 Compose로 pull하고 기동합니다.

ECC는 승인된 AI CLI를 실행합니다. 따라서 **CLI가 설치·인증된 개발 PC 또는 전용 실행 호스트**에 배포해야 합니다. 기본 GHCR 이미지는 Claude·Gemini·Codex CLI를 포함하지 않습니다. 기존 로컬 Compose에서 CLI가 호스트에만 설치되어 있다면 컨테이너가 자동으로 사용할 수 없으므로, CLI를 포함한 파생 이미지를 준비해야 합니다.

```text
Telegram ──polling──▶ ECC 실행 호스트
                           ├── Jetson Nano (선택 분류기)
                           └── 승인된 CLI ──▶ 마운트한 작업공간
```

## 1. GHCR 이미지 게시

`.github/workflows/deploy.yml`은 다음과 같이 동작합니다.

| 이벤트 | 동작·태그 |
|---|---|
| `deploy` 대상 PR | Python 패키지 설치 및 소스 문법 검사 |
| `deploy` 브랜치 push | 검증 후 이미지 게시: `latest`, `sha-...` |
| `v*` 태그 push | 검증 후 이미지 게시: semver, `sha-...` |

이미지 이름은 `ghcr.io/david-yj-52/d94-app-ecc`입니다. GHCR 패키지가 private이면 서버에서 `read:packages` 권한 토큰으로 로그인합니다.

```sh
docker login ghcr.io
```

ECC에는 private Maven 의존성이 없어 `PACKAGES_TOKEN`이 필요하지 않습니다.

## 2. 실행 호스트 준비

1. Docker Engine과 Docker Compose 플러그인을 설치합니다.
2. ECC 전용 운영 계정으로 AI CLI를 설치·인증합니다. CLI 실행 파일은 컨테이너 안의 `ECC_CLI_EXECUTABLES` 경로에 있어야 합니다.
3. 해당 CLI 버전을 고정해 설치하는 파생 이미지를 만들고 컨테이너 UID `10001`로 비대화형 실행되는지 확인합니다. Docker socket을 ECC에 마운트하지 마세요.
4. ECC가 수정할 저장소만 담은 호스트 작업공간을 만듭니다. Compose는 이를 컨테이너의 `/workspace`에 연결합니다.
5. Eureka 등록이 필요할 때만 기존 Eureka Docker 네트워크를 준비합니다.

CLI 설치·headless 인증 방법은 각 공급자에 따라 달라집니다. 공급자의 최신 공식 설치 안내를 확인하고, 실제 명령과 버전을 파생 이미지에서 검증하세요. 기본 ECC 이미지는 오케스트레이터만 포함합니다.

## 3. Compose 설정

```sh
cp .env.example .env
mkdir -p workspace cli-auth
```

`.env`에서 아래 값을 설정합니다.

| 변수 | 설명 |
|---|---|
| `ECC_API_TOKEN` | REST API용 긴 무작위 비밀값 |
| `ECC_TELEGRAM_BOT_TOKEN` | BotFather가 발급한 토큰. 필수 |
| `ECC_TELEGRAM_ALLOWED_USER_IDS` | 요청·승인 가능한 Telegram 숫자 사용자 ID 목록. 쉼표 구분, 필수 |
| `ECC_TELEGRAM_DEFAULT_WORKSPACE` | Telegram `/task` 작업 경로. 기본 `/workspace` |
| `WORKSPACE_HOST_PATH` | 호스트의 허용 저장소 디렉터리 |
| `CLI_AUTH_HOST_PATH` | 컨테이너 홈으로 연결하는 전용 CLI 인증 디렉터리 |
| `ECC_CLI_EXECUTABLES` | 컨테이너 안 CLI 절대 경로 매핑 |
| `ECC_CLI_WORKSPACES` | CLI 작업을 허용할 컨테이너 경로 |
| `ECC_NANO_ENDPOINT` | 선택 설정. Nano 분류기 URL |
| `ECC_EUREKA_ENABLED`, `ECC_EUREKA_URL` | 선택 설정. Eureka 등록 |

Telegram 봇 토큰 또는 사용자 ID allowlist가 없으면 ECC가 시작되지 않습니다. API 포트는 기본 `127.0.0.1:8085` 바인딩입니다. 외부에 공개하지 말고, 원격 접근이 필요하면 인증된 역방향 프록시나 신뢰된 VPN을 사용하세요.

기동 후 allowlist에 등록한 각 사용자는 Telegram에서 봇을 열고 `/start`를 먼저 보내야 합니다. 봇이 사용자의 대화를 먼저 시작할 수 없기 때문입니다. `/task <요청>`으로 요청하면 계획과 승인 버튼이 돌아옵니다. REST에서 티켓을 만들면 ECC가 allowlist의 가장 작은 숫자 ID를 대상으로 승인 메시지를 보내므로, 그 계정도 먼저 `/start`를 보내야 합니다.

기본 `docker-compose.yml`은 ECC에 외부 통신용 bridge를 연결합니다. Telegram polling에는 Eureka 네트워크가 필요하지 않습니다. Eureka 등록을 켜면 `docker-compose.cloud.yml` overlay로 ECC를 공유 네트워크에 연결합니다. ECC Compose는 Redis를 설치하거나 실행하지 않습니다.

현재 티켓 상태는 ECC 프로세스 메모리에만 저장됩니다. d94-query에서 티켓 API가 제공되면 ECC 연동 버전을 배포할 예정입니다.

## 4. 파생 실행 이미지와 CLI 인증

실행 호스트에서 ECC 버전을 고정한 Dockerfile을 만들고, 해당 버전에 맞는 CLI 설치 절차를 추가합니다. Compose의 `image`를 파생 이미지로 바꾸거나 override 파일을 사용합니다. CLI 인증 디렉터리는 컨테이너의 `/home/ecc`로 연결되며 CLI가 상태를 기록할 수 있어야 합니다. 이 디렉터리를 ECC 전용으로 분리하고 UID `10001`에 필요한 권한만 주세요. 인증정보를 이미지에 bake하거나 저장소에 커밋하지 마세요.

기본 설정은 다음 실행 경로를 기대합니다.

```text
claude=/usr/local/bin/claude
gemini=/usr/local/bin/gemini
codex=/usr/local/bin/codex
```

실제로 설치된 CLI와 일치하도록 `ECC_CLI_EXECUTABLES`와 `ECC_CLI_ALLOWLIST`를 조정합니다.

## 5. 기동·업데이트·롤백

```sh
docker compose --env-file .env pull
docker compose --env-file .env up -d
docker compose ps
curl -fsS http://127.0.0.1:8085/actuator/health
```

Eureka 등록을 켠 경우에는 두 Compose 파일을 함께 지정합니다.

```sh
docker compose -f docker-compose.yml -f docker-compose.cloud.yml --env-file .env up -d
```

배포 후 `/actuator/health`의 `status`가 `UP`인지 확인합니다. 이전 버전으로 되돌리려면 `.env`의 `IMAGE_TAG`를 이전 semver 또는 `sha-...`로 변경하고 `pull`, `up -d`를 다시 실행합니다. ECC 재시작 시 메모리의 티켓 상태는 초기화됩니다.

## 6. API 확인

`GET /actuator/health`는 컨테이너 health check를 위해 인증 없이 사용할 수 있습니다. 나머지 REST 경로는 `X-ECC-Token`을 확인합니다.

```sh
curl -H "X-ECC-Token: <ECC_API_TOKEN>" \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"인증 흐름을 검토해줘","workspace":"/workspace/my-repo"}' \
  http://127.0.0.1:8085/api/v1/tickets
```

생성된 티켓은 `AWAITING_CONFIRM` 상태로 Telegram 승인 메시지를 보냅니다. 승인 시 단일 큐에서 실행하고, 거절 시 실행하지 않습니다. 상태는 `GET /api/v1/tickets/{ticket_id}`에서 확인합니다. Telegram에서는 `/task <요청>` 명령으로 기본 작업공간 티켓을 만들 수 있습니다.

## 운영 제약

- 현재 승인 잠금은 ECC 복제본 간 분산 실행 lease가 아닙니다. **ECC는 한 인스턴스만 실행하세요.**
- REST API에는 사용자 계정 체계가 없습니다. 토큰을 안전하게 보관하고 API 포트를 loopback 또는 신뢰된 네트워크에 바인딩하세요.
- 작업 프롬프트와 CLI 결과는 민감할 수 있습니다. CLI 인증 디렉터리를 보호하세요.
- Config Server 설정 로드는 아직 구현되지 않았으며 `.env` 환경 변수로 설정합니다.
- ECC는 티켓 상태 저장용 Redis를 사용하지 않습니다. 기존 인프라 Redis가 필요하면 그 Redis를 사용하는 서비스의 설정을 따릅니다.
