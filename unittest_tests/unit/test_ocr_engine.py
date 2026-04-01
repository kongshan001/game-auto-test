"""
Unit tests for OCREngine module.
"""
import sys
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, "d:/claude_code_proj/py_unit_test_skills/game-auto-test/src")

from vision.ocr_engine import OCREngine


# ---------------------------------------------------------------------------
# Sample OCR results used across tests
# Each tuple is (text, bbox, confidence) matching easyocr output format.
# bbox is a list of 4 [x, y] points.
# ---------------------------------------------------------------------------
SAMPLE_BBOX_1 = [[10, 20], [110, 20], [110, 50], [10, 50]]
SAMPLE_BBOX_2 = [[200, 300], [400, 300], [400, 350], [200, 350]]
SAMPLE_BBOX_3 = [[500, 100], [600, 100], [600, 130], [500, 130]]

SAMPLE_OCR_RESULTS = [
    ("Hello", SAMPLE_BBOX_1, 0.95),
    ("World", SAMPLE_BBOX_2, 0.80),
    ("hello world", SAMPLE_BBOX_3, 0.60),
]

LOW_CONFIDENCE_RESULT = [
    ("fuzzy", [[0, 0], [1, 0], [1, 1], [0, 1]], 0.15),
]


def _make_mock_reader(results=None):
    """Create a MagicMock that behaves like an easyocr Reader."""
    reader = MagicMock()
    reader.readtext.return_value = results if results is not None else SAMPLE_OCR_RESULTS
    return reader


def _make_fake_image(mode="RGB", size=(640, 480)):
    """Create a fake PIL Image whose np.array conversion is controlled."""
    fake_img = MagicMock()
    fake_img.size = size

    if mode == "L":
        # Grayscale 2-D array  -> triggers the np.stack branch
        arr = MagicMock()
        arr.shape = (480, 640)
        stacked = MagicMock()
        stacked.shape = (480, 640, 3)
        stacked.__getitem__ = MagicMock(return_value=MagicMock())
    elif mode == "RGBA":
        # RGBA 4-channel array -> triggers the [:, :, :3] slice branch
        sliced = MagicMock()
        sliced.shape = (480, 640, 3)
        arr = MagicMock()
        arr.shape = (480, 640, 4)
        arr.__getitem__ = MagicMock(return_value=sliced)
    else:
        # Standard RGB 3-channel
        arr = MagicMock()
        arr.shape = (480, 640, 3)

    return fake_img, arr


class TestOCREngineInit(unittest.TestCase):
    """Tests for OCREngine.__init__."""

    def test_default_languages(self):
        engine = OCREngine()
        self.assertEqual(engine.languages, ["ch_sim", "en"])

    def test_custom_languages(self):
        engine = OCREngine(languages=["en", "fr"])
        self.assertEqual(engine.languages, ["en", "fr"])

    def test_use_gpu_default_false(self):
        engine = OCREngine()
        self.assertFalse(engine.use_gpu)

    def test_use_gpu_true(self):
        engine = OCREngine(use_gpu=True)
        self.assertTrue(engine.use_gpu)

    def test_reader_initially_none(self):
        engine = OCREngine()
        self.assertIsNone(engine._reader)


class TestOCREngineReaderProperty(unittest.TestCase):
    """Tests for the lazy-loading `reader` property."""

    @patch("vision.ocr_engine.easyocr", create=True)
    @patch("builtins.__import__", wraps=__import__)
    def test_lazy_loading_creates_reader(self, mock_import, mock_easyocr_cls):
        """Accessing `reader` should create an easyocr.Reader exactly once."""
        mock_reader_instance = MagicMock()
        mock_easyocr_cls.Reader.return_value = mock_reader_instance

        engine = OCREngine(languages=["en"], use_gpu=False)

        with patch.dict("sys.modules", {"easyocr": mock_easyocr_cls}):
            result = engine.reader

        mock_easyocr_cls.Reader.assert_called_once_with(
            ["en"], gpu=False, verbose=False
        )
        self.assertIs(result, mock_reader_instance)

    def test_reader_cached_after_first_access(self):
        """Subsequent accesses to `reader` should return the same instance."""
        mock_reader = MagicMock()
        engine = OCREngine()
        engine._reader = mock_reader

        with self.subTest("first access"):
            self.assertIs(engine.reader, mock_reader)

        with self.subTest("second access"):
            self.assertIs(engine.reader, mock_reader)

    def test_reader_import_error(self):
        """If easyocr cannot be imported, an ImportError should be raised."""
        engine = OCREngine()
        # Ensure _reader is None so the import path is triggered
        engine._reader = None

        with patch.dict("sys.modules", {"easyocr": None}):
            # Remove easyocr from cached modules so import triggers ImportError
            with self.assertRaises(ImportError):
                _ = engine.reader


