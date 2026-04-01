import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch, PropertyMock

# Adjust sys.path so the src package is importable
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "src")),
)

# Mock heavy external libraries before importing the module under test
mock_cv2 = MagicMock()
mock_np = MagicMock()
mock_pil_image = MagicMock()

sys.modules["cv2"] = mock_cv2
sys.modules["numpy"] = mock_np
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = mock_pil_image

from vision.element_locator import ElementLocator  # noqa: E402


class TestElementLocatorInit(unittest.TestCase):
    """Tests for ElementLocator.__init__."""

    def test_init_with_all_parameters(self):
        """Should store all provided dependencies."""
        mock_ocr = Mock()
        mock_glm = Mock()
        mock_window = Mock()

        locator = ElementLocator(
            ocr_engine=mock_ocr,
            glm_client=mock_glm,
            window_info=mock_window,
        )

        self.assertIs(locator.ocr_engine, mock_ocr)
        self.assertIs(locator.glm_client, mock_glm)
        self.assertIs(locator.window_info, mock_window)

    def test_init_with_no_parameters(self):
        """Should default all attributes to None."""
        locator = ElementLocator()

        self.assertIsNone(locator.ocr_engine)
        self.assertIsNone(locator.glm_client)
        self.assertIsNone(locator.window_info)

    def test_init_with_partial_parameters(self):
        """Should store provided values and default others to None."""
        mock_ocr = Mock()
        locator = ElementLocator(ocr_engine=mock_ocr)

        self.assertIs(locator.ocr_engine, mock_ocr)
        self.assertIsNone(locator.glm_client)
        self.assertIsNone(locator.window_info)


class TestLocateByText(unittest.TestCase):
    """Tests for ElementLocator.locate_by_text."""

    def setUp(self):
        self.mock_ocr = Mock()
        self.mock_glm = Mock()
        self.mock_image = Mock()
        self.locator = ElementLocator(
            ocr_engine=self.mock_ocr,
            glm_client=self.mock_glm,
        )

    def test_ocr_success_returns_bbox(self):
        """Should return bounding box when OCR finds the text."""
        self.mock_ocr.search_text.return_value = [
            {
                "bbox": [(10, 20), (100, 20), (100, 50), (10, 50)],
                "text": "login",
                "confidence": 0.95,
            }
        ]

        result = self.locator.locate_by_text(
            self.mock_image, "login", confidence_threshold=0.5
        )

        self.mock_ocr.search_text.assert_called_once_with(
            self.mock_image, "login", 0.5
        )
        self.assertEqual(result, (10, 20, 90, 30))

    def test_ocr_success_with_different_coordinates(self):
        """Should correctly compute bbox from arbitrary polygon points."""
        self.mock_ocr.search_text.return_value = [
            {
                "bbox": [(5, 5), (200, 5), (200, 100), (5, 100)],
                "text": "username",
                "confidence": 0.8,
            }
        ]

        result = self.locator.locate_by_text(self.mock_image, "username")

        self.assertEqual(result, (5, 5, 195, 95))

    def test_ocr_returns_empty_matches_falls_back_to_glm(self):
        """Should fall back to GLM when OCR returns empty list."""
        self.mock_ocr.search_text.return_value = []
        self.mock_glm.chat_with_image.return_value = '{"x": 150, "y": 200}'

        result = self.locator.locate_by_text(self.mock_image, "button")

        self.assertEqual(result, (125, 175, 50, 50))

    def test_ocr_none_falls_back_to_glm(self):
        """Should fall back to GLM when OCR returns falsy value."""
        self.mock_ocr.search_text.return_value = None
        self.mock_glm.chat_with_image.return_value = '{"x": 300, "y": 400}'

        result = self.locator.locate_by_text(self.mock_image, "settings")

        self.assertEqual(result, (275, 375, 50, 50))

    def test_ocr_failure_glm_also_fails_returns_none(self):
        """Should return None when both OCR and GLM fail."""
        self.mock_ocr.search_text.return_value = []
        self.mock_glm.chat_with_image.return_value = "invalid response"

        result = self.locator.locate_by_text(self.mock_image, "missing")

        self.assertIsNone(result)

    def test_no_ocr_engine_uses_glm(self):
        """Should use GLM directly when no OCR engine is available."""
        locator = ElementLocator(glm_client=self.mock_glm)
        self.mock_glm.chat_with_image.return_value = '{"x": 50, "y": 60}'

        result = locator.locate_by_text(self.mock_image, "start")

        self.assertEqual(result, (25, 35, 50, 50))

    def test_no_ocr_no_glm_returns_none(self):
        """Should return None when neither OCR nor GLM is available."""
        locator = ElementLocator()
        result = locator.locate_by_text(self.mock_image, "anything")

        self.assertIsNone(result)

    def test_ocr_takes_first_match(self):
        """Should use only the first match when OCR returns multiple results."""
        self.mock_ocr.search_text.return_value = [
            {
                "bbox": [(10, 10), (50, 10), (50, 50), (10, 50)],
                "text": "first",
                "confidence": 0.9,
            },
            {
                "bbox": [(100, 100), (200, 100), (200, 200), (100, 200)],
                "text": "second",
                "confidence": 0.7,
            },
        ]

        result = self.locator.locate_by_text(self.mock_image, "text")

        self.assertEqual(result, (10, 10, 40, 40))


