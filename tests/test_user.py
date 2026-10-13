import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.schemas import ErrorCode
from app.services.user_service import validate_username


class TestUser(unittest.TestCase):
    def test_empty_rejected(self):
        self.assertEqual(validate_username("")[0], ErrorCode.USERNAME_EMPTY)
        self.assertEqual(validate_username("   ")[0], ErrorCode.USERNAME_EMPTY)

    def test_too_long_rejected(self):
        self.assertEqual(validate_username("a" * 21)[0], ErrorCode.USERNAME_TOO_LONG)

    def test_phone_rejected(self):
        self.assertEqual(validate_username("13800138000")[0], ErrorCode.LOGIN_MODE_FORBIDDEN)

    def test_email_rejected(self):
        self.assertEqual(validate_username("a@b.com")[0], ErrorCode.LOGIN_MODE_FORBIDDEN)

    def test_valid_username(self):
        self.assertIsNone(validate_username("张三")[0])
        self.assertIsNone(validate_username("a" * 20)[0])


if __name__ == "__main__":
    unittest.main()