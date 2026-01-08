"""
Document Service
Handles document scanning, reading, and metadata extraction from local filesystem.
Documents are assumed to be pre-placed in folders organized by application ID.
"""

import os
import sys
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import base64

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "4_endpoints"))


class DocumentType(str, Enum):
    FINANCIAL_STATEMENT = "financial_statement"
    TAX_RETURN = "tax_return"
    BANK_STATEMENT = "bank_statement"
    BUSINESS_LICENSE = "business_license"
    COLLATERAL_APPRAISAL = "collateral_appraisal"
    ARTICLES_OF_INCORPORATION = "articles_of_incorporation"
    GUARANTOR_FINANCIALS = "guarantor_financials"
    LOAN_APPLICATION = "loan_application"
    OTHER = "other"


# File patterns to identify document types
DOCUMENT_TYPE_PATTERNS = {
    DocumentType.FINANCIAL_STATEMENT: ["financial", "balance_sheet", "income_statement", "p&l", "profit_loss", "fs_"],
    DocumentType.TAX_RETURN: ["tax", "1120", "schedule_c"],
    DocumentType.BANK_STATEMENT: ["bank_statement", "bank_stmt", "account_statement"],
    DocumentType.BUSINESS_LICENSE: ["license", "registration", "permit"],
    DocumentType.COLLATERAL_APPRAISAL: ["appraisal", "valuation", "collateral"],
    DocumentType.ARTICLES_OF_INCORPORATION: ["articles", "incorporation", "bylaws", "charter"],
    DocumentType.GUARANTOR_FINANCIALS: ["guarantor", "personal_financial"],
    DocumentType.LOAN_APPLICATION: ["application", "loan_app", "credit_app"],
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".doc", ".docx", ".png", ".jpg", ".jpeg"}

# Max file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


@dataclass
class DocumentMetadata:
    """Metadata for a document."""
    document_id: str
    filename: str
    document_type: str
    file_path: str
    file_size: int
    mime_type: str
    checksum: str
    created_at: str
    application_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DocumentService:
    """
    Service for managing documents on local filesystem.

    Documents are organized by application ID:
    data/documents/{application_id}/
        ├── financial_statement_2023.pdf
        ├── tax_return_2023.pdf
        ├── bank_statement_jan.pdf
        └── ...
    """

    def __init__(self, base_path: Optional[str] = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Default path relative to project root
            self.base_path = Path(__file__).parent.parent.parent / "data" / "documents"

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.endpoint_url = None  # Set for CML deployment

    def get_application_folder(self, application_id: str) -> Path:
        """Get the document folder for an application."""
        folder = self.base_path / application_id
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _generate_document_id(self, file_path: Path) -> str:
        """Generate a unique document ID based on file path and content."""
        content_hash = self._calculate_checksum(file_path)[:8]
        return f"DOC-{content_hash.upper()}"

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _detect_document_type(self, filename: str) -> DocumentType:
        """Detect document type from filename."""
        filename_lower = filename.lower()

        for doc_type, patterns in DOCUMENT_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in filename_lower:
                    return doc_type

        return DocumentType.OTHER

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type of a file."""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"

    def scan_documents(self, application_id: str) -> List[DocumentMetadata]:
        """
        Scan the application's document folder and return metadata for all documents.

        Args:
            application_id: The application ID to scan documents for

        Returns:
            List of DocumentMetadata objects
        """
        folder = self.get_application_folder(application_id)
        documents = []

        if not folder.exists():
            return documents

        for file_path in folder.iterdir():
            if not file_path.is_file():
                continue

            # Check extension
            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue

            # Check file size
            file_size = file_path.stat().st_size
            if file_size > MAX_FILE_SIZE:
                print(f"[DOCUMENT_SERVICE] Skipping {file_path.name}: exceeds size limit")
                continue

            try:
                metadata = DocumentMetadata(
                    document_id=self._generate_document_id(file_path),
                    filename=file_path.name,
                    document_type=self._detect_document_type(file_path.name).value,
                    file_path=str(file_path),
                    file_size=file_size,
                    mime_type=self._get_mime_type(file_path),
                    checksum=self._calculate_checksum(file_path),
                    created_at=datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    application_id=application_id,
                )
                documents.append(metadata)
            except Exception as e:
                print(f"[DOCUMENT_SERVICE] Error processing {file_path.name}: {e}")

        return documents

    def get_document(self, application_id: str, document_id: str) -> Optional[DocumentMetadata]:
        """Get a specific document by ID."""
        documents = self.scan_documents(application_id)
        for doc in documents:
            if doc.document_id == document_id:
                return doc
        return None

    def read_document(self, application_id: str, document_id: str) -> Optional[bytes]:
        """Read document content as bytes."""
        doc = self.get_document(application_id, document_id)
        if doc:
            with open(doc.file_path, "rb") as f:
                return f.read()
        return None

    def get_documents_summary(self, application_id: str) -> Dict[str, Any]:
        """
        Get a summary of documents for an application.

        Returns:
            Dictionary with document counts by type and completeness check
        """
        documents = self.scan_documents(application_id)

        # Count by type
        type_counts = {}
        for doc in documents:
            doc_type = doc.document_type
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

        # Required documents for a complete application
        required_types = [
            DocumentType.FINANCIAL_STATEMENT.value,
            DocumentType.BANK_STATEMENT.value,
        ]

        missing_types = [t for t in required_types if t not in type_counts]

        return {
            "application_id": application_id,
            "total_documents": len(documents),
            "documents_by_type": type_counts,
            "missing_required": missing_types,
            "is_complete": len(missing_types) == 0,
            "documents": [doc.to_dict() for doc in documents],
        }

    def validate_documents(self, application_id: str) -> Dict[str, Any]:
        """
        Validate documents for an application.

        Returns:
            Validation results with any issues found
        """
        documents = self.scan_documents(application_id)
        issues = []

        if not documents:
            issues.append({
                "severity": "warning",
                "message": "No documents found for application",
            })
            return {
                "valid": True,  # Still valid, just no docs
                "issues": issues,
                "documents_count": 0,
            }

        # Check for required documents
        doc_types = {doc.document_type for doc in documents}

        if DocumentType.FINANCIAL_STATEMENT.value not in doc_types:
            issues.append({
                "severity": "info",
                "message": "Financial statements not found",
            })

        if DocumentType.BANK_STATEMENT.value not in doc_types:
            issues.append({
                "severity": "info",
                "message": "Bank statements not found",
            })

        # Check file sizes
        for doc in documents:
            if doc.file_size < 1000:  # Less than 1KB might be empty
                issues.append({
                    "severity": "warning",
                    "message": f"Document {doc.filename} appears to be empty or very small",
                })

        return {
            "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
            "documents_count": len(documents),
            "document_types": list(doc_types),
        }

    # Legacy methods for backward compatibility
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

    def validate_document_upload(self, document: dict) -> dict:
        """Validate uploaded document metadata."""
        required_fields = ["filename", "content_type", "size"]
        missing = [f for f in required_fields if f not in document]

        if missing:
            return {
                "valid": False,
                "missing_fields": missing,
            }

        # Check file size (max 10MB)
        if document.get("size", 0) > MAX_FILE_SIZE:
            return {
                "valid": False,
                "error": "File too large (max 10MB)",
            }

        # Check allowed types
        allowed_types = ["application/pdf", "image/png", "image/jpeg", "text/plain",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]
        if document.get("content_type") not in allowed_types:
            return {
                "valid": False,
                "error": f"Invalid file type: {document.get('content_type')}",
            }

        return {"valid": True}


# Singleton instance
_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """Get or create singleton document service."""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service