class TestLocateByTemplate(unittest.TestCase):
    """Tests for ElementLocator.locate_by_template."""

    def setUp(self):
        self.mock_image = Mock()
        self.locator = ElementLocator()

    @patch("vision.element_locator.np")
    @patch("vision.element_locator.cv2")
    def test_match_found_above_threshold(self, mock_cv2_mod, mock_np_mod):
        """Should return bbox when template match exceeds threshold."""
        mock_np_mod.array.return_value = "gray_array"
        mock_cv2_mod.cvtColor.return_value = "img_gray"
        mock_cv2_mod.IMREAD_GRAYSCALE = 0
        mock_cv2_mod.imread.return_value = MagicMock(shape=(30, 50))
        mock_cv2_mod.TM_CCOEFF_NORMED = 5
        mock_cv2_mod.matchTemplate.return_value = "result"
        mock_cv2_mod.minMaxLoc.return_value = (0.1, 0.95, (10, 20), (100, 200))

        result = self.locator.locate_by_template(
            self.mock_image, "template.png", threshold=0.8
        )

        mock_cv2_mod.cvtColor.assert_called_once_with(
            "gray_array", mock_cv2_mod.COLOR_RGB2GRAY
        )
        mock_cv2_mod.matchTemplate.assert_called_once_with(
            "img_gray",
            mock_cv2_mod.imread.return_value,
            mock_cv2_mod.TM_CCOEFF_NORMED,
        )
        # max_loc is the 4th element of minMaxLoc: (100, 200)
        self.assertEqual(result, (100, 200, 50, 30))

    @patch("vision.element_locator.np")
    @patch("vision.element_locator.cv2")
    def test_no_match_below_threshold(self, mock_cv2_mod, mock_np_mod):
        """Should return None when match value is below threshold."""
        mock_np_mod.array.return_value = "gray_array"
        mock_cv2_mod.cvtColor.return_value = "img_gray"
        mock_cv2_mod.IMREAD_GRAYSCALE = 0
        mock_cv2_mod.imread.return_value = MagicMock(shape=(30, 50))
        mock_cv2_mod.TM_CCOEFF_NORMED = 5
        mock_cv2_mod.matchTemplate.return_value = "result"
        mock_cv2_mod.minMaxLoc.return_value = (0.1, 0.5, (10, 20), (100, 200))

        result = self.locator.locate_by_template(
            self.mock_image, "template.png", threshold=0.8
        )

        self.assertIsNone(result)

    @patch("vision.element_locator.np")
    @patch("vision.element_locator.cv2")
    def test_invalid_template_returns_none(self, mock_cv2_mod, mock_np_mod):
        """Should return None when template image cannot be loaded."""
        mock_np_mod.array.return_value = "gray_array"
        mock_cv2_mod.cvtColor.return_value = "img_gray"
        mock_cv2_mod.IMREAD_GRAYSCALE = 0
        mock_cv2_mod.imread.return_value = None

        result = self.locator.locate_by_template(
            self.mock_image, "nonexistent.png"
        )

        self.assertIsNone(result)

    @patch("vision.element_locator.np")
    @patch("vision.element_locator.cv2")
    def test_match_exactly_at_threshold(self, mock_cv2_mod, mock_np_mod):
        """Should return bbox when match value equals threshold exactly."""
        mock_np_mod.array.return_value = "gray_array"
        mock_cv2_mod.cvtColor.return_value = "img_gray"
        mock_cv2_mod.IMREAD_GRAYSCALE = 0
        mock_cv2_mod.imread.return_value = MagicMock(shape=(20, 40))
        mock_cv2_mod.TM_CCOEFF_NORMED = 5
        mock_cv2_mod.matchTemplate.return_value = "result"
        mock_cv2_mod.minMaxLoc.return_value = (0.0, 0.8, (5, 15), (50, 60))

        result = self.locator.locate_by_template(
            self.mock_image, "template.png", threshold=0.8
        )

        # max_loc is the 4th element: (50, 60), template shape reversed: (40, 20)
        self.assertEqual(result, (50, 60, 40, 20))


