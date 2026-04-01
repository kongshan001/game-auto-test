"""
Unit tests for src.utils.config.Config dataclass.

Covers:
- Config.__init__ with default and custom values
- Config.from_env with full, partial, and missing environment variables
- Config.validate for success and all failure modes
- Type conversions for int, float, bool, and list fields from env vars
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import unittest
from unittest.mock import patch, MagicMock

from src.utils.config import Config


class TestConfigInit(unittest.TestCase):
    """Tests for Config.__init__ default values and custom values."""

    def test_default_glm_api_key_is_empty_string(self):
        """Config defaults glm_api_key to an empty string."""
        config = Config()
        self.assertEqual(config.glm_api_key, "")

    def test_default_glm_model(self):
        """Config defaults glm_model to 'glm-4v'."""
        config = Config()
        self.assertEqual(config.glm_model, "glm-4v")

    def test_default_game_exe_path_is_empty_string(self):
        """Config defaults game_exe_path to an empty string."""
        config = Config()
        self.assertEqual(config.game_exe_path, "")

    def test_default_game_window_title_is_none(self):
        """Config defaults game_window_title to None."""
        config = Config()
        self.assertIsNone(config.game_window_title)

    def test_default_game_startup_delay(self):
        """Config defaults game_startup_delay to 5."""
        config = Config()
        self.assertEqual(config.game_startup_delay, 5)

    def test_default_test_case_is_empty_string(self):
        """Config defaults test_case to an empty string."""
        config = Config()
        self.assertEqual(config.test_case, "")

    def test_default_max_steps(self):
        """Config defaults max_steps to 100."""
        config = Config()
        self.assertEqual(config.max_steps, 100)

    def test_default_step_timeout(self):
        """Config defaults step_timeout to 30."""
        config = Config()
        self.assertEqual(config.step_timeout, 30)

    def test_default_log_level(self):
        """Config defaults log_level to 'INFO'."""
        config = Config()
        self.assertEqual(config.log_level, "INFO")

    def test_default_screenshot_save_path(self):
        """Config defaults screenshot_save_path to './logs/screenshots'."""
        config = Config()
        self.assertEqual(config.screenshot_save_path, "./logs/screenshots")

    def test_default_save_screenshots_is_true(self):
        """Config defaults save_screenshots to True."""
        config = Config()
        self.assertTrue(config.save_screenshots)

    def test_default_ocr_enabled_is_true(self):
        """Config defaults ocr_enabled to True."""
        config = Config()
        self.assertTrue(config.ocr_enabled)

    def test_default_ocr_languages(self):
        """Config defaults ocr_languages to ['ch_sim', 'en']."""
        config = Config()
        self.assertEqual(config.ocr_languages, ["ch_sim", "en"])

    def test_default_click_delay(self):
        """Config defaults click_delay to 0.5."""
        config = Config()
        self.assertEqual(config.click_delay, 0.5)

    def test_default_type_delay(self):
        """Config defaults type_delay to 0.1."""
        config = Config()
        self.assertEqual(config.type_delay, 0.1)

    def test_default_keypress_delay(self):
        """Config defaults keypress_delay to 0.3."""
        config = Config()
        self.assertEqual(config.keypress_delay, 0.3)

    def test_custom_values_for_all_fields(self):
        """Config accepts custom values for every field at construction."""
        config = Config(
            glm_api_key="key-123",
            glm_model="glm-5",
            game_exe_path="/usr/bin/game",
            game_window_title="My Game",
            game_startup_delay=10,
            test_case="test_main_menu",
            max_steps=200,
            step_timeout=60,
            log_level="DEBUG",
            screenshot_save_path="/tmp/screens",
            save_screenshots=False,
            ocr_enabled=False,
            ocr_languages=["ja", "en"],
            click_delay=1.0,
            type_delay=0.2,
            keypress_delay=0.5,
        )
        self.assertEqual(config.glm_api_key, "key-123")
        self.assertEqual(config.glm_model, "glm-5")
        self.assertEqual(config.game_exe_path, "/usr/bin/game")
        self.assertEqual(config.game_window_title, "My Game")
        self.assertEqual(config.game_startup_delay, 10)
        self.assertEqual(config.test_case, "test_main_menu")
        self.assertEqual(config.max_steps, 200)
        self.assertEqual(config.step_timeout, 60)
        self.assertEqual(config.log_level, "DEBUG")
        self.assertEqual(config.screenshot_save_path, "/tmp/screens")
        self.assertFalse(config.save_screenshots)
        self.assertFalse(config.ocr_enabled)
        self.assertEqual(config.ocr_languages, ["ja", "en"])
        self.assertEqual(config.click_delay, 1.0)
        self.assertEqual(config.type_delay, 0.2)
        self.assertEqual(config.keypress_delay, 0.5)

    def test_ocr_languages_default_factory_produces_independent_lists(self):
        """Each Config instance gets an independent ocr_languages list via default_factory."""
        config_a = Config()
        config_b = Config()
        config_a.ocr_languages.append("fr")
        self.assertEqual(config_a.ocr_languages, ["ch_sim", "en", "fr"])
        self.assertEqual(config_b.ocr_languages, ["ch_sim", "en"])


class TestConfigFromEnv(unittest.TestCase):
    """Tests for Config.from_env classmethod."""

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_from_env_with_all_env_vars_set(self, mock_getenv, mock_load_dotenv):
        """from_env reads every field from environment variables when all are set."""
        env_map = {
            "GLM_API_KEY": "env-key-abc",
            "GLM_MODEL": "glm-3",
            "GAME_EXE_PATH": "C:\\Games\\game.exe",
            "GAME_WINDOW_TITLE": "Cool Game",
            "GAME_STARTUP_DELAY": "15",
            "TEST_CASE": "integration_test",
            "MAX_STEPS": "50",
            "STEP_TIMEOUT": "45",
            "LOG_LEVEL": "WARNING",
            "SCREENSHOT_SAVE_PATH": "/var/screenshots",
            "SAVE_SCREENSHOTS": "true",
            "OCR_ENABLED": "false",
            "OCR_LANGUAGES": "ko,en,ja",
            "CLICK_DELAY": "1.5",
            "TYPE_DELAY": "0.3",
            "KEYPRESS_DELAY": "0.7",
        }

        def getenv_side_effect(key, default=None):
            return env_map.get(key, default)

        mock_getenv.side_effect = getenv_side_effect

        config = Config.from_env(env_path="/custom/.env")

        mock_load_dotenv.assert_called_once_with("/custom/.env")
        self.assertEqual(config.glm_api_key, "env-key-abc")
        self.assertEqual(config.glm_model, "glm-3")
        self.assertEqual(config.game_exe_path, "C:\\Games\\game.exe")
        self.assertEqual(config.game_window_title, "Cool Game")
        self.assertEqual(config.game_startup_delay, 15)
        self.assertEqual(config.test_case, "integration_test")
        self.assertEqual(config.max_steps, 50)
        self.assertEqual(config.step_timeout, 45)
        self.assertEqual(config.log_level, "WARNING")
        self.assertEqual(config.screenshot_save_path, "/var/screenshots")
        self.assertTrue(config.save_screenshots)
        self.assertFalse(config.ocr_enabled)
        self.assertEqual(config.ocr_languages, ["ko", "en", "ja"])
        self.assertEqual(config.click_delay, 1.5)
        self.assertEqual(config.type_delay, 0.3)
        self.assertEqual(config.keypress_delay, 0.7)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_from_env_with_no_env_vars_returns_defaults(self, mock_getenv, mock_load_dotenv):
        """from_env falls back to defaults when no environment variables are set."""
        # Use side_effect that returns the default argument, simulating no env vars set.
        mock_getenv.side_effect = lambda key, default=None: default

        config = Config.from_env()

        mock_load_dotenv.assert_called_once_with(".env")
        self.assertEqual(config.glm_api_key, "")
        self.assertEqual(config.glm_model, "glm-4v")
        self.assertEqual(config.game_exe_path, "")
        self.assertIsNone(config.game_window_title)
        self.assertEqual(config.game_startup_delay, 5)
        self.assertEqual(config.test_case, "")
        self.assertEqual(config.max_steps, 100)
        self.assertEqual(config.step_timeout, 30)
        self.assertEqual(config.log_level, "INFO")
        self.assertEqual(config.screenshot_save_path, "./logs/screenshots")
        self.assertTrue(config.save_screenshots)
        self.assertTrue(config.ocr_enabled)
        self.assertEqual(config.ocr_languages, ["ch_sim", "en"])
        self.assertEqual(config.click_delay, 0.5)
        self.assertEqual(config.type_delay, 0.1)
        self.assertEqual(config.keypress_delay, 0.3)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_from_env_with_partial_env_vars(self, mock_getenv, mock_load_dotenv):
        """from_env uses env vars for set fields and defaults for the rest."""
        env_map = {
            "GLM_API_KEY": "partial-key",
            "GAME_EXE_PATH": "/games/start",
            "TEST_CASE": "partial_test",
        }

        def getenv_side_effect(key, default=None):
            if key in env_map:
                return env_map[key]
            return default

        mock_getenv.side_effect = getenv_side_effect

        config = Config.from_env()

        self.assertEqual(config.glm_api_key, "partial-key")
        self.assertEqual(config.game_exe_path, "/games/start")
        self.assertEqual(config.test_case, "partial_test")
        # Remaining fields keep defaults
        self.assertEqual(config.glm_model, "glm-4v")
        self.assertIsNone(config.game_window_title)
        self.assertEqual(config.max_steps, 100)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_from_env_calls_load_dotenv_with_env_path(self, mock_getenv, mock_load_dotenv):
        """from_env passes the env_path argument to load_dotenv."""
        mock_getenv.side_effect = lambda key, default=None: default
        Config.from_env(env_path="/prod/.env")
        mock_load_dotenv.assert_called_once_with("/prod/.env")

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_from_env_default_env_path_is_dotenv(self, mock_getenv, mock_load_dotenv):
        """from_env defaults the env_path to '.env'."""
        mock_getenv.side_effect = lambda key, default=None: default
        Config.from_env()
        mock_load_dotenv.assert_called_once_with(".env")


class TestConfigFromEnvTypeConversions(unittest.TestCase):
    """Tests for type conversions performed by Config.from_env."""

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_int_conversion_for_game_startup_delay(self, mock_getenv, mock_load_dotenv):
        """from_env converts GAME_STARTUP_DELAY from string to int."""
        mock_getenv.side_effect = lambda key, default=None: "20" if key == "GAME_STARTUP_DELAY" else default
        config = Config.from_env()
        self.assertEqual(config.game_startup_delay, 20)
        self.assertIsInstance(config.game_startup_delay, int)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_int_conversion_for_max_steps(self, mock_getenv, mock_load_dotenv):
        """from_env converts MAX_STEPS from string to int."""
        mock_getenv.side_effect = lambda key, default=None: "999" if key == "MAX_STEPS" else default
        config = Config.from_env()
        self.assertEqual(config.max_steps, 999)
        self.assertIsInstance(config.max_steps, int)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_int_conversion_for_step_timeout(self, mock_getenv, mock_load_dotenv):
        """from_env converts STEP_TIMEOUT from string to int."""
        mock_getenv.side_effect = lambda key, default=None: "120" if key == "STEP_TIMEOUT" else default
        config = Config.from_env()
        self.assertEqual(config.step_timeout, 120)
        self.assertIsInstance(config.step_timeout, int)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_float_conversion_for_click_delay(self, mock_getenv, mock_load_dotenv):
        """from_env converts CLICK_DELAY from string to float."""
        mock_getenv.side_effect = lambda key, default=None: "2.75" if key == "CLICK_DELAY" else default
        config = Config.from_env()
        self.assertEqual(config.click_delay, 2.75)
        self.assertIsInstance(config.click_delay, float)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_float_conversion_for_type_delay(self, mock_getenv, mock_load_dotenv):
        """from_env converts TYPE_DELAY from string to float."""
        mock_getenv.side_effect = lambda key, default=None: "0.05" if key == "TYPE_DELAY" else default
        config = Config.from_env()
        self.assertEqual(config.type_delay, 0.05)
        self.assertIsInstance(config.type_delay, float)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_float_conversion_for_keypress_delay(self, mock_getenv, mock_load_dotenv):
        """from_env converts KEYPRESS_DELAY from string to float."""
        mock_getenv.side_effect = lambda key, default=None: "1.25" if key == "KEYPRESS_DELAY" else default
        config = Config.from_env()
        self.assertEqual(config.keypress_delay, 1.25)
        self.assertIsInstance(config.keypress_delay, float)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_bool_save_screenshots_true_lowercase(self, mock_getenv, mock_load_dotenv):
        """from_env converts SAVE_SCREENSHOTS='true' to True."""
        mock_getenv.side_effect = lambda key, default=None: "true" if key == "SAVE_SCREENSHOTS" else default
        config = Config.from_env()
        self.assertTrue(config.save_screenshots)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_bool_save_screenshots_false(self, mock_getenv, mock_load_dotenv):
        """from_env converts SAVE_SCREENSHOTS='false' to False."""
        mock_getenv.side_effect = lambda key, default=None: "false" if key == "SAVE_SCREENSHOTS" else default
        config = Config.from_env()
        self.assertFalse(config.save_screenshots)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_bool_save_screenshots_mixed_case(self, mock_getenv, mock_load_dotenv):
        """from_env treats any non-'true' SAVE_SCREENSHOTS value as False."""
        mock_getenv.side_effect = lambda key, default=None: "TRUE" if key == "SAVE_SCREENSHOTS" else default
        config = Config.from_env()
        self.assertTrue(config.save_screenshots)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_bool_save_screenshots_arbitrary_string(self, mock_getenv, mock_load_dotenv):
        """from_env treats arbitrary SAVE_SCREENSHOTS string as False."""
        mock_getenv.side_effect = lambda key, default=None: "yes" if key == "SAVE_SCREENSHOTS" else default
        config = Config.from_env()
        self.assertFalse(config.save_screenshots)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_bool_ocr_enabled_true(self, mock_getenv, mock_load_dotenv):
        """from_env converts OCR_ENABLED='true' to True."""
        mock_getenv.side_effect = lambda key, default=None: "true" if key == "OCR_ENABLED" else default
        config = Config.from_env()
        self.assertTrue(config.ocr_enabled)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_bool_ocr_enabled_false(self, mock_getenv, mock_load_dotenv):
        """from_env converts OCR_ENABLED='false' to False."""
        mock_getenv.side_effect = lambda key, default=None: "false" if key == "OCR_ENABLED" else default
        config = Config.from_env()
        self.assertFalse(config.ocr_enabled)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_bool_ocr_enabled_mixed_case_false(self, mock_getenv, mock_load_dotenv):
        """from_env converts OCR_ENABLED='FALSE' to False via .lower()."""
        mock_getenv.side_effect = lambda key, default=None: "FALSE" if key == "OCR_ENABLED" else default
        config = Config.from_env()
        self.assertFalse(config.ocr_enabled)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_bool_ocr_enabled_True_uppercase(self, mock_getenv, mock_load_dotenv):
        """from_env converts OCR_ENABLED='True' to True via .lower()."""
        mock_getenv.side_effect = lambda key, default=None: "True" if key == "OCR_ENABLED" else default
        config = Config.from_env()
        self.assertTrue(config.ocr_enabled)

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_list_conversion_ocr_languages(self, mock_getenv, mock_load_dotenv):
        """from_env splits OCR_LANGUAGES by comma into a list."""
        mock_getenv.side_effect = lambda key, default=None: "a,b,c,d" if key == "OCR_LANGUAGES" else default
        config = Config.from_env()
        self.assertEqual(config.ocr_languages, ["a", "b", "c", "d"])

    @patch("src.utils.config.load_dotenv")
    @patch("src.utils.config.os.getenv")
    def test_list_conversion_ocr_languages_single_item(self, mock_getenv, mock_load_dotenv):
        """from_env handles a single-item OCR_LANGUAGES value."""
        mock_getenv.side_effect = lambda key, default=None: "ch_sim" if key == "OCR_LANGUAGES" else default
        config = Config.from_env()
        self.assertEqual(config.ocr_languages, ["ch_sim"])


class TestConfigValidate(unittest.TestCase):
    """Tests for Config.validate method."""

    def _make_valid_config(self):
        """Helper to build a minimally valid Config for validate tests."""
        return Config(
            glm_api_key="sk-test-key",
            game_exe_path="/usr/bin/game",
            test_case="test_login",
        )

    def test_validate_returns_true_when_all_required_fields_set(self):
        """validate returns True when glm_api_key, game_exe_path, and test_case are all set."""
        config = self._make_valid_config()
        self.assertTrue(config.validate())

    def test_validate_raises_when_glm_api_key_missing(self):
        """validate raises ValueError when glm_api_key is empty."""
        config = Config(
            glm_api_key="",
            game_exe_path="/usr/bin/game",
            test_case="test_login",
        )
        with self.assertRaises(ValueError) as ctx:
            config.validate()
        self.assertIn("GLM_API_KEY", str(ctx.exception))

    def test_validate_raises_when_game_exe_path_missing(self):
        """validate raises ValueError when game_exe_path is empty."""
        config = Config(
            glm_api_key="sk-test-key",
            game_exe_path="",
            test_case="test_login",
        )
        with self.assertRaises(ValueError) as ctx:
            config.validate()
        self.assertIn("GAME_EXE_PATH", str(ctx.exception))

    def test_validate_raises_when_test_case_missing(self):
        """validate raises ValueError when test_case is empty."""
        config = Config(
            glm_api_key="sk-test-key",
            game_exe_path="/usr/bin/game",
            test_case="",
        )
        with self.assertRaises(ValueError) as ctx:
            config.validate()
        self.assertIn("TEST_CASE", str(ctx.exception))

    def test_validate_raises_when_all_required_fields_missing(self):
        """validate raises ValueError on the first missing required field (glm_api_key) when all three are empty."""
        config = Config()
        with self.assertRaises(ValueError) as ctx:
            config.validate()
        self.assertIn("GLM_API_KEY", str(ctx.exception))

    def test_validate_checks_glm_api_key_before_game_exe_path(self):
        """validate checks glm_api_key first, so missing game_exe_path is not raised if api_key is also missing."""
        config = Config(glm_api_key="", game_exe_path="", test_case="test")
        with self.assertRaises(ValueError) as ctx:
            config.validate()
        self.assertIn("GLM_API_KEY", str(ctx.exception))
        self.assertNotIn("GAME_EXE_PATH", str(ctx.exception))

    def test_validate_checks_game_exe_path_before_test_case(self):
        """validate checks game_exe_path before test_case."""
        config = Config(glm_api_key="key", game_exe_path="", test_case="")
        with self.assertRaises(ValueError) as ctx:
            config.validate()
        self.assertIn("GAME_EXE_PATH", str(ctx.exception))
        self.assertNotIn("TEST_CASE", str(ctx.exception))

    def test_validate_default_config_raises_for_glm_api_key(self):
        """A freshly constructed Config (all defaults) fails validation on glm_api_key."""
        config = Config()
        with self.assertRaises(ValueError) as ctx:
            config.validate()
        self.assertEqual(str(ctx.exception), "GLM_API_KEY is required")

    def test_validate_error_messages_are_specific(self):
        """Each validation error message names the specific missing field."""
        cases = [
            ("", "/path", "case", "GLM_API_KEY is required"),
            ("key", "", "case", "GAME_EXE_PATH is required"),
            ("key", "/path", "", "TEST_CASE is required"),
        ]
        for api_key, exe_path, test_case, expected_msg in cases:
            config = Config(
                glm_api_key=api_key,
                game_exe_path=exe_path,
                test_case=test_case,
            )
            with self.subTest(glm_api_key=api_key, game_exe_path=exe_path, test_case=test_case):
                with self.assertRaises(ValueError) as ctx:
                    config.validate()
                self.assertEqual(str(ctx.exception), expected_msg)


if __name__ == "__main__":
    unittest.main()
