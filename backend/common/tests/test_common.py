from cryptography.fernet import Fernet
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework import exceptions as drf_exceptions
from rest_framework import serializers

from common import crypto
from common.email.utils import mask_email, normalize_email
from common.exception.domain import ConflictException, ServiceUnavailableException
from common.exception.handler import exception_handler
from common.serializers.base import StrictSerializer
from common.serializers.fields import NormalizedEmailField


class ExceptionHandlerTests(SimpleTestCase):
    def test_app_exception_envelope(self):
        response = exception_handler(ConflictException(error_code="dup"), {})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "dup")
        self.assertFalse(response.data["success"])

    def test_drf_validation_error_flattened(self):
        exc = drf_exceptions.ValidationError({"email": ["Bad."]})
        response = exception_handler(exc, {})
        self.assertEqual(
            response.data["errors"], [{"field": "email", "message": "Bad."}]
        )

    def test_throttled_sets_retry_after(self):
        response = exception_handler(drf_exceptions.Throttled(wait=30), {})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "30")

    def test_unknown_exception_not_swallowed(self):
        self.assertIsNone(exception_handler(RuntimeError("boom"), {}))


class StrictSerializerTests(SimpleTestCase):
    def test_unknown_fields_listed(self):
        class S(StrictSerializer):
            name = serializers.CharField()

        s = S(data={"name": "a", "extra": 1})
        self.assertFalse(s.is_valid())
        self.assertIn("extra", s.errors)

    def test_email_field_normalizes(self):
        class S(StrictSerializer):
            email = NormalizedEmailField()

        self.assertEqual(S.parse({"email": "  A@B.com "})["email"], "a@b.com")

    def test_email_helpers(self):
        self.assertEqual(normalize_email(" X@Y.io "), "x@y.io")
        self.assertEqual(mask_email("jane@example.com"), "j***@example.com")


class CryptoTests(SimpleTestCase):
    def test_round_trip_and_rotation(self):
        old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        with override_settings(ENCRYPTION_KEYS=[old]):
            token = crypto.encrypt("secret")
        with override_settings(ENCRYPTION_KEYS=[new, old]):
            self.assertEqual(crypto.decrypt(token), "secret")
            rotated = crypto.rotate(token)
        with override_settings(ENCRYPTION_KEYS=[new]):
            self.assertEqual(crypto.decrypt(rotated), "secret")

    def test_missing_keys_raises(self):
        with (
            override_settings(ENCRYPTION_KEYS=[]),
            self.assertRaises(ServiceUnavailableException),
        ):
            crypto.encrypt("x")


class HealthTests(TestCase):
    def test_health_envelope(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"], {"status": "ok"})
        self.assertIn("X-Request-ID", response.headers)
