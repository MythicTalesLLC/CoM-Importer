"""
PDF handling utilities for extracting pages and converting to images.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image

logger = logging.getLogger(__name__)


class PDFHandler:
    """Handles PDF extraction and image conversion."""

    @staticmethod
    def get_page_count(pdf_path: str | Path) -> int:
        """
        Get total number of pages in PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Number of pages

        Raises:
            Exception: If PDF cannot be read
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            images = convert_from_path(pdf_path, first_page=1, last_page=1)
            # Get total pages (try to convert all to count)
            images = convert_from_path(pdf_path)
            return len(images)
        except Exception as e:
            logger.error(f"Failed to read PDF: {e}")
            raise RuntimeError(f"Cannot read PDF file: {str(e)}") from e

    @staticmethod
    def extract_page_as_image(
        pdf_path: str | Path,
        page_number: int,
        dpi: int = 200,
    ) -> Image.Image:
        """
        Extract a single page from PDF and return as PIL Image.

        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-indexed)
            dpi: Resolution for conversion (higher = better quality, slower)

        Returns:
            PIL Image of the page

        Raises:
            Exception: If page cannot be extracted
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            # Convert page to image
            images = convert_from_path(
                pdf_path,
                first_page=page_number,
                last_page=page_number,
                dpi=dpi,
            )

            if not images:
                raise ValueError(f"Page {page_number} not found in PDF")

            return images[0]

        except Exception as e:
            logger.error(f"Failed to extract PDF page {page_number}: {e}")
            raise RuntimeError(f"Cannot extract page {page_number} from PDF: {str(e)}") from e

    @staticmethod
    def extract_page_as_file(
        pdf_path: str | Path,
        page_number: int,
        output_path: str | Path,
        dpi: int = 200,
    ) -> Path:
        """
        Extract a PDF page and save as image file.

        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-indexed)
            output_path: Where to save the image
            dpi: Resolution for conversion

        Returns:
            Path to saved image file

        Raises:
            Exception: If extraction or saving fails
        """
        image = PDFHandler.extract_page_as_image(pdf_path, page_number, dpi)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as PNG
        if output_path.suffix.lower() != ".png":
            output_path = output_path.with_suffix(".png")

        image.save(output_path, "PNG")
        logger.info(f"Saved PDF page {page_number} to {output_path}")

        return output_path

    @staticmethod
    def extract_all_pages_as_images(
        pdf_path: str | Path,
        dpi: int = 200,
    ) -> list[Image.Image]:
        """
        Extract all pages from PDF as images.

        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for conversion

        Returns:
            List of PIL Images

        Raises:
            Exception: If PDF cannot be read
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            images = convert_from_path(pdf_path, dpi=dpi)
            logger.info(f"Extracted {len(images)} pages from PDF")
            return images

        except Exception as e:
            logger.error(f"Failed to extract PDF pages: {e}")
            raise RuntimeError(f"Cannot extract pages from PDF: {str(e)}") from e
