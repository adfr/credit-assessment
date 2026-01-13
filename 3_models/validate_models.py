#!/usr/bin/env python3
"""
Model Validation Suite
Comprehensive validation of PD and LGD models.
"""

import os
import sys
import pickle
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

try:
    import pandas as pd
    import numpy as np
    from scipy import stats
    from sklearn.metrics import roc_auc_score, roc_curve, mean_absolute_error
except ImportError as e:
    print(f"[ERROR] Missing required package: {e}")
    sys.exit(1)


def load_model(model_type: str) -> dict:
    """Load trained model."""
    project_root = Path(__file__).parent.parent
    model_path = project_root / "data" / "models" / model_type / f"{model_type}_model_latest.pkl"

    if not model_path.exists():
        print(f"[ERROR] Model not found: {model_path}")
        return None

    with open(model_path, "rb") as f:
        return pickle.load(f)


def load_features() -> pd.DataFrame:
    """Load feature matrix."""
    project_root = Path(__file__).parent.parent
    data_path = project_root / "data" / "features" / "feature_matrix.parquet"

    if not data_path.exists():
        print(f"[ERROR] Feature matrix not found")
        return None

    return pd.read_parquet(data_path)


def calculate_gini(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Gini coefficient."""
    auc = roc_auc_score(y_true, y_pred)
    return 2 * auc - 1


def calculate_ks(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate KS statistic."""
    fpr, tpr, _ = roc_curve(y_true, y_pred)
    return max(tpr - fpr)


def calculate_somers_d(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Somers' D statistic."""
    # Somers' D = 2 * AUC - 1 for binary classification
    return calculate_gini(y_true, y_pred)


def hosmer_lemeshow_test(y_true: np.ndarray, y_pred: np.ndarray, n_bins: int = 10) -> dict:
    """Perform Hosmer-Lemeshow test for calibration."""
    # Create decile bins
    try:
        bins = pd.qcut(y_pred, n_bins, duplicates='drop')
    except ValueError:
        bins = pd.cut(y_pred, n_bins)

    df = pd.DataFrame({'actual': y_true, 'predicted': y_pred, 'bin': bins})

    # Calculate expected and observed per bin
    result = df.groupby('bin', observed=True).agg({
        'actual': ['sum', 'count'],
        'predicted': 'mean'
    })

    result.columns = ['observed', 'n', 'expected_rate']
    result['expected'] = result['expected_rate'] * result['n']

    # Calculate chi-square statistic
    chi2 = 0
    for _, row in result.iterrows():
        if row['expected'] > 0 and (row['n'] - row['expected']) > 0:
            chi2 += (row['observed'] - row['expected'])**2 / row['expected']
            chi2 += ((row['n'] - row['observed']) - (row['n'] - row['expected']))**2 / (row['n'] - row['expected'])

    # Degrees of freedom = n_bins - 2
    dof = len(result) - 2
    p_value = 1 - stats.chi2.cdf(chi2, dof) if dof > 0 else 1.0

    return {
        'chi2': chi2,
        'dof': dof,
        'p_value': p_value,
        'passed': p_value > 0.05
    }


def binomial_test_by_decile(y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    """Perform binomial test per decile."""
    try:
        deciles = pd.qcut(y_pred, 10, labels=False, duplicates='drop')
    except ValueError:
        deciles = pd.cut(y_pred, 10, labels=False)

    df = pd.DataFrame({'actual': y_true, 'predicted': y_pred, 'decile': deciles})

    results = []
    for decile in sorted(df['decile'].unique()):
        subset = df[df['decile'] == decile]
        n = len(subset)
        observed = subset['actual'].sum()
        expected_rate = subset['predicted'].mean()
        expected = expected_rate * n

        # Binomial test
        if n > 0:
            result = stats.binomtest(observed, n, expected_rate, alternative='two-sided')
            p_value = result.pvalue
        else:
            p_value = 1.0

        results.append({
            'decile': decile + 1,
            'n': n,
            'observed': observed,
            'observed_rate': observed / n if n > 0 else 0,
            'expected': expected,
            'expected_rate': expected_rate,
            'p_value': p_value,
            'passed': p_value > 0.05
        })

    return pd.DataFrame(results)


def calculate_psi(baseline: np.ndarray, current: np.ndarray, n_bins: int = 10) -> float:
    """Calculate Population Stability Index."""
    # Create bins from baseline
    try:
        bins = pd.qcut(baseline, n_bins, duplicates='drop', retbins=True)[1]
    except ValueError:
        bins = np.linspace(baseline.min(), baseline.max(), n_bins + 1)

    # Calculate distributions
    baseline_dist = np.histogram(baseline, bins=bins)[0] / len(baseline)
    current_dist = np.histogram(current, bins=bins)[0] / len(current)

    # Avoid division by zero
    baseline_dist = np.where(baseline_dist == 0, 0.0001, baseline_dist)
    current_dist = np.where(current_dist == 0, 0.0001, current_dist)

    # Calculate PSI
    psi = np.sum((current_dist - baseline_dist) * np.log(current_dist / baseline_dist))

    return psi


def calculate_csi(
    baseline: pd.DataFrame,
    current: pd.DataFrame,
    features: list,
    n_bins: int = 10
) -> pd.DataFrame:
    """Calculate Characteristic Stability Index per feature."""
    results = []

    for feature in features:
        if feature in baseline.columns and feature in current.columns:
            base_vals = baseline[feature].dropna().values
            curr_vals = current[feature].dropna().values

            if len(base_vals) > 0 and len(curr_vals) > 0:
                csi = calculate_psi(base_vals, curr_vals, n_bins)
                results.append({
                    'feature': feature,
                    'csi': csi,
                    'status': 'OK' if csi < 0.1 else 'WARN' if csi < 0.25 else 'ALERT'
                })

    return pd.DataFrame(results).sort_values('csi', ascending=False)


def validate_pd_model(model_data: dict, df: pd.DataFrame) -> dict:
    """Validate PD model."""
    print("\n" + "=" * 60)
    print("PD Model Validation")
    print("=" * 60)

    model = model_data['model']
    features = model_data['features']
    scaler = model_data.get('scaler')

    # Prepare data
    X = df[features].fillna(df[features].median())
    y = df['default_flag']

    if scaler:
        X = pd.DataFrame(scaler.transform(X), columns=features, index=X.index)

    # Get predictions
    y_pred = model.predict_proba(X)[:, 1]

    # Discrimination tests
    print("\n--- Discrimination Tests ---")
    auc = roc_auc_score(y, y_pred)
    gini = calculate_gini(y, y_pred)
    ks = calculate_ks(y, y_pred)
    somers_d = calculate_somers_d(y, y_pred)

    print(f"  AUC-ROC: {auc:.4f} {'✓' if auc > 0.7 else '✗'}")
    print(f"  Gini Coefficient: {gini:.4f} {'✓' if gini > 0.4 else '✗'}")
    print(f"  KS Statistic: {ks:.4f} {'✓' if ks > 0.3 else '✗'}")
    print(f"  Somers' D: {somers_d:.4f}")

    # Calibration tests
    print("\n--- Calibration Tests ---")
    hl_result = hosmer_lemeshow_test(y, y_pred)
    print(f"  Hosmer-Lemeshow Chi²: {hl_result['chi2']:.4f}")
    print(f"  Hosmer-Lemeshow p-value: {hl_result['p_value']:.4f} {'✓' if hl_result['passed'] else '✗'}")

    binomial_results = binomial_test_by_decile(y, y_pred)
    passed_deciles = binomial_results['passed'].sum()
    print(f"  Binomial Test: {passed_deciles}/10 deciles passed")

    # Stability tests (using train/test split as proxy)
    print("\n--- Stability Tests ---")
    n_samples = len(df)
    mid_point = n_samples // 2
    baseline = y_pred[:mid_point]
    current = y_pred[mid_point:]

    psi = calculate_psi(baseline, current)
    psi_status = 'OK' if psi < 0.1 else 'WARN' if psi < 0.25 else 'ALERT'
    print(f"  PSI: {psi:.4f} [{psi_status}]")

    csi_results = calculate_csi(
        df.iloc[:mid_point],
        df.iloc[mid_point:],
        features[:10]  # Top 10 features
    )
    print("\n  Feature Stability (CSI):")
    for _, row in csi_results.head(5).iterrows():
        print(f"    {row['feature']:<30} {row['csi']:.4f} [{row['status']}]")

    return {
        'auc': auc,
        'gini': gini,
        'ks': ks,
        'somers_d': somers_d,
        'hl_chi2': hl_result['chi2'],
        'hl_pvalue': hl_result['p_value'],
        'psi': psi,
        'binomial_results': binomial_results,
        'csi_results': csi_results
    }


def validate_lgd_model(model_data: dict, df: pd.DataFrame) -> dict:
    """Validate LGD model."""
    print("\n" + "=" * 60)
    print("LGD Model Validation")
    print("=" * 60)

    model = model_data['model']
    features = model_data['features']

    # Filter to defaulted loans
    df_default = df[df['default_flag'] == 1].copy()
    df_default = df_default[df_default['lgd'].notna()]

    if len(df_default) == 0:
        print("  No defaulted loans with LGD values for validation")
        return {}

    # Prepare data
    available_features = [f for f in features if f in df_default.columns]
    X = df_default[available_features].fillna(df_default[available_features].median())
    y = df_default['lgd']

    # Get predictions
    y_pred = model.predict(X)
    y_pred = np.clip(y_pred, 0, 1)

    # Performance metrics
    print("\n--- Performance Metrics ---")
    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(np.mean((y - y_pred) ** 2))
    r2 = 1 - np.sum((y - y_pred) ** 2) / np.sum((y - y.mean()) ** 2)

    print(f"  MAE: {mae:.4f} {'✓' if mae < 0.15 else '✗'}")
    print(f"  RMSE: {rmse:.4f} {'✓' if rmse < 0.20 else '✗'}")
    print(f"  R²: {r2:.4f} {'✓' if r2 > 0.3 else '✗'}")

    # Prediction distribution
    print("\n--- Prediction Distribution ---")
    print(f"  Actual LGD Mean: {y.mean():.4f}")
    print(f"  Predicted LGD Mean: {y_pred.mean():.4f}")
    print(f"  Actual LGD Std: {y.std():.4f}")
    print(f"  Predicted LGD Std: {y_pred.std():.4f}")

    return {
        'mae': mae,
        'rmse': rmse,
        'r2': r2,
        'actual_mean': y.mean(),
        'predicted_mean': y_pred.mean()
    }


def generate_validation_report(pd_results: dict, lgd_results: dict):
    """Generate validation report."""
    print("\n" + "=" * 60)
    print("Validation Summary Report")
    print("=" * 60)

    print("\nPD Model:")
    if pd_results:
        passed_checks = 0
        total_checks = 4

        if pd_results['auc'] > 0.7:
            passed_checks += 1
        if pd_results['gini'] > 0.4:
            passed_checks += 1
        if pd_results['psi'] < 0.25:
            passed_checks += 1
        if pd_results['hl_pvalue'] > 0.05:
            passed_checks += 1

        print(f"  Overall: {passed_checks}/{total_checks} checks passed")
        print(f"  Status: {'APPROVED' if passed_checks >= 3 else 'NEEDS REVIEW'}")

    print("\nLGD Model:")
    if lgd_results:
        passed_checks = 0
        total_checks = 3

        if lgd_results.get('mae', 1) < 0.15:
            passed_checks += 1
        if lgd_results.get('rmse', 1) < 0.20:
            passed_checks += 1
        if lgd_results.get('r2', 0) > 0.3:
            passed_checks += 1

        print(f"  Overall: {passed_checks}/{total_checks} checks passed")
        print(f"  Status: {'APPROVED' if passed_checks >= 2 else 'NEEDS REVIEW'}")


def save_report(pd_results: dict, lgd_results: dict):
    """Save validation report."""
    project_root = Path(__file__).parent.parent
    report_dir = project_root / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Save PD validation
    if pd_results:
        pd_summary = {k: v for k, v in pd_results.items()
                      if not isinstance(v, pd.DataFrame)}
        pd_df = pd.DataFrame([pd_summary])
        pd_df.to_csv(report_dir / "pd_validation.csv", index=False)

        if 'binomial_results' in pd_results:
            pd_results['binomial_results'].to_csv(
                report_dir / "pd_binomial_test.csv", index=False
            )
        if 'csi_results' in pd_results:
            pd_results['csi_results'].to_csv(
                report_dir / "pd_feature_stability.csv", index=False
            )

    # Save LGD validation
    if lgd_results:
        lgd_df = pd.DataFrame([lgd_results])
        lgd_df.to_csv(report_dir / "lgd_validation.csv", index=False)

    print(f"\n[INFO] Reports saved to: {report_dir}")


def main():
    """Main function to run model validation."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - Model Validation Suite")
    print("=" * 60)

    # Load feature data
    print("\n[INFO] Loading data...")
    df = load_features()
    if df is None:
        return 1

    print(f"  - Loaded {len(df)} observations")

    # Validate PD model
    pd_model = load_model("pd")
    pd_results = {}
    if pd_model:
        pd_results = validate_pd_model(pd_model, df)
    else:
        print("\n[WARN] PD model not found, skipping validation")

    # Validate LGD model
    lgd_model = load_model("lgd")
    lgd_results = {}
    if lgd_model:
        lgd_results = validate_lgd_model(lgd_model, df)
    else:
        print("\n[WARN] LGD model not found, skipping validation")

    # Generate report
    generate_validation_report(pd_results, lgd_results)

    # Save report
    save_report(pd_results, lgd_results)

    print("\n" + "=" * 60)
    print("[SUCCESS] Model validation completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Review validation reports in data/reports/")
    print("  2. Run 3_models/register_models.py to register in MLflow")
    print("  3. Deploy models using 4_endpoints/")

    return 0


if __name__ == "__main__":
    main()
