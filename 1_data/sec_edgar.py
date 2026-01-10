#!/usr/bin/env python3
"""
SEC EDGAR Integration

Fetches 10-K filings directly from SEC EDGAR (free, no API key required).
"""

import re
import time
import requests
from typing import Optional
from pathlib import Path
from bs4 import BeautifulSoup

# SEC requires a User-Agent header with contact info
HEADERS = {
    "User-Agent": "CreditRiskPlatform/1.0 (contact@example.com)",
    "Accept-Encoding": "gzip, deflate",
}

# SEC API endpoints
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"

# Ticker to CIK mapping for our companies
# CIK numbers are 10 digits, zero-padded
TICKER_TO_CIK = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "JNJ": "0000200406",
    "PFE": "0000078003",
    "JPM": "0000019617",
    "GS": "0000886982",
    "XOM": "0000034088",
    "CVX": "0000093410",
    "WMT": "0000104169",
    "AMZN": "0001018724",
    "GE": "0000040545",
    "MMM": "0000066740",
    "DAL": "0000027904",
    "UNP": "0000100885",
    "CAT": "0000018230",
    "DE": "0000315189",
    "TSLA": "0001318605",
    "BA": "0000012927",
    "KO": "0000021344",
    "VZ": "0000732712",
}


def get_cik(ticker: str) -> Optional[str]:
    """Get CIK number for a ticker symbol."""
    return TICKER_TO_CIK.get(ticker.upper())


def get_recent_10k_filing(ticker: str) -> Optional[dict]:
    """
    Get the most recent 10-K filing info for a company.

    Returns:
        dict with accession_number, filing_date, primary_document
    """
    cik = get_cik(ticker)
    if not cik:
        print(f"    [WARN] No CIK mapping for {ticker}")
        return None

    url = SEC_SUBMISSIONS_URL.format(cik=cik)

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Find the most recent 10-K filing
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        dates = filings.get("filingDate", [])
        primary_docs = filings.get("primaryDocument", [])

        for i, form in enumerate(forms):
            if form == "10-K":
                return {
                    "accession_number": accessions[i],
                    "filing_date": dates[i],
                    "primary_document": primary_docs[i],
                    "cik": cik.lstrip("0"),  # Remove leading zeros for URL
                }

        # Try 10-K/A (amended) if no 10-K found
        for i, form in enumerate(forms):
            if form == "10-K/A":
                return {
                    "accession_number": accessions[i],
                    "filing_date": dates[i],
                    "primary_document": primary_docs[i],
                    "cik": cik.lstrip("0"),
                }

        return None

    except Exception as e:
        print(f"    [ERROR] Failed to get filing info for {ticker}: {e}")
        return None


def fetch_10k_text(ticker: str, max_chars: int = 100000) -> Optional[dict]:
    """
    Fetch the 10-K filing text from SEC EDGAR.

    Args:
        ticker: Stock ticker symbol
        max_chars: Maximum characters to extract (10-Ks can be huge)

    Returns:
        dict with ticker, year, content, filing_date, source
    """
    print(f"    [SEC] Fetching 10-K from EDGAR...")

    filing_info = get_recent_10k_filing(ticker)
    if not filing_info:
        return None

    accession_no_dashes = filing_info["accession_number"].replace("-", "")

    try:
        # Rate limiting - SEC asks for max 10 requests per second
        time.sleep(0.2)

        # Use the primary document directly (the main 10-K filing)
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{filing_info['cik']}/{accession_no_dashes}/{filing_info['primary_document']}"
        print(f"    [SEC] Document: {filing_info['primary_document']}")

        time.sleep(0.2)
        response = requests.get(doc_url, headers=HEADERS, timeout=90)
        response.raise_for_status()

        content = response.text

        # Parse HTML to extract text
        soup = BeautifulSoup(content, "html.parser")

        # Remove non-content elements
        for element in soup(["script", "style", "meta", "link", "head", "title", "table"]):
            element.decompose()

        # Get all text
        text = soup.get_text(separator="\n")

        # Decode HTML entities
        import html
        text = html.unescape(text)

        # Clean up whitespace
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                lines.append(line)
        text = "\n".join(lines)

        # Remove duplicate lines (common in SEC filings)
        seen = set()
        unique_lines = []
        for line in text.split("\n"):
            if line not in seen or len(line) > 100:  # Keep long lines even if duplicate
                seen.add(line)
                unique_lines.append(line)
        text = "\n".join(unique_lines)

        # Extract key sections
        extracted = extract_key_sections(text, max_chars)

        # Get fiscal year from filing date
        year = int(filing_info["filing_date"][:4])
        if filing_info["filing_date"][5:7] in ["01", "02", "03", "04"]:
            year -= 1

        return {
            "ticker": ticker,
            "year": year,
            "type": "10-K",
            "content": extracted,
            "filing_date": filing_info["filing_date"],
            "source": "SEC EDGAR",
            "accession": filing_info["accession_number"],
        }

    except Exception as e:
        print(f"    [ERROR] Failed to fetch 10-K document: {e}")
        return None


