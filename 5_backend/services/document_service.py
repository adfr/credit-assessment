"""
Document Service
Handles document processing and data extraction.
"""

import sys
from pathlib import Path
from typing import Optional
import base64

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "4_endpoints"))


class DocumentService:
    """Service for document processing operations."""

    def __init__(self):
        self.endpoint_url = None  # Set for CML deployment

    async def process_document(
        self,
        document_path: Optional[str] = None,
        document_base64: Optional[str] = None,
        document_type: str = "pdf",
        extraction_type: str = "financial"
    ) -> dict:
        """Process a document and extract structured data."""
        try:
            from serve_documents import process

            args = {
                "document_type": document_type,
                "extraction_type": extraction_type,
            }

            if document_path:
                args["document_path"] = document_path
            elif document_base64:
                args["document_base64"] = document_base64

            result = process(args)
            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    async def extract_financial_data(self, text: str) -> dict:
        """Extract financial data from text."""
        try:
            from serve_documents import process

            result = process({
                "text": text,
                "document_type": "text",
                "extraction_type": "financial",
            })
            return result.get("extracted_data", {})

        except Exception as e:
            return {"error": str(e)}

    async def extract_loan_application(self, text: str) -> dict:
        """Extract loan application data from text."""
        try:
            from serve_documents import process

            result = process({
                "text": text,
                "document_type": "text",
                "extraction_type": "loan_application",
            })
            return result.get("extracted_data", {})

        except Exception as e:
            return {"error": str(e)}

    def validate_document(self, document: dict) -> dict:
        """Validate uploaded document."""
        required_fields = ["filename", "content_type", "size"]
        missing = [f for f in required_fields if f not in document]

        if missing:
            return {
                "valid": False,
                "missing_fields": missing,
            }

        # Check file size (max 10MB)
        if document.get("size", 0) > 10 * 1024 * 1024:
            return {
                "valid": False,
                "error": "File too large (max 10MB)",
            }

        # Check allowed types
        allowed_types = ["application/pdf", "image/png", "image/jpeg", "text/plain"]
        if document.get("content_type") not in allowed_types:
            return {
                "valid": False,
                "error": f"Invalid file type: {document.get('content_type')}",
            }

        return {"valid": True}
