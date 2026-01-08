#!/usr/bin/env python3
"""
Portfolio Data Population Script
Populates the loans and repayments tables with sample portfolio data.
"""

import sqlite3
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta

try:
    from faker import Faker
    import numpy as np
except ImportError as e:
    print(f"[ERROR] Missing required package: {e}")
    print("Run: pip install faker numpy")
    exit(1)

# Initialize
fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

# Configuration
NUM_LOANS = 500
BASE_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2024, 12, 31)

# Industry definitions
INDUSTRIES = {
    "technology": {"default_rate": 0.03, "risk_tier": 2},
    "healthcare": {"default_rate": 0.025, "risk_tier": 1},
    "manufacturing": {"default_rate": 0.04, "risk_tier": 3},
    "retail": {"default_rate": 0.06, "risk_tier": 4},
    "financial_services": {"default_rate": 0.02, "risk_tier": 1},
    "energy": {"default_rate": 0.05, "risk_tier": 4},
    "construction": {"default_rate": 0.07, "risk_tier": 5},
    "transportation": {"default_rate": 0.045, "risk_tier": 3},
}

PURPOSES = ["working_capital", "expansion", "equipment", "acquisition", "refinancing", "real_estate"]
COLLATERAL_TYPES = ["real_estate", "equipment", "inventory", "receivables", "unsecured"]
REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America"]
COUNTRIES = {
    "North America": ["USA", "Canada"],
    "Europe": ["UK", "Germany", "France", "Netherlands"],
    "Asia Pacific": ["Japan", "Australia", "Singapore"],
    "Latin America": ["Brazil", "Mexico"],
}

# Risk grade mapping based on PD
def pd_to_grade(pd: float) -> str:
    if pd < 0.005: return "AAA"
    elif pd < 0.01: return "AA"
    elif pd < 0.02: return "A"
    elif pd < 0.04: return "BBB"
    elif pd < 0.08: return "BB"
    elif pd < 0.15: return "B"
    else: return "CCC"


def generate_company_name() -> str:
    """Generate a realistic company name."""
    patterns = [
        lambda: f"{fake.last_name()} {fake.company_suffix()}",
        lambda: f"{fake.last_name()} & {fake.last_name()} {fake.company_suffix()}",
        lambda: fake.company(),
    ]
    return random.choice(patterns)()


def get_db_path() -> Path:
    """Get the database file path."""
    return Path(__file__).parent.parent / "data" / "credit_risk.db"


def create_loans_table(conn: sqlite3.Connection):
    """Create the loans table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            loan_id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
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
    conn.commit()


def create_repayments_table(conn: sqlite3.Connection):
    """Create the repayments table if it doesn't exist."""
    cursor = conn.cursor()
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


