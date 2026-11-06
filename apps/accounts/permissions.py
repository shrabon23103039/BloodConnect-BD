"""Reusable server-side account role and object access permissions."""

from enum import StrEnum

from rest_framework.permissions import BasePermission

from apps.accounts.models import AccountStatus


class AccountRole(StrEnum):
    AUTHENTICATED_USER = "AUTHENTICATED_USER"
    DONOR = "DONOR"
    MODERATOR = "MODERATOR"
    SUPERADMIN = "SUPERADMIN"
    ORGANIZATION_USER = "ORGANIZATION_USER"


def has_role(user, role: AccountRole | str) -> bool:
    """Return whether an active account has the requested application role."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "account_status", None) != AccountStatus.ACTIVE:
        return False

    role_name = str(role)
    if role_name == AccountRole.AUTHENTICATED_USER:
        return True
    if role_name == AccountRole.SUPERADMIN:
        return bool(getattr(user, "is_superuser", False))
    if role_name == AccountRole.DONOR:
        # Donor authority will be tied to a profile relation in P3-02.
        try:
            return getattr(user, "donor_profile", None) is not None
        except AttributeError:
            return False
    if role_name in {AccountRole.MODERATOR, AccountRole.ORGANIZATION_USER}:
        return user.groups.filter(name=role_name).exists()
    return False


class IsActiveAccount(BasePermission):
    """Allow only authenticated, active BloodConnect accounts."""

    def has_permission(self, request, view):
        return has_role(request.user, AccountRole.AUTHENTICATED_USER)


class HasAnyRole(BasePermission):
    """Allow a view only when the account has one of its declared roles."""

    def has_permission(self, request, view):
        roles = getattr(view, "required_roles", ())
        return any(has_role(request.user, role) for role in roles)


class IsObjectOwner(BasePermission):
    """Allow object access only to its owning user; no implicit staff bypass."""

    def has_object_permission(self, request, view, obj):
        if not has_role(request.user, AccountRole.AUTHENTICATED_USER):
            return False

        owner = getattr(obj, "user", None)
        if owner is None:
            owner = getattr(obj, "owner", None)
        return owner is not None and owner.pk == request.user.pk
