# L2 — CLI 실행기

> L1: 저장소 [AGENTS.md](../../AGENTS.md) · L3: [architecture](../../docs/architecture.md) · L4: [CLI 실행 경계](../../docs/features/cli-execution.md)

## 책임

허용된 CLI 실행 파일을 지정 작업공간에서 하나씩 실행하고, 제한 시간과 출력을 관리합니다.

## 파일과 계약

| 파일 | 책임 |
|---|---|
| `runner.py` | workspace 경계 검사, asyncio 단일 worker queue, subprocess 실행 |

## 불변식

- CLI 이름은 `ECC_CLI_ALLOWLIST`, 실행 경로는 `ECC_CLI_EXECUTABLES`에서 가져옵니다.
- 실행 파일은 절대 경로여야 하고 컨테이너에서 UID 10001로 실행 가능해야 합니다.
- 셸을 거치지 않고 `create_subprocess_exec`를 사용합니다. 프롬프트는 하나의 argv 인자로 전달합니다.
- cwd는 해석된 경로가 `ECC_CLI_WORKSPACES` 중 하나 아래에 있는 디렉터리일 때만 허용합니다.
- CLI timeout은 `ECC_CLI_TIMEOUT_SECONDS`로 제한합니다. 종료 시 실행 중 작업과 큐 worker를 정리합니다.
- 사용자 프롬프트로 CLI 종류·실행 파일·추가 인자를 선택하게 하지 않습니다.

