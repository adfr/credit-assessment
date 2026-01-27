"""
Seed Portfolio Data Script
Generates synthetic loan portfolio data for the risk management platform.
"""

import sqlite3
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import math

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "credit_risk.db"

# Industry distribution
INDUSTRIES = [
    ("manufacturing", 0.20),
    ("technology", 0.15),
    ("healthcare", 0.15),
    ("retail", 0.12),
    ("construction", 0.10),
    ("services", 0.10),
    ("energy", 0.08),
    ("transportation", 0.05),
    ("hospitality", 0.05),
]

# Region distribution
REGIONS = [
    ("North America", ["USA", "Canada", "Mexico"], 0.40),
    ("Europe", ["UK", "Germany", "France", "Netherlands"], 0.30),
    ("Asia Pacific", ["Japan", "Australia", "Singapore", "South Korea"], 0.20),
    ("Latin America", ["Brazil", "Chile", "Colombia"], 0.10),
]

# Risk grade distribution and PD ranges
RISK_GRADES = [
    ("AAA", 0.001, 0.005, 0.05),   # grade, pd_min, pd_max, weight
    ("AA", 0.005, 0.01, 0.10),
    ("A", 0.01, 0.03, 0.20),
    ("BBB", 0.03, 0.05, 0.25),
    ("BB", 0.05, 0.10, 0.20),
    ("B", 0.10, 0.15, 0.12),
    ("CCC", 0.15, 0.30, 0.08),
]

# Collateral types with LGD assumptions
COLLATERAL_TYPES = [
    ("real_estate", 0.35, 0.25),    # type, lgd, weight
    ("equipment", 0.45, 0.20),
    ("inventory", 0.55, 0.15),
    ("receivables", 0.50, 0.15),
    ("securities", 0.40, 0.10),
    ("unsecured", 0.75, 0.15),
]

# Loan purposes
PURPOSES = ["working_capital", "expansion", "equipment", "acquisition", "refinancing", "real_estate"]

# Payment status distribution
PAYMENT_STATUS = [
    ("current", 0.70),
    ("delinquent", 0.20),
    ("default", 0.10),
]