class TestLocateByColor(unittest.TestCase):
    """Tests for ElementLocator.locate_by_color."""

    def setUp(self):
        self.mock_image = Mock()
        self.locator = ElementLocator()

    @patch("vision.element_locator.np")
    @patch("vision.element_locator.cv2")
    def test_color_found_single_region(self, mock_cv2_mod, mock_np_mod):
        """Should return one bbox when a single contour is found."""
        mock_np_mod.array.side_effect = lambda x: f"nparray_{x}"
        mock_cv2_mod.cvtColor.return_value = "img_hsv"
        mock_cv2_mod.inRange.return_value = "mask"

        contour = Mock()
        mock_cv2_mod.contourArea.return_value = 500
        mock_cv2_mod.boundingRect.return_value = (10, 20, 30, 40)
        mock_cv2_mod.findContours.return_value = ([contour], None)
        mock_cv2_mod.RETR_EXTERNAL = 0
        mock_cv2_mod.CHAIN_APPROX_SIMPLE = 1

        color_range = ((0, 0, 0), (180, 255, 255))
        result = self.locator.locate_by_color(self.mock_image, color_range)

        mock_cv2_mod.cvtColor.assert_called_once()
        mock_cv2_mod.inRange.assert_called_once_with(
            "img_hsv", "nparray_(0, 0, 0)", "nparray_(180, 255, 255)"
        )
        self.assertEqual(result, [(10, 20, 30, 40)])

    @patch("vision.element_locator.np")
    @patch("vision.element_locator.cv2")
    def test_color_not_found_empty(self, mock_cv2_mod, mock_np_mod):
        """Should return empty list when no contours are found."""
        mock_np_mod.array.side_effect = lambda x: f"nparray_{x}"
        mock_cv2_mod.cvtColor.return_value = "img_hsv"
        mock_cv2_mod.inRange.return_value = "mask"
        mock_cv2_mod.findContours.return_value = ([], None)
        mock_cv2_mod.RETR_EXTERNAL = 0
        mock_cv2_mod.CHAIN_APPROX_SIMPLE = 1

        color_range = ((100, 100, 100), (150, 255, 255))
        result = self.locator.locate_by_color(self.mock_image, color_range)

        self.assertEqual(result, [])

    @patch("vision.element_locator.np")
    @patch("vision.element_locator.cv2")
    def test_multiple_regions_above_min_area(self, mock_cv2_mod, mock_np_mod):
        """Should return bboxes for all contours above min_area."""
        mock_np_mod.array.side_effect = lambda x: f"nparray_{x}"
        mock_cv2_mod.cvtColor.return_value = "img_hsv"
        mock_cv2_mod.inRange.return_value = "mask"

        contour1 = Mock(name="contour1")
        contour2 = Mock(name="contour2")
        contour3 = Mock(name="contour3")

        # contour1: area 500, contour2: area 50 (below min), contour3: area 200
        mock_cv2_mod.contourArea.side_effect = [500, 50, 200]
        mock_cv2_mod.boundingRect.side_effect = [
            (10, 20, 30, 40),
            (5, 5, 10, 10),
        ]
        mock_cv2_mod.findContours.return_value = (
            [contour1, contour2, contour3],
            None,
        )
        mock_cv2_mod.RETR_EXTERNAL = 0
        mock_cv2_mod.CHAIN_APPROX_SIMPLE = 1

        color_range = ((0, 0, 0), (180, 255, 255))
        result = self.locator.locate_by_color(
            self.mock_image, color_range, min_area=100
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], (10, 20, 30, 40))
        self.assertEqual(result[1], (5, 5, 10, 10))

    @patch("vision.element_locator.np")
    @patch("vision.element_locator.cv2")
    def test_all_contours_below_min_area(self, mock_cv2_mod, mock_np_mod):
        """Should return empty list when all contours are below min_area."""
        mock_np_mod.array.side_effect = lambda x: f"nparray_{x}"
        mock_cv2_mod.cvtColor.return_value = "img_hsv"
        mock_cv2_mod.inRange.return_value = "mask"

        contour = Mock()
        mock_cv2_mod.contourArea.return_value = 50
        mock_cv2_mod.findContours.return_value = ([contour], None)
        mock_cv2_mod.RETR_EXTERNAL = 0
        mock_cv2_mod.CHAIN_APPROX_SIMPLE = 1

        color_range = ((0, 0, 0), (180, 255, 255))
        result = self.locator.locate_by_color(
            self.mock_image, color_range, min_area=100
        )

        self.assertEqual(result, [])

    @patch("vision.element_locator.np")
    @patch("vision.element_locator.cv2")
    def test_custom_min_area(self, mock_cv2_mod, mock_np_mod):
        """Should respect a custom min_area value."""
        mock_np_mod.array.side_effect = lambda x: f"nparray_{x}"
        mock_cv2_mod.cvtColor.return_value = "img_hsv"
        mock_cv2_mod.inRange.return_value = "mask"

        contour = Mock()
        mock_cv2_mod.contourArea.return_value = 200
        mock_cv2_mod.boundingRect.return_value = (0, 0, 15, 15)
        mock_cv2_mod.findContours.return_value = ([contour], None)
        mock_cv2_mod.RETR_EXTERNAL = 0
        mock_cv2_mod.CHAIN_APPROX_SIMPLE = 1

        color_range = ((0, 0, 0), (180, 255, 255))
        result = self.locator.locate_by_color(
            self.mock_image, color_range, min_area=150
        )

        self.assertEqual(result, [(0, 0, 15, 15)])


