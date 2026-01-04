#!/usr/bin/env python3
"""
Load Policy Documents Script
Creates sample credit policy documents and loads them into the vector store.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import uuid

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("[ERROR] ChromaDB not installed. Run: pip install chromadb")
    sys.exit(1)


# Sample Policy Documents
POLICY_DOCUMENTS = [
    {
        "id": "policy_approval_criteria",
        "title": "Credit Approval Criteria",
        "category": "approval",
        "content": """
# Credit Approval Criteria

## Automatic Approval Criteria
Applications meeting ALL of the following criteria may be approved automatically:

1. **Probability of Default (PD)**
   - PD Score < 3% for investment grade
   - PD Score < 5% for standard grade

2. **Financial Ratios**
   - Debt-to-Equity Ratio < 2.0
   - Interest Coverage Ratio > 3.0
   - Current Ratio > 1.2

3. **Credit Bureau Score**
   - Business Credit Score > 70 (out of 100)
   - No derogatory marks in past 24 months

4. **Collateral Requirements**
   - LTV Ratio < 80% for secured loans
   - Collateral must be independently valued

## Referral Criteria
Applications meeting ANY of the following must be referred for manual review:

1. PD Score between 5% and 10%
2. Loan amount exceeds $10 million
3. Industry classified as high-risk
4. Debt-to-Equity Ratio between 2.0 and 4.0
5. New customer with less than 3 years of operating history
6. Any missing or incomplete documentation

## Automatic Decline Criteria
Applications meeting ANY of the following will be automatically declined:

1. PD Score > 15%
2. Failed sanctions/AML screening
3. Active bankruptcy or insolvency proceedings
4. Fraud indicators detected
5. Debt-to-Equity Ratio > 5.0
6. Interest Coverage Ratio < 1.0
"""
    },
    {
        "id": "policy_risk_thresholds",
        "title": "Risk Thresholds and Limits",
        "category": "risk",
        "content": """
# Risk Thresholds and Limits

## Probability of Default (PD) Bands
| Risk Grade | PD Range | Action |
|------------|----------|--------|
| AAA-A | 0% - 1% | Auto-approve eligible |
| BBB | 1% - 3% | Auto-approve eligible |
| BB | 3% - 5% | Senior review required |
| B | 5% - 10% | Committee approval |
| CCC | 10% - 15% | Enhanced due diligence |
| CC-D | >15% | Decline |

## Loss Given Default (LGD) Assumptions
- Secured with real estate: 35% LGD
- Secured with equipment: 45% LGD
- Secured with receivables: 55% LGD
- Unsecured: 75% LGD

## Expected Loss (EL) Limits
- Single obligor EL limit: $5 million
- Portfolio EL concentration: Maximum 10% to single industry

## Economic Capital Requirements
- Confidence level: 99.9%
- Time horizon: 1 year
- Minimum capital buffer: 8% of exposure

## Exposure Limits
| Company Size | Maximum Exposure |
|--------------|------------------|
| Large (Revenue > $500M) | $50 million |
| Medium ($50M - $500M) | $25 million |
| Small (< $50M) | $10 million |
"""
    },
    {
        "id": "policy_rorac_hurdles",
        "title": "RORAC Hurdle Rates",
        "category": "pricing",
        "content": """
# RORAC Hurdle Rates and Pricing Guidelines

## Return on Risk-Adjusted Capital (RORAC)
RORAC = (Net Income - Expected Loss) / Economic Capital

## Minimum Hurdle Rates
| Risk Grade | Minimum RORAC | Target RORAC |
|------------|---------------|--------------|
| AAA-A | 12% | 15% |
| BBB | 14% | 18% |
| BB | 16% | 22% |
| B | 18% | 25% |
| CCC | 22% | 30% |

## Pricing Components
1. **Cost of Funds**: SOFR + 50bps (floating rate benchmark)
2. **Operating Cost**: 25bps per annum
3. **Expected Loss Premium**: Based on PD x LGD
4. **Capital Charge**: EC x Hurdle Rate / Loan Amount
5. **Profit Margin**: Minimum 50bps

## Pricing Formula
Minimum Rate = Cost of Funds + Operating Cost + EL Premium + Capital Charge + Profit Margin

## Exceptions
- Strategic relationships may receive up to 25bps discount with approval
- Cross-sell opportunities may receive up to 15bps discount
- All exceptions require documented approval from Credit Committee
"""
    },
    {
        "id": "policy_documentation",
        "title": "Documentation Requirements",
        "category": "documentation",
        "content": """
# Documentation Requirements

## Required Documents - All Applications
1. **Financial Statements**
   - Audited financials for past 3 years
   - Most recent quarterly financials
   - Management accounts if >90 days from year-end

2. **Corporate Documents**
   - Certificate of incorporation
   - Board resolution authorizing borrowing
   - List of directors and beneficial owners

3. **Business Information**
   - Business plan or description
   - Organizational chart
   - Key customer/supplier information

## Additional Requirements by Loan Size
### Loans > $5 Million
- Independent valuation of collateral
- Environmental assessment (if applicable)
- Legal opinion on enforceability

