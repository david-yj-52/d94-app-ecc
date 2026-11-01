# 런타임·인프라 연동 (L4)

## 티켓 상태 저장

현재 티켓 상태는 ECC 한 프로세스의 메모리에만 저장합니다. Redis나 d94-query 테이블은 사용하지 않습니다. ECC가 재시작되면 기존 티켓을 조회하거나 승인할 수 없습니다. 따라서 현재는 ECC를 한 인스턴스로 운영합니다.

d94-query에서 ECC 티켓 API를 제공하면 ECC의 저장소 경계를 해당 API로 교체합니다. 이때까지는 d94-query에 ECC 전용 테이블이나 API를 추가하지 않습니다.

## Redis

ECC는 Redis에 연결하지 않으며 Compose에서도 Redis를 실행하지 않습니다. 향후 별도 기능이 Redis를 요구하면 이미 구축된 인프라 Redis를 사용하도록 해당 기능의 설정을 추가합니다.

## 설정

`ecc/config/settings.py`는 `ECC_` 접두사 환경변수를 읽습니다. 전체 키와 기본값은 L3 [아키텍처](../architecture.md#6-설정-변수), 배포 값은 [배포 가이드](../deployment.md) 기준입니다. 설정 키 변경 시 `.env.example`, L1, L3를 함께 갱신합니다.

## Eureka

`ECC_EUREKA_ENABLED=true`면 앱 lifespan에서 `py-eureka-client`로 서비스 이름, hostname, 포트를 등록합니다. 등록 hostname은 공유 Docker 네트워크에서 ECC 컨테이너에 연결 가능해야 합니다. Eureka를 쓰지 않는 로컬 실행은 기본 `false`를 유지하면 됩니다.

Spring Cloud Config Server에서 설정을 내려받는 기능은 아직 구현되지 않았습니다.

## 코드 위치

- `ecc/tickets/store.py`: 현재 임시 메모리 저장소
- `ecc/api/app.py`: 앱 수명주기와 임시 저장소 연결
- `ecc/config/settings.py`: 런타임 환경 변수
