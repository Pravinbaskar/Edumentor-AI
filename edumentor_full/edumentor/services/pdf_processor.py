from __future__ import annotations

import io
import logging
from typing import List
from PyPDF2 import PdfReader

logger = logging.getLogger("edumentor.pdf_processor")


class PDFProcessor:
    """Process PDF files and extract text content."""

    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """
        Extract text from PDF bytes.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Extracted text content
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            if len(pdf_reader.pages) == 0:
                raise ValueError("PDF has no pages")
            
            text_content = []
            pages_with_text = 0
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        text_content.append(text)
                        pages_with_text += 1
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
            
            full_text = "\n\n".join(text_content)
            logger.info(
                f"Extracted {len(full_text)} characters from {pages_with_text}/{len(pdf_reader.pages)} pages"
            )
            
            if pages_with_text == 0:
                raise ValueError(
                    f"Could not extract text from any of the {len(pdf_reader.pages)} pages. "
                    "This PDF might be image-based or protected."
                )
            
            return full_text
        except Exception as e:
            logger.error(f"Failed to process PDF: {e}")
            raise ValueError(f"Failed to process PDF: {e}")

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            
            # Try to break at sentence or paragraph boundary
            if end < text_length:
                # Look for paragraph break
                para_break = text.rfind('\n\n', start, end)
                if para_break > start:
                    end = para_break
                else:
                    # Look for sentence break
                    sentence_break = max(
                        text.rfind('. ', start, end),
                        text.rfind('! ', start, end),
                        text.rfind('? ', start, end)
                    )
                    if sentence_break > start:
                        end = sentence_break + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - overlap if end < text_length else text_length
        
        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks

    @classmethod
    def process_pdf(cls, pdf_bytes: bytes, chunk_size: int = 500) -> List[str]:
        """
        Process PDF and return text chunks.
        
        Args:
            pdf_bytes: PDF file content as bytes
            chunk_size: Maximum chunk size
            
        Returns:
            List of text chunks
        """
        text = cls.extract_text_from_pdf(pdf_bytes)
        chunks = cls.chunk_text(text, chunk_size=chunk_size)
        return chunks
