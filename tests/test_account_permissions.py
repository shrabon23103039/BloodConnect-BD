from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser, Group
from django.test import RequestFactory, TestCase

from apps.accounts.models import AccountStatus, User
from apps.accounts.permissions import (
    AccountRole,
    HasAnyRole,
    IsActiveAccount,
    IsObjectOwner,
    has_role,
)


class AccountPermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="strong-test-password-123",
            display_name="Owner",
        )
        self.other = User.objects.create_user(
            email="other@example.com",
            password="strong-test-password-123",
            display_name="Other",
        )
        self.owner.account_status = AccountStatus.ACTIVE
        self.owner.save(update_fields=["account_status", "updated_at"])
        self.other.account_status = AccountStatus.ACTIVE
        self.other.save(update_fields=["account_status", "updated_at"])
        self.view = SimpleNamespace()
        self.obj = SimpleNamespace(user=self.owner)

    def request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_active_account_role_and_permission(self):
        request = self.request(self.owner)
        self.assertTrue(has_role(self.owner, AccountRole.AUTHENTICATED_USER))
        self.assertTrue(IsActiveAccount().has_permission(request, self.view))

    def test_anonymous_pending_suspended_and_deactivated_are_denied(self):
        self.assertFalse(has_role(AnonymousUser(), AccountRole.AUTHENTICATED_USER))
        self.assertFalse(IsActiveAccount().has_permission(self.request(AnonymousUser()), self.view))
        for status in (AccountStatus.PENDING, AccountStatus.SUSPENDED, AccountStatus.DEACTIVATED):
            self.owner.account_status = status
            self.assertFalse(has_role(self.owner, AccountRole.AUTHENTICATED_USER))

    def test_only_explicit_moderator_group_grants_moderator_role(self):
        self.owner.is_staff = True
        self.owner.save(update_fields=["is_staff", "updated_at"])
        self.view.required_roles = (AccountRole.MODERATOR,)
        permission = HasAnyRole()
        self.assertFalse(permission.has_permission(self.request(self.owner), self.view))

        self.owner.groups.add(Group.objects.create(name=AccountRole.MODERATOR))
        self.assertTrue(permission.has_permission(self.request(self.owner), self.view))

    def test_superadmin_role_requires_is_superuser_not_staff(self):
        self.assertFalse(has_role(self.owner, AccountRole.SUPERADMIN))
        self.owner.is_staff = True
        self.owner.save(update_fields=["is_staff", "updated_at"])
        self.assertFalse(has_role(self.owner, AccountRole.SUPERADMIN))
        self.owner.is_superuser = True
        self.assertTrue(has_role(self.owner, AccountRole.SUPERADMIN))

    def test_owner_access_is_limited_to_the_exact_active_user(self):
        permission = IsObjectOwner()
        self.assertTrue(permission.has_object_permission(self.request(self.owner), self.view, self.obj))
        self.assertFalse(permission.has_object_permission(self.request(self.other), self.view, self.obj))
        self.assertFalse(permission.has_object_permission(self.request(AnonymousUser()), self.view, self.obj))

    def test_owner_permission_supports_owner_attribute_and_no_admin_bypass(self):
        permission = IsObjectOwner()
        self.obj = SimpleNamespace(owner=self.owner)
        self.assertTrue(permission.has_object_permission(self.request(self.owner), self.view, self.obj))

        self.other.is_superuser = True
        self.assertFalse(permission.has_object_permission(self.request(self.other), self.view, self.obj))
