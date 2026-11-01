import asyncio
import os
from pathlib import Path

from ecc.config.settings import Settings


class CliExecutor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.queue: asyncio.Queue[tuple[str, str, str, asyncio.Future[str]]] = asyncio.Queue()
        self.worker: asyncio.Task | None = None

    async def start(self) -> None:
        self.worker = asyncio.create_task(self._run_queue(), name="ecc-cli-worker")

    async def stop(self) -> None:
        if self.worker:
            self.worker.cancel()
            try:
                await self.worker
            except asyncio.CancelledError:
                pass

    def resolve_workspace(self, value: str) -> Path:
        target = Path(value).resolve(strict=True)
        roots = [Path(root).resolve(strict=True) for root in self.settings.workspace_roots]
        if not any(target == root or root in target.parents for root in roots):
            raise ValueError("Workspace is outside configured ECC_CLI_WORKSPACES")
        if not target.is_dir():
            raise ValueError("Workspace must be a directory")
        return target

    async def execute(self, cli: str, workspace: str, prompt: str) -> str:
        cli = cli.lower()
        if cli not in self.settings.allowed_clis:
            raise ValueError("Requested CLI is not allowlisted")
        root = self.resolve_workspace(workspace)
        if not self.worker or self.worker.done():
            raise RuntimeError("CLI worker is not running")
        future = asyncio.get_running_loop().create_future()
        await self.queue.put((cli, str(root), prompt, future))
        return await future

    async def _run_queue(self) -> None:
        while True:
            cli, workspace, prompt, future = await self.queue.get()
            try:
                executable = self.settings.executable_map.get(cli, cli)
                if not os.path.isabs(executable):
                    raise ValueError(f"CLI executable for {cli} must be an absolute path")
                # Use each CLI's non-interactive mode; prompt stays a single argv item.
                args = {
                    "claude": ["-p", prompt],
                    "gemini": ["-p", prompt],
                    "codex": ["exec", prompt],
                }[cli]
                proc = await asyncio.create_subprocess_exec(
                    executable,
                    *args,
                    cwd=workspace,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    env={**os.environ, "CI": "1"},
                )
                try:
                    output, _ = await asyncio.wait_for(
                        proc.communicate(), timeout=self.settings.cli_timeout_seconds
                    )
                except TimeoutError:
                    proc.kill()
                    await proc.wait()
                    raise RuntimeError("CLI execution timed out")
                result = output.decode(errors="replace")[-12000:]
                if proc.returncode:
                    raise RuntimeError(f"CLI exited {proc.returncode}: {result}")
                if not future.cancelled():
                    future.set_result(result)
            except Exception as exc:
                if not future.cancelled():
                    future.set_exception(exc)
            finally:
                self.queue.task_done()

