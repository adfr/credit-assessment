#!/usr/bin/env python3
"""
Synthetic Data Generation Script
Generates realistic corporate loan data for the Credit Risk Platform.
"""

import os
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import math

try:
    import pandas as pd
    import numpy as np
    from faker import Faker
except ImportError as e:
    print(f"[ERROR] Missing required package: {e}")
    print("Run: pip install pandas numpy faker")
    sys.exit(1)

# Initialize Faker
fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

# Configuration
NUM_COMPANIES = 5000
NUM_LOANS = 10000
BASE_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2024, 12, 31)

# Industry definitions with risk characteristics
INDUSTRIES = {
    "technology": {"default_rate": 0.03, "risk_tier": 2, "revenue_range": (1e6, 500e6)},
    "healthcare": {"default_rate": 0.025, "risk_tier": 1, "revenue_range": (5e6, 1e9)},
    "manufacturing": {"default_rate": 0.04, "risk_tier": 3, "revenue_range": (10e6, 2e9)},
    "retail": {"default_rate": 0.06, "risk_tier": 4, "revenue_range": (2e6, 500e6)},
    "financial_services": {"default_rate": 0.02, "risk_tier": 1, "revenue_range": (10e6, 5e9)},
    "energy": {"default_rate": 0.05, "risk_tier": 4, "revenue_range": (50e6, 10e9)},
    "construction": {"default_rate": 0.07, "risk_tier": 5, "revenue_range": (5e6, 500e6)},
    "transportation": {"default_rate": 0.045, "risk_tier": 3, "revenue_range": (10e6, 1e9)},
    "hospitality": {"default_rate": 0.08, "risk_tier": 5, "revenue_range": (1e6, 200e6)},
    "professional_services": {"default_rate": 0.025, "risk_tier": 2, "revenue_range": (500e3, 100e6)},
}

LOAN_PURPOSES = [
    "working_capital",
    "expansion",
    "equipment",
    "acquisition",
    "refinancing",
    "real_estate",
]

COLLATERAL_TYPES = [
    "real_estate",
    "equipment",
    "inventory",
    "receivables",
    "securities",
    "unsecured",
]

REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America"]

COUNTRIES = {
    "North America": ["United States", "Canada"],
    "Europe": ["United Kingdom", "Germany", "France", "Netherlands", "Switzerland"],
    "Asia Pacific": ["Japan", "Australia", "Singapore", "Hong Kong"],
    "Latin America": ["Brazil", "Mexico", "Chile"],
}


def generate_company_name() -> str:
    """Generate a realistic company name."""
    patterns = [
        lambda: f"{fake.last_name()} {fake.company_suffix()}",
        lambda: f"{fake.last_name()} & {fake.last_name()} {fake.company_suffix()}",
        lambda: f"{fake.word().title()}{fake.word().title()} {fake.company_suffix()}",
        lambda: fake.company(),
    ]
    return random.choice(patterns)()


