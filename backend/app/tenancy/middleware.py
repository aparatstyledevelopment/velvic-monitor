from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_org_scope(session: AsyncSession, org_id: UUID) -> None:
    """Set Postgres session-level org context. RLS policies read this.

    Called from auth dependency at the start of every authenticated request.
    Uses SET LOCAL so the value is scoped to the current transaction.
    """
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)").bindparams(
            org_id=str(org_id)
        )
    )