# Real companies by industry (S&P 500 and major public companies)
REAL_COMPANIES = {
    "manufacturing": [
        ("Caterpillar Inc.", "CAT"), ("Deere & Company", "DE"), ("3M Company", "MMM"),
        ("Honeywell International", "HON"), ("General Electric", "GE"), ("Illinois Tool Works", "ITW"),
        ("Emerson Electric", "EMR"), ("Parker-Hannifin", "PH"), ("Rockwell Automation", "ROK"),
        ("Stanley Black & Decker", "SWK"), ("Dover Corporation", "DOV"), ("Fortive Corporation", "FTV"),
        ("PACCAR Inc.", "PCAR"), ("Cummins Inc.", "CMI"), ("Eaton Corporation", "ETN"),
        ("Boeing Company", "BA"), ("Lockheed Martin", "LMT"), ("Raytheon Technologies", "RTX"),
        ("General Dynamics", "GD"), ("Northrop Grumman", "NOC"),
    ],
    "technology": [
        ("Apple Inc.", "AAPL"), ("Microsoft Corporation", "MSFT"), ("Alphabet Inc.", "GOOGL"),
        ("Amazon.com Inc.", "AMZN"), ("Meta Platforms Inc.", "META"), ("NVIDIA Corporation", "NVDA"),
        ("Tesla Inc.", "TSLA"), ("Adobe Inc.", "ADBE"), ("Salesforce Inc.", "CRM"),
        ("Intel Corporation", "INTC"), ("Cisco Systems Inc.", "CSCO"), ("Oracle Corporation", "ORCL"),
        ("IBM Corporation", "IBM"), ("Qualcomm Inc.", "QCOM"), ("AMD Inc.", "AMD"),
        ("ServiceNow Inc.", "NOW"), ("Palantir Technologies", "PLTR"), ("CrowdStrike Holdings", "CRWD"),
        ("Palo Alto Networks", "PANW"), ("Snowflake Inc.", "SNOW"),
    ],
    "healthcare": [
        ("Johnson & Johnson", "JNJ"), ("UnitedHealth Group", "UNH"), ("Pfizer Inc.", "PFE"),
        ("Eli Lilly and Company", "LLY"), ("AbbVie Inc.", "ABBV"), ("Merck & Co.", "MRK"),
        ("Thermo Fisher Scientific", "TMO"), ("Abbott Laboratories", "ABT"), ("Danaher Corporation", "DHR"),
        ("Bristol-Myers Squibb", "BMY"), ("Amgen Inc.", "AMGN"), ("Gilead Sciences", "GILD"),
        ("Moderna Inc.", "MRNA"), ("CVS Health Corporation", "CVS"), ("Cigna Group", "CI"),
        ("Humana Inc.", "HUM"), ("HCA Healthcare", "HCA"), ("Medtronic plc", "MDT"),
        ("Boston Scientific", "BSX"), ("Stryker Corporation", "SYK"),
    ],
    "retail": [
        ("Walmart Inc.", "WMT"), ("Costco Wholesale", "COST"), ("Target Corporation", "TGT"),
        ("Home Depot", "HD"), ("Lowe's Companies", "LOW"), ("TJX Companies", "TJX"),
        ("Ross Stores", "ROST"), ("Dollar General", "DG"), ("Dollar Tree", "DLTR"),
        ("Best Buy Co.", "BBY"), ("AutoZone Inc.", "AZO"), ("O'Reilly Automotive", "ORLY"),
        ("Ulta Beauty", "ULTA"), ("Gap Inc.", "GPS"), ("Nordstrom Inc.", "JWN"),
        ("Macy's Inc.", "M"), ("Dick's Sporting Goods", "DKS"), ("Tractor Supply", "TSCO"),
        ("Williams-Sonoma", "WSM"), ("Etsy Inc.", "ETSY"),
    ],
    "construction": [
        ("D.R. Horton", "DHI"), ("Lennar Corporation", "LEN"), ("PulteGroup Inc.", "PHM"),
        ("NVR Inc.", "NVR"), ("Toll Brothers", "TOL"), ("Meritage Homes", "MTH"),
        ("KB Home", "KBH"), ("Jacobs Engineering", "J"), ("AECOM", "ACM"),
        ("Quanta Services", "PWR"), ("EMCOR Group", "EME"), ("MasTec Inc.", "MTZ"),
        ("Martin Marietta", "MLM"), ("Vulcan Materials", "VMC"), ("Eagle Materials", "EXP"),
        ("Builders FirstSource", "BLDR"), ("Owens Corning", "OC"), ("Masco Corporation", "MAS"),
        ("Trex Company", "TREX"), ("UFP Industries", "UFPI"),
    ],
    "services": [
        ("Accenture plc", "ACN"), ("Cognizant Technology", "CTSH"), ("Automatic Data Processing", "ADP"),
        ("Robert Half International", "RHI"), ("ManpowerGroup", "MAN"), ("Booz Allen Hamilton", "BAH"),
        ("Leidos Holdings", "LDOS"), ("Gartner Inc.", "IT"), ("Verisk Analytics", "VRSK"),
        ("Equifax Inc.", "EFX"), ("TransUnion", "TRU"), ("Dun & Bradstreet", "DNB"),
        ("FactSet Research", "FDS"), ("CoStar Group", "CSGP"), ("Cintas Corporation", "CTAS"),
        ("Waste Management", "WM"), ("Republic Services", "RSG"), ("Rollins Inc.", "ROL"),
        ("Iron Mountain", "IRM"), ("Paychex Inc.", "PAYX"),
    ],
    "energy": [
        ("Exxon Mobil", "XOM"), ("Chevron Corporation", "CVX"), ("ConocoPhillips", "COP"),
        ("EOG Resources", "EOG"), ("Schlumberger Limited", "SLB"), ("Pioneer Natural Resources", "PXD"),
        ("Phillips 66", "PSX"), ("Valero Energy", "VLO"), ("Marathon Petroleum", "MPC"),
        ("Occidental Petroleum", "OXY"), ("Devon Energy", "DVN"), ("Diamondback Energy", "FANG"),
        ("NextEra Energy", "NEE"), ("Duke Energy", "DUK"), ("Southern Company", "SO"),
        ("Dominion Energy", "D"), ("Kinder Morgan", "KMI"), ("Williams Companies", "WMB"),
        ("Baker Hughes", "BKR"), ("Halliburton Company", "HAL"),
    ],
    "transportation": [
        ("Union Pacific", "UNP"), ("CSX Corporation", "CSX"), ("Norfolk Southern", "NSC"),
        ("FedEx Corporation", "FDX"), ("United Parcel Service", "UPS"), ("XPO Logistics", "XPO"),
        ("J.B. Hunt Transport", "JBHT"), ("Old Dominion Freight", "ODFL"), ("Delta Air Lines", "DAL"),
        ("United Airlines", "UAL"), ("American Airlines", "AAL"), ("Southwest Airlines", "LUV"),
        ("Uber Technologies", "UBER"), ("Lyft Inc.", "LYFT"), ("Ryder System", "R"),
        ("Avis Budget Group", "CAR"), ("GATX Corporation", "GATX"), ("Landstar System", "LSTR"),
        ("Knight-Swift Transportation", "KNX"), ("Werner Enterprises", "WERN"),
    ],
    "hospitality": [
        ("Marriott International", "MAR"), ("Hilton Worldwide", "HLT"), ("Hyatt Hotels", "H"),
        ("Wyndham Hotels", "WH"), ("Choice Hotels", "CHH"), ("McDonald's Corporation", "MCD"),
        ("Starbucks Corporation", "SBUX"), ("Yum! Brands", "YUM"), ("Chipotle Mexican Grill", "CMG"),
        ("Domino's Pizza", "DPZ"), ("Darden Restaurants", "DRI"), ("Wendy's Company", "WEN"),
        ("Texas Roadhouse", "TXRH"), ("Carnival Corporation", "CCL"), ("Royal Caribbean", "RCL"),
        ("Norwegian Cruise Line", "NCLH"), ("Vail Resorts", "MTN"), ("Live Nation Entertainment", "LYV"),
        ("Six Flags Entertainment", "SIX"), ("Cedar Fair", "FUN"),
    ],
}

