# 승인된 CLI 실행 (L4)

## 실행 계약

`CliExecutor.execute(cli, workspace, prompt)`는 허용된 CLI와 허용 root 아래 workspace만 받습니다. 단일 asyncio queue가 작업을 직렬 실행하고 `ECC_CLI_TIMEOUT_SECONDS` 뒤 프로세스를 종료합니다.

| 이름 | 고정 인수 형식 |
|---|---|
| `claude` | `-p`, prompt |
| `gemini` | `-p`, prompt |
| `codex` | `exec`, prompt |

실제 프로그램 경로는 `ECC_CLI_EXECUTABLES`의 `name=/absolute/path` 매핑으로 결정합니다. CLI는 컨테이너에 설치돼야 하며 `ECC_CLI_ALLOWLIST`에 포함된 이름만 실행됩니다.

## 작업공간 경계

`Path.resolve(strict=True)`로 요청 workspace와 허용 root를 정규화합니다. 요청 경로가 허용 root와 같거나 그 자손이고 디렉터리인 경우만 허용합니다. Compose bind mount를 통해 호스트의 허용 저장소를 `/workspace`에 연결합니다.

## 종료 코드·결과

- 종료 코드 0: stdout/stderr 합친 결과의 마지막 12,000자를 반환합니다.
- 비영 종료 코드: 실행 실패 예외에 종료 코드와 결과 일부를 포함합니다.
- timeout: 프로세스 종료 후 timeout 실패를 보고합니다.
- Telegram 완료 메시지는 결과의 마지막 3,500자를 전송합니다.

## 코드 위치·제약

- `ecc/execution/runner.py`: workspace 검사, 실행 인자, queue, timeout
- `ecc/telegram/bot.py`: approve 후 실행 호출
- `ecc/config/settings.py`: CLI allowlist·경로·timeout 설정
- `ecc/tickets/store.py`: 임시 메모리에서 승인 상태를 처리하고 실행 결과를 저장

현재 CLI 실행은 동일 컨테이너 안에서 이뤄집니다. 호스트 설치 CLI를 원격 호출하지 않습니다. 작업 프롬프트를 실행하는 행위는 승인된 변경을 작업공간에 수행할 수 있으므로 승인 전에 계획과 대상 workspace를 확인해야 합니다.