### Loans > $10 Million
- CIM or investment memo
- Industry analysis
- Management interviews

### Loans > $25 Million
- Third-party due diligence
- External credit rating
- Syndication feasibility (if applicable)

## Document Age Requirements
- Financial statements: Maximum 120 days old at closing
- Credit bureau report: Maximum 30 days old
- Collateral valuation: Maximum 6 months old

## Verification Requirements
- All financials must be verified against source documents
- Bank statements for cash verification
- Confirmation of major receivables (>10% of total)
"""
    },
    {
        "id": "policy_industry_risk",
        "title": "Industry Risk Classification",
        "category": "risk",
        "content": """
# Industry Risk Classification

## High-Risk Industries (Enhanced Due Diligence Required)
1. **Oil & Gas** - Commodity price volatility
2. **Mining** - Environmental and commodity risks
3. **Airlines** - Cyclical and capital intensive
4. **Retail** - E-commerce disruption
5. **Restaurants/Hospitality** - High failure rates
6. **Construction** - Cyclical and project risk
7. **Gaming/Casinos** - Regulatory and reputational risk

## Medium-Risk Industries
1. Manufacturing
2. Transportation & Logistics
3. Wholesale Distribution
4. Business Services
5. Real Estate (non-development)

## Low-Risk Industries
1. Healthcare Services
2. Technology (established companies)
3. Food & Beverage (non-restaurant)
4. Utilities
5. Telecommunications
6. Financial Services (regulated)

## Industry Concentration Limits
- Single industry: Maximum 15% of portfolio
- High-risk industries combined: Maximum 20% of portfolio

## Industry-Specific Requirements
### Real Estate
- Maximum LTV: 70% for commercial, 75% for residential
- DSCR minimum: 1.25x

### Technology
- Revenue traction required (minimum $5M ARR)
- Customer concentration: No single customer >30%

### Manufacturing
- Working capital analysis required
- Supplier/customer dependency review
"""
    },
    {
        "id": "policy_compliance",
        "title": "Compliance Requirements",
        "category": "compliance",
        "content": """
# Compliance Requirements

## Know Your Customer (KYC)
All borrowers must complete KYC verification including:
1. Identity verification of beneficial owners (>25% ownership)
2. Source of funds documentation
3. Nature of business verification
4. Expected transaction patterns

## Anti-Money Laundering (AML)
- Sanctions screening against OFAC, EU, UN lists
- PEP (Politically Exposed Persons) screening
- Adverse media screening
- Enhanced due diligence for high-risk jurisdictions

## High-Risk Jurisdictions
The following require enhanced due diligence:
- Countries on FATF grey list
- Tax haven jurisdictions
- Countries with active conflict

## Regulatory Requirements
### Basel III/IV Compliance
- Risk-weighted assets calculation
- IRB approach for PD/LGD
- Capital adequacy reporting

### Fair Lending
- Consistent application of criteria
- No discrimination in pricing or terms
- Documentation of all decisions

## Periodic Review Requirements
| Risk Grade | Review Frequency |
|------------|------------------|
| Investment Grade | Annual |
| Sub-Investment Grade | Semi-annual |
| Watch List | Quarterly |
| Problem Credits | Monthly |

## Reporting Requirements
- All declines must be documented with reasons
- Material exceptions require Risk Committee approval
- Regulatory reports filed within prescribed timelines
"""
    },
    {
        "id": "policy_workflow",
        "title": "Credit Workflow Process",
        "category": "process",
        "content": """
# Credit Workflow Process

## Application Processing Steps

### Step 1: Document Collection
- Gather all required documents
- Verify document authenticity
- Flag missing or expired documents

### Step 2: Data Validation
- Extract financial data from documents
- Cross-reference with external sources
- Validate calculations and ratios

### Step 3: Bureau Data Pull
- Obtain credit bureau report
- Calculate bureau-derived metrics
- Flag any derogatory information

### Step 4: Compliance Check
- Sanctions screening
- AML verification
- Industry restriction check

### Step 5: Risk Scoring
- Run PD model
- Run LGD model
- Calculate Expected Loss
- Calculate Economic Capital
- Determine RORAC

### Step 6: Decision Routing
- Auto-approve if all criteria met
- Auto-decline if hard declines triggered
- Route to analyst for manual review otherwise

### Step 7: Manual Review (if required)
- Analyst reviews full package
- AI assistant available for queries
- Analyst makes recommendation

### Step 8: Decision & Documentation
- Record final decision
- Generate decision letter
- Set up monitoring triggers

## SLA Requirements
| Step | Target Time |
|------|-------------|
| Document Collection | 2 business days |
| Data Validation | 4 hours |
| Compliance Check | 1 hour |
| Risk Scoring | 5 minutes |
| Manual Review | 2 business days |
| Total (simple) | 3 business days |
| Total (complex) | 5 business days |
"""
    },
    {
        "id": "policy_monitoring",
        "title": "Portfolio Monitoring",
        "category": "monitoring",
        "content": """
# Portfolio Monitoring Requirements

