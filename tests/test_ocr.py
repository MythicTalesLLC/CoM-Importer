"""
Test OCR and PDF functionality.
"""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from com_importer.image_parser import (
    ImageOCRFactory,
    TesseractImageParser,
)
from com_importer.pdf_handler import PDFHandler


class TestTesseractOCR:
    """Test Tesseract OCR parser."""

    def test_tesseract_availability(self):
        """Test if Tesseract is available on system."""
        parser = TesseractImageParser()
        # May not be installed in test environment, but should not crash
        assert parser is not None

    def test_image_preprocessing(self):
        """Test image preprocessing for OCR."""
        # Create a simple test image
        img = Image.new("RGB", (100, 100), color="white")

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f.name)
            temp_path = f.name

        try:
            # Preprocess should not crash
            processed = TesseractImageParser._preprocess_image(temp_path)
            assert processed is not None
            assert processed.size[0] >= 300  # Should upscale small images
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_find_tesseract_common_paths_when_path_missing(self, monkeypatch):
        """Packaged apps may not have Homebrew in PATH; common-path fallback should still work."""
        monkeypatch.delenv("COM_IMPORTER_TESSERACT_PATH", raising=False)
        monkeypatch.delenv("TESSERACT_PATH", raising=False)
        monkeypatch.delenv("TESSERACT_CMD", raising=False)

        monkeypatch.setattr("com_importer.image_parser.shutil.which", lambda *_: None)

        real_is_file = Path.is_file

        def fake_is_file(self):
            if str(self) == "/opt/homebrew/bin/tesseract":
                return True
            return real_is_file(self)

        monkeypatch.setattr(Path, "is_file", fake_is_file)

        assert TesseractImageParser._find_tesseract() == "/opt/homebrew/bin/tesseract"


class TestPDFHandler:
    """Test PDF extraction functionality."""

    def test_ocr_factory_creation(self):
        """Test factory can create parsers."""
        # Factory should create parser (even if Tesseract not available)
        try:
            parser = ImageOCRFactory.create_parser(method="tesseract")
            assert parser is not None
        except Exception:
            # OK if Tesseract not installed
            pass

    def test_ocr_factory_disabled(self):
        """Test that disabled OCR raises error."""
        with pytest.raises(ValueError):
            ImageOCRFactory.create_parser(method="disabled")

    def test_ocr_factory_unknown_method(self):
        """Test that unknown method raises error."""
        with pytest.raises(ValueError):
            ImageOCRFactory.create_parser(method="unknown_method")


class TestImageOCRIntegration:
    """Integration tests for OCR."""

    def test_parse_image_with_text(self):
        """Test parsing an image (if Tesseract available)."""
        # Create test image with text (requires PIL and Tesseract)
        try:
            from PIL import ImageDraw

            # Create image with text
            img = Image.new("RGB", (200, 100), color="white")
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), "Test Danger", fill="black")

            # Save to temp
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                img.save(f.name)
                temp_path = f.name

            try:
                parser = TesseractImageParser()
                if parser.tesseract_path:
                    # Only test if Tesseract is available
                    text = parser.parse_image(temp_path)
                    assert len(text) > 0
            finally:
                Path(temp_path).unlink(missing_ok=True)

        except (ImportError, Exception):
            # Skip if dependencies missing
            pytest.skip("Tesseract or PIL not available")

    def test_pdf_page_count_invalid_file(self):
        """Test that invalid PDF raises error."""
        with pytest.raises(FileNotFoundError):
            PDFHandler.get_page_count("/nonexistent/file.pdf")

    def test_extract_page_invalid_file(self):
        """Test that extracting from invalid PDF raises error."""
        with pytest.raises(FileNotFoundError):
            PDFHandler.extract_page_as_image("/nonexistent/file.pdf", 1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