def extract_key_sections(text: str, max_chars: int = 100000) -> str:
    """
    Extract key sections from 10-K text.

    Focuses on: Item 1A (Risk Factors), Item 1 (Business), Item 7 (MD&A)
    """
    sections = []

    # Find all occurrences of section headers and pick the one with substantial content after it
    section_configs = [
        ("RISK FACTORS", r"(?:ITEM|Item)\s*1A[.\s\-–—]*Risk\s*Factors"),
        ("BUSINESS", r"(?:ITEM|Item)\s*1[.\s\-–—]*Business(?!\s*\d)"),
        ("MD&A", r"(?:ITEM|Item)\s*7[.\s\-–—]*Management.{0,30}Discussion"),
    ]

    for section_name, header_pattern in section_configs:
        # Find all matches
        matches = list(re.finditer(header_pattern, text, re.IGNORECASE))

        for match in matches:
            # Get text after this header
            start_pos = match.end()
            remaining = text[start_pos:start_pos + 35000]

            # Check if this looks like TOC (short content before next item)
            # or actual section content (long paragraphs)
            next_item = re.search(r'\n(?:ITEM|Item)\s*\d', remaining)
            if next_item:
                section_text = remaining[:next_item.start()]
            else:
                section_text = remaining

            # Skip if this is TOC-like (mostly short lines)
            lines = section_text.strip().split('\n')
            long_lines = [l for l in lines if len(l) > 80]

            # If less than 10% of lines are long, it's probably TOC
            if len(lines) > 0 and len(long_lines) / len(lines) < 0.1:
                continue

            # If we have substantial content, use it
            if len(section_text.strip()) > 1000:
                # Clean up
                section_text = re.sub(r'\n{3,}', '\n\n', section_text)

                if len(section_text) > 30000:
                    section_text = section_text[:30000] + "\n\n[Section truncated...]"

                sections.append(f"\n{'='*60}\n{section_name}\n{'='*60}\n{section_text}")
                break  # Found good content for this section

    if sections:
        result = "\n".join(sections)
    else:
        # Fallback: extract paragraphs (lines > 200 chars likely real content)
        lines = text.split('\n')
        content_lines = []
        for line in lines:
            if len(line) > 150:  # Long lines are likely actual content
                content_lines.append(line)

        result = '\n\n'.join(content_lines[:100])  # Take first 100 paragraphs
        if not result:
            result = text[:max_chars]

    return result[:max_chars]


def test_fetch(ticker: str = "AAPL"):
    """Test fetching a 10-K filing."""
    print(f"\n[TEST] Fetching 10-K for {ticker}")

    result = fetch_10k_text(ticker)

    if result:
        print(f"\n[OK] Successfully fetched {ticker} 10-K")
        print(f"  Filing Date: {result['filing_date']}")
        print(f"  Fiscal Year: {result['year']}")
        print(f"  Source: {result['source']}")
        print(f"  Content Length: {len(result['content']):,} characters")
        print(f"\n  Preview (first 500 chars):")
        print("-" * 60)
        print(result["content"][:500])
        print("-" * 60)
    else:
        print(f"\n[FAIL] Could not fetch 10-K for {ticker}")


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    test_fetch(ticker)
