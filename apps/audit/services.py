"""Record redacted, append-only audit events."""

from uuid import UUID

from apps.audit.models import AuditEvent

ALLOWED_METADATA_KEYS = {"from_status", "to_status", "reason_code"}


def record_audit_event(
    *, actor, action, resource_type, resource_id=None, correlation_id=None, metadata=None
):
    """Persist only a small allowlist of non-sensitive audit metadata."""
    if not action or len(action) > 80:
        raise ValueError("Audit action must contain 1 to 80 characters.")
    if not resource_type or len(resource_type) > 60:
        raise ValueError("Audit resource type must contain 1 to 60 characters.")
    metadata = metadata or {}
    if not isinstance(metadata, dict) or metadata.keys() - ALLOWED_METADATA_KEYS:
        raise ValueError("Audit metadata contains unsupported fields.")
    safe_metadata = {}
    for key, value in metadata.items():
        if value is None:
            continue
        value = str(value)
        if len(value) > 40:
            raise ValueError("Audit metadata values are limited to 40 characters.")
        safe_metadata[key] = value
    for identifier in (resource_id, correlation_id):
        if identifier is not None and not isinstance(identifier, UUID):
            raise ValueError("Audit identifiers must be UUID values.")
    return AuditEvent.objects.create(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        correlation_id=correlation_id,
        metadata_redacted=safe_metadata,
    )
