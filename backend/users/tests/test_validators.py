from django.test import TestCase
from django.core.exceptions import ValidationError
from users.validators import ComplexPasswordValidator

class ComplexPasswordValidatorTests(TestCase):
    def setUp(self):
        self.validator = ComplexPasswordValidator()

    def test_valid_password(self):
        password = "Test123!@#"
        try:
            self.validator.validate(password)
        except ValidationError:
            self.fail("Valid password raised ValidationError unexpectedly")

    def test_password_too_short(self):
        password = "Test12!"
        with self.assertRaisesMessage(ValidationError, "Mật khẩu phải có ít nhất 8 ký tự."):
            self.validator.validate(password)

    def test_password_no_digit(self):
        password = "Testabcd!@"
        with self.assertRaisesMessage(ValidationError, "Mật khẩu phải chứa ít nhất một chữ số."):
            self.validator.validate(password)

    def test_password_no_letter(self):
        password = "12345678!@"
        with self.assertRaisesMessage(ValidationError, "Mật khẩu phải chứa ít nhất một chữ cái."):
            self.validator.validate(password)

    def test_password_no_special_char(self):
        password = "Test123456"
        with self.assertRaisesMessage(ValidationError, "Mật khẩu phải chứa ít nhất một ký tự đặc biệt"):
            self.validator.validate(password)

    def test_get_help_text(self):
        expected = "Mật khẩu phải có ít nhất 8 ký tự và chứa ít nhất một chữ số, một chữ cái và một ký tự đặc biệt."
        self.assertEqual(self.validator.get_help_text(), expected)
