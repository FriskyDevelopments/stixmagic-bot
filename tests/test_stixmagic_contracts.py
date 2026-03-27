"""
Tests for stixmagic/contracts.py – shared product constants.

Covers:
 - All START_PAYLOAD_* constants are non-empty strings
 - PACK_TYPES is a set with the expected members
 - API_VERSION and PRODUCT_NAME are defined
 - MINIAPP_AUTH_HEADER is correct
 - Constants satisfy URL/slug rules expected by the Mini App flow
"""

import unittest

from stixmagic.contracts import (
    API_VERSION,
    MINIAPP_AUTH_HEADER,
    PACK_TYPE_ANIMATED,
    PACK_TYPE_IMAGE,
    PACK_TYPE_VIDEO,
    PACK_TYPES,
    PRODUCT_NAME,
    START_PAYLOAD_ADD,
    START_PAYLOAD_CREATE,
    START_PAYLOAD_FEATURE,
    START_PAYLOAD_MAGIC,
    START_PAYLOAD_MANAGE,
)


class TestContractConstants(unittest.TestCase):

    def test_product_name_defined(self):
        self.assertIsInstance(PRODUCT_NAME, str)
        self.assertTrue(len(PRODUCT_NAME) > 0)

    def test_api_version_defined(self):
        self.assertIsInstance(API_VERSION, str)
        self.assertTrue(len(API_VERSION) > 0)

    def test_miniapp_auth_header_value(self):
        self.assertEqual(MINIAPP_AUTH_HEADER, "X-Telegram-Init-Data")

    def test_start_payload_create(self):
        self.assertIsInstance(START_PAYLOAD_CREATE, str)
        self.assertTrue(len(START_PAYLOAD_CREATE) > 0)

    def test_start_payload_add(self):
        self.assertIsInstance(START_PAYLOAD_ADD, str)
        self.assertTrue(len(START_PAYLOAD_ADD) > 0)

    def test_start_payload_manage(self):
        self.assertIsInstance(START_PAYLOAD_MANAGE, str)
        self.assertTrue(len(START_PAYLOAD_MANAGE) > 0)

    def test_start_payload_magic(self):
        self.assertIsInstance(START_PAYLOAD_MAGIC, str)
        self.assertTrue(len(START_PAYLOAD_MAGIC) > 0)

    def test_start_payload_feature(self):
        self.assertIsInstance(START_PAYLOAD_FEATURE, str)
        self.assertTrue(len(START_PAYLOAD_FEATURE) > 0)

    def test_start_payloads_are_unique(self):
        payloads = [
            START_PAYLOAD_CREATE,
            START_PAYLOAD_ADD,
            START_PAYLOAD_MANAGE,
            START_PAYLOAD_MAGIC,
            START_PAYLOAD_FEATURE,
        ]
        self.assertEqual(len(payloads), len(set(payloads)), "START_PAYLOAD constants must be unique")

    def test_pack_types_set(self):
        self.assertIsInstance(PACK_TYPES, set)

    def test_pack_types_contains_image(self):
        self.assertIn(PACK_TYPE_IMAGE, PACK_TYPES)

    def test_pack_types_contains_animated(self):
        self.assertIn(PACK_TYPE_ANIMATED, PACK_TYPES)

    def test_pack_types_contains_video(self):
        self.assertIn(PACK_TYPE_VIDEO, PACK_TYPES)

    def test_pack_types_has_three_members(self):
        self.assertEqual(len(PACK_TYPES), 3)

    def test_pack_type_image_value(self):
        self.assertEqual(PACK_TYPE_IMAGE, "image")

    def test_pack_type_animated_value(self):
        self.assertEqual(PACK_TYPE_ANIMATED, "animated")

    def test_pack_type_video_value(self):
        self.assertEqual(PACK_TYPE_VIDEO, "video")

    def test_start_payloads_url_safe(self):
        """START_PAYLOAD values should be safe for use in Telegram bot deep link ?start= params."""
        import re
        safe_pattern = re.compile(r'^[a-zA-Z0-9_\-]+$')
        payloads = [
            START_PAYLOAD_CREATE,
            START_PAYLOAD_ADD,
            START_PAYLOAD_MANAGE,
            START_PAYLOAD_MAGIC,
            START_PAYLOAD_FEATURE,
        ]
        for payload in payloads:
            self.assertRegex(
                payload,
                safe_pattern,
                f"START_PAYLOAD {payload!r} contains characters unsafe for Telegram deep links",
            )


if __name__ == "__main__":
    unittest.main()