from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import AccountStatus

User = get_user_model()


class UserIdentityTests(TestCase):
    def test_email_identifier_is_trimmed_casefolded_and_password_is_hashed(self):
        user = User.objects.create_user(
            email="  Donor.Name@Example.Test ",
            display_name="  Example Donor  ",
            password="Synthetic-Password-Only-For-Test!",
        )

        self.assertEqual(user.email, "donor.name@example.test")
        self.assertIsNone(user.phone_e164)
        self.assertEqual(user.display_name, "Example Donor")
        self.assertEqual(user.account_status, AccountStatus.PENDING)
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password("Synthetic-Password-Only-For-Test!"))
        self.assertNotEqual(user.password, "Synthetic-Password-Only-For-Test!")

    def test_phone_identifier_requires_e164_and_remains_pending(self):
        user = User.objects.create_user(
            phone_e164=" +8801700000000 ",
            display_name="Example Phone User",
            password="Synthetic-Password-Only-For-Test!",
        )

        self.assertEqual(user.phone_e164, "+8801700000000")
        self.assertIsNone(user.email)
        self.assertEqual(user.get_username(), "+8801700000000")
        self.assertFalse(user.is_active)

    def test_creation_requires_exactly_one_identifier(self):
        with self.assertRaisesMessage(ValueError, "exactly one login identifier"):
            User.objects.create_user(display_name="No Identifier")
        with self.assertRaisesMessage(ValueError, "exactly one login identifier"):
            User.objects.create_user(
                email="one@example.test",
                phone_e164="+8801700000000",
                display_name="Two Identifiers",
            )

    def test_non_pending_regular_account_cannot_be_created(self):
        with self.assertRaisesMessage(ValueError, "must remain PENDING"):
            User.objects.create_user(
                email="premature@example.test",
                display_name="Unverified User",
                account_status=AccountStatus.ACTIVE,
            )

    def test_phone_identifier_normalizes_bangladesh_local_input_and_rejects_invalid(self):
        user = User.objects.create_user(
            phone_e164="01700000000",
            display_name="Local Phone",
            password="Synthetic-Password-Only-For-Test!",
        )
        self.assertEqual(user.phone_e164, "+8801700000000")
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                phone_e164="0170000000",
                display_name="Invalid Phone",
                password="Synthetic-Password-Only-For-Test!",
            )

    def test_phone_manager_normalizes_common_bangladesh_mobile_formats(self):
        from apps.accounts.managers import UserManager

        expected = "+8801700000000"
        for phone in (
            "01700000000",
            "+880 170 000 0000",
            "8801700000000",
            "008801700000000",
            "০১৭০০০০০০০০",
        ):
            with self.subTest(phone_format=phone):
                self.assertEqual(UserManager.normalize_phone_identifier(phone), expected)

    def test_direct_model_save_rejects_invalid_bangladesh_mobile(self):
        user = User(
            phone_e164="+8801100000000",
            display_name="Invalid Direct Save",
        )

        with self.assertRaises(ValidationError):
            user.save()

    def test_non_mobile_bangladesh_e164_remains_valid_for_legacy_compatibility(self):
        user = User.objects.create_user(
            phone_e164="+880212345678",
            display_name="Legacy E164 Example",
            password="Synthetic-Password-Only-For-Test!",
        )

        self.assertEqual(user.phone_e164, "+880212345678")

    def test_casefolded_email_and_phone_duplicates_are_rejected(self):
        User.objects.create_user(
            email="duplicate@example.test",
            display_name="First Email",
        )
        User.objects.create_user(
            phone_e164="+8801700000000",
            display_name="First Phone",
        )

        with self.assertRaises(ValidationError):
            User.objects.create_user(
                email="DUPLICATE@example.test",
                display_name="Second Email",
            )
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                phone_e164="+8801700000000",
                display_name="Second Phone",
            )

    def test_database_check_constraint_rejects_two_identifiers(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create(
                    email="both@example.test",
                    phone_e164="+8801700000000",
                    display_name="Invalid Both",
                    password="!",
                )

    def test_account_status_controls_authentication(self):
        user = User.objects.create_user(
            email="status@example.test",
            display_name="Status User",
        )
        self.assertFalse(user.is_active)

        user.account_status = AccountStatus.ACTIVE
        user.save(update_fields=["account_status", "updated_at"])
        self.assertTrue(user.is_active)

        for status in (AccountStatus.PENDING, AccountStatus.SUSPENDED, AccountStatus.DEACTIVATED):
            user.account_status = status
            user.save(update_fields=["account_status", "updated_at"])
            self.assertFalse(user.is_active)

    def test_django_authentication_rejects_pending_and_accepts_active_email_account(self):
        password = "Synthetic-Password-Only-For-Test!"
        user = User.objects.create_user(
            email="auth-status@example.test",
            display_name="Auth Status User",
            password=password,
        )

        self.assertIsNone(authenticate(username=user.email, password=password))
        user.account_status = AccountStatus.ACTIVE
        user.save(update_fields=["account_status", "updated_at"])
        self.assertEqual(authenticate(username=user.email, password=password), user)

    def test_superuser_creation_sets_required_permissions_and_active_status(self):
        user = User.objects.create_superuser(
            email="administrator@example.test",
            display_name="Synthetic Administrator",
            password="Synthetic-Password-Only-For-Test!",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.account_status, AccountStatus.ACTIVE)