# Track used companies to avoid duplicates in the same seeding run
_used_companies = set()


def weighted_choice(choices):
    """Select item based on weights."""
    items = [c[0] if isinstance(c[0], str) else c[:-1] for c in choices]
    weights = [c[-1] for c in choices]
    return random.choices(items, weights=weights, k=1)[0]


def generate_company_name(industry: str) -> tuple:
    """Get a real company name and ticker for the given industry."""
    global _used_companies

    # Get available companies for this industry
    available = [c for c in REAL_COMPANIES.get(industry, []) if c[0] not in _used_companies]

    if available:
        company = random.choice(available)
        _used_companies.add(company[0])
        return company  # (name, ticker)
    else:
        # If all real companies used, reuse with a slight variation
        base_company = random.choice(REAL_COMPANIES.get(industry, [("Unknown Corp", "UNK")]))
        return (base_company[0], base_company[1])


def generate_loan():
    """Generate a single synthetic loan."""
    loan_id = f"LOAN-{uuid.uuid4().hex[:8].upper()}"

    # Industry first (needed for company selection)
    industry = weighted_choice(INDUSTRIES)

    # Company info - get real company name and ticker
    company_name, ticker = generate_company_name(industry)

    # Geography
    region_data = weighted_choice(REGIONS)
    if isinstance(region_data, tuple):
        region, countries, _ = region_data
    else:
        region = region_data
        countries = ["USA"]
    country = random.choice(countries)

    # Risk profile
    risk_grade_data = weighted_choice(RISK_GRADES)
    if isinstance(risk_grade_data, tuple):
        risk_grade, pd_min, pd_max, _ = risk_grade_data
    else:
        risk_grade, pd_min, pd_max = "BBB", 0.03, 0.05

    pd_score = round(random.uniform(pd_min, pd_max), 4)

    # Collateral
    collateral_data = weighted_choice(COLLATERAL_TYPES)
    if isinstance(collateral_data, tuple):
        collateral_type, base_lgd, _ = collateral_data
    else:
        collateral_type, base_lgd = "unsecured", 0.75

    lgd_score = round(base_lgd * random.uniform(0.85, 1.15), 4)  # +/- 15% variance

    # Loan amount (500K to 25M, log-normal distribution)
    original_balance = round(random.lognormvariate(15.5, 0.8), -3)  # Mean ~$5M
    original_balance = max(500000, min(25000000, original_balance))

    # Payment status
    payment_status = weighted_choice(PAYMENT_STATUS)

    # Outstanding balance based on payment status
    if payment_status == "current":
        # 20-80% repaid
        outstanding_balance = round(original_balance * random.uniform(0.2, 0.8), -3)
        days_past_due = 0
    elif payment_status == "delinquent":
        # 40-90% still outstanding
        outstanding_balance = round(original_balance * random.uniform(0.4, 0.9), -3)
        days_past_due = random.randint(30, 90)
    else:  # default
        # 60-100% outstanding
        outstanding_balance = round(original_balance * random.uniform(0.6, 1.0), -3)
        days_past_due = random.randint(90, 365)

    # Dates
    disbursement_date = datetime.now() - timedelta(days=random.randint(180, 1800))
    term_months = random.choice([12, 24, 36, 48, 60, 72, 84, 96, 120])
    maturity_date = disbursement_date + timedelta(days=term_months * 30)

    # Last payment
    if payment_status == "current":
        last_payment_date = datetime.now() - timedelta(days=random.randint(1, 30))
        last_payment_amount = round(original_balance / term_months * random.uniform(0.9, 1.1), 2)
    elif payment_status == "delinquent":
        last_payment_date = datetime.now() - timedelta(days=random.randint(30, 90))
        last_payment_amount = round(original_balance / term_months * random.uniform(0.5, 1.0), 2)
    else:
        last_payment_date = datetime.now() - timedelta(days=random.randint(90, 365))
        last_payment_amount = round(original_balance / term_months * random.uniform(0.2, 0.5), 2)

    # Collateral value
    if collateral_type == "unsecured":
        collateral_value = 0
    else:
        # LTV between 60-120%
        ltv = random.uniform(0.6, 1.2)
        collateral_value = round(original_balance / ltv, -3)

    # Interest rate based on risk grade
    base_rate = 0.05  # 5% base
    risk_premium = pd_score * 2  # 2x PD as premium
    interest_rate = round(base_rate + risk_premium + random.uniform(-0.01, 0.02), 4)

    # Financial metrics
    annual_revenue = round(original_balance * random.uniform(2, 10), -3)
    net_income = round(annual_revenue * random.uniform(0.02, 0.15), -3)
    total_assets = round(annual_revenue * random.uniform(0.8, 2.0), -3)
    total_liabilities = round(total_assets * random.uniform(0.3, 0.7), -3)

    # Loan status
    if payment_status == "default":
        status = "defaulted"
    elif maturity_date < datetime.now():
        status = "paid_off" if random.random() > 0.3 else "defaulted"
    else:
        status = "active"

    return {
        "loan_id": loan_id,
        "company_name": company_name,
        "ticker": ticker,
        "industry": industry,
        "region": region,
        "country": country,
        "original_balance": original_balance,
        "outstanding_balance": outstanding_balance,
        "interest_rate": interest_rate,
        "term_months": term_months,
        "purpose": random.choice(PURPOSES),
        "collateral_type": collateral_type,
        "collateral_value": collateral_value,
        "disbursement_date": disbursement_date.strftime("%Y-%m-%d"),
        "maturity_date": maturity_date.strftime("%Y-%m-%d"),
        "last_payment_date": last_payment_date.strftime("%Y-%m-%d"),
        "last_payment_amount": last_payment_amount,
        "days_past_due": days_past_due,
        "payment_status": payment_status,
        "status": status,
        "pd_score": pd_score,
        "lgd_score": lgd_score,
        "risk_grade": risk_grade,
        "annual_revenue": annual_revenue,
        "net_income": net_income,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "submitted_at": disbursement_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


def create_schema(conn):
    """Create or update the loans table schema."""
    cursor = conn.cursor()

    # Drop old applications table if exists and create loans table
    cursor.execute("DROP TABLE IF EXISTS loans")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            loan_id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            ticker TEXT,
            industry TEXT,
            region TEXT,
            country TEXT,
            original_balance REAL,
            outstanding_balance REAL,
            interest_rate REAL,
            term_months INTEGER,
            purpose TEXT,
            collateral_type TEXT,
            collateral_value REAL,
            disbursement_date TEXT,
            maturity_date TEXT,
            last_payment_date TEXT,
            last_payment_amount REAL,
            days_past_due INTEGER DEFAULT 0,
            payment_status TEXT DEFAULT 'current',
            status TEXT DEFAULT 'active',
            pd_score REAL,
            lgd_score REAL,
            risk_grade TEXT,
            annual_revenue REAL,
            net_income REAL,
            total_assets REAL,
            total_liabilities REAL,
            documents_json TEXT DEFAULT '[]',
            submitted_at TEXT,
            updated_at TEXT
        )
    """)

    # Create repayments table
    cursor.execute("DROP TABLE IF EXISTS repayments")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repayments (
            repayment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id TEXT NOT NULL,
            payment_date TEXT NOT NULL,
            payment_amount REAL NOT NULL,
            principal_amount REAL,
            interest_amount REAL,
            balance_after REAL,
            status TEXT DEFAULT 'completed',
            FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
        )
    """)

    conn.commit()
    print("Schema created successfully.")


