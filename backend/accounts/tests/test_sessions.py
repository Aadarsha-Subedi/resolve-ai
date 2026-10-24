from rest_framework.test import APIClient

from accounts.services.device import device_label
from accounts.tests.base import AccountsTestCase, google_identity

CHROME_LINUX = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)
SAFARI_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


class DeviceLabelTests(AccountsTestCase):
    def test_labels(self):
        self.assertEqual(device_label(CHROME_LINUX), "Chrome on Linux")
        self.assertEqual(device_label(SAFARI_IPHONE), "Safari on iOS")
        self.assertEqual(device_label(""), "Unknown device")


class SessionEndpointTests(AccountsTestCase):
    def two_devices(self):
        a = self.login_client(ua=CHROME_LINUX, ip="10.0.0.1")
        b = self.login_client(ua=SAFARI_IPHONE, ip="10.0.0.2")
        a.get("/api/me/", HTTP_USER_AGENT=CHROME_LINUX, REMOTE_ADDR="10.0.0.1")
        b.get("/api/me/", HTTP_USER_AGENT=SAFARI_IPHONE, REMOTE_ADDR="10.0.0.2")
        return a, b

    def test_requires_authentication(self):
        for method, path in (
            ("get", "/api/auth/sessions/"),
            ("delete", "/api/auth/sessions/1/"),
            ("post", "/api/auth/logout/"),
            ("post", "/api/auth/logout-all/"),
            ("get", "/api/me/"),
            ("patch", "/api/me/"),
            ("delete", "/api/me/"),
        ):
            response = getattr(APIClient(), method)(path)
            self.assertIn(response.status_code, (401, 403), (method, path))

    def test_list_marks_current_and_hides_ip(self):
        a, _ = self.two_devices()
        response = a.get("/api/auth/sessions/")
        self.assertEqual(response.status_code, 200)
        items = response.data["data"]["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(sum(i["is_current"] for i in items), 1)
        self.assertEqual(
            {i["device"] for i in items}, {"Chrome on Linux", "Safari on iOS"}
        )
        self.assertNotIn("10.0.0", response.content.decode())
        self.assertNotIn("ip", items[0])

    def test_revoke_other_device_and_it_is_rejected_next_request(self):
        a, b = self.two_devices()
        items = a.get("/api/auth/sessions/").data["data"]["items"]
        other = next(i for i in items if not i["is_current"])
        self.assertEqual(
            a.delete(f"/api/auth/sessions/{other['id']}/").status_code, 200
        )
        self.assertIn(b.get("/api/me/").status_code, (401, 403))
        self.assertEqual(a.get("/api/me/").status_code, 200)
        self.assertEqual(len(a.get("/api/auth/sessions/").data["data"]["items"]), 1)

    def test_cannot_revoke_current_session(self):
        a, _ = self.two_devices()
        items = a.get("/api/auth/sessions/").data["data"]["items"]
        current = next(i for i in items if i["is_current"])
        response = a.delete(f"/api/auth/sessions/{current['id']}/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "cannot_revoke_current_session")

    def test_cannot_revoke_another_users_session(self):
        a, _ = self.two_devices()
        stranger = self.login_client(
            identity=google_identity(sub="g-9", email="eve@example.com"),
            ua=CHROME_LINUX,
            ip="10.0.0.9",
        )
        stranger.get("/api/me/")
        other_id = stranger.get("/api/auth/sessions/").data["data"]["items"][0]["id"]
        self.assertEqual(a.delete(f"/api/auth/sessions/{other_id}/").status_code, 404)
        self.assertEqual(stranger.get("/api/me/").status_code, 200)

    def test_logout_ends_only_this_session(self):
        a, b = self.two_devices()
        self.assertEqual(a.post("/api/auth/logout/").status_code, 200)
        self.assertIn(a.get("/api/me/").status_code, (401, 403))
        self.assertEqual(b.get("/api/me/").status_code, 200)

    def test_logout_all_ends_every_session(self):
        a, b = self.two_devices()
        self.assertEqual(a.post("/api/auth/logout-all/").status_code, 200)
        self.assertIn(a.get("/api/me/").status_code, (401, 403))
        self.assertIn(b.get("/api/me/").status_code, (401, 403))

    def test_csrf_enforced_on_post_endpoints(self):
        client = APIClient(enforce_csrf_checks=True)
        self.sign_in(client=client)
        for method, path in (
            ("post", "/api/auth/logout/"),
            ("post", "/api/auth/logout-all/"),
            ("patch", "/api/me/"),
            ("delete", "/api/me/"),
        ):
            response = getattr(client, method)(
                path, {"display_name": "x"}, format="json"
            )
            self.assertEqual(response.status_code, 403, (method, path))
        self.assertEqual(client.get("/api/me/").status_code, 200)
        token = client.get("/api/csrf/").cookies["csrftoken"].value
        self.assertEqual(
            client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token).status_code, 200
        )

    def test_csrf_endpoint_sets_cookie(self):
        response = APIClient().get("/api/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
