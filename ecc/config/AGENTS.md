# L2 — 설정과 서비스 등록

> L1: 저장소 [AGENTS.md](../../AGENTS.md) · L3: [architecture](../../docs/architecture.md), [deployment](../../docs/deployment.md)

## 책임

Pydantic Settings로 환경 설정을 읽고, Eureka 활성화 시 서비스 인스턴스를 등록할 설정을 제공합니다.

## 파일과 계약

| 파일 | 책임 |
|---|---|
| `settings.py` | `ECC_` 접두사 환경 변수, 사용자/CLI/workspace 목록 파싱 |

## 불변식

- 운영 비밀은 `.env` 또는 secret 관리 시스템으로 전달하며 저장소에 커밋하지 않습니다.
- `.env.example`, L1 환경 변수 지도, L3 설정 표를 함께 갱신합니다.
- `ECC_EUREKA_ENABLED` 기본값은 `false`입니다. Eureka가 없어도 동작하지만, d94-query 컨테이너 DNS를 사용할 때는 같은 cloud network에 연결해야 합니다.
- Config Server에서 설정을 읽는 구현은 아직 없습니다.

