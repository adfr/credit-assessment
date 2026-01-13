# NiFi Integration for Credit Risk Platform

Apache NiFi integration for automated financial data ingestion from SEC EDGAR, news APIs, and credit bureaus.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         NiFi Flow                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ SEC EDGAR    │    │ Serper News  │    │ Financial    │      │
│  │ (Daily 6AM)  │    │ (Hourly)     │    │ Datasets API │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │               │
│         └─────────┬─────────┴─────────┬─────────┘               │
│                   ↓                   ↓                         │
│           ┌──────────────────────────────────┐                 │
│           │     Transform & Validate         │                 │
│           └──────────────┬───────────────────┘                 │
│                          ↓                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Route by Type                         │   │
│  └────┬──────────────┬─────────────────┬───────────────────┘   │
│       ↓              ↓                 ↓                        │
│  ┌─────────┐   ┌───────────┐    ┌──────────────┐               │
│  │ SQLite  │   │ File      │    │ POST to      │               │
│  │ PutSQL  │   │ Storage   │    │ /api/docs    │               │
│  └─────────┘   └───────────┘    └──────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                   Credit Risk Platform API
                   └── /api/documents/ingest
                   └── /api/documents/index
```

## Quick Start

### 1. Start NiFi with Docker

```bash
cd nifi

# Set environment variables
export SERPER_API_KEY=your_serper_key
export FINANCIAL_DATASETS_API_KEY=your_financial_api_key
export CML_API_URL=http://localhost:8000

# Start NiFi
docker-compose up -d
```

### 2. Access NiFi UI

- **URL**: https://localhost:8443/nifi
- **Username**: admin
- **Password**: creditrisk123

### 3. Import Flow Template

1. Right-click on the canvas → **Upload Template**
2. Select `config/financial_data_ingestion.json`
3. Drag the template onto the canvas
4. Configure Controller Services (SQLite connection pool)
5. Start all processors

## Flow Components

### SEC EDGAR Ingestion

Fetches 10-K annual reports from SEC EDGAR (free, no API key required).

| Processor | Purpose |
|-----------|---------|
| GenerateFlowFile | Triggers daily at 6 AM with company list |
| SplitJson | Splits into individual company requests |
| InvokeHTTP | Fetches SEC submissions JSON |
| EvaluateJsonPath | Extracts filing metadata |
| InvokeHTTP | Downloads 10-K document |
| ExecuteScript | Parses HTML, extracts key sections |
| PutSQL | Stores in SQLite database |
| InvokeHTTP | Triggers RAG indexing API |

### News Integration (Serper)

Fetches financial news for portfolio companies hourly.

| Processor | Purpose |
|-----------|---------|
| GenerateFlowFile | Triggers hourly |
| InvokeHTTP | Calls Serper News API |
| SplitJson | Splits news articles |
| JoltTransformJSON | Normalizes format |
| PutSQL | Stores in database |

### Financial Datasets API

Fetches structured financial data (revenue, debt, etc.).

| Processor | Purpose |
|-----------|---------|
| InvokeHTTP | Calls financialdatasets.ai API |
| EvaluateJsonPath | Extracts financial metrics |
| UpdateRecord | Enriches company records |

## API Endpoints

NiFi flows call these Credit Risk Platform API endpoints:

### POST /api/documents/ingest

Receives documents from NiFi and stores them.

```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "doc_type": "10-K",
  "fiscal_year": 2023,
  "content": "...",
  "source": "nifi",
  "filing_date": "2024-01-15"
}
```

### POST /api/documents/index

Triggers RAG indexing for documents.

```json
{
  "ticker": "AAPL",
  "doc_type": "10-K",
  "force_reindex": false
}
```

### GET /api/documents/stats

Returns indexing statistics.

## Configuration

### Company Tickers

Edit `config/company_tickers.json` to add/remove companies:

```json
{
  "tickers": [
    {"ticker": "AAPL", "cik": "0000320193", "name": "Apple Inc."},
    {"ticker": "MSFT", "cik": "0000789019", "name": "Microsoft Corporation"}
  ]
}
```

### Scheduling

| Flow | Default Schedule | Cron Expression |
|------|------------------|-----------------|
| SEC EDGAR | Daily 6 AM | `0 6 * * *` |
| News | Hourly | `0 * * * *` |
| Financial Data | Daily 7 AM | `0 7 * * *` |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SERPER_API_KEY` | Serper.dev API key for news | Yes |
| `FINANCIAL_DATASETS_API_KEY` | financialdatasets.ai key | Yes |
| `CML_API_URL` | Credit Risk API base URL | Yes |

## Deployment on Cloudera DataFlow (CDF)

### 1. Export Flow Definition

In NiFi UI:
1. Select the Process Group
2. Right-click → **Download Flow Definition**
3. Save as `credit_risk_flow.json`

### 2. Deploy to CDF

```bash
# Using CDP CLI
cdp df import-flow-definition \
  --name "Credit Risk Data Ingestion" \
  --file credit_risk_flow.json

# Create deployment
cdp df create-deployment \
  --service-name credit-risk-nifi \
  --flow-name "Credit Risk Data Ingestion" \
  --environment-crn $ENV_CRN
```

### 3. Configure Parameters

In CDF UI:
1. Go to **Catalog** → **Flow Definitions**
2. Select "Credit Risk Data Ingestion"
3. Click **Deploy**
4. Set parameter values for API keys and URLs

## Monitoring

### NiFi Provenance

Track every document processed:
1. Right-click any processor → **View Data Provenance**
2. See full lineage from source to destination

### Bulletins

Check for errors:
- Yellow/Red icons on processors indicate warnings/errors
- Click the bulletin icon to see details

### Metrics

Key metrics to monitor:
- **Bytes In/Out**: Data volume
- **FlowFiles In/Out**: Document count
- **Queue Size**: Backpressure indicator

## Troubleshooting

### SEC EDGAR Rate Limiting

SEC allows max 10 requests/second. The flow includes:
- 200ms delay between requests
- Retry on 429 errors
- Exponential backoff

### Connection Errors

If CML API is unreachable:
1. Check `CML_API_URL` environment variable
2. Verify network connectivity from NiFi container
3. Check API health: `curl http://localhost:8000/health`

### Memory Issues

For large 10-K filings (some are 20MB+):
- Increase NiFi heap: `-Xmx4g` in `bootstrap.conf`
- Use content repository on fast SSD

## Files

```
nifi/
├── README.md                           # This file
├── docker-compose.yaml                 # Docker deployment
├── financial_data_ingestion.json       # Flow definition
├── config/
│   └── company_tickers.json           # Companies to fetch
└── scripts/
    └── parse_10k_html.py              # 10-K HTML parser
```