def generate_loans(conn: sqlite3.Connection, n: int):
    """Generate loan records."""
    print(f"\n[INFO] Generating {n} loans...")

    cursor = conn.cursor()
    now = datetime.now()

    for i in range(n):
        if (i + 1) % 100 == 0:
            print(f"  - Generated {i + 1} loans")

        # Company info
        industry = random.choice(list(INDUSTRIES.keys()))
        industry_info = INDUSTRIES[industry]
        company_name = generate_company_name()
        region = random.choice(REGIONS)
        country = random.choice(COUNTRIES[region])

        # Loan details
        loan_id = f"LOAN-{uuid.uuid4().hex[:8].upper()}"
        original_balance = random.uniform(100000, 10000000)

        # Disbursement date
        days_range = (END_DATE - BASE_DATE).days
        random_days = random.randint(0, days_range)
        disbursement_date = BASE_DATE + timedelta(days=random_days)

        # Term and maturity
        term_months = random.choice([12, 24, 36, 48, 60])
        maturity_date = disbursement_date + timedelta(days=term_months * 30)

        # Calculate how much has been paid off
        months_elapsed = max(0, (now - disbursement_date).days // 30)
        months_elapsed = min(months_elapsed, term_months)

        # Interest rate based on risk
        base_rate = 0.04 + industry_info["risk_tier"] * 0.005
        interest_rate = base_rate + random.uniform(-0.01, 0.02)
        interest_rate = max(0.03, min(0.12, interest_rate))

        # Outstanding balance
        if months_elapsed >= term_months:
            outstanding_balance = 0
            status = "paid_off"
        else:
            # Simple amortization
            payment_ratio = months_elapsed / term_months
            outstanding_balance = original_balance * (1 - payment_ratio * 0.9)
            status = "active"

        # PD/LGD scores
        base_pd = industry_info["default_rate"]
        pd_score = base_pd * random.uniform(0.5, 2.0)
        pd_score = max(0.001, min(0.30, pd_score))

        lgd_score = random.uniform(0.30, 0.60)
        risk_grade = pd_to_grade(pd_score)

        # Purpose and collateral
        purpose = random.choice(PURPOSES)
        collateral_type = random.choice(COLLATERAL_TYPES)
        collateral_value = 0 if collateral_type == "unsecured" else original_balance * random.uniform(1.0, 1.5)

        # Default simulation (5% chance for active loans)
        if status == "active" and random.random() < 0.05:
            status = "defaulted"
            days_past_due = random.randint(90, 365)
            payment_status = "default"
        elif status == "active" and random.random() < 0.10:
            days_past_due = random.randint(1, 89)
            payment_status = "delinquent"
        else:
            days_past_due = 0
            payment_status = "current" if status == "active" else "current"

        # Last payment info
        if months_elapsed > 0:
            last_payment_date = disbursement_date + timedelta(days=months_elapsed * 30)
            monthly_payment = original_balance / term_months * (1 + interest_rate / 12)
            last_payment_amount = monthly_payment
        else:
            last_payment_date = None
            last_payment_amount = 0

        # Company financials
        annual_revenue = random.uniform(1000000, 100000000)
        profit_margin = random.uniform(0.02, 0.20)
        net_income = annual_revenue * profit_margin
        total_assets = annual_revenue / random.uniform(0.5, 2.0)
        total_liabilities = total_assets * random.uniform(0.3, 0.7)

        cursor.execute("""
            INSERT INTO loans (
                loan_id, company_name, industry, region, country,
                original_balance, outstanding_balance, interest_rate, term_months,
                purpose, collateral_type, collateral_value,
                disbursement_date, maturity_date,
                last_payment_date, last_payment_amount, days_past_due, payment_status,
                status, pd_score, lgd_score, risk_grade,
                annual_revenue, net_income, total_assets, total_liabilities
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            loan_id, company_name, industry, region, country,
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

        # Generate repayment history
        if months_elapsed > 0:
            generate_repayments(cursor, loan_id, disbursement_date,
                              original_balance, term_months, interest_rate, months_elapsed)

    conn.commit()
    print(f"  [OK] Generated {n} loans")


def generate_repayments(cursor, loan_id: str, disbursement_date: datetime,
                       original_balance: float, term_months: int,
                       interest_rate: float, months_elapsed: int):
    """Generate repayment records for a loan."""
    monthly_principal = original_balance / term_months
    balance = original_balance

    for month in range(min(months_elapsed, term_months)):
        payment_date = disbursement_date + timedelta(days=(month + 1) * 30)
        interest_amount = balance * (interest_rate / 12)
        principal_amount = monthly_principal
        payment_amount = principal_amount + interest_amount
        balance -= principal_amount

        cursor.execute("""
            INSERT INTO repayments (
                loan_id, payment_date, payment_amount,
                principal_amount, interest_amount, balance_after, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            loan_id, payment_date.strftime("%Y-%m-%d"),
            round(payment_amount, 2), round(principal_amount, 2),
            round(interest_amount, 2), round(max(0, balance), 2), "completed"
        ))


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

    cursor.execute("SELECT COUNT(*) FROM loans WHERE status = 'active'")
    active_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM loans WHERE status = 'defaulted'")
    default_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM repayments")
    repayment_count = cursor.fetchone()[0]

    print(f"\n  Loans: {loan_count}")
    print(f"  Total Exposure: ${total_exposure:,.0f}")
    print(f"  Average PD: {avg_pd * 100:.2f}%")
    print(f"  Active Loans: {active_count}")
    print(f"  Defaulted Loans: {default_count}")
    print(f"  Repayment Records: {repayment_count}")

    # By industry
    print("\n  Exposure by Industry:")
    cursor.execute("""
        SELECT industry, SUM(outstanding_balance) as exposure, COUNT(*) as count
        FROM loans GROUP BY industry ORDER BY exposure DESC
    """)
    for row in cursor.fetchall():
        print(f"    - {row[0]}: ${row[1]:,.0f} ({row[2]} loans)")


def main():
    """Main function."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - Portfolio Data Population")
    print("=" * 60)

    db_path = get_db_path()
    print(f"\nDatabase: {db_path}")

    # Ensure data directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))

    try:
        # Create tables
        print("\n[INFO] Creating tables...")
        create_loans_table(conn)
        create_repayments_table(conn)

        # Clear existing data
        cursor = conn.cursor()
        cursor.execute("DELETE FROM repayments")
        cursor.execute("DELETE FROM loans")
        conn.commit()

        # Generate loans
        generate_loans(conn, NUM_LOANS)

        # Print summary
        print_summary(conn)

        print("\n" + "=" * 60)
        print("[SUCCESS] Portfolio data populated!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Start backend: cd 5_backend && python main.py")
        print("  2. Start frontend: cd 6_frontend && npm run dev")

    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    exit(main())
