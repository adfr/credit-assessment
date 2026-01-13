#!/usr/bin/env python3
"""
Load Data to Database Script
Loads generated CSV/Parquet files into SQLite database tables.
Can be adapted for Iceberg tables in production.
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    print("[ERROR] pandas not installed. Run: pip install pandas")
    sys.exit(1)


def get_paths() -> tuple[Path, Path]:
    """Get data and database paths."""
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data" / "synthetic"
    db_path = project_root / "data" / "credit_risk.db"
    return data_dir, db_path


def create_connection(db_path: Path) -> sqlite3.Connection:
    """Create a database connection."""
    if not db_path.exists():
        print(f"[ERROR] Database not found at {db_path}")
        print("Please run 0_setup/create_tables.py first")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_companies(conn: sqlite3.Connection, data_dir: Path):
    """Load companies data into database."""
    print("\n[INFO] Loading companies data...")

    # Read CSV
    df = pd.read_csv(data_dir / "companies.csv")
    print(f"  - Read {len(df)} companies from CSV")

    # Add timestamps
    df["created_at"] = datetime.now().isoformat()
    df["updated_at"] = datetime.now().isoformat()

    # Load to database
    df.to_sql("companies", conn, if_exists="replace", index=False)

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM companies")
    count = cursor.fetchone()[0]
    print(f"  - Loaded {count} companies into database")

    return df


def load_loans(conn: sqlite3.Connection, data_dir: Path):
    """Load loans data into database."""
    print("\n[INFO] Loading loans data...")

    # Read CSV
    df = pd.read_csv(data_dir / "loans.csv")
    print(f"  - Read {len(df)} loans from CSV")

    # Calculate maturity date
    df["origination_date"] = pd.to_datetime(df["origination_date"])
    df["maturity_date"] = df.apply(
        lambda x: (x["origination_date"] + pd.DateOffset(months=x["term_months"])).strftime("%Y-%m-%d"),
        axis=1
    )
    df["origination_date"] = df["origination_date"].dt.strftime("%Y-%m-%d")

    # Add timestamp
    df["created_at"] = datetime.now().isoformat()

    # Load to database
    df.to_sql("loan_history", conn, if_exists="replace", index=False)

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM loan_history")
    count = cursor.fetchone()[0]
    print(f"  - Loaded {count} loans into database")

    # Print statistics
    cursor.execute("SELECT AVG(default_flag) FROM loan_history")
    default_rate = cursor.fetchone()[0]
    print(f"  - Default rate: {default_rate:.2%}")

    return df


def load_bureau_data(conn: sqlite3.Connection, data_dir: Path):
    """Load bureau data into database."""
    print("\n[INFO] Loading bureau data...")

    # Read CSV
    df = pd.read_csv(data_dir / "bureau_data.csv")
    print(f"  - Read {len(df)} bureau records from CSV")

    # Add timestamp
    df["created_at"] = datetime.now().isoformat()

    # Load to database
    df.to_sql("bureau_data", conn, if_exists="replace", index=False)

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bureau_data")
    count = cursor.fetchone()[0]
    print(f"  - Loaded {count} bureau records into database")

    return df


def load_payments(conn: sqlite3.Connection, data_dir: Path):
    """Load payment history into database."""
    print("\n[INFO] Loading payment history...")

    # Read CSV
    df = pd.read_csv(data_dir / "payments.csv")
    print(f"  - Read {len(df)} payment records from CSV")

    # Add timestamp
    df["created_at"] = datetime.now().isoformat()

    # Load to database (in chunks for large datasets)
    chunk_size = 50000
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i + chunk_size]
        if_exists = "replace" if i == 0 else "append"
        chunk.to_sql("payment_history", conn, if_exists=if_exists, index=False)
        print(f"  - Loaded chunk {i // chunk_size + 1} ({len(chunk)} records)")

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM payment_history")
    count = cursor.fetchone()[0]
    print(f"  - Total {count} payment records in database")

    return df


def create_indices(conn: sqlite3.Connection):
    """Create additional indices for common queries."""
    print("\n[INFO] Creating additional indices...")

    indices = [
        ("idx_company_industry", "companies", "industry"),
        ("idx_loan_origination", "loan_history", "origination_date"),
        ("idx_loan_amount", "loan_history", "loan_amount"),
        ("idx_payment_status", "payment_history", "payment_status"),
    ]

    cursor = conn.cursor()
    for idx_name, table, column in indices:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            print(f"  - Created index {idx_name}")
        except sqlite3.Error as e:
            print(f"  - Warning: Could not create index {idx_name}: {e}")

    conn.commit()


def validate_data(conn: sqlite3.Connection):
    """Validate data integrity."""
    print("\n[INFO] Validating data integrity...")

    cursor = conn.cursor()

    # Check foreign key relationships
    cursor.execute("""
        SELECT COUNT(*) FROM loan_history l
        WHERE NOT EXISTS (SELECT 1 FROM companies c WHERE c.company_id = l.company_id)
    """)
    orphan_loans = cursor.fetchone()[0]
    if orphan_loans > 0:
        print(f"  [WARN] Found {orphan_loans} loans without matching companies")
    else:
        print("  [OK] All loans have matching companies")

    cursor.execute("""
        SELECT COUNT(*) FROM payment_history p
        WHERE NOT EXISTS (SELECT 1 FROM loan_history l WHERE l.loan_id = p.loan_id)
    """)
    orphan_payments = cursor.fetchone()[0]
    if orphan_payments > 0:
        print(f"  [WARN] Found {orphan_payments} payments without matching loans")
    else:
        print("  [OK] All payments have matching loans")

    # Check for null values in key fields
    cursor.execute("SELECT COUNT(*) FROM companies WHERE company_id IS NULL")
    null_companies = cursor.fetchone()[0]
    if null_companies > 0:
        print(f"  [WARN] Found {null_companies} companies with null IDs")
    else:
        print("  [OK] No null company IDs")

    cursor.execute("SELECT COUNT(*) FROM loan_history WHERE loan_amount <= 0")
    invalid_amounts = cursor.fetchone()[0]
    if invalid_amounts > 0:
        print(f"  [WARN] Found {invalid_amounts} loans with invalid amounts")
    else:
        print("  [OK] All loan amounts are valid")

    return orphan_loans == 0 and orphan_payments == 0


def print_summary(conn: sqlite3.Connection):
    """Print data loading summary."""
    print("\n" + "=" * 60)
    print("Data Loading Summary")
    print("=" * 60)

    cursor = conn.cursor()

    tables = ["companies", "loan_history", "bureau_data", "payment_history"]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count:,} records")

    # Additional statistics
    cursor.execute("""
        SELECT
            COUNT(*) as total_loans,
            SUM(loan_amount) as total_amount,
            AVG(loan_amount) as avg_amount,
            SUM(default_flag) as defaults,
            AVG(default_flag) as default_rate
        FROM loan_history
    """)
    stats = cursor.fetchone()
    print(f"\nLoan Statistics:")
    print(f"  - Total Loans: {stats[0]:,}")
    print(f"  - Total Amount: ${stats[1]:,.0f}")
    print(f"  - Average Loan: ${stats[2]:,.0f}")
    print(f"  - Defaults: {stats[3]:,}")
    print(f"  - Default Rate: {stats[4]:.2%}")

    cursor.execute("""
        SELECT industry, COUNT(*) as count, AVG(annual_revenue) as avg_revenue
        FROM companies
        GROUP BY industry
        ORDER BY count DESC
    """)
    print("\nCompanies by Industry:")
    for row in cursor.fetchall():
        print(f"  - {row[0]}: {row[1]} companies (avg revenue: ${row[2]:,.0f})")


def main():
    """Main function to load all data into database."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - Data Loading")
    print("=" * 60)

    # Get paths
    data_dir, db_path = get_paths()

    # Check if data exists
    if not data_dir.exists():
        print(f"\n[ERROR] Data directory not found: {data_dir}")
        print("Please run 1_data/generate_synthetic.py first")
        return 1

    required_files = ["companies.csv", "loans.csv", "bureau_data.csv", "payments.csv"]
    for filename in required_files:
        if not (data_dir / filename).exists():
            print(f"\n[ERROR] Required file not found: {filename}")
            print("Please run 1_data/generate_synthetic.py first")
            return 1

    print(f"\nData directory: {data_dir}")
    print(f"Database path: {db_path}")

    # Create connection
    conn = create_connection(db_path)

    try:
        # Load data
        load_companies(conn, data_dir)
        load_loans(conn, data_dir)
        load_bureau_data(conn, data_dir)
        load_payments(conn, data_dir)

        # Create additional indices
        create_indices(conn)

        # Validate data
        is_valid = validate_data(conn)

        # Print summary
        print_summary(conn)

        # Commit all changes
        conn.commit()

        print("\n" + "=" * 60)
        if is_valid:
            print("[SUCCESS] Data loading completed successfully!")
        else:
            print("[WARNING] Data loaded with some integrity issues")
        print("=" * 60)

        print("\nNext steps:")
        print("  1. Run 2_features/feature_pipeline.py to engineer features")
        print("  2. Run 3_models/train_pd_model.py to train PD model")

    except Exception as e:
        print(f"\n[ERROR] Data loading failed: {e}")
        conn.rollback()
        return 1

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    main()