class TestOCREngineRecognize(unittest.TestCase):
    """Tests for OCREngine.recognize()."""

    def _setup_engine(self, results=None):
        engine = OCREngine()
        engine._reader = _make_mock_reader(results)
        return engine

    def test_recognize_detail_1_returns_tuples(self):
        """detail=1 should return (text, bbox, confidence) tuples."""
        engine = self._setup_engine()
        fake_img, fake_arr = _make_fake_image("RGB")

        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            results = engine.recognize(fake_img, detail=1)

        self.assertEqual(len(results), 3)
        for item in results:
            self.assertEqual(len(item), 3)
            text, bbox, confidence = item
            self.assertIsInstance(text, str)
            self.assertIsInstance(bbox, list)
            self.assertIsInstance(confidence, float)

    def test_recognize_detail_0_returns_texts_only(self):
        """detail=0 should return a flat list of text strings."""
        engine = self._setup_engine()
        fake_img, fake_arr = _make_fake_image("RGB")

        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            results = engine.recognize(fake_img, detail=0)

        self.assertEqual(results, ["Hello", "World", "hello world"])

    def test_recognize_empty_result(self):
        """An empty OCR result should return an empty list for both detail levels."""
        engine = self._setup_engine(results=[])
        fake_img, fake_arr = _make_fake_image("RGB")

        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            detail_0 = engine.recognize(fake_img, detail=0)
            detail_1 = engine.recognize(fake_img, detail=1)

        self.assertEqual(detail_0, [])
        self.assertEqual(detail_1, [])

    def test_recognize_grayscale_image(self):
        """A grayscale image (2-D array) should trigger the np.stack conversion."""
        engine = self._setup_engine(results=[])
        fake_img, fake_arr = _make_fake_image("L")

        stacked_arr = MagicMock()
        stacked_arr.shape = (480, 640, 3)

        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            mock_np.stack.return_value = stacked_arr
            engine.recognize(fake_img, detail=1)

        mock_np.stack.assert_called_once()

    def test_recognize_rgba_image(self):
        """An RGBA image (4-channel) should trigger the slicing conversion."""
        engine = self._setup_engine(results=[])
        fake_img, fake_arr = _make_fake_image("RGBA")

        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            engine.recognize(fake_img, detail=1)

        # np.array should have been called and the array subscript used
        mock_np.array.assert_called_once_with(fake_img)


class TestOCREngineSearchText(unittest.TestCase):
    """Tests for OCREngine.search_text()."""

    def _setup_engine(self, results=None):
        engine = OCREngine()
        engine._reader = _make_mock_reader(results)
        return engine

    def _recognize_with_mock(self, engine, fake_img):
        """Patch np.array so recognize works with the fake image."""
        fake_arr = MagicMock()
        fake_arr.shape = (480, 640, 3)
        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            return engine.search_text(fake_img, "hello")

    def test_search_text_match_found(self):
        """Searching for an exact match should return the matching entry."""
        engine = self._setup_engine()
        fake_img, _ = _make_fake_image()
        matches = self._recognize_with_mock(engine, fake_img)

        # "Hello" (exact) and "hello world" (contains) should match
        matched_texts = [m["text"] for m in matches]
        self.assertIn("Hello", matched_texts)
        self.assertIn("hello world", matched_texts)
        # "World" should NOT match "hello"
        self.assertNotIn("World", matched_texts)

    def test_search_text_no_match(self):
        """Searching for a term not in the image should return an empty list."""
        engine = self._setup_engine()
        fake_img, _ = _make_fake_image()
        fake_arr = MagicMock()
        fake_arr.shape = (480, 640, 3)

        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            matches = engine.search_text(fake_img, "not_found_term")

        self.assertEqual(matches, [])

    def test_search_text_multiple_matches(self):
        """Multiple matches should all be returned."""
        engine = self._setup_engine()
        fake_img, _ = _make_fake_image()
        fake_arr = MagicMock()
        fake_arr.shape = (480, 640, 3)

        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            matches = engine.search_text(fake_img, "hello")

        # "Hello" and "hello world" both contain "hello"
        self.assertEqual(len(matches), 2)

    def test_search_text_confidence_threshold(self):
        """Results below the confidence threshold should be excluded."""
        results = [
            ("Hello", SAMPLE_BBOX_1, 0.90),
            ("hello low", SAMPLE_BBOX_2, 0.40),
        ]
        engine = self._setup_engine(results=results)
        fake_img, _ = _make_fake_image()
        fake_arr = MagicMock()
        fake_arr.shape = (480, 640, 3)

        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            matches = engine.search_text(fake_img, "hello", confidence_threshold=0.5)

        matched_texts = [m["text"] for m in matches]
        self.assertIn("Hello", matched_texts)
        self.assertNotIn("hello low", matched_texts)

    def test_search_text_center_calculation(self):
        """The center coordinates should be the average of the four bbox points."""
        engine = self._setup_engine(results=[("Test", SAMPLE_BBOX_1, 0.99)])
        fake_img, _ = _make_fake_image()
        fake_arr = MagicMock()
        fake_arr.shape = (480, 640, 3)

        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            matches = engine.search_text(fake_img, "Test")

        self.assertEqual(len(matches), 1)
        # bbox points: (10,20), (110,20), (110,50), (10,50) -> center (60, 35)
        self.assertEqual(matches[0]["center"], (60, 35))

    def test_search_text_result_structure(self):
        """Each match dict should contain text, bbox, confidence, and center."""
        engine = self._setup_engine(results=[("Hello", SAMPLE_BBOX_1, 0.95)])
        fake_img, _ = _make_fake_image()
        fake_arr = MagicMock()
        fake_arr.shape = (480, 640, 3)

        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            matches = engine.search_text(fake_img, "Hello")

        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertIn("text", match)
        self.assertIn("bbox", match)
        self.assertIn("confidence", match)
        self.assertIn("center", match)
        self.assertEqual(match["text"], "Hello")
        self.assertAlmostEqual(match["confidence"], 0.95)


