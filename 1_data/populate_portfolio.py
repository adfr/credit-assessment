#!/usr/bin/env python3
"""
Portfolio Data Population Script
Populates the loans table with 20 real public companies.
"""

import sqlite3
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np

from real_companies import COMPANIES, INDUSTRY_PARAMS

# Set seeds for reproducibility
np.random.seed(42)
random.seed(42)

# Configuration
BASE_DATE = datetime(2022, 1, 1)
END_DATE = datetime(2024, 12, 31)


def pd_to_grade(pd: float) -> str:
    """Convert PD to risk grade."""
    if pd < 0.005: return "AAA"
    elif pd < 0.01: return "AA"
    elif pd < 0.02: return "A"
    elif pd < 0.04: return "BBB"
    elif pd < 0.08: return "BB"
    elif pd < 0.15: return "B"
    else: return "CCC"


def get_db_path() -> Path:
    """Get the database file path."""
    return Path(__file__).parent.parent / "data" / "credit_risk.db"


def create_tables(conn: sqlite3.Connection):
    """Create all necessary tables."""
    cursor = conn.cursor()

    # Loans table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            loan_id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            ticker TEXT,
            industry TEXT NOT NULL,
            region TEXT,
            country TEXT,
            original_balance REAL NOT NULL,
            outstanding_balance REAL NOT NULL,
            interest_rate REAL NOT NULL,
            term_months INTEGER NOT NULL,
            purpose TEXT,
            collateral_type TEXT,
            collateral_value REAL DEFAULT 0,
            disbursement_date DATE NOT NULL,
            maturity_date DATE,
            last_payment_date DATE,
            last_payment_amount REAL DEFAULT 0,
            days_past_due INTEGER DEFAULT 0,
            payment_status TEXT DEFAULT 'current',
            status TEXT DEFAULT 'active',
            pd_score REAL DEFAULT 0.05,
            lgd_score REAL DEFAULT 0.45,
            risk_grade TEXT DEFAULT 'BBB',
            annual_revenue REAL,
            net_income REAL,
            total_assets REAL,
            total_liabilities REAL,
            documents_json TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Company documents table for RAG
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_documents (
            doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            company_name TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            filing_date DATE,
            fiscal_year INTEGER,
            content TEXT,
            summary TEXT,
            file_path TEXT,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            indexed_at TIMESTAMP,
            UNIQUE(ticker, doc_type, fiscal_year)
        )
    """)

    # Company news table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_news (
            news_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            company_name TEXT NOT NULL,
            title TEXT NOT NULL,
            snippet TEXT,
            source TEXT,
            url TEXT,
            published_date DATE,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sentiment TEXT,
            relevance_score REAL
        )
    """)

    # Repayments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repayments (
            repayment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id TEXT NOT NULL,
            payment_date DATE NOT NULL,
            payment_amount REAL NOT NULL,
            principal_amount REAL DEFAULT 0,
            interest_amount REAL DEFAULT 0,
            balance_after REAL,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
        )
    """)

    conn.commit()
    print("[OK] Tables created")


def generate_loans(conn: sqlite3.Connection):
    """Generate loan records for real companies."""
    print(f"\n[INFO] Generating loans for {len(COMPANIES)} companies...")

    cursor = conn.cursor()
    now = datetime.now()

    purposes = ["working_capital", "expansion", "equipment", "acquisition", "refinancing"]
    collateral_types = ["real_estate", "equipment", "inventory", "receivables", "unsecured"]

    for company in COMPANIES:
        industry = company["industry"]
        params = INDUSTRY_PARAMS[industry]

        # Loan details
        loan_id = f"LOAN-{company['ticker']}-{uuid.uuid4().hex[:4].upper()}"

        # Larger loan amounts for major corporations (in millions)
        original_balance = random.uniform(50_000_000, 500_000_000)

        # Disbursement date
        days_range = (END_DATE - BASE_DATE).days
        random_days = random.randint(0, days_range)
        disbursement_date = BASE_DATE + timedelta(days=random_days)

        # Term and maturity
        term_months = random.choice([36, 48, 60, 84, 120])
        maturity_date = disbursement_date + timedelta(days=term_months * 30)

        # Calculate how much has been paid off
        months_elapsed = max(0, (now - disbursement_date).days // 30)
        months_elapsed = min(months_elapsed, term_months)

        # Interest rate based on risk tier
        base_rate = 0.035 + params["risk_tier"] * 0.003
        interest_rate = base_rate + random.uniform(-0.005, 0.01)
        interest_rate = max(0.03, min(0.08, interest_rate))

        # Outstanding balance
        if months_elapsed >= term_months:
            outstanding_balance = 0
            status = "paid_off"
        else:
            payment_ratio = months_elapsed / term_months
            outstanding_balance = original_balance * (1 - payment_ratio * 0.85)
            status = "active"

        # PD/LGD based on industry with some variation
        pd_score = params["base_pd"] * random.uniform(0.7, 1.5)
        pd_score = max(0.005, min(0.15, pd_score))

        lgd_score = params["base_lgd"] * random.uniform(0.8, 1.2)
        lgd_score = max(0.25, min(0.65, lgd_score))

        risk_grade = pd_to_grade(pd_score)

        # Purpose and collateral
        purpose = random.choice(purposes)
        collateral_type = random.choice(collateral_types)
        collateral_value = 0 if collateral_type == "unsecured" else original_balance * random.uniform(1.0, 1.3)

        # Payment status (most should be current for major corps)
        if status == "active":
            if random.random() < 0.05:  # 5% chance of minor delinquency
                days_past_due = random.randint(1, 30)
                payment_status = "delinquent"
            else:
                days_past_due = 0
                payment_status = "current"
        else:
            days_past_due = 0
            payment_status = "current"

        # Last payment info
        if months_elapsed > 0:
            last_payment_date = disbursement_date + timedelta(days=months_elapsed * 30)
            monthly_payment = original_balance / term_months * (1 + interest_rate / 12)
            last_payment_amount = monthly_payment
        else:
            last_payment_date = None
            last_payment_amount = 0

        # Company financials (realistic ranges for large corps)
        annual_revenue = random.uniform(10_000_000_000, 500_000_000_000)
        profit_margin = random.uniform(0.05, 0.25)
        net_income = annual_revenue * profit_margin
        total_assets = annual_revenue * random.uniform(1.0, 3.0)
        total_liabilities = total_assets * random.uniform(0.4, 0.7)

        cursor.execute("""
            INSERT INTO loans (
                loan_id, company_name, ticker, industry, region, country,
                original_balance, outstanding_balance, interest_rate, term_months,
                purpose, collateral_type, collateral_value,
                disbursement_date, maturity_date,
                last_payment_date, last_payment_amount, days_past_due, payment_status,
                status, pd_score, lgd_score, risk_grade,
                annual_revenue, net_income, total_assets, total_liabilities
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            loan_id, company["name"], company["ticker"], industry,
            company["region"], company["country"],
            round(original_balance, 2), round(outstanding_balance, 2),
            round(interest_rate, 4), term_months,
            purpose, collateral_type, round(collateral_value, 2),
            disbursement_date.strftime("%Y-%m-%d"), maturity_date.strftime("%Y-%m-%d"),
            last_payment_date.strftime("%Y-%m-%d") if last_payment_date else None,
            round(last_payment_amount, 2), days_past_due, payment_status,
            status, round(pd_score, 4), round(lgd_score, 4), risk_grade,
            round(annual_revenue, 2), round(net_income, 2),
            round(total_assets, 2), round(total_liabilities, 2)
        ))

        print(f"  - {company['name']} ({company['ticker']}): ${original_balance/1e6:.1f}M loan")

    conn.commit()
    print(f"\n[OK] Generated {len(COMPANIES)} loans")


