import base64

from django.test import SimpleTestCase

from email_integration.services import mime_service, parsing


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


class ParsingTests(SimpleTestCase):
    def test_message_ids_from_headers(self):
        self.assertEqual(
            parsing.message_ids("<a@x.com>", "<b@x.com> <c@y.org>\n <a@x.com>", ""),
            ["<a@x.com>", "<b@x.com>", "<c@y.org>"],
        )
        self.assertEqual(parsing.message_ids("", None), [])

    def test_parse_sender(self):
        self.assertEqual(
            parsing.parse_sender('"Jane Doe" <Jane@Example.COM>'),
            ("Jane Doe", "jane@example.com"),
        )
        self.assertEqual(
            parsing.parse_sender("plain@example.com"), ("", "plain@example.com")
        )
        self.assertEqual(parsing.parse_sender(""), ("", ""))

    def test_quoted_reply_and_signature_are_dropped(self):
        text = (
            "Thanks, that fixed it!\n\nOn Tue, 20 Oct 2026 at 10:00, Support <s@acme.com> wrote:\n"
            "> Did you try resetting?\n> More text\n"
        )
        self.assertEqual(parsing.strip_quoted_reply(text), "Thanks, that fixed it!")
        self.assertEqual(
            parsing.strip_quoted_reply("Hi\n> quoted\nStill me\n-- \nJane"),
            "Hi\nStill me",
        )
        self.assertEqual(parsing.strip_quoted_reply("A\n\n\n\nB"), "A\n\nB")
        self.assertEqual(len(parsing.strip_quoted_reply("x" * 30_000)), 20_000)

    def test_html_becomes_text_without_scripts(self):
        html = "<div>Hello<br>world</div><script>alert(1)</script><p>Bye</p>"
        text = parsing.html_to_text(html)
        self.assertIn("Hello", text)
        self.assertNotIn("alert", text)
        self.assertNotIn("<", text)

    def test_extract_text_prefers_plain_and_walks_parts(self):
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/html", "body": {"data": _b64("<b>html</b>")}},
                {"mimeType": "text/plain", "body": {"data": _b64("plain text")}},
            ],
        }
        self.assertEqual(parsing.extract_text(payload), "plain text")
        only_html = {
            "mimeType": "text/html",
            "body": {"data": _b64("<p>just html</p>")},
        }
        self.assertEqual(parsing.extract_text(only_html), "just html")
        self.assertEqual(
            parsing.extract_text({"mimeType": "image/png", "body": {}}), ""
        )

    def test_clean_header_removes_line_breaks(self):
        self.assertEqual(
            parsing.clean_header("Hi\r\nBcc: evil@x.com"), "Hi Bcc: evil@x.com"
        )


class MimeTests(SimpleTestCase):
    def test_reply_has_threading_headers_and_no_injection(self):
        from email import message_from_bytes

        raw = mime_service.build_reply(
            from_name="Agent\r\nBcc: evil@x.com",
            from_email="agent@acme.com",
            to_email="cust@example.com\r\nBcc: evil@x.com",
            subject="Re: Help\r\nBcc: evil@x.com",
            body="Hello",
            in_reply_to="<a@x.com>",
            references=["<a@x.com>", "<b@x.com>"],
        )
        message = message_from_bytes(raw)
        self.assertIsNone(message["Bcc"])
        self.assertEqual(message["In-Reply-To"], "<a@x.com>")
        self.assertEqual(message["References"], "<a@x.com> <b@x.com>")
        self.assertTrue(message["Message-ID"].startswith("<"))
        self.assertEqual(message.get_payload().strip(), "Hello")
        self.assertEqual(message.get_content_type(), "text/plain")

    def test_reply_subject(self):
        self.assertEqual(
            mime_service.reply_subject("Cannot log in", 7), "Re: Cannot log in [#7]"
        )
        self.assertEqual(
            mime_service.reply_subject("Re: Cannot log in", 7), "Re: Cannot log in [#7]"
        )
