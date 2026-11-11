# 런타임·인프라 (L4)

- 설정은 `ecc/config/settings.py`의 `ECC_` 환경 변수. 전체 표는 [아키텍처](../architecture.md#설정).
- Compose는 external 네트워크 `${CLOUD_NETWORK_NAME:-befw-cloud-network}`에 연결하고 Eureka(`ECC_EUREKA_ENABLED=true`, 호스트 `d94-ecc`)에 등록합니다. 볼륨은 없습니다.
- ayaan은 게이트웨이(`gateway-cloud-gateway-1:10001`) 경유로 호출합니다.
- Redis·DB를 사용하지 않습니다.