def print_summary(conn: sqlite3.Connection):
    """Print summary statistics."""
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("Portfolio Summary")
    print("=" * 60)

    cursor.execute("SELECT COUNT(*) FROM loans")
    loan_count = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(outstanding_balance) FROM loans")
    total_exposure = cursor.fetchone()[0] or 0

    cursor.execute("SELECT AVG(pd_score) FROM loans")
    avg_pd = cursor.fetchone()[0] or 0

    cursor.execute("SELECT AVG(lgd_score) FROM loans")
    avg_lgd = cursor.fetchone()[0] or 0

    print(f"\n  Total Loans: {loan_count}")
    print(f"  Total Exposure: ${total_exposure/1e9:.2f}B")
    print(f"  Average PD: {avg_pd * 100:.2f}%")
    print(f"  Average LGD: {avg_lgd * 100:.2f}%")

    print("\n  Companies in Portfolio:")
    cursor.execute("""
        SELECT company_name, ticker, industry, outstanding_balance, pd_score, risk_grade
        FROM loans ORDER BY outstanding_balance DESC
    """)
    for row in cursor.fetchall():
        print(f"    - {row[0]} ({row[1]}): ${row[3]/1e6:.1f}M | PD: {row[4]*100:.2f}% | Grade: {row[5]}")


def main():
    """Main function."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - Real Company Portfolio")
    print("=" * 60)

    db_path = get_db_path()
    print(f"\nDatabase: {db_path}")

    # Ensure data directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))

    try:
        # Drop and recreate tables (schema changed)
        print("\n[INFO] Dropping existing tables...")
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS repayments")
        cursor.execute("DROP TABLE IF EXISTS loans")
        cursor.execute("DROP TABLE IF EXISTS company_documents")
        cursor.execute("DROP TABLE IF EXISTS company_news")
        conn.commit()

        # Create tables
        print("[INFO] Creating tables...")
        create_tables(conn)

        # Generate loans
        generate_loans(conn)

        # Print summary
        print_summary(conn)

        print("\n" + "=" * 60)
        print("[SUCCESS] Portfolio populated with real companies!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Run: python fetch_10k_filings.py (to download 10-K filings)")
        print("  2. Start backend: cd ../5_backend && uvicorn main:app --reload")

    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    exit(main())
