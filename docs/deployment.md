# ECC 배포 가이드 — GHCR + Docker Compose

`.github/workflows/deploy.yml`이 `deploy` 브랜치 push 시 이미지를 `ghcr.io/david-yj-52/d94-app-ecc`(`latest`, `sha-...`)로 게시합니다. 서버에서는 Compose로 pull·기동합니다. ECC는 CLI를 실행하지 않으므로 기본 이미지로 충분합니다.

## 준비

1. Docker 호스트에 external 네트워크 `befw-cloud-network`(변경 시 `CLOUD_NETWORK_NAME`)가 있어야 합니다. 게이트웨이(`gateway-cloud-gateway-1`)와 Eureka(`eureka-cloud-eureka-1`)가 같은 네트워크에 있습니다.
2. `cp .env.example .env` 후 `ECC_API_TOKEN`, `ECC_TELEGRAM_BOT_TOKEN`, `ECC_TELEGRAM_ALLOWED_USER_IDS`, `ECC_AYAAN_TOKEN`을 채웁니다.
3. ayaan의 ECC 알림 설정에 `http://d94-ecc:8080/api/v1/notify`와 `ECC_API_TOKEN` 값을 지정합니다.

## 기동

```sh
docker login ghcr.io   # private 패키지일 때
docker compose --env-file .env pull
docker compose --env-file .env up -d
```

Telegram은 polling(아웃바운드)이므로 공인 인바운드 포트가 필요 없습니다. 포트는 기본 loopback에만 바인딩합니다.

## 확인

```sh
curl http://127.0.0.1:8085/actuator/health
curl -X POST -H 'X-ECC-Token: <token>' -H 'Content-Type: application/json' \
  -d '{"event":"TEST","title":"hello","body":"ping"}' http://127.0.0.1:8085/api/v1/notify
```

`{"sent": n}`이 오고 Telegram 메시지가 도착하면 정상입니다. `docker-compose.cloud.yml` overlay는 폐기되었고 `docker-compose.yml` 하나로 통합되었습니다.
