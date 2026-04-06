import sys
import unittest
from unittest.mock import patch, MagicMock

def _make_stub(name):
    mod = MagicMock()
    mod.__name__ = name
    return mod

STUBS = {
    "telegram": _make_stub("telegram"),
    "telegram.ext": _make_stub("telegram.ext"),
    "telegram.error": _make_stub("telegram.error"),
    "PIL": _make_stub("PIL"),
    "PIL.Image": _make_stub("PIL.Image"),
    "PIL.ImageOps": _make_stub("PIL.ImageOps"),
    "dotenv": _make_stub("dotenv"),
}

class StubMock:
    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], list):
            self.inline_keyboard = args[0]
        if "inline_keyboard" in kwargs:
            self.inline_keyboard = kwargs["inline_keyboard"]
        if "callback_data" in kwargs:
            self.callback_data = kwargs["callback_data"]
    DEFAULT_TYPE = MagicMock()

for cls in ["InputSticker", "InlineKeyboardButton", "InlineKeyboardMarkup",
            "InlineQueryResultArticle", "InputTextMessageContent",
            "MenuButtonWebApp", "Update", "WebAppInfo"]:
    setattr(STUBS["telegram"], cls, StubMock)

for cls in ["Application", "CallbackQueryHandler", "CommandHandler",
            "ContextTypes", "ConversationHandler", "InlineQueryHandler",
            "MessageHandler"]:
    setattr(STUBS["telegram.ext"], cls, StubMock)

STUBS["telegram.ext"].ConversationHandler.END = -1
STUBS["telegram.ext"].filters = MagicMock()
STUBS["telegram.error"].BadRequest = Exception

class TestPackNamespacePrefix(unittest.TestCase):
    def setUp(self):
        self.modules_patcher = patch.dict('sys.modules', STUBS)
        self.modules_patcher.start()

        # Patch local and third-party modules that fail on import
        self.local_patcher = patch.dict('sys.modules', {
            'config.runtime': _make_stub('config.runtime'),
            'infra.db': _make_stub('infra.db'),
            'core.engine': _make_stub('core.engine'),
            'domain.media': _make_stub('domain.media'),
            'src.stickers.media': _make_stub('src.stickers.media'),
            'stixmagic.settings': _make_stub('stixmagic.settings'),
            'menus': _make_stub('menus'),
            'packs.db': _make_stub('packs.db'),
            'moderation.guard': _make_stub('moderation.guard'),
            'loaders': _make_stub('loaders'),
            'platforms.telegram': _make_stub('platforms.telegram')
        })
        self.local_patcher.start()

        # In main.py, config.runtime.get_settings and infra.db.init_db are called.
        sys.modules['config.runtime'].get_settings = MagicMock(return_value=MagicMock())
        sys.modules['config.runtime'].ConfigError = Exception
        sys.modules['infra.db'].init_db = MagicMock()

        import main
        self.main = main

    def tearDown(self):
        self.modules_patcher.stop()
        self.local_patcher.stop()

    @patch('main.get_settings')
    def test_pack_namespace_prefix_dev(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.is_development = True
        mock_get_settings.return_value = mock_settings

        result = self.main._pack_namespace_prefix()

        self.assertEqual(result, 'devstix')
        mock_get_settings.assert_called_once()

    @patch('main.get_settings')
    def test_pack_namespace_prefix_prod(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.is_development = False
        mock_get_settings.return_value = mock_settings

        result = self.main._pack_namespace_prefix()

        self.assertEqual(result, 'stix')
        mock_get_settings.assert_called_once()

if __name__ == '__main__':
    unittest.main()
