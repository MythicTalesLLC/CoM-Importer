"""
Image parsing with OCR support for both local and cloud-based solutions.

Supports Tesseract (local, offline) and Google Cloud Vision (cloud, high accuracy).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

logger = logging.getLogger(__name__)


class ImageOCRParser(ABC):
    """Abstract base for image OCR parsers."""

    @abstractmethod
    def parse_image(self, image_path: str | Path) -> str:
        """
        Parse image and extract text.

        Args:
            image_path: Path to image file

        Returns:
            Extracted text

        Raises:
            Exception: If parsing fails
        """


class TesseractImageParser(ImageOCRParser):
    """Local OCR using Tesseract."""

    def __init__(self, tesseract_path: str | None = None) -> None:
        """
        Initialize Tesseract parser.

        Args:
            tesseract_path: Optional path to tesseract binary. Auto-detects if not provided.
        """
        self.tesseract_path = tesseract_path or self._find_tesseract()
        if not self.tesseract_path:
            logger.warning(
                "Tesseract not found. Install it with: "
                "brew install tesseract (Mac) or apt-get install tesseract-ocr (Linux)"
            )

    @staticmethod
    def _find_tesseract() -> str | None:
        """Find tesseract using env override, PATH lookup, and common install paths."""
        # Allow explicit override for packaged-app environments with restricted PATH.
        for env_var in ("COM_IMPORTER_TESSERACT_PATH", "TESSERACT_PATH", "TESSERACT_CMD"):
            candidate = os.environ.get(env_var)
            if candidate and Path(candidate).is_file():
                return candidate

        which_path = shutil.which("tesseract")
        if which_path:
            return which_path

        # Common install locations on macOS and Linux.
        for path in (
            "/opt/homebrew/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/local/bin/tesseract",
            "/usr/bin/tesseract",
        ):
            if Path(path).is_file():
                return path

        return None

    def parse_image(self, image_path: str | Path) -> str:
        """
        Extract text from image using Tesseract.

        Args:
            image_path: Path to image file

        Returns:
            Extracted text

        Raises:
            RuntimeError: If Tesseract not available or extraction fails
        """
        if not self.tesseract_path:
            raise RuntimeError(
                "Tesseract not found. Install with: "
                "brew install tesseract (Mac) or apt-get install tesseract-ocr (Linux)"
            )

        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        try:
            # Preprocess image for better OCR
            preprocessed = self._preprocess_image(image_path)

            # Use pytesseract if available, otherwise call tesseract directly.
            # Point pytesseract at the discovered binary to avoid PATH issues in app bundles.
            try:
                import pytesseract

                pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
                text = pytesseract.image_to_string(preprocessed)
            except ImportError:
                # Fall back to subprocess
                text = self._tesseract_subprocess(preprocessed)
            except (OSError, RuntimeError) as e:
                msg = str(e).lower()
                if "tesseract is not installed" in msg or "not found" in msg:
                    text = self._tesseract_subprocess(preprocessed)
                else:
                    raise

            return text.strip()

        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            raise RuntimeError(f"OCR extraction failed: {str(e)}") from e

    @staticmethod
    def _preprocess_image(image_path: str | Path) -> Image.Image:
        """
        Preprocess image for better OCR accuracy.

        - Convert to grayscale
        - Deskew if needed
        - Enhance contrast
        - Upscale if too small
        """
        img = Image.open(image_path)

        # Convert to grayscale
        if img.mode != "L":
            img = img.convert("L")

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Enhance brightness
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)

        # Auto-deskew if possible (simple rotation correction)
        img = ImageOps.autocontrast(img)

        # Upscale if image is small
        width, height = img.size
        if width < 300 or height < 300:
            scale_factor = max(300 / width, 300 / height)
            new_size = (
                int(width * scale_factor),
                int(height * scale_factor),
            )
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        return img

    def _tesseract_subprocess(self, image: Image.Image) -> str:
        """Call tesseract via subprocess."""
        import tempfile

        # Save preprocessed image to temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            image.save(f.name)
            temp_path = f.name

        try:
            result = subprocess.run(
                [self.tesseract_path, temp_path, "stdout"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Tesseract error: {result.stderr}")
            return result.stdout
        finally:
            Path(temp_path).unlink(missing_ok=True)


class CloudVisionImageParser(ImageOCRParser):
    """Cloud-based OCR using Google Cloud Vision API."""

    def __init__(self, api_key: str | None = None) -> None:
        """
        Initialize Cloud Vision parser.

        Args:
            api_key: Google Cloud Vision API key
        """
        self.api_key = api_key
        self.vision_client = None

        if api_key:
            self._init_client()

    def _init_client(self) -> None:
        """Initialize Google Cloud Vision client."""
        try:
            from google.cloud import vision

            self.vision_client = vision.ImageAnnotatorClient(credentials=self._get_credentials())
        except ImportError:
            logger.warning(
                "google-cloud-vision not installed. Install with: "
                "pip install google-cloud-vision"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Cloud Vision: {e}")

    def _get_credentials(self):
        """Get Google Cloud credentials from API key."""
        try:
            from google.oauth2 import service_account

            # If api_key is a JSON file path
            if Path(self.api_key).exists():
                return service_account.Credentials.from_service_account_file(self.api_key)

            # If api_key is a JSON string
            import json

            creds_dict = json.loads(self.api_key)
            return service_account.Credentials.from_service_account_info(creds_dict)
        except Exception:
            return None

    def parse_image(self, image_path: str | Path) -> str:
        """
        Extract text from image using Cloud Vision.

        Args:
            image_path: Path to image file

        Returns:
            Extracted text

        Raises:
            RuntimeError: If Cloud Vision not available or extraction fails
        """
        if not self.vision_client:
            raise RuntimeError("Cloud Vision client not initialized. Provide valid API key.")

        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        try:
            from google.cloud import vision

            # Read image file
            with open(image_path, "rb") as f:
                content = f.read()

            image = vision.Image(content=content)

            # Detect text
            response = self.vision_client.document_text_detection(image=image)

            if response.error.message:
                raise RuntimeError(f"Cloud Vision error: {response.error.message}")

            # Extract text from response
            text = response.full_text_annotation.text

            return text.strip()

        except ImportError as e:
            raise RuntimeError("google-cloud-vision library not installed") from e
        except Exception as e:
            logger.error(f"Cloud Vision OCR failed: {e}")
            raise RuntimeError(f"OCR extraction failed: {str(e)}") from e


class ImageOCRFactory:
    """Factory for creating appropriate image parser."""

    @staticmethod
    def create_parser(
        method: str = "auto",
        tesseract_path: str | None = None,
        vision_api_key: str | None = None,
    ) -> ImageOCRParser:
        """
        Create an image parser based on method.

        Args:
            method: "auto" (try Tesseract first), "tesseract", "cloud_vision", "disabled"
            tesseract_path: Optional path to tesseract binary
            vision_api_key: Optional Cloud Vision API key

        Returns:
            ImageOCRParser instance

        Raises:
            ValueError: If no suitable parser can be created
        """
        if method == "disabled":
            raise ValueError("OCR is disabled")

        if method == "auto":
            # Try Tesseract first (faster, no API key needed)
            parser = TesseractImageParser(tesseract_path)
            if parser.tesseract_path:
                logger.info("Using Tesseract OCR")
                return parser

            # Fall back to Cloud Vision
            if vision_api_key:
                logger.info("Using Cloud Vision OCR")
                return CloudVisionImageParser(vision_api_key)

            raise ValueError(
                "No OCR method available. Install Tesseract or provide Cloud Vision API key."
            )

        if method == "tesseract":
            return TesseractImageParser(tesseract_path)

        if method == "cloud_vision":
            if not vision_api_key:
                raise ValueError("Cloud Vision API key required")
            return CloudVisionImageParser(vision_api_key)

        raise ValueError(f"Unknown OCR method: {method}")
