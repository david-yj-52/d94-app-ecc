# ECC deployment (GHCR + Docker Compose)

## Deployment shape

GitHub Actions performs package validation and builds/pushes the container image. Like d94-query and UMD, it does not SSH to or restart a server. Operators pull a published tag and run Compose on the target machine.

ECC has an important placement requirement: it executes approved AI CLIs. Deploy it on the development PC or on a dedicated execution host that has the approved CLI programs and their credentials. The generic GHCR image intentionally does not install Claude, Gemini, or Codex. A server used only for Eureka/Config or ticket storage cannot execute developer-PC CLIs; keep ECC on the machine that owns those CLIs or provide a separately secured runner integration.

```text
Telegram ──polling──▶ ECC (execution host) ──▶ Jetson Nano (optional classifier)
                              │
                              ├── Redis (ticket state)
                              ├── Eureka (optional registration)
                              └── approved CLI ──▶ mounted workspace
```

## 1. Publish the image

The workflow `.github/workflows/deploy.yml` follows the d94-query/UMD release pattern:

| Event | Result |
|---|---|
| Pull request targeting `deploy` | Python package install and source compilation validation |
| Push to `deploy` | Validation, container build, GHCR push with `latest` and `sha-...` tags |
| Push `v*` tag | Validation, container build, GHCR push with semver and `sha-...` tags |

The image is `ghcr.io/david-yj-52/d94-app-ecc`. There is no Maven package token because ECC has no private Maven dependencies. If the GHCR package is private, authenticate on the host with a GitHub token granted `read:packages`:

```sh
docker login ghcr.io
```

## 2. Prepare the execution host

1. Install Docker Engine and the Compose plugin.
2. Install the vendor CLI programs and authenticate them for a dedicated ECC operating-system account. The binaries must be accessible inside the container at the paths set by `ECC_CLI_EXECUTABLES`.
3. Build a derived image that installs those CLI programs, or mount a controlled executable/runtime bundle. Confirm each CLI can run non-interactively as container UID `10001`. Do not expose a host Docker socket to ECC.
4. Create a workspace directory containing only repositories ECC may modify. The compose file mounts this directory at `/workspace`.
5. Create the shared cloud network only if Eureka registration is enabled and ECC needs to share the existing Eureka network.

CLI vendors change their installation and headless-authentication requirements independently. Provision and pin the CLI versions in the derived execution image and validate them against that vendor's current official instructions before rollout. The generic ECC image only contains the orchestration service.

## 3. Configure Compose

```sh
cp .env.example .env
mkdir -p workspace cli-auth
```

Edit `.env` and provide:

- `ECC_API_TOKEN`: long random REST API secret; never publish the API port publicly.
- `ECC_TELEGRAM_BOT_TOKEN` and `ECC_TELEGRAM_ALLOWED_USER_IDS`: bot token and numeric IDs permitted to submit and approve work. Keep the allowlist narrow.
- `WORKSPACE_HOST_PATH`: absolute host path to the authorized repository directory.
- `ECC_CLI_EXECUTABLES`: absolute executable paths available inside the ECC image.
- `ECC_CLI_WORKSPACES`: allowed in-container workspace roots. Requests outside them are rejected.
- Optional `ECC_NANO_ENDPOINT` and Eureka settings.

The Compose file publishes the REST API on `127.0.0.1:8085` by default, creates an internal Redis network and persistent data volume, and attaches ECC to the existing `befw-cloud-network` for optional Eureka access. If that external network does not exist and Eureka is unused, remove the `cloud` network attachment and declaration for this deployment.

## 4. Build a derived execution image

Create a host-managed Dockerfile based on the exact GHCR ECC release and add pinned CLI installations according to each vendor's official install guide. Configure those CLIs for non-interactive use. Keep the vendor auth state in the dedicated `CLI_AUTH_HOST_PATH` directory, owned by or writable to UID 10001. This directory is mounted as the container home so CLI tools can persist their own state; protect it like a credential store and never commit it. Then either update the compose `image` to your derived image or use a Compose override file. Do not bake credentials into the image.

## 5. Deploy / update

```sh
docker compose --env-file .env pull
docker compose --env-file .env up -d
docker compose ps
curl -fsS http://127.0.0.1:8085/actuator/health
```

To roll back, set `IMAGE_TAG` to the previous semver or `sha-...` tag, then run `pull` and `up -d` again. Keep the same `ecc-redis` volume to retain tickets; Redis expiry removes ticket records after `ECC_TICKET_TTL_SECONDS`.

## 6. API and lifecycle

`GET /actuator/health` checks Redis and is unauthenticated for container health checks. Other REST endpoints require `X-ECC-Token: $ECC_API_TOKEN`:

```sh
curl -H "X-ECC-Token: $ECC_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Review the authentication flow","workspace":"/workspace/my-repo"}' \
  http://127.0.0.1:8085/api/v1/tickets
```

Ticket creation returns `AWAITING_CONFIRM` and sends an approval request to the first configured Telegram user. Approval runs the ticket through a single in-process queue; reject does not run it. `GET /api/v1/tickets/{ticket_id}` returns current state. Telegram `/task <request>` creates the same kind of ticket using `ECC_TELEGRAM_DEFAULT_WORKSPACE`.

## Operational limits

- Current tickets are stored in Redis. The approval claim prevents duplicate callback execution; it is not a distributed execution lease for multiple ECC replicas. Run exactly one ECC instance until distributed worker leasing is implemented.
- The REST API has no user identity model; protect its token and keep it bound to loopback or a trusted private network.
- CLI calls receive the request text as one argument and run in the approved workspace. Approval authorizes the requested prompt; inspect Nano-generated plans before approving if a classifier is enabled.
- The FastAPI service does not currently fetch settings from Spring Cloud Config. Deploy-time configuration is supplied through `.env`.
- Back up or preserve the `ecc-redis` volume if ticket history matters. No database migrations are required.