class TestOCREngineFindTextPosition(unittest.TestCase):
    """Tests for OCREngine.find_text_position()."""

    def _setup_engine(self, results=None):
        engine = OCREngine()
        engine._reader = _make_mock_reader(results)
        return engine

    def _find_with_mock(self, engine, fake_img, term, threshold=0.5):
        fake_arr = MagicMock()
        fake_arr.shape = (480, 640, 3)
        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            return engine.find_text_position(fake_img, term, threshold)

    def test_find_text_position_found(self):
        """Should return the center of the highest-confidence match."""
        results = [
            ("Hello", SAMPLE_BBOX_1, 0.70),
            ("Hello", SAMPLE_BBOX_3, 0.95),
        ]
        engine = self._setup_engine(results=results)
        fake_img, _ = _make_fake_image()
        pos = self._find_with_mock(engine, fake_img, "Hello")

        self.assertIsNotNone(pos)
        # Should pick the one with confidence 0.95 -> SAMPLE_BBOX_3
        xs = [p[0] for p in SAMPLE_BBOX_3]
        ys = [p[1] for p in SAMPLE_BBOX_3]
        expected_center = (int(sum(xs) / 4), int(sum(ys) / 4))
        self.assertEqual(pos, expected_center)

    def test_find_text_position_not_found(self):
        """Should return None when no match is found."""
        engine = self._setup_engine()
        fake_img, _ = _make_fake_image()
        pos = self._find_with_mock(engine, fake_img, "missing_text")

        self.assertIsNone(pos)

    def test_find_text_position_below_threshold(self):
        """Should return None when matches exist but are below the threshold."""
        engine = self._setup_engine(
            results=[("Hello", SAMPLE_BBOX_1, 0.20)]
        )
        fake_img, _ = _make_fake_image()
        pos = self._find_with_mock(engine, fake_img, "Hello", threshold=0.5)

        self.assertIsNone(pos)


class TestOCREngineGetAllTextWithPositions(unittest.TestCase):
    """Tests for OCREngine.get_all_text_with_positions()."""

    def _setup_engine(self, results=None):
        engine = OCREngine()
        engine._reader = _make_mock_reader(results)
        return engine

    def _get_all_with_mock(self, engine, fake_img, threshold=0.3):
        fake_arr = MagicMock()
        fake_arr.shape = (480, 640, 3)
        with patch("vision.ocr_engine.np") as mock_np:
            mock_np.array.return_value = fake_arr
            return engine.get_all_text_with_positions(fake_img, threshold)

    def test_multiple_results(self):
        """Should return all text items with correct structure."""
        engine = self._setup_engine()
        fake_img, _ = _make_fake_image()
        items = self._get_all_with_mock(engine, fake_img)

        self.assertEqual(len(items), 3)
        for item in items:
            self.assertIn("text", item)
            self.assertIn("bbox", item)
            self.assertIn("center", item)
            self.assertIn("confidence", item)

    def test_empty_results(self):
        """Should return an empty list when no text is detected."""
        engine = self._setup_engine(results=[])
        fake_img, _ = _make_fake_image()
        items = self._get_all_with_mock(engine, fake_img)

        self.assertEqual(items, [])

    def test_low_confidence_filtered(self):
        """Items below the confidence threshold should be excluded."""
        results = [
            ("High", SAMPLE_BBOX_1, 0.90),
            ("Low", SAMPLE_BBOX_2, 0.10),
            ("Medium", SAMPLE_BBOX_3, 0.35),
        ]
        engine = self._setup_engine(results=results)
        fake_img, _ = _make_fake_image()
        items = self._get_all_with_mock(engine, fake_img, threshold=0.3)

        texts = [item["text"] for item in items]
        self.assertIn("High", texts)
        self.assertIn("Medium", texts)
        self.assertNotIn("Low", texts)
        self.assertEqual(len(items), 2)

    def test_center_calculation(self):
        """Center coordinates should be correctly computed from the bounding box."""
        engine = self._setup_engine(
            results=[("Solo", SAMPLE_BBOX_2, 0.88)]
        )
        fake_img, _ = _make_fake_image()
        items = self._get_all_with_mock(engine, fake_img)

        self.assertEqual(len(items), 1)
        xs = [p[0] for p in SAMPLE_BBOX_2]
        ys = [p[1] for p in SAMPLE_BBOX_2]
        expected_center = (int(sum(xs) / 4), int(sum(ys) / 4))
        self.assertEqual(items[0]["center"], expected_center)
        self.assertEqual(items[0]["text"], "Solo")


if __name__ == "__main__":
    unittest.main()
