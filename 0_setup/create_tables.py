#!/usr/bin/env python3
"""
Database Table Creation Script
Creates all required tables for the Credit Risk Platform.
Uses SQLite for demo/development, can be adapted for Iceberg in production.
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime


def get_db_path() -> Path:
    """Get the database file path."""
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "credit_risk.db"


def create_connection(db_path: Path) -> sqlite3.Connection:
    """Create a database connection."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_companies_table(cursor: sqlite3.Cursor):
    """Create companies table for corporate entities."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            company_id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            years_in_business INTEGER,
            employee_count INTEGER,
            annual_revenue REAL,
            net_income REAL,
            total_assets REAL,
            total_liabilities REAL,
            current_ratio REAL,
            quick_ratio REAL,
            debt_to_equity REAL,
            interest_coverage_ratio REAL,
            region TEXT,
            country TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  [OK] companies table created")


def create_loan_history_table(cursor: sqlite3.Cursor):
    """Create loan history table for historical corporate loans."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_history (
            loan_id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            loan_amount REAL NOT NULL,
            interest_rate REAL NOT NULL,
            term_months INTEGER NOT NULL,
            purpose TEXT,
            collateral_type TEXT,
            collateral_value REAL,
            ltv_ratio REAL,
            origination_date DATE NOT NULL,
            maturity_date DATE,
            loan_status TEXT NOT NULL,
            default_flag INTEGER DEFAULT 0,
            days_to_default INTEGER,
            loss_amount REAL,
            recovery_amount REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(company_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_loan_company ON loan_history(company_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_loan_status ON loan_history(loan_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_loan_default ON loan_history(default_flag)")
    print("  [OK] loan_history table created")


def create_payment_history_table(cursor: sqlite3.Cursor):
    """Create payment history table for tracking payments."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_history (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id TEXT NOT NULL,
            payment_date DATE NOT NULL,
            scheduled_amount REAL NOT NULL,
            actual_amount REAL,
            days_past_due INTEGER DEFAULT 0,
            payment_status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES loan_history(loan_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_loan ON payment_history(loan_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_date ON payment_history(payment_date)")
    print("  [OK] payment_history table created")


def create_bureau_data_table(cursor: sqlite3.Cursor):
    """Create credit bureau data table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bureau_data (
            bureau_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            report_date DATE NOT NULL,
            credit_score INTEGER,
            payment_index REAL,
            derogatory_count INTEGER DEFAULT 0,
            years_on_file REAL,
            trade_lines_count INTEGER,
            utilization_rate REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(company_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bureau_company ON bureau_data(company_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bureau_date ON bureau_data(report_date)")
    print("  [OK] bureau_data table created")


def create_model_features_table(cursor: sqlite3.Cursor):
    """Create model features table for engineered features."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_features (
            feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            loan_id TEXT,
            feature_date DATE NOT NULL,

            -- Financial Ratios
            debt_to_equity REAL,
            debt_to_assets REAL,
            current_ratio REAL,
            quick_ratio REAL,
            interest_coverage_ratio REAL,
            return_on_assets REAL,
            return_on_equity REAL,
            revenue_growth_yoy REAL,
            profit_margin REAL,

            -- Bureau Features
            credit_score_normalized REAL,
            payment_index_trend REAL,
            utilization_rate REAL,
            derogatory_ratio REAL,

            -- Behavioral Features
            avg_days_past_due REAL,
            max_days_past_due INTEGER,
            payment_volatility REAL,
            count_30dpd INTEGER DEFAULT 0,
            count_60dpd INTEGER DEFAULT 0,
            count_90dpd INTEGER DEFAULT 0,
            payment_consistency_score REAL,

            -- Loan Features
            loan_to_revenue_ratio REAL,
            loan_to_assets_ratio REAL,
            collateral_coverage_ratio REAL,

            -- Industry Features
            industry_default_rate REAL,
            industry_risk_tier INTEGER,

            -- Target
            default_flag INTEGER,
            lgd REAL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(company_id),
            FOREIGN KEY (loan_id) REFERENCES loan_history(loan_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_company ON model_features(company_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_loan ON model_features(loan_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_date ON model_features(feature_date)")
    print("  [OK] model_features table created")


def create_applications_table(cursor: sqlite3.Cursor):
    """Create applications table for new credit applications."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            application_id TEXT PRIMARY KEY,
            company_id TEXT,
            company_name TEXT NOT NULL,
            industry TEXT,

            -- Loan Request
            requested_amount REAL NOT NULL,
            requested_term_months INTEGER,
            purpose TEXT,
            collateral_type TEXT,
            collateral_value REAL,

            -- Financial Data (from application)
            annual_revenue REAL,
            net_income REAL,
            total_assets REAL,
            total_liabilities REAL,

            -- Application Status
            status TEXT DEFAULT 'pending',
            workflow_id TEXT,
            current_step TEXT,

            -- Documents
            documents_json TEXT,

            -- Timestamps
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            decided_at TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_submitted ON applications(submitted_at)")
    print("  [OK] applications table created")


def create_predictions_table(cursor: sqlite3.Cursor):
    """Create predictions table for model prediction audit trail."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT NOT NULL,
            model_version TEXT NOT NULL,

            -- Risk Scores
            pd_score REAL,
            lgd_score REAL,
            ead REAL,
            expected_loss REAL,
            economic_capital REAL,
            regulatory_capital REAL,
            rorac REAL,

            -- Feature Values (JSON)
            features_json TEXT,

            -- Model Decision
            model_decision TEXT,
            decision_threshold REAL,

            -- Timestamps
            predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (application_id) REFERENCES applications(application_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pred_app ON predictions(application_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pred_date ON predictions(predicted_at)")
    print("  [OK] predictions table created")


def create_workflow_state_table(cursor: sqlite3.Cursor):
    """Create workflow state table for LangGraph checkpoints."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflow_state (
            checkpoint_id TEXT PRIMARY KEY,
            application_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,

            -- State Data (JSON)
            state_json TEXT NOT NULL,

            -- Step Tracking
            current_step TEXT,
            step_history_json TEXT,

            -- Status
            status TEXT DEFAULT 'running',
            error_message TEXT,

            -- Timestamps
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (application_id) REFERENCES applications(application_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wf_app ON workflow_state(application_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wf_thread ON workflow_state(thread_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wf_status ON workflow_state(status)")
    print("  [OK] workflow_state table created")


def create_decisions_table(cursor: sqlite3.Cursor):
    """Create decisions table for final credit decisions."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT NOT NULL UNIQUE,

            -- Decision Details
            final_decision TEXT NOT NULL,
            decision_type TEXT,  -- auto, manual, override
            decision_reason TEXT,
            conditions_json TEXT,

            -- Approver Info
            approved_by TEXT,
            approved_amount REAL,
            approved_rate REAL,
            approved_term_months INTEGER,

            -- Risk Metrics at Decision
            pd_at_decision REAL,
            lgd_at_decision REAL,
            el_at_decision REAL,

            -- Timestamps
            decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (application_id) REFERENCES applications(application_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dec_app ON decisions(application_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dec_decision ON decisions(final_decision)")
    print("  [OK] decisions table created")


def create_analyst_notes_table(cursor: sqlite3.Cursor):
    """Create analyst notes table for review comments."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyst_notes (
            note_id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT NOT NULL,
            analyst_id TEXT,
            note_text TEXT NOT NULL,
            note_type TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES applications(application_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_app ON analyst_notes(application_id)")
    print("  [OK] analyst_notes table created")


def create_monitoring_table(cursor: sqlite3.Cursor):
    """Create monitoring table for drift detection results."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitoring (
            monitoring_id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            monitoring_date DATE NOT NULL,

            -- Drift Metrics
            psi_score REAL,
            csi_scores_json TEXT,

            -- Performance Metrics
            auc_score REAL,
            gini_score REAL,
            ks_statistic REAL,

            -- Counts
            prediction_count INTEGER,
            approval_rate REAL,

            -- Alert Status
            alert_triggered INTEGER DEFAULT 0,
            alert_message TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mon_date ON monitoring(monitoring_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mon_model ON monitoring(model_name)")
    print("  [OK] monitoring table created")


def create_all_tables(conn: sqlite3.Connection):
    """Create all database tables."""
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("Creating database tables...")
    print("="*60 + "\n")

    # Create tables in order (respecting foreign key dependencies)
    create_companies_table(cursor)
    create_loan_history_table(cursor)
    create_payment_history_table(cursor)
    create_bureau_data_table(cursor)
    create_model_features_table(cursor)
    create_applications_table(cursor)
    create_predictions_table(cursor)
    create_workflow_state_table(cursor)
    create_decisions_table(cursor)
    create_analyst_notes_table(cursor)
    create_monitoring_table(cursor)

    conn.commit()


def verify_tables(conn: sqlite3.Connection):
    """Verify all tables were created."""
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    print("\n" + "="*60)
    print("Database Tables Verification")
    print("="*60)
    print(f"\nTotal tables created: {len(tables)}")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  - {table[0]}: {count} rows")


def main():
    """Main function to create all database tables."""
    print("\n" + "="*60)
    print("Credit Risk Platform - Database Setup")
    print("="*60)

    db_path = get_db_path()
    print(f"\nDatabase path: {db_path}")

    # Create connection
    conn = create_connection(db_path)

    try:
        # Create all tables
        create_all_tables(conn)

        # Verify tables
        verify_tables(conn)

        print("\n" + "="*60)
        print("[SUCCESS] Database setup completed successfully!")
        print("="*60)
        print(f"\nDatabase file: {db_path}")
        print("Next steps:")
        print("  1. Run 0_setup/setup_vector_store.py to initialize ChromaDB")
        print("  2. Run 1_data/generate_synthetic.py to generate sample data")

    except Exception as e:
        print(f"\n[ERROR] Database setup failed: {e}")
        return 1

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    exit(main())
