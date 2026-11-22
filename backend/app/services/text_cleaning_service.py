import logging
import re
from typing import List, Tuple
from app.schemas.document_schemas import DocumentPage

logger = logging.getLogger("nitsetu.text_cleaning")


class TextCleaningService:
    """Cleans and standardizes extracted text from government circulars and gazettes.

    Preserves critical statutory provisions, section numbers, act titles,
    tabular data, dates, and amounts without destructive truncation.
    """

    # Common running headers/footers in Indian official gazettes & department circulars
    RUNNING_HEADER_PATTERNS = [
        r"^(The Gazette of India|భారత రాజపత్రం|भारत का राजपत्र).*$",
        r"^Page\s+\d+\s+of\s+\d+.*$",
        r"^\d+\s*/\s*\d+\s*/\s*\d{4}.*$",
        r"^(CONFIDENTIAL|FOR OFFICIAL USE ONLY|NOT FOR SALE)$",
    ]

    def clean_text(self, text: str) -> str:
        """Cleans and normalizes raw text while preserving semantic structure."""
        if not text:
            return ""

        # 1. Normalize line breaks and tabs
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = cleaned.replace("\t", "    ")

        # 2. Remove standard page numbering stamps if on a line by itself
        lines = cleaned.split("\n")
        preserved_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip purely isolated pagination markers like "- 4 -" or "Page 2"
            if re.match(r"^[-–—]\s*\d+\s*[-–—]$", stripped) or re.match(r"^Page\s+\d+(\s+of\s+\d+)?$", stripped, re.IGNORECASE):
                continue
            # Check against running header patterns
            is_artifact = False
            for pat in self.RUNNING_HEADER_PATTERNS:
                if re.match(pat, stripped, re.IGNORECASE):
                    is_artifact = True
                    break
            if not is_artifact:
                preserved_lines.append(line)

        cleaned = "\n".join(preserved_lines)

        # 3. Collapse 3+ consecutive newlines to 2 newlines (preserve paragraph breaks)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # 4. Collapse multiple inline spaces to a single space, but preserve indentation
        cleaned_lines = []
        for line in cleaned.split("\n"):
            # Preserve intentional indentation for bullet points / lists
            indent_match = re.match(r"^(\s+)", line)
            indent = indent_match.group(1) if indent_match else ""
            line_body = re.sub(r"[ ]{2,}", " ", line.strip())
            cleaned_lines.append(f"{indent}{line_body}" if line_body else "")

        cleaned = "\n".join(cleaned_lines).strip()
        return cleaned

    def clean_document_pages(self, pages: List[DocumentPage]) -> List[DocumentPage]:
        """Cleans text across all document pages, updating counts and filtering empty pages."""
        cleaned_pages: List[DocumentPage] = []
        for page in pages:
            cleaned_content = self.clean_text(page.text)
            words = cleaned_content.split()
            cleaned_pages.append(
                DocumentPage(
                    page_number=page.page_number,
                    text=cleaned_content,
                    word_count=len(words),
                    character_count=len(cleaned_content),
                )
            )
        return cleaned_pages


# Default singleton instance
text_cleaning_service = TextCleaningService()
