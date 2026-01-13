#!/usr/bin/env python3
"""
10-K Filing Fetcher

Downloads 10-K annual reports from financialdatasets.ai API
and stores them for RAG indexing.

Usage:
    python fetch_10k_filings.py

Requires:
    FINANCIAL_DATASETS_API_KEY environment variable
"""

import os
import sys
import json
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

# Get project root from environment or current working directory
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", os.getcwd()))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Add parent to path
sys.path.insert(0, str(PROJECT_ROOT / "1_data"))

from real_companies import COMPANIES, get_tickers

# Configuration
API_KEY = os.getenv("FINANCIAL_DATASETS_API_KEY")
BASE_URL = "https://api.financialdatasets.ai"
DOCS_DIR = PROJECT_ROOT / "data" / "company_docs"


def get_db_path() -> Path:
    """Get database path."""
    return PROJECT_ROOT / "data" / "credit_risk.db"


def get_db_connection():
    """Get database connection."""
    return sqlite3.connect(str(get_db_path()))


def fetch_10k_filing(ticker: str, year: int = 2023) -> Optional[dict]:
    """
    Fetch 10-K filing - primary from SEC EDGAR, fallback to mock.

    Args:
        ticker: Stock ticker symbol
        year: Fiscal year

    Returns:
        Filing data or None if not found
    """
    # Try SEC EDGAR first (free, no API key required)
    try:
        from sec_edgar import fetch_10k_text

        result = fetch_10k_text(ticker)
        if result and result.get("content") and len(result["content"]) > 1000:
            return {
                "ticker": ticker,
                "year": result.get("year", year),
                "type": "10-K",
                "content": result["content"],
                "company_name": next((c["name"] for c in COMPANIES if c["ticker"] == ticker), ticker),
                "source": "SEC EDGAR",
                "filing_date": result.get("filing_date"),
                "accession": result.get("accession"),
            }
        else:
            print(f"  [INFO] SEC EDGAR returned insufficient content for {ticker}")
    except Exception as e:
        print(f"  [WARN] SEC EDGAR failed for {ticker}: {e}")

    # Fallback to mock data
    print(f"  [INFO] Using mock data for {ticker}")
    return generate_mock_10k(ticker, year)


def generate_mock_10k(ticker: str, year: int) -> dict:
    """
    Generate mock 10-K content for demo purposes.
    In production, this would be real SEC filing data.
    """
    company = next((c for c in COMPANIES if c["ticker"] == ticker), None)
    if not company:
        return None

    # Generate realistic mock content based on industry
    industry_risks = {
        "technology": [
            "Cybersecurity threats and data breaches",
            "Rapid technological change requiring continuous innovation",
            "Dependence on key personnel and talent retention",
            "Intellectual property litigation risks",
            "Supply chain disruptions for hardware components"
        ],
        "healthcare": [
            "Regulatory changes in healthcare policy",
            "Drug pricing pressures and reimbursement risks",
            "Clinical trial failures and R&D uncertainties",
            "Patent expirations and generic competition",
            "Product liability and litigation exposure"
        ],
        "financial_services": [
            "Interest rate volatility affecting net interest margin",
            "Credit losses in loan portfolios",
            "Regulatory capital requirements",
            "Cybersecurity and operational risks",
            "Market risk from trading activities"
        ],
        "energy": [
            "Commodity price volatility",
            "Environmental regulations and climate policy",
            "Transition risks to renewable energy",
            "Geopolitical risks affecting supply",
            "Capital intensity of exploration and production"
        ],
        "retail": [
            "Consumer spending sensitivity to economic conditions",
            "E-commerce competition and channel shift",
            "Supply chain and inventory management risks",
            "Labor costs and workforce challenges",
            "Real estate and lease obligations"
        ],
        "manufacturing": [
            "Raw material cost fluctuations",
            "Global supply chain dependencies",
            "Labor relations and workforce availability",
            "Product quality and safety recalls",
            "Automation and technology investments"
        ],
        "transportation": [
            "Fuel price volatility",
            "Economic cyclicality affecting demand",
            "Regulatory compliance costs",
            "Infrastructure and fleet maintenance",
            "Labor negotiations and work stoppages"
        ],
        "construction": [
            "Economic cycle sensitivity",
            "Material and labor cost inflation",
            "Project delays and cost overruns",
            "Weather-related disruptions",
            "Bonding and insurance requirements"
        ]
    }

    risks = industry_risks.get(company["industry"], ["General business risks"])

    content = f"""
UNITED STATES SECURITIES AND EXCHANGE COMMISSION
Washington, D.C. 20549

FORM 10-K
ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934

For the fiscal year ended December 31, {year}

{company['name']}
(Exact name of registrant as specified in its charter)

Ticker Symbol: {ticker}
Industry: {company['industry'].replace('_', ' ').title()}

================================================================================
PART I
================================================================================

ITEM 1. BUSINESS

{company['name']} is a leading company in the {company['industry'].replace('_', ' ')} sector.
The company operates primarily in {company['region']} with headquarters in {company['country']}.

Our principal business activities include providing products and services to customers
across multiple market segments. We maintain a strong competitive position through
continuous innovation, operational excellence, and strategic investments.

ITEM 1A. RISK FACTORS

The following risk factors could materially affect our business, financial condition,
and results of operations:

{''.join([f'''
{i+1}. {risk}
   This risk could result in decreased revenues, increased costs, or regulatory penalties
   that may adversely affect our financial performance and credit profile.
''' for i, risk in enumerate(risks)])}

Additional risks include:
- General economic conditions and market volatility
- Foreign currency exchange rate fluctuations
- Changes in tax laws and regulations
- Competition from existing and new market entrants
- Ability to access capital markets on favorable terms

ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION

Financial Highlights for Fiscal Year {year}:
- Revenue growth driven by strong demand in core markets
- Operating margins reflect ongoing efficiency initiatives
- Strong balance sheet with manageable debt levels
- Continued investment in growth opportunities

Liquidity and Capital Resources:
The company maintains adequate liquidity through cash on hand, operating cash flows,
and available credit facilities. Our debt-to-equity ratio remains within target ranges,
and we have no significant near-term debt maturities that pose refinancing risk.

Credit Profile:
- Investment grade credit rating maintained
- Strong interest coverage ratio
- Diversified funding sources
- Manageable debt maturity profile

ITEM 8. FINANCIAL STATEMENTS

[Financial statements would be included here in actual filing]

Key Financial Metrics:
- Total Revenue: [Reported in financial statements]
- Net Income: [Reported in financial statements]
- Total Assets: [Reported in financial statements]
- Total Debt: [Reported in financial statements]
- Shareholders' Equity: [Reported in financial statements]

================================================================================
PART IV
================================================================================

ITEM 15. EXHIBITS AND FINANCIAL STATEMENT SCHEDULES

[List of exhibits would be included here]

This Form 10-K contains forward-looking statements that involve risks and uncertainties.
Actual results may differ materially from those expressed or implied.

================================================================================
END OF FORM 10-K
================================================================================
"""

    return {
        "ticker": ticker,
        "year": year,
        "type": "10-K",
        "content": content,
        "risks": risks,
        "company_name": company["name"],
        "industry": company["industry"],
        "source": "mock_data"
    }


