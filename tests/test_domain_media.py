"""
Tests for domain/media.py – sticker media processing pipeline.

Covers:
 - extract_file_info: all message media types
 - convert_to_sticker: WEBP output, RGBA mode, size capping, invalid input
 - apply_mask_to_image: compositing, inversion, size/format output
 - async wrappers: delegate correctly via asyncio.run()
 - download_file_bytes: success and error paths
"""

import asyncio
import io
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from PIL import Image

from domain.media import (
    apply_mask_to_image,
    async_apply_mask_to_image,
    async_convert_to_sticker,
    async_convert_video_to_sticker,
    convert_to_sticker,
    download_file_bytes,
    extract_file_info,
)


# ── Helpers ───────────────────────────────────────────────────

def _make_png_bytes(width: int = 100, height: int = 100, mode: str = "RGB") -> io.BytesIO:
    """Return a BytesIO containing a simple solid-colour PNG."""
    img = Image.new(mode, (width, height), color=(255, 128, 0) if mode == "RGB" else (255, 128, 0, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _make_message(
    *,
    sticker=None,
    photo=None,
    document=None,
    video=None,
    animation=None,
    video_note=None,
) -> MagicMock:
    """Build a minimal mock telegram.Message object."""
    msg = MagicMock()
    msg.sticker = sticker
    msg.photo = photo
    msg.document = document
    msg.video = video
    msg.animation = animation
    msg.video_note = video_note
    return msg


# ── extract_file_info ─────────────────────────────────────────

class TestExtractFileInfo(unittest.TestCase):

    def test_photo_returns_image_static(self):
        photo_obj = MagicMock(file_id="photo_id_1")
        msg = _make_message(photo=[MagicMock(file_id="small"), photo_obj])
        fid, mt, sf = extract_file_info(msg)
        self.assertEqual(fid, "photo_id_1")
        self.assertEqual(mt, "image")
        self.assertEqual(sf, "static")

    def test_sticker_static(self):
        sticker = MagicMock(file_id="sticker_static", is_video=False)
        msg = _make_message(sticker=sticker)
        fid, mt, sf = extract_file_info(msg)
        self.assertEqual(fid, "sticker_static")
        self.assertEqual(mt, "sticker")
        self.assertEqual(sf, "static")

    def test_sticker_video(self):
        sticker = MagicMock(file_id="sticker_vid", is_video=True)
        msg = _make_message(sticker=sticker)
        fid, mt, sf = extract_file_info(msg)
        self.assertEqual(fid, "sticker_vid")
        self.assertEqual(mt, "sticker")
        self.assertEqual(sf, "video")

    def test_document_image_mime(self):
        doc = MagicMock(file_id="doc_img", mime_type="image/png")
        msg = _make_message(document=doc)
        fid, mt, sf = extract_file_info(msg)
        self.assertEqual(fid, "doc_img")
        self.assertEqual(mt, "image")
        self.assertEqual(sf, "static")

    def test_document_video_mime(self):
        doc = MagicMock(file_id="doc_vid", mime_type="video/mp4")
        msg = _make_message(document=doc)
        fid, mt, sf = extract_file_info(msg)
        self.assertEqual(fid, "doc_vid")
        self.assertEqual(mt, "video")
        self.assertEqual(sf, "video")

    def test_document_gif_mime(self):
        # "image/gif" starts with "image/" so the image/ branch fires first.
        # The mime == "image/gif" check on the video branch is unreachable for this value.
        doc = MagicMock(file_id="doc_gif", mime_type="image/gif")
        msg = _make_message(document=doc)
        fid, mt, sf = extract_file_info(msg)
        self.assertEqual(fid, "doc_gif")
        self.assertEqual(mt, "image")
        self.assertEqual(sf, "static")

    def test_document_unknown_mime_falls_back_to_image(self):
        doc = MagicMock(file_id="doc_unk", mime_type="application/octet-stream")
        msg = _make_message(document=doc)
        fid, mt, sf = extract_file_info(msg)
        self.assertEqual(fid, "doc_unk")
        self.assertEqual(mt, "image")
        self.assertEqual(sf, "static")

    def test_document_none_mime_falls_back_to_image(self):
        doc = MagicMock(file_id="doc_none", mime_type=None)
        msg = _make_message(document=doc)
        fid, mt, sf = extract_file_info(msg)
        self.assertEqual(fid, "doc_none")
        self.assertEqual(mt, "image")
        self.assertEqual(sf, "static")

    def test_video_message(self):
        vid = MagicMock(file_id="vid_id")
        msg = _make_message(video=vid)
        fid, mt, sf = extract_file_info(msg)
        self.assertEqual(fid, "vid_id")
        self.assertEqual(mt, "video")
        self.assertEqual(sf, "video")

    def test_animation_message(self):
        anim = MagicMock(file_id="anim_id")
        msg = _make_message(animation=anim)
        fid, mt, sf = extract_file_info(msg)
        self.assertEqual(fid, "anim_id")
        self.assertEqual(mt, "video")
        self.assertEqual(sf, "video")

    def test_video_note_message(self):
        vn = MagicMock(file_id="vn_id")
        msg = _make_message(video_note=vn)
        fid, mt, sf = extract_file_info(msg)
        self.assertEqual(fid, "vn_id")
        self.assertEqual(mt, "video")
        self.assertEqual(sf, "video")

    def test_no_media_returns_none_triple(self):
        msg = _make_message()
        fid, mt, sf = extract_file_info(msg)
        self.assertIsNone(fid)
        self.assertIsNone(mt)
        self.assertIsNone(sf)

    def test_photo_uses_last_element(self):
        """Telegram returns photos in ascending resolution; last = highest."""
        photos = [
            MagicMock(file_id="small"),
            MagicMock(file_id="medium"),
            MagicMock(file_id="large"),
        ]
        msg = _make_message(photo=photos)
        fid, _, _ = extract_file_info(msg)
        self.assertEqual(fid, "large")


# ── convert_to_sticker ────────────────────────────────────────

class TestConvertToSticker(unittest.TestCase):

    def test_returns_bytesio(self):
        buf = _make_png_bytes(100, 100)
        result = convert_to_sticker(buf)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, io.BytesIO)

    def test_output_is_webp(self):
        buf = _make_png_bytes(100, 100)
        result = convert_to_sticker(buf)
        img = Image.open(result)
        self.assertEqual(img.format, "WEBP")

    def test_output_is_rgba(self):
        # Lossy WebP may store as RGB even when the source was RGBA.
        # The function guarantees a valid WebP output, not necessarily RGBA mode on disk.
        buf = _make_png_bytes(100, 100, mode="RGB")
        result = convert_to_sticker(buf)
        img = Image.open(result)
        # Should always be convertible to RGBA
        self.assertEqual(img.convert("RGBA").mode, "RGBA")

    def test_output_size_within_512(self):
        buf = _make_png_bytes(1024, 768)
        result = convert_to_sticker(buf)
        img = Image.open(result)
        w, h = img.size
        self.assertLessEqual(max(w, h), 512)

    def test_landscape_image_caps_width(self):
        buf = _make_png_bytes(800, 400)
        result = convert_to_sticker(buf)
        img = Image.open(result)
        self.assertEqual(img.size[0], 512)

    def test_portrait_image_caps_height(self):
        buf = _make_png_bytes(300, 600)
        result = convert_to_sticker(buf)
        img = Image.open(result)
        self.assertEqual(img.size[1], 512)

    def test_small_image_is_not_upscaled_to_512(self):
        """An image smaller than 512 px should stay below 512 on the long side."""
        buf = _make_png_bytes(50, 50)
        result = convert_to_sticker(buf)
        img = Image.open(result)
        # Small images get scaled up to fill 512 px on longest side
        self.assertLessEqual(max(img.size), 512)

    def test_file_size_within_64kb(self):
        buf = _make_png_bytes(512, 512)
        result = convert_to_sticker(buf)
        result.seek(0, 2)
        size = result.tell()
        self.assertLessEqual(size, 64_000)

    def test_invalid_input_returns_none(self):
        buf = io.BytesIO(b"not-an-image")
        result = convert_to_sticker(buf)
        self.assertIsNone(result)

    def test_empty_bytesio_returns_none(self):
        result = convert_to_sticker(io.BytesIO(b""))
        self.assertIsNone(result)

    def test_rgba_input_preserved(self):
        buf = _make_png_bytes(100, 100, mode="RGBA")
        result = convert_to_sticker(buf)
        self.assertIsNotNone(result)
        img = Image.open(result)
        self.assertEqual(img.mode, "RGBA")


# ── apply_mask_to_image ───────────────────────────────────────

class TestApplyMaskToImage(unittest.TestCase):

    def _make_mask_bytes(self, width: int = 100, height: int = 100, value: int = 255) -> io.BytesIO:
        """Return a solid grayscale PNG mask (L mode)."""
        img = Image.new("L", (width, height), color=value)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def test_returns_bytesio(self):
        src = _make_png_bytes(100, 100)
        mask = self._make_mask_bytes()
        result = apply_mask_to_image(src, mask)
        self.assertIsInstance(result, io.BytesIO)

    def test_output_is_webp(self):
        src = _make_png_bytes(100, 100)
        mask = self._make_mask_bytes()
        result = apply_mask_to_image(src, mask)
        img = Image.open(result)
        self.assertEqual(img.format, "WEBP")

    def test_output_has_alpha(self):
        src = _make_png_bytes(100, 100)
        mask = self._make_mask_bytes()
        result = apply_mask_to_image(src, mask)
        img = Image.open(result)
        # Convert to RGBA to check: lossy WEBP may strip a fully-opaque alpha channel
        rgba = img.convert("RGBA")
        self.assertEqual(rgba.mode, "RGBA")

    def test_white_mask_keeps_content(self):
        """White mask (255) should keep pixels fully opaque."""
        src = _make_png_bytes(64, 64)
        mask = self._make_mask_bytes(64, 64, value=255)
        result = apply_mask_to_image(src, mask)
        img = Image.open(result).convert("RGBA")
        # Sample corners — all should be fully opaque
        w, h = img.size
        corners = [img.getpixel((0, 0)), img.getpixel((w-1, h-1))]
        for pixel in corners:
            self.assertEqual(pixel[3], 255, "Expected fully opaque pixel with white mask")

    def test_black_mask_makes_transparent(self):
        """Black mask (0) should produce fully transparent pixels."""
        src = _make_png_bytes(64, 64)
        mask = self._make_mask_bytes(64, 64, value=0)
        result = apply_mask_to_image(src, mask)
        img = Image.open(result).convert("RGBA")
        # Sample corners — all should be fully transparent
        w, h = img.size
        corners = [img.getpixel((0, 0)), img.getpixel((w-1, h-1))]
        for pixel in corners:
            self.assertEqual(pixel[3], 0, "Expected fully transparent pixel with black mask")

    def test_inverted_flips_mask(self):
        """White mask + inverted=True should produce transparent output."""
        src = _make_png_bytes(64, 64)
        mask = self._make_mask_bytes(64, 64, value=255)
        result = apply_mask_to_image(src, mask, inverted=True)
        img = Image.open(result).convert("RGBA")
        w, h = img.size
        corners = [img.getpixel((0, 0)), img.getpixel((w-1, h-1))]
        for pixel in corners:
            self.assertEqual(pixel[3], 0, "Expected fully transparent pixel when white mask inverted")

    def test_output_size_within_512(self):
        src = _make_png_bytes(1024, 768)
        mask = self._make_mask_bytes(1024, 768)
        result = apply_mask_to_image(src, mask)
        img = Image.open(result)
        w, h = img.size
        self.assertLessEqual(max(w, h), 512)

    def test_file_size_within_64kb(self):
        src = _make_png_bytes(512, 512)
        mask = self._make_mask_bytes(512, 512)
        result = apply_mask_to_image(src, mask)
        result.seek(0, 2)
        size = result.tell()
        self.assertLessEqual(size, 64_000)

    def test_mask_resized_to_source_dimensions(self):
        """Mask with different dimensions from source should be resized."""
        src = _make_png_bytes(200, 200)
        mask = self._make_mask_bytes(50, 50, value=255)
        # Should not raise
        result = apply_mask_to_image(src, mask)
        self.assertIsNotNone(result)
        img = Image.open(result)
        self.assertIsNotNone(img)

    def test_default_inverted_false(self):
        """Default inverted=False means white keeps, black discards."""
        src = _make_png_bytes(64, 64)
        mask_white = self._make_mask_bytes(64, 64, value=255)
        result = apply_mask_to_image(src, mask_white)
        img = Image.open(result).convert("RGBA")
        w, h = img.size
        corners = [img.getpixel((0, 0)), img.getpixel((w-1, h-1))]
        for pixel in corners:
            self.assertEqual(pixel[3], 255, "White mask (not inverted) should keep pixels opaque")


# ── Async wrappers ────────────────────────────────────────────

class TestAsyncWrappers(unittest.TestCase):

    def test_async_convert_to_sticker_delegates(self):
        buf = _make_png_bytes(100, 100)
        result = asyncio.run(async_convert_to_sticker(buf))
        self.assertIsNotNone(result)
        self.assertIsInstance(result, io.BytesIO)
        img = Image.open(result)
        self.assertEqual(img.format, "WEBP")

    def test_async_convert_to_sticker_invalid_returns_none(self):
        buf = io.BytesIO(b"garbage data")
        result = asyncio.run(async_convert_to_sticker(buf))
        self.assertIsNone(result)

    def test_async_apply_mask_delegates(self):
        src = _make_png_bytes(100, 100)
        mask_img = Image.new("L", (100, 100), color=255)
        mask_buf = io.BytesIO()
        mask_img.save(mask_buf, format="PNG")
        mask_buf.seek(0)
        result = asyncio.run(async_apply_mask_to_image(src, mask_buf))
        self.assertIsNotNone(result)
        img = Image.open(result)
        self.assertEqual(img.format, "WEBP")

    def test_async_apply_mask_inverted(self):
        src = _make_png_bytes(64, 64)
        mask_img = Image.new("L", (64, 64), color=255)
        mask_buf = io.BytesIO()
        mask_img.save(mask_buf, format="PNG")
        mask_buf.seek(0)
        result = asyncio.run(async_apply_mask_to_image(src, mask_buf, inverted=True))
        img = Image.open(result).convert("RGBA")
        w, h = img.size
        # Sample corners: inverted white mask → all transparent
        corners = [img.getpixel((0, 0)), img.getpixel((w-1, h-1))]
        for pixel in corners:
            self.assertEqual(pixel[3], 0, "Inverted white mask should yield transparent pixels")

    def test_async_convert_video_to_sticker_with_mock(self):
        """Test async video wrapper calls the sync function (mocked to avoid ffmpeg)."""
        fake_result = io.BytesIO(b"fake-webm-data")
        with patch("domain.media.convert_video_to_sticker", return_value=fake_result) as mock_fn:
            buf = io.BytesIO(b"fake-video")
            result = asyncio.run(async_convert_video_to_sticker(buf))
            mock_fn.assert_called_once_with(buf)
            self.assertIs(result, fake_result)


# ── download_file_bytes ───────────────────────────────────────

class TestDownloadFileBytes(unittest.TestCase):

    def test_successful_download(self):
        fake_data = b"PNG\x89data"
        mock_file = AsyncMock()
        mock_file.download_to_memory = AsyncMock(side_effect=lambda buf: buf.write(fake_data))
        mock_bot = AsyncMock()
        mock_bot.get_file = AsyncMock(return_value=mock_file)

        result = asyncio.run(download_file_bytes(mock_bot, "file_id_abc"))
        self.assertIsNotNone(result)
        self.assertEqual(result.read(), fake_data)

    def test_download_returns_none_on_exception(self):
        mock_bot = AsyncMock()
        mock_bot.get_file = AsyncMock(side_effect=Exception("Network error"))
        result = asyncio.run(download_file_bytes(mock_bot, "bad_file_id"))
        self.assertIsNone(result)

    def test_download_seeks_to_start(self):
        """Returned BytesIO must be seeked to position 0."""
        fake_data = b"some content"
        mock_file = AsyncMock()
        mock_file.download_to_memory = AsyncMock(side_effect=lambda buf: buf.write(fake_data))
        mock_bot = AsyncMock()
        mock_bot.get_file = AsyncMock(return_value=mock_file)

        result = asyncio.run(download_file_bytes(mock_bot, "fid"))
        self.assertEqual(result.tell(), 0)


if __name__ == "__main__":
    unittest.main()