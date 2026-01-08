# Portfolio Monitoring

**Category:** monitoring

---


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
