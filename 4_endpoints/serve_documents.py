#!/usr/bin/env python3
"""
Document Processing Endpoint
Extracts structured data from uploaded documents using OCR and LLM.
"""

import os
import base64
import json
import re
from pathlib import Path
from typing import Optional

# Try to import document processing libraries
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file."""
    if not PYMUPDF_AVAILABLE:
        return "[PDF extraction not available - install PyMuPDF]"

    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return f"[Error extracting PDF: {e}]"


def extract_text_from_image(image_path: str) -> str:
    """Extract text from image using OCR."""
    if not OCR_AVAILABLE:
        return "[OCR not available - install pytesseract and Pillow]"

    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        return f"[Error with OCR: {e}]"


def extract_financial_data(text: str) -> dict:
    """Extract financial data from text using pattern matching."""
    extracted = {
        "company_name": None,
        "annual_revenue": None,
        "net_income": None,
        "total_assets": None,
        "total_liabilities": None,
        "current_ratio": None,
        "debt_to_equity": None,
        "fiscal_year": None,
    }

    # Pattern matching for common financial terms
    patterns = {
        "annual_revenue": [
            r"(?:revenue|sales|total revenue)[:\s]*\$?([\d,]+(?:\.\d{2})?)\s*(?:million|M)?",
            r"(?:revenue|sales)[:\s]*([\d,]+(?:\.\d{2})?)",
        ],
        "net_income": [
            r"(?:net income|net profit|profit)[:\s]*\$?([\d,]+(?:\.\d{2})?)\s*(?:million|M)?",
        ],
        "total_assets": [
            r"(?:total assets)[:\s]*\$?([\d,]+(?:\.\d{2})?)\s*(?:million|M)?",
        ],
        "total_liabilities": [
            r"(?:total liabilities)[:\s]*\$?([\d,]+(?:\.\d{2})?)\s*(?:million|M)?",
        ],
        "current_ratio": [
            r"(?:current ratio)[:\s]*([\d.]+)",
        ],
        "debt_to_equity": [
            r"(?:debt.to.equity|d/e ratio)[:\s]*([\d.]+)",
        ],
    }

    for field, field_patterns in patterns.items():
        for pattern in field_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).replace(",", "")
                try:
                    extracted[field] = float(value)
                except ValueError:
                    extracted[field] = value
                break

    # Extract company name (look for common patterns)
    company_patterns = [
        r"^([A-Z][A-Za-z\s&]+(?:Inc\.|Corp\.|LLC|Ltd\.|Corporation|Company))",
        r"(?:Company Name|Legal Name)[:\s]*([A-Za-z\s&]+)",
    ]

    for pattern in company_patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            extracted["company_name"] = match.group(1).strip()
            break

    # Extract fiscal year
    year_match = re.search(r"(?:fiscal year|fy|year ended)[:\s]*(\d{4})", text, re.IGNORECASE)
    if year_match:
        extracted["fiscal_year"] = int(year_match.group(1))

    return extracted


def extract_loan_application_data(text: str) -> dict:
    """Extract loan application data from text."""
    extracted = {
        "requested_amount": None,
        "loan_purpose": None,
        "term_months": None,
        "collateral_type": None,
        "collateral_value": None,
    }

    # Amount patterns
    amount_patterns = [
        r"(?:requested amount|loan amount)[:\s]*\$?([\d,]+(?:\.\d{2})?)",
        r"\$([\d,]+(?:\.\d{2})?)\s*(?:requested|loan)",
    ]

    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            extracted["requested_amount"] = float(match.group(1).replace(",", ""))
            break

    # Purpose
    purpose_patterns = [
        r"(?:purpose|use of funds)[:\s]*([A-Za-z\s]+?)(?:\n|$)",
    ]

    for pattern in purpose_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            purpose = match.group(1).strip().lower()
            if any(p in purpose for p in ["working capital", "expansion", "equipment", "acquisition"]):
                extracted["loan_purpose"] = purpose
            break

    # Term
    term_match = re.search(r"(?:term|months)[:\s]*(\d+)\s*months?", text, re.IGNORECASE)
    if term_match:
        extracted["term_months"] = int(term_match.group(1))

    return extracted


def process(args: dict) -> dict:
    """
    Main processing function for document extraction.

    Args:
        args: Dictionary containing:
            - document_base64: str (base64 encoded document)
            - document_path: str (path to document file)
            - document_type: str (pdf, image, text)
            - extraction_type: str (financial, loan_application, general)

    Returns:
        Dictionary with extracted fields
    """
    try:
        document_type = args.get("document_type", "text")
        extraction_type = args.get("extraction_type", "financial")

        # Get document content
        if "document_base64" in args:
            # Decode base64 content
            content = base64.b64decode(args["document_base64"])
            # Save temporarily for processing
            temp_path = Path("/tmp/temp_document")
            with open(temp_path, "wb") as f:
                f.write(content)
            document_path = str(temp_path)
        elif "document_path" in args:
            document_path = args["document_path"]
        elif "text" in args:
            # Direct text input
            text = args["text"]
            document_path = None
        else:
            return {
                "status": "error",
                "error": "No document provided",
            }

        # Extract text based on document type
        if document_path:
            if document_type == "pdf":
                text = extract_text_from_pdf(document_path)
            elif document_type in ["image", "png", "jpg", "jpeg"]:
                text = extract_text_from_image(document_path)
            else:
                # Assume text file
                with open(document_path, "r") as f:
                    text = f.read()

        # Extract structured data
        if extraction_type == "financial":
            extracted_data = extract_financial_data(text)
        elif extraction_type == "loan_application":
            extracted_data = extract_loan_application_data(text)
        else:
            extracted_data = {
                "raw_text": text[:5000],  # First 5000 chars
                "text_length": len(text),
            }

        # Count fields extracted
        fields_found = sum(1 for v in extracted_data.values() if v is not None)

        return {
            "status": "success",
            "extraction_type": extraction_type,
            "document_type": document_type,
            "extracted_data": extracted_data,
            "fields_found": fields_found,
            "text_length": len(text) if text else 0,
            "confidence": min(1.0, fields_found / 5),  # Simple confidence score
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


if __name__ == "__main__":
    # Test with sample text
    sample_financial = """
    ACME Corporation
    Consolidated Financial Statements
    Fiscal Year Ended December 31, 2024

    Total Revenue: $125,450,000
    Net Income: $11,700,000
    Total Assets: $104,000,000
    Total Liabilities: $61,500,000

    Current Ratio: 1.95
    Debt-to-Equity Ratio: 1.45
    """

    print("\n" + "=" * 50)
    print("Document Processing Endpoint - Test")
    print("=" * 50)

    result = process({
        "text": sample_financial,
        "document_type": "text",
        "extraction_type": "financial",
    })

    print(f"\nExtraction Results:")
    print(f"  Status: {result['status']}")
    print(f"  Fields Found: {result['fields_found']}")
    print(f"\nExtracted Data:")
    for key, value in result.get("extracted_data", {}).items():
        if value is not None:
            print(f"  {key}: {value}")
