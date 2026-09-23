from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AuditLog

async def log_audit_event(
    db: AsyncSession,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict = None
):
    """Log an action to the audit table."""
    audit_entry = AuditLog(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_=metadata or {}
    )
    db.add(audit_entry)
    # The caller is responsible for db.commit() in most endpoints
