"""Re-export RBAC decorators from core.permissions."""
from apps.core.permissions import super_admin_required

__all__ = ["super_admin_required"]