def generate_companies(n: int) -> pd.DataFrame:
    """Generate synthetic company data."""
    print(f"\n[INFO] Generating {n} companies...")

    companies = []
    for i in range(n):
        if (i + 1) % 1000 == 0:
            print(f"  - Generated {i + 1} companies")

        industry = random.choice(list(INDUSTRIES.keys()))
        industry_info = INDUSTRIES[industry]

        # Generate financial data with realistic correlations
        annual_revenue = np.random.uniform(*industry_info["revenue_range"])
        years_in_business = random.randint(1, 50)

        # Larger, older companies tend to have better financials
        maturity_factor = min(1.0, years_in_business / 20)
        size_factor = min(1.0, annual_revenue / 100e6)

        # Profit margin influenced by industry and maturity
        base_margin = random.uniform(0.02, 0.15)
        profit_margin = base_margin * (0.8 + 0.4 * maturity_factor)
        net_income = annual_revenue * profit_margin

        # Assets and liabilities
        asset_turnover = random.uniform(0.5, 2.0)
        total_assets = annual_revenue / asset_turnover

        # Leverage - younger/smaller companies tend to have more debt
        base_leverage = random.uniform(0.3, 0.7)
        leverage = base_leverage * (1.2 - 0.4 * maturity_factor)
        total_liabilities = total_assets * leverage

        # Liquidity ratios
        current_ratio = random.uniform(0.8, 3.0) * (1 + 0.3 * maturity_factor)
        quick_ratio = current_ratio * random.uniform(0.5, 0.9)

        # Calculate derived ratios
        equity = total_assets - total_liabilities
        debt_to_equity = total_liabilities / max(equity, 1)

        # Interest coverage - correlated with profitability
        interest_expense = total_liabilities * random.uniform(0.03, 0.08)
        ebit = net_income + interest_expense * random.uniform(0.8, 1.2)
        interest_coverage = ebit / max(interest_expense, 1)

        # Region and country
        region = random.choice(REGIONS)
        country = random.choice(COUNTRIES[region])

        # Employee count based on revenue
        employees_per_million = random.uniform(1, 10)
        employee_count = int(annual_revenue / 1e6 * employees_per_million)
        employee_count = max(5, min(employee_count, 100000))

        company = {
            "company_id": f"COMP_{i+1:06d}",
            "company_name": generate_company_name(),
            "industry": industry,
            "years_in_business": years_in_business,
            "employee_count": employee_count,
            "annual_revenue": round(annual_revenue, 2),
            "net_income": round(net_income, 2),
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "current_ratio": round(current_ratio, 4),
            "quick_ratio": round(quick_ratio, 4),
            "debt_to_equity": round(debt_to_equity, 4),
            "interest_coverage_ratio": round(interest_coverage, 4),
            "region": region,
            "country": country,
        }
        companies.append(company)

    return pd.DataFrame(companies)


def calculate_default_probability(
    company: dict, loan: dict, bureau: dict, economic_stress: float = 0.0
) -> float:
    """Calculate probability of default based on risk factors."""
    industry_rate = INDUSTRIES[company["industry"]]["default_rate"]

    # Base PD from industry
    pd = industry_rate

    # Financial health adjustments
    if company["debt_to_equity"] > 3:
        pd += 0.03
    elif company["debt_to_equity"] > 2:
        pd += 0.015
    elif company["debt_to_equity"] < 1:
        pd -= 0.01

    if company["interest_coverage_ratio"] < 1.5:
        pd += 0.04
    elif company["interest_coverage_ratio"] < 2.5:
        pd += 0.02
    elif company["interest_coverage_ratio"] > 5:
        pd -= 0.01

    if company["current_ratio"] < 1.0:
        pd += 0.02
    elif company["current_ratio"] > 2.0:
        pd -= 0.005

    # Age factor
    if company["years_in_business"] < 3:
        pd += 0.03
    elif company["years_in_business"] < 5:
        pd += 0.015
    elif company["years_in_business"] > 20:
        pd -= 0.01

    # Bureau score impact
    if bureau["credit_score"] < 50:
        pd += 0.04
    elif bureau["credit_score"] < 60:
        pd += 0.02
    elif bureau["credit_score"] > 80:
        pd -= 0.015

    # Derogatory marks
    pd += bureau["derogatory_count"] * 0.01

    # Loan characteristics
    loan_to_revenue = loan["loan_amount"] / max(company["annual_revenue"], 1)
    if loan_to_revenue > 0.5:
        pd += 0.02
    elif loan_to_revenue > 0.3:
        pd += 0.01

    # LTV impact
    if loan["ltv_ratio"] and loan["ltv_ratio"] > 0.9:
        pd += 0.02
    elif loan["ltv_ratio"] and loan["ltv_ratio"] > 0.8:
        pd += 0.01

    # Economic stress factor (simulate recession)
    pd += economic_stress * 0.05

    # Ensure PD is within bounds
    return max(0.001, min(0.50, pd))


