"""
Real Public Companies for Credit Risk Portfolio

20 real publicly traded companies across different industries
with their tickers for fetching financial data.
"""

COMPANIES = [
    # Technology
    {
        "name": "Apple Inc.",
        "ticker": "AAPL",
        "industry": "technology",
        "region": "North America",
        "country": "USA",
    },
    {
        "name": "Microsoft Corporation",
        "ticker": "MSFT",
        "industry": "technology",
        "region": "North America",
        "country": "USA",
    },
    # Healthcare
    {
        "name": "Johnson & Johnson",
        "ticker": "JNJ",
        "industry": "healthcare",
        "region": "North America",
        "country": "USA",
    },
    {
        "name": "Pfizer Inc.",
        "ticker": "PFE",
        "industry": "healthcare",
        "region": "North America",
        "country": "USA",
    },
    # Financial Services
    {
        "name": "JPMorgan Chase & Co.",
        "ticker": "JPM",
        "industry": "financial_services",
        "region": "North America",
        "country": "USA",
    },
    {
        "name": "Goldman Sachs Group Inc.",
        "ticker": "GS",
        "industry": "financial_services",
        "region": "North America",
        "country": "USA",
    },
    # Energy
    {
        "name": "Exxon Mobil Corporation",
        "ticker": "XOM",
        "industry": "energy",
        "region": "North America",
        "country": "USA",
    },
    {
        "name": "Chevron Corporation",
        "ticker": "CVX",
        "industry": "energy",
        "region": "North America",
        "country": "USA",
    },
    # Retail
    {
        "name": "Walmart Inc.",
        "ticker": "WMT",
        "industry": "retail",
        "region": "North America",
        "country": "USA",
    },
    {
        "name": "Amazon.com Inc.",
        "ticker": "AMZN",
        "industry": "retail",
        "region": "North America",
        "country": "USA",
    },
    # Manufacturing
    {
        "name": "General Electric Company",
        "ticker": "GE",
        "industry": "manufacturing",
        "region": "North America",
        "country": "USA",
    },
    {
        "name": "3M Company",
        "ticker": "MMM",
        "industry": "manufacturing",
        "region": "North America",
        "country": "USA",
    },
    # Transportation
    {
        "name": "Delta Air Lines Inc.",
        "ticker": "DAL",
        "industry": "transportation",
        "region": "North America",
        "country": "USA",
    },
    {
        "name": "Union Pacific Corporation",
        "ticker": "UNP",
        "industry": "transportation",
        "region": "North America",
        "country": "USA",
    },
    # Construction
    {
        "name": "Caterpillar Inc.",
        "ticker": "CAT",
        "industry": "construction",
        "region": "North America",
        "country": "USA",
    },
    {
        "name": "Deere & Company",
        "ticker": "DE",
        "industry": "construction",
        "region": "North America",
        "country": "USA",
    },
    # Additional diversified
    {
        "name": "Tesla Inc.",
        "ticker": "TSLA",
        "industry": "manufacturing",
        "region": "North America",
        "country": "USA",
    },
    {
        "name": "The Boeing Company",
        "ticker": "BA",
        "industry": "manufacturing",
        "region": "North America",
        "country": "USA",
    },
    {
        "name": "Coca-Cola Company",
        "ticker": "KO",
        "industry": "retail",
        "region": "North America",
        "country": "USA",
    },
    {
        "name": "Verizon Communications Inc.",
        "ticker": "VZ",
        "industry": "technology",
        "region": "North America",
        "country": "USA",
    },
]

# Industry risk parameters
INDUSTRY_PARAMS = {
    "technology": {"base_pd": 0.025, "base_lgd": 0.40, "risk_tier": 2},
    "healthcare": {"base_pd": 0.020, "base_lgd": 0.35, "risk_tier": 1},
    "financial_services": {"base_pd": 0.030, "base_lgd": 0.45, "risk_tier": 2},
    "energy": {"base_pd": 0.045, "base_lgd": 0.50, "risk_tier": 4},
    "retail": {"base_pd": 0.050, "base_lgd": 0.55, "risk_tier": 4},
    "manufacturing": {"base_pd": 0.035, "base_lgd": 0.45, "risk_tier": 3},
    "transportation": {"base_pd": 0.040, "base_lgd": 0.50, "risk_tier": 3},
    "construction": {"base_pd": 0.055, "base_lgd": 0.55, "risk_tier": 5},
}


def get_companies():
    """Return list of companies with ticker symbols."""
    return COMPANIES


def get_tickers():
    """Return list of ticker symbols."""
    return [c["ticker"] for c in COMPANIES]