class TestGetElementCenter(unittest.TestCase):
    """Tests for ElementLocator.get_element_center."""

    def setUp(self):
        self.mock_image = Mock()
        self.mock_ocr = Mock()
        self.mock_window = Mock()

    def test_success_returns_center_without_window_info(self):
        """Should return center coordinates when element is found."""
        self.mock_ocr.search_text.return_value = [
            {
                "bbox": [(10, 20), (110, 20), (110, 70), (10, 70)],
                "text": "ok",
                "confidence": 0.9,
            }
        ]
        locator = ElementLocator(ocr_engine=self.mock_ocr)

        result = locator.get_element_center(self.mock_image, "ok")

        # bbox = (10, 20, 100, 50), center = (10+50, 20+25) = (60, 45)
        self.assertEqual(result, (60, 45))

    def test_success_with_window_info_adds_offset(self):
        """Should add window offset to center coordinates."""
        self.mock_ocr.search_text.return_value = [
            {
                "bbox": [(10, 20), (110, 20), (110, 70), (10, 70)],
                "text": "ok",
                "confidence": 0.9,
            }
        ]
        self.mock_window.left = 100
        self.mock_window.top = 200

        locator = ElementLocator(
            ocr_engine=self.mock_ocr,
            window_info=self.mock_window,
        )

        result = locator.get_element_center(self.mock_image, "ok")

        # center = (60, 45), offset = (100, 200) -> (160, 245)
        self.assertEqual(result, (160, 245))

    def test_failure_returns_none(self):
        """Should return None when element cannot be located."""
        self.mock_ocr.search_text.return_value = []
        locator = ElementLocator(ocr_engine=self.mock_ocr)

        result = locator.get_element_center(self.mock_image, "missing")

        self.assertIsNone(result)

    def test_center_integer_division(self):
        """Should use integer division (floor) for odd-dimension bboxes."""
        self.mock_ocr.search_text.return_value = [
            {
                "bbox": [(0, 0), (9, 0), (9, 5), (0, 5)],
                "text": "odd",
                "confidence": 0.9,
            }
        ]
        locator = ElementLocator(ocr_engine=self.mock_ocr)

        result = locator.get_element_center(self.mock_image, "odd")

        # bbox = (0, 0, 9, 5), center = (0+9//2, 0+5//2) = (4, 2)
        self.assertEqual(result, (4, 2))