def generate_repayment_history(conn, loan):
    """Generate repayment history for a loan."""
    cursor = conn.cursor()

    disbursement = datetime.strptime(loan["disbursement_date"], "%Y-%m-%d")
    now = datetime.now()

    # Monthly payments
    monthly_payment = loan["original_balance"] / loan["term_months"]
    balance = loan["original_balance"]

    current_date = disbursement + timedelta(days=30)

    while current_date < now and balance > 0:
        # Determine payment status based on loan's payment status
        if loan["payment_status"] == "current":
            # Regular payments
            payment_amount = monthly_payment * random.uniform(0.95, 1.05)
            status = "completed"
        elif loan["payment_status"] == "delinquent":
            # Some missed payments
            if random.random() > 0.3:
                payment_amount = monthly_payment * random.uniform(0.8, 1.0)
                status = "completed"
            else:
                payment_amount = 0
                status = "missed"
        else:  # default
            # Many missed payments
            if random.random() > 0.7:
                payment_amount = monthly_payment * random.uniform(0.5, 0.8)
                status = "partial"
            else:
                payment_amount = 0
                status = "missed"

        if payment_amount > 0:
            principal = payment_amount * 0.7
            interest = payment_amount * 0.3
            balance = max(0, balance - principal)

            cursor.execute("""
                INSERT INTO repayments (loan_id, payment_date, payment_amount, principal_amount, interest_amount, balance_after, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                loan["loan_id"],
                current_date.strftime("%Y-%m-%d"),
                round(payment_amount, 2),
                round(principal, 2),
                round(interest, 2),
                round(balance, 2),
                status
            ))

        current_date += timedelta(days=30)

    conn.commit()


def seed_data(num_loans=75):
    """Seed the database with synthetic loan data."""
    global _used_companies
    _used_companies = set()  # Reset used companies for fresh seeding

    print(f"Seeding {num_loans} loans to {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    # Create schema
    create_schema(conn)

    cursor = conn.cursor()

    # Generate and insert loans
    loans = []
    for i in range(num_loans):
        loan = generate_loan()
        loans.append(loan)

        cursor.execute("""
            INSERT INTO loans (
                loan_id, company_name, ticker, industry, region, country,
                original_balance, outstanding_balance, interest_rate, term_months,
                purpose, collateral_type, collateral_value,
                disbursement_date, maturity_date,
                last_payment_date, last_payment_amount, days_past_due, payment_status,
                status, pd_score, lgd_score, risk_grade,
                annual_revenue, net_income, total_assets, total_liabilities,
                submitted_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            loan["loan_id"], loan["company_name"], loan["ticker"], loan["industry"], loan["region"], loan["country"],
            loan["original_balance"], loan["outstanding_balance"], loan["interest_rate"], loan["term_months"],
            loan["purpose"], loan["collateral_type"], loan["collateral_value"],
            loan["disbursement_date"], loan["maturity_date"],
            loan["last_payment_date"], loan["last_payment_amount"], loan["days_past_due"], loan["payment_status"],
            loan["status"], loan["pd_score"], loan["lgd_score"], loan["risk_grade"],
            loan["annual_revenue"], loan["net_income"], loan["total_assets"], loan["total_liabilities"],
            loan["submitted_at"], loan["updated_at"]
        ))

        if (i + 1) % 10 == 0:
            print(f"  Generated {i + 1}/{num_loans} loans...")

    conn.commit()
    print(f"Inserted {num_loans} loans.")

    # Generate repayment histories
    print("Generating repayment histories...")
    for i, loan in enumerate(loans):
        generate_repayment_history(conn, loan)
        if (i + 1) % 10 == 0:
            print(f"  Generated repayments for {i + 1}/{num_loans} loans...")

    conn.close()

    # Print summary
    print("\n=== Portfolio Summary ===")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*), SUM(outstanding_balance), AVG(pd_score), AVG(lgd_score) FROM loans")
    count, total_exposure, avg_pd, avg_lgd = cursor.fetchone()
    print(f"Total Loans: {count}")
    print(f"Total Exposure: ${total_exposure:,.0f}")
    print(f"Average PD: {avg_pd:.2%}")
    print(f"Average LGD: {avg_lgd:.2%}")

    cursor.execute("SELECT risk_grade, COUNT(*), SUM(outstanding_balance) FROM loans GROUP BY risk_grade ORDER BY risk_grade")
    print("\nRisk Distribution:")
    for grade, cnt, exposure in cursor.fetchall():
        print(f"  {grade}: {cnt} loans, ${exposure:,.0f}")

    cursor.execute("SELECT payment_status, COUNT(*) FROM loans GROUP BY payment_status")
    print("\nPayment Status:")
    for status, cnt in cursor.fetchall():
        print(f"  {status}: {cnt} loans")

    cursor.execute("SELECT industry, COUNT(*), SUM(outstanding_balance) FROM loans GROUP BY industry ORDER BY SUM(outstanding_balance) DESC")
    print("\nIndustry Concentration:")
    for ind, cnt, exposure in cursor.fetchall():
        print(f"  {ind}: {cnt} loans, ${exposure:,.0f}")

    conn.close()
    print("\nSeeding complete!")


if __name__ == "__main__":
    seed_data(75)
