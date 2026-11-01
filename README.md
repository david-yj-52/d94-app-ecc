# d94-app-ecc

ECC(External Communication Channel)는 Telegram에서 개발 요청을 받고, 선택적으로 Jetson Nano의 의도 분류를 거친 다음, 승인된 작업만 AI CLI로 실행하는 오케스트레이션 서비스입니다.

## 주요 기능

- Telegram `/task` 명령과 승인·거절 버튼
- `X-ECC-Token` 인증을 사용하는 티켓 생성·조회 REST API
- d94-query PostgreSQL 기반 티켓 상태 저장·조회 및 승인 원자 처리
- 선택적 Jetson Nano 분류기 및 Eureka 등록
- 허용된 작업공간에서의 순차 CLI 실행
- GitHub Actions의 GHCR 이미지 게시와 Docker Compose 배포

문서 계층은 저장소 [AGENTS.md](AGENTS.md)(L1) → 기능별 `ecc/**/AGENTS.md`(L2) → [아키텍처](docs/architecture.md)(L3) → [기능 계약](docs/features/README.md)(L4)입니다.

Telegram polling은 ECC에서 Telegram으로 나가는 연결이므로 공인 인바운드 포트가 필요하지 않습니다. 다만 FastAPI와 CLI 실행은 같은 컨테이너 안에서 이뤄집니다. 로컬 PC CLI를 사용하려면 CLI가 설치·인증된 파생 이미지를 구성해야 합니다. [배포 가이드](docs/deployment.md)를 참고하세요.

