from django.test import TestCase
from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils import timezone
from users.backends import EmailPhoneBackend
from rest_framework.exceptions import ValidationError
from common.enums import UserRole

User = get_user_model()

class EmailPhoneBackendTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a standard user
        cls.user = User.objects.create_user(
            email='test@example.com',
            phone='0987654321',
            password='TestPass123!',
            role=UserRole.PATIENT.value,
            is_active=True,
            is_deleted=False
        )
        # Create an inactive user
        cls.inactive_user = User.objects.create_user(
            email='inactive@example.com',
            phone='0123456789',
            password='InactivePass123!',
            role=UserRole.PATIENT.value,
            is_active=False,
            is_deleted=False
        )
        # Create a soft-deleted user
        cls.deleted_user = User.objects.create_user(
            email='deleted@example.com',
            phone='0112233445',
            password='DeletedPass123!',
            role=UserRole.PATIENT.value,
            is_active=True,
            is_deleted=False
        )
        cls.deleted_user.soft_delete()

    def setUp(self):
        self.backend = EmailPhoneBackend()

    def test_authenticate_with_email_success(self):
        user = self.backend.authenticate(None, username='test@example.com', password='TestPass123!')
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.user.id)
        self.assertEqual(user.email, 'test@example.com')

    def test_authenticate_with_phone_success(self):
        user = self.backend.authenticate(None, username='0987654321', password='TestPass123!')
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.user.id)
        self.assertEqual(user.phone, '0987654321')

    def test_authenticate_with_email_kwargs_success(self):
        user = self.backend.authenticate(None, email='test@example.com', password='TestPass123!')
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.user.id)
        self.assertEqual(user.email, 'test@example.com')

    def test_authenticate_with_phone_kwargs_success(self):
        user = self.backend.authenticate(None, phone='0987654321', password='TestPass123!')
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.user.id)
        self.assertEqual(user.phone, '0987654321')

    def test_authenticate_nonexistent_user(self):
        user = self.backend.authenticate(None, username='nonexistent@example.com', password='TestPass123!')
        self.assertIsNone(user)
        user = self.backend.authenticate(None, username='9999999999', password='TestPass123!')
        self.assertIsNone(user)

    def test_authenticate_incorrect_password(self):
        user = self.backend.authenticate(None, username='test@example.com', password='WrongPass123!')
        self.assertIsNone(user)
        user = self.backend.authenticate(None, username='0987654321', password='WrongPass123!')
        self.assertIsNone(user)

    def test_authenticate_inactive_user(self):
        user = self.backend.authenticate(None, username='inactive@example.com', password='InactivePass123!')
        self.assertIsNone(user)
        user = self.backend.authenticate(None, username='0123456789', password='InactivePass123!')
        self.assertIsNone(user)

    def test_authenticate_deleted_user(self):
        user = self.backend.authenticate(None, username='deleted@example.com', password='DeletedPass123!')
        self.assertIsNone(user)
        user = self.backend.authenticate(None, username='0112233445', password='DeletedPass123!')
        self.assertIsNone(user)

    def test_authenticate_missing_username(self):
        user = self.backend.authenticate(None, password='TestPass123!')
        self.assertIsNone(user)

    def test_authenticate_missing_password(self):
        user = self.backend.authenticate(None, username='test@example.com')
        self.assertIsNone(user)

    def test_user_can_authenticate_active_user(self):
        self.assertTrue(self.backend.user_can_authenticate(self.user))

    def test_user_can_authenticate_inactive_user(self):
        self.assertFalse(self.backend.user_can_authenticate(self.inactive_user))

    def test_user_can_authenticate_deleted_user(self):
        self.assertFalse(self.backend.user_can_authenticate(self.deleted_user))

    def test_get_user_success(self):
        user = self.backend.get_user(self.user.id)
        self.assertEqual(user.id, self.user.id)
        self.assertEqual(user.email, 'test@example.com')

    def test_get_user_nonexistent(self):
        with self.assertRaises(Http404):
            self.backend.get_user(999)

    def test_get_user_deleted(self):
        with self.assertRaises(Http404):
            self.backend.get_user(self.deleted_user.id)