def generate_loans(companies_df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Generate synthetic loan data."""
    print(f"\n[INFO] Generating {n} loans...")

    loans = []
    company_ids = companies_df["company_id"].tolist()

    for i in range(n):
        if (i + 1) % 2000 == 0:
            print(f"  - Generated {i + 1} loans")

        company_id = random.choice(company_ids)
        company = companies_df[companies_df["company_id"] == company_id].iloc[0].to_dict()

        # Loan amount based on company size (1% to 30% of revenue)
        loan_pct = random.uniform(0.01, 0.30)
        loan_amount = company["annual_revenue"] * loan_pct
        loan_amount = max(100000, min(loan_amount, 50000000))  # $100K to $50M

        # Interest rate based on risk
        base_rate = 0.05  # 5% base
        risk_premium = INDUSTRIES[company["industry"]]["risk_tier"] * 0.005
        interest_rate = base_rate + risk_premium + random.uniform(-0.01, 0.02)
        interest_rate = max(0.03, min(0.15, interest_rate))

        # Term
        term_months = random.choice([12, 24, 36, 48, 60])

        # Purpose
        purpose = random.choice(LOAN_PURPOSES)

        # Collateral
        collateral_type = random.choice(COLLATERAL_TYPES)
        if collateral_type == "unsecured":
            collateral_value = 0
            ltv_ratio = None
        else:
            coverage = random.uniform(1.1, 2.0)
            collateral_value = loan_amount * coverage
            ltv_ratio = loan_amount / collateral_value

        # Origination date
        days_range = (END_DATE - BASE_DATE).days
        random_days = random.randint(0, days_range)
        origination_date = BASE_DATE + timedelta(days=random_days)

        loan = {
            "loan_id": f"LOAN_{i+1:06d}",
            "company_id": company_id,
            "loan_amount": round(loan_amount, 2),
            "interest_rate": round(interest_rate, 4),
            "term_months": term_months,
            "purpose": purpose,
            "collateral_type": collateral_type,
            "collateral_value": round(collateral_value, 2),
            "ltv_ratio": round(ltv_ratio, 4) if ltv_ratio else None,
            "origination_date": origination_date.strftime("%Y-%m-%d"),
        }
        loans.append(loan)

    return pd.DataFrame(loans)


def generate_bureau_data(companies_df: pd.DataFrame) -> pd.DataFrame:
    """Generate credit bureau data for companies."""
    print(f"\n[INFO] Generating bureau data...")

    bureau_records = []
    for _, company in companies_df.iterrows():
        # Generate 1-3 bureau reports per company
        num_reports = random.randint(1, 3)
        base_score = random.randint(40, 95)

        for j in range(num_reports):
            # Score changes slightly over time
            score_change = random.randint(-5, 5)
            credit_score = max(0, min(100, base_score + score_change))

            # Report date
            report_date = BASE_DATE + timedelta(days=random.randint(0, (END_DATE - BASE_DATE).days))

            # Payment index (0-100, higher is better)
            payment_index = random.uniform(60, 100) if credit_score > 60 else random.uniform(30, 80)

            # Derogatory marks
            if credit_score > 80:
                derogatory_count = 0 if random.random() > 0.1 else random.randint(1, 2)
            elif credit_score > 60:
                derogatory_count = random.randint(0, 3)
            else:
                derogatory_count = random.randint(1, 5)

            record = {
                "company_id": company["company_id"],
                "report_date": report_date.strftime("%Y-%m-%d"),
                "credit_score": credit_score,
                "payment_index": round(payment_index, 2),
                "derogatory_count": derogatory_count,
                "years_on_file": random.uniform(1, min(20, company["years_in_business"])),
                "trade_lines_count": random.randint(3, 50),
                "utilization_rate": round(random.uniform(0.1, 0.9), 4),
            }
            bureau_records.append(record)

    return pd.DataFrame(bureau_records)


def simulate_loan_outcomes(
    loans_df: pd.DataFrame, companies_df: pd.DataFrame, bureau_df: pd.DataFrame
) -> pd.DataFrame:
    """Simulate loan outcomes (default/paid off) with realistic patterns."""
    print("\n[INFO] Simulating loan outcomes...")

    loans_df = loans_df.copy()
    loans_df["loan_status"] = "current"
    loans_df["default_flag"] = 0
    loans_df["days_to_default"] = None
    loans_df["loss_amount"] = None
    loans_df["recovery_amount"] = None

    # Economic stress periods (simulate recession 2022-2023)
    recession_start = datetime(2022, 6, 1)
    recession_end = datetime(2023, 12, 31)

    for idx, loan in loans_df.iterrows():
        company = companies_df[companies_df["company_id"] == loan["company_id"]].iloc[0].to_dict()

        # Get most recent bureau data
        company_bureau = bureau_df[bureau_df["company_id"] == loan["company_id"]]
        if len(company_bureau) > 0:
            bureau = company_bureau.sort_values("report_date").iloc[-1].to_dict()
        else:
            bureau = {"credit_score": 70, "derogatory_count": 0}

        # Check if loan was during recession
        orig_date = datetime.strptime(loan["origination_date"], "%Y-%m-%d")
        economic_stress = 1.0 if recession_start <= orig_date <= recession_end else 0.0

        # Calculate default probability
        pd_value = calculate_default_probability(company, loan, bureau, economic_stress)

        # Determine if loan defaulted
        if random.random() < pd_value:
            loans_df.at[idx, "default_flag"] = 1
            loans_df.at[idx, "loan_status"] = "default"

            # Days to default (weighted toward earlier in term)
            max_days = loan["term_months"] * 30
            days_to_default = int(np.random.exponential(max_days / 3))
            days_to_default = min(days_to_default, max_days)
            loans_df.at[idx, "days_to_default"] = days_to_default

            # Loss amount based on collateral
            if loan["collateral_type"] == "unsecured":
                lgd = random.uniform(0.6, 0.9)
            elif loan["collateral_type"] == "real_estate":
                lgd = random.uniform(0.2, 0.4)
            elif loan["collateral_type"] in ["equipment", "securities"]:
                lgd = random.uniform(0.3, 0.5)
            else:
                lgd = random.uniform(0.4, 0.7)

            loss_amount = loan["loan_amount"] * lgd
            recovery_amount = loan["loan_amount"] - loss_amount

            loans_df.at[idx, "loss_amount"] = round(loss_amount, 2)
            loans_df.at[idx, "recovery_amount"] = round(recovery_amount, 2)
        else:
            # Non-defaulted loans
            term_end = orig_date + timedelta(days=loan["term_months"] * 30)
            if term_end < datetime.now():
                loans_df.at[idx, "loan_status"] = "paid_off"
            elif random.random() < 0.02:
                loans_df.at[idx, "loan_status"] = "restructured"

    # Calculate statistics
    default_rate = loans_df["default_flag"].mean()
    print(f"  - Overall default rate: {default_rate:.2%}")

    return loans_df


def generate_payment_history(loans_df: pd.DataFrame) -> pd.DataFrame:
    """Generate payment history for loans."""
    print("\n[INFO] Generating payment history...")

    payments = []
    for idx, loan in loans_df.iterrows():
        if (idx + 1) % 2000 == 0:
            print(f"  - Processed {idx + 1} loans")

        orig_date = datetime.strptime(loan["origination_date"], "%Y-%m-%d")
        term_months = loan["term_months"]
        monthly_payment = loan["loan_amount"] / term_months

        # Determine number of payments based on status
        if loan["loan_status"] == "default":
            num_payments = loan["days_to_default"] // 30
        elif loan["loan_status"] == "paid_off":
            num_payments = term_months
        else:
            # Current loan - payments up to now
            months_elapsed = (datetime.now() - orig_date).days // 30
            num_payments = min(months_elapsed, term_months)

        # Generate payments
        for month in range(num_payments):
            payment_date = orig_date + timedelta(days=(month + 1) * 30)

            # Determine payment behavior
            if loan["default_flag"] == 1 and month >= num_payments - 3:
                # Payments deteriorate before default
                if month == num_payments - 1:
                    actual_amount = 0
                    days_past_due = random.randint(90, 180)
                    payment_status = "missed"
                else:
                    actual_amount = monthly_payment * random.uniform(0.3, 0.8)
                    days_past_due = random.randint(30, 90)
                    payment_status = "partial"
            else:
                # Normal payment behavior
                if random.random() < 0.95:
                    actual_amount = monthly_payment
                    days_past_due = 0
                    payment_status = "on_time"
                elif random.random() < 0.7:
                    actual_amount = monthly_payment
                    days_past_due = random.randint(1, 30)
                    payment_status = "late"
                else:
                    actual_amount = monthly_payment * random.uniform(0.5, 0.99)
                    days_past_due = random.randint(30, 60)
                    payment_status = "partial"

            payment = {
                "loan_id": loan["loan_id"],
                "payment_date": payment_date.strftime("%Y-%m-%d"),
                "scheduled_amount": round(monthly_payment, 2),
                "actual_amount": round(actual_amount, 2),
                "days_past_due": days_past_due,
                "payment_status": payment_status,
            }
            payments.append(payment)

    return pd.DataFrame(payments)


def save_data(
    companies_df: pd.DataFrame,
    loans_df: pd.DataFrame,
    bureau_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    output_dir: Path,
):
    """Save all generated data to CSV and Parquet files."""
    print("\n[INFO] Saving data...")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as CSV
    companies_df.to_csv(output_dir / "companies.csv", index=False)
    loans_df.to_csv(output_dir / "loans.csv", index=False)
    bureau_df.to_csv(output_dir / "bureau_data.csv", index=False)
    payments_df.to_csv(output_dir / "payments.csv", index=False)

    print(f"  - Saved CSV files to {output_dir}")

    # Save as Parquet
    companies_df.to_parquet(output_dir / "companies.parquet", index=False)
    loans_df.to_parquet(output_dir / "loans.parquet", index=False)
    bureau_df.to_parquet(output_dir / "bureau_data.parquet", index=False)
    payments_df.to_parquet(output_dir / "payments.parquet", index=False)

    print(f"  - Saved Parquet files to {output_dir}")


def print_summary(
    companies_df: pd.DataFrame,
    loans_df: pd.DataFrame,
    bureau_df: pd.DataFrame,
    payments_df: pd.DataFrame,
):
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("Data Generation Summary")
    print("=" * 60)

    print(f"\nCompanies: {len(companies_df):,}")
    print(f"  - Industries: {companies_df['industry'].nunique()}")
    print(f"  - Regions: {companies_df['region'].nunique()}")
    print(f"  - Avg Revenue: ${companies_df['annual_revenue'].mean():,.0f}")

    print(f"\nLoans: {len(loans_df):,}")
    print(f"  - Total Amount: ${loans_df['loan_amount'].sum():,.0f}")
    print(f"  - Avg Amount: ${loans_df['loan_amount'].mean():,.0f}")
    print(f"  - Default Rate: {loans_df['default_flag'].mean():.2%}")

    print("\nDefault Rate by Industry:")
    industry_defaults = (
        loans_df.merge(companies_df[["company_id", "industry"]], on="company_id")
        .groupby("industry")["default_flag"]
        .mean()
        .sort_values(ascending=False)
    )
    for industry, rate in industry_defaults.items():
        print(f"  - {industry}: {rate:.2%}")

    print(f"\nBureau Records: {len(bureau_df):,}")
    print(f"  - Avg Credit Score: {bureau_df['credit_score'].mean():.1f}")

    print(f"\nPayment Records: {len(payments_df):,}")
    print(
        f"  - On-time Rate: {(payments_df['payment_status'] == 'on_time').mean():.2%}"
    )


def main():
    """Main function to generate all synthetic data."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - Synthetic Data Generation")
    print("=" * 60)

    # Output directory
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "data" / "synthetic"

    # Generate data
    companies_df = generate_companies(NUM_COMPANIES)
    loans_df = generate_loans(companies_df, NUM_LOANS)
    bureau_df = generate_bureau_data(companies_df)
    loans_df = simulate_loan_outcomes(loans_df, companies_df, bureau_df)
    payments_df = generate_payment_history(loans_df)

    # Save data
    save_data(companies_df, loans_df, bureau_df, payments_df, output_dir)

    # Print summary
    print_summary(companies_df, loans_df, bureau_df, payments_df)

    print("\n" + "=" * 60)
    print("[SUCCESS] Synthetic data generation completed!")
    print("=" * 60)
    print(f"\nOutput directory: {output_dir}")
    print("\nNext steps:")
    print("  1. Run 1_data/load_to_iceberg.py to load data into database")
    print("  2. Run 2_features/feature_pipeline.py to engineer features")

    return 0


if __name__ == "__main__":
    main()