class TestLocateByGlm(unittest.TestCase):
    """Tests for ElementLocator._locate_by_glm (private method)."""

    def setUp(self):
        self.mock_glm = Mock()
        self.mock_image = Mock()

    def test_success_returns_coordinates(self):
        """Should parse JSON response and return (x, y) tuple."""
        self.mock_glm.chat_with_image.return_value = '{"x": 100, "y": 200}'
        locator = ElementLocator(glm_client=self.mock_glm)

        result = locator._locate_by_glm(self.mock_image, "play button")

        self.mock_glm.chat_with_image.assert_called_once()
        self.assertEqual(result, (100, 200))

    def test_success_with_surrounding_text(self):
        """Should extract JSON from response with surrounding text."""
        self.mock_glm.chat_with_image.return_value = (
            'Here is the result: {"x": 50, "y": 75} done.'
        )
        locator = ElementLocator(glm_client=self.mock_glm)

        result = locator._locate_by_glm(self.mock_image, "menu")

        self.assertEqual(result, (50, 75))

    def test_failure_invalid_json(self):
        """Should return None when response contains no valid JSON."""
        self.mock_glm.chat_with_image.return_value = "No JSON here at all"
        locator = ElementLocator(glm_client=self.mock_glm)

        result = locator._locate_by_glm(self.mock_image, "target")

        self.assertIsNone(result)

    def test_failure_exception_during_parsing(self):
        """Should return None when chat_with_image raises an exception."""
        self.mock_glm.chat_with_image.side_effect = RuntimeError("API error")
        locator = ElementLocator(glm_client=self.mock_glm)

        result = locator._locate_by_glm(self.mock_image, "broken")

        self.assertIsNone(result)

    def test_no_glm_client_returns_none(self):
        """Should return None when no GLM client is configured."""
        locator = ElementLocator()

        result = locator._locate_by_glm(self.mock_image, "anything")

        self.assertIsNone(result)

    def test_missing_x_y_keys_default_to_zero(self):
        """Should default x and y to 0 when keys are missing from JSON."""
        self.mock_glm.chat_with_image.return_value = '{"a": 1}'
        locator = ElementLocator(glm_client=self.mock_glm)

        result = locator._locate_by_glm(self.mock_image, "target")

        self.assertEqual(result, (0, 0))

    def test_missing_x_key_only(self):
        """Should default x to 0 when only y is present in JSON."""
        self.mock_glm.chat_with_image.return_value = '{"y": 42}'
        locator = ElementLocator(glm_client=self.mock_glm)

        result = locator._locate_by_glm(self.mock_image, "target")

        self.assertEqual(result, (0, 42))

    def test_missing_y_key_only(self):
        """Should default y to 0 when only x is present in JSON."""
        self.mock_glm.chat_with_image.return_value = '{"x": 99}'
        locator = ElementLocator(glm_client=self.mock_glm)

        result = locator._locate_by_glm(self.mock_image, "target")

        self.assertEqual(result, (99, 0))

    def test_prompt_contains_description(self):
        """Should pass the element description in the GLM prompt."""
        self.mock_glm.chat_with_image.return_value = '{"x": 0, "y": 0}'
        locator = ElementLocator(glm_client=self.mock_glm)

        locator._locate_by_glm(self.mock_image, "login button")

        call_args = self.mock_glm.chat_with_image.call_args
        prompt = call_args[0][0]
        self.assertIn("login button", prompt)


if __name__ == "__main__":
    unittest.main()