## Early Warning Indicators
Monitor for the following triggers:
1. Payment 30+ days past due
2. Credit bureau score decline >10 points
3. Material adverse news
4. Financial covenant breach
5. Revenue decline >20% YoY
6. Loss of major customer

## Model Performance Monitoring
### Drift Detection
- Population Stability Index (PSI) threshold: 0.25
- Feature drift monitoring monthly
- Recalibration if PSI > 0.10 for 3 consecutive months

### Performance Metrics
- AUC-ROC tracked monthly
- Gini coefficient target: >0.40
- Recalibration trigger if AUC drops >5%

## Watch List Criteria
Add to watch list if:
- PD increases to >10%
- Payment 60+ days past due
- Covenant breach not waived
- Material litigation filed

## Problem Credit Management
For accounts with PD >15%:
1. Assign to specialized workout team
2. Weekly status updates required
3. Develop resolution strategy
4. Monitor recovery proceeds

## Reporting Cadence
- Daily: New delinquencies, large exposure changes
- Weekly: Watch list updates, covenant breaches
- Monthly: Portfolio risk report, model performance
- Quarterly: Comprehensive credit review, board report
"""
    }
]


def get_chroma_path() -> Path:
    """Get the ChromaDB persistence directory."""
    project_root = Path(__file__).parent.parent
    return project_root / "data" / "chroma_db"


def chunk_document(content: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split a document into overlapping chunks."""
    # Split by paragraphs first
    paragraphs = content.split("\n\n")

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) < chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def load_policy_documents(client: chromadb.PersistentClient):
    """Load policy documents into the vector store."""
    print("\n" + "="*60)
    print("Loading Policy Documents")
    print("="*60 + "\n")

    collection = client.get_collection("policy_documents")

    total_chunks = 0
    for doc in POLICY_DOCUMENTS:
        print(f"Processing: {doc['title']}")

        # Chunk the document
        chunks = chunk_document(doc["content"])
        print(f"  - Split into {len(chunks)} chunks")

        # Prepare data for insertion
        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc['id']}_chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "document_id": doc["id"],
                "title": doc["title"],
                "category": doc["category"],
                "chunk_index": i,
                "total_chunks": len(chunks),
                "loaded_at": datetime.now().isoformat()
            })

        # Add to collection
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

        total_chunks += len(chunks)
        print(f"  - Added to collection")

    print(f"\nTotal chunks loaded: {total_chunks}")
    return total_chunks


def save_policy_files(output_dir: Path):
    """Save policy documents as markdown files for reference."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for doc in POLICY_DOCUMENTS:
        filename = f"{doc['id']}.md"
        filepath = output_dir / filename

        with open(filepath, "w") as f:
            f.write(f"# {doc['title']}\n\n")
            f.write(f"**Category:** {doc['category']}\n\n")
            f.write("---\n\n")
            f.write(doc["content"])

    print(f"\nPolicy files saved to: {output_dir}")


def test_retrieval(client: chromadb.PersistentClient):
    """Test that retrieval works correctly."""
    print("\n" + "="*60)
    print("Testing Document Retrieval")
    print("="*60 + "\n")

    collection = client.get_collection("policy_documents")

    test_queries = [
        "What is the minimum RORAC for BBB grade loans?",
        "What documents are required for loans over $10 million?",
        "When should a credit be added to the watch list?",
        "What are the automatic decline criteria?"
    ]

    for query in test_queries:
        print(f"Query: {query}")
        results = collection.query(
            query_texts=[query],
            n_results=2
        )

        print(f"  Results found: {len(results['documents'][0])}")
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i]
            print(f"  [{i+1}] From: {metadata['title']} (chunk {metadata['chunk_index']})")
            print(f"      Preview: {doc[:100]}...")
        print()

    return True


def main():
    """Main function to load policy documents."""
    print("\n" + "="*60)
    print("Credit Risk Platform - Policy Document Loader")
    print("="*60)

    # Check if ChromaDB exists
    chroma_path = get_chroma_path()
    if not chroma_path.exists():
        print(f"\n[ERROR] ChromaDB not found at {chroma_path}")
        print("Please run 0_setup/setup_vector_store.py first")
        return 1

    # Create client
    client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False)
    )

    # Load documents
    total_chunks = load_policy_documents(client)

    # Save policy files as markdown
    project_root = Path(__file__).parent.parent
    policy_dir = project_root / "docs" / "policies"
    save_policy_files(policy_dir)

    # Test retrieval
    test_retrieval(client)

    # Summary
    print("\n" + "="*60)
    print("Policy Document Loading Summary")
    print("="*60)
    print(f"\n[SUCCESS] Loaded {len(POLICY_DOCUMENTS)} policy documents")
    print(f"Total chunks: {total_chunks}")
    print(f"\nPolicy files saved to: {policy_dir}")
    print("\nNext steps:")
    print("  1. Run 1_data/generate_synthetic.py to generate sample data")
    print("  2. Run 2_features/feature_pipeline.py to engineer features")

    return 0


if __name__ == "__main__":
    sys.exit(main())
