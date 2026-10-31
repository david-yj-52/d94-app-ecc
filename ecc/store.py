import json

from redis.asyncio import Redis

from ecc.config import Settings
from ecc.models import Ticket


class TicketStore:
    def __init__(self, redis: Redis, settings: Settings):
        self.redis = redis
        self.ttl = settings.ticket_ttl_seconds

    @staticmethod
    def _key(ticket_id: str) -> str:
        return f"ecc:ticket:{ticket_id}"

    async def save(self, ticket: Ticket) -> Ticket:
        await self.redis.set(self._key(ticket.ticket_id), ticket.model_dump_json(), ex=self.ttl)
        return ticket

    async def get(self, ticket_id: str) -> Ticket | None:
        raw = await self.redis.get(self._key(ticket_id))
        return Ticket.model_validate_json(raw) if raw else None

