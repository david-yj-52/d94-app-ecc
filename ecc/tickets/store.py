import asyncio

from ecc.tickets.models import Ticket, TicketStatus


class InMemoryTicketStore:
    """Temporary single-process store until d94-query exposes its ticket API."""

    def __init__(self) -> None:
        self._tickets: dict[str, Ticket] = {}
        self._lock = asyncio.Lock()

    async def create(self, ticket: Ticket) -> Ticket:
        async with self._lock:
            if ticket.ticket_id in self._tickets:
                raise ValueError(f"Ticket already exists: {ticket.ticket_id}")
            self._tickets[ticket.ticket_id] = ticket.model_copy(deep=True)
            return ticket.model_copy(deep=True)

    async def get(self, ticket_id: str) -> Ticket | None:
        async with self._lock:
            ticket = self._tickets.get(ticket_id)
            return ticket.model_copy(deep=True) if ticket else None

    async def decide(self, ticket_id: str, action: str, actor_id: int) -> Ticket | None:
        async with self._lock:
            ticket = self._tickets.get(ticket_id)
            if not ticket or ticket.status != TicketStatus.AWAITING_CONFIRM:
                return None
            if action == "approve":
                ticket.status = TicketStatus.PROCESSING
                ticket.approved_by = str(actor_id)
            elif action == "reject":
                ticket.status = TicketStatus.REJECTED
            else:
                raise ValueError("action must be approve or reject")
            return ticket.model_copy(deep=True)

    async def finish(self, ticket_id: str, status: TicketStatus, result: str) -> Ticket | None:
        async with self._lock:
            ticket = self._tickets.get(ticket_id)
            if not ticket or ticket.status != TicketStatus.PROCESSING:
                return None
            if status not in (TicketStatus.DONE, TicketStatus.FAILED):
                raise ValueError("finished status must be DONE or FAILED")
            ticket.status = status
            ticket.result = result
            return ticket.model_copy(deep=True)
