# d94-app-ecc

ECC is a Python 3.12 FastAPI orchestration service. Telegram requests and authenticated REST requests create tickets, classify them through an optional Jetson Nano endpoint, and require an explicit Telegram approval before a serialized CLI execution.

## Commands

- Build image: `docker build -t d94-app-ecc .`
- Run locally: `pip install .` then `uvicorn ecc.main:app --reload`
- Deployment guide: [docs/deployment.md](docs/deployment.md)

## Safety invariants

- Telegram submissions and approval callbacks require a configured numeric user allowlist.
- REST API routes require `ECC_API_TOKEN`; health is the only unauthenticated route.
- Only configured CLI names and workspaces can be used. CLI executable paths must be absolute and configured inside the container.
- Every CLI job requires a Telegram approval and is processed through the single worker queue.
- Never put tokens, CLI credentials, or private keys in tracked files.

## Deployment

GitHub Actions builds and publishes `ghcr.io/david-yj-52/d94-app-ecc` on `deploy` pushes and `v*` tags. Servers pull and run it through Docker Compose. ECC must run on a machine/container environment that has the approved CLI executables and their credentials; the generic image does not bundle vendor CLIs.