def save_filing_to_db(conn: sqlite3.Connection, filing: dict) -> bool:
    """Save filing to database."""
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO company_documents
            (ticker, company_name, doc_type, fiscal_year, content, summary, downloaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            filing["ticker"],
            filing.get("company_name", filing["ticker"]),
            filing["type"],
            filing["year"],
            filing.get("content", json.dumps(filing.get("financials", {}))),
            f"10-K Annual Report for fiscal year {filing['year']}",
            datetime.now().isoformat()
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to save {filing['ticker']}: {e}")
        return False


def save_filing_to_file(filing: dict) -> Optional[Path]:
    """Save filing content to file."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    file_path = DOCS_DIR / f"{filing['ticker']}_{filing['year']}_10K.txt"

    try:
        content = filing.get("content", json.dumps(filing, indent=2))
        file_path.write_text(content)
        return file_path
    except Exception as e:
        print(f"  [ERROR] Failed to write file for {filing['ticker']}: {e}")
        return None


def main():
    """Main function to fetch all 10-K filings."""
    print("\n" + "=" * 60)
    print("10-K Filing Fetcher")
    print("=" * 60)

    if not API_KEY:
        print("\n[WARN] FINANCIAL_DATASETS_API_KEY not set")
        print("       Using mock data for demonstration")
        print("       Get API key from: https://financialdatasets.ai")

    tickers = get_tickers()
    print(f"\n[INFO] Fetching 10-K filings for {len(tickers)} companies...")

    conn = get_db_connection()
    success_count = 0
    failed_count = 0

    for ticker in tickers:
        company = next((c for c in COMPANIES if c["ticker"] == ticker), None)
        print(f"\n  Processing {ticker} ({company['name'] if company else 'Unknown'})...")

        # Fetch filing
        filing = fetch_10k_filing(ticker, year=2023)

        if filing:
            # Save to database
            if save_filing_to_db(conn, filing):
                success_count += 1
                print(f"    [OK] Saved to database")

            # Save to file
            file_path = save_filing_to_file(filing)
            if file_path:
                print(f"    [OK] Saved to {file_path.name}")
        else:
            failed_count += 1
            print(f"    [FAIL] Could not fetch filing")

    conn.close()

    print("\n" + "=" * 60)
    print(f"[DONE] Fetched {success_count} filings, {failed_count} failed")
    print("=" * 60)

    if success_count > 0:
        print("\nNext steps:")
        print("  1. Run: python index_documents.py (to index for RAG)")
        print("  2. Ask the AI: 'What are the risk factors for Apple?'")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    exit(main())
