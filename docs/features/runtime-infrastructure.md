# d94-query·설정·Eureka 연동 (L4)

## 티켓 상태 저장

ECC는 별도 Redis나 메모리에 티켓 상태를 보관하지 않습니다. 모든 티켓 생성·조회·승인 전이·실행 결과 저장은 d94-query 서비스 API를 호출하며, d94-query는 PostgreSQL의 `SN_ECC_TICKET`에 상태를 보관합니다.

ECC 설정은 `ECC_QUERY_BASE_URL`(기본 `http://d94-query:8080/tsh`)과 `ECC_QUERY_SERVICE_TOKEN`입니다. query 저장소에는 같은 비밀값을 `ECC_SERVICE_TOKEN`으로 설정해야 합니다.

| 메서드 | 경로 (context path 제외) | 설명 |
|---|---|---|
| POST | `/api/v1/ecc/tickets` | `AWAITING_CONFIRM` 또는 분류 실패 `FAILED` 티켓 생성 |
| GET | `/api/v1/ecc/tickets/{ticket_id}` | 상태 조회 |
| POST | `/api/v1/ecc/tickets/{ticket_id}/decision` | `AWAITING_CONFIRM` → `PROCESSING` 또는 `REJECTED` 조건부 전이 |
| PATCH | `/api/v1/ecc/tickets/{ticket_id}/result` | `PROCESSING` → `DONE` 또는 `FAILED` 조건부 전이 |

모든 요청은 `X-ECC-Service-Token` 헤더를 사용합니다. query의 조건부 DB update가 한 티켓의 승인을 한 번만 성공시킵니다.

## Redis

ECC 자체는 Redis에 연결하지 않으며 Compose에서도 Redis를 실행하지 않습니다. d94-query나 다른 인프라 기능이 기존 Redis를 사용하는 경우 그 구성은 해당 서비스의 소유입니다. ECC 티켓 기능을 위해 ECC가 Redis를 별도로 요구하지 않습니다.

## 설정

`ecc/config/settings.py`는 `ECC_` 접두사 환경변수를 읽습니다. 전체 키와 기본값은 L3 [아키텍처](../architecture.md#6-설정-변수), 배포 값은 [배포 가이드](../deployment.md) 기준입니다. 설정 키 변경 시 `.env.example`, L1, L3를 함께 갱신합니다.

## Eureka

`ECC_EUREKA_ENABLED=true`면 앱 lifespan에서 `py-eureka-client`로 서비스 이름, hostname, 포트를 등록합니다. 등록 hostname은 공유 Docker 네트워크에서 ECC 컨테이너에 연결 가능해야 합니다. Eureka를 쓰지 않는 로컬 실행은 기본 `false`를 유지하면 됩니다.

Spring Cloud Config Server에서 설정을 내려받는 기능은 아직 구현되지 않았습니다.

## 코드 위치

- `ecc/tickets/query_client.py`: d94-query API 호출과 응답 envelope 처리
- `ecc/api/app.py`: query client와 Eureka 수명주기
- d94-query `EccTicketController`: 서비스 토큰 검증과 REST 경로
- d94-query `EccTicketService`: 상태 전이 규칙·tenant 선택
- d94-query `EccTicketModel` / `EccTicketRepo`: PostgreSQL 엔티티 및 조건부 갱신
- d94-query `V310__create_ecc_ticket.sql`: 테이블·인덱스

