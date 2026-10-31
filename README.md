# d94-app-ecc

External Communication Channel (ECC) is a FastAPI service that accepts work requests over Telegram or an authenticated REST API, obtains an optional Jetson Nano intent plan, and sends a ticket to an allowlisted Telegram user for approval. Approved work runs serially through an allowlisted AI CLI in a configured workspace.

## Current scope

- Telegram polling with `/task <request>` and inline approve/reject buttons.
- Authenticated ticket creation and status lookup (`X-ECC-Token`).
- Optional Nano classifier at `/api/v1/classify`.
- Redis ticket storage with a seven-day default TTL.
- Optional Eureka registration.
- GHCR image publishing and manual Docker Compose deployment.

See [deployment.md](docs/deployment.md) for runtime requirements and operations.

