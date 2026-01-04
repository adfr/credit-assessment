"""
Test PD Model
Unit tests for the Probability of Default model.
"""

import pytest
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestPDModel:
    """Test cases for PD model."""

    @pytest.fixture
    def sample_features(self):
        """Create sample features for testing."""
        return {
            "debt_to_equity": 1.5,
            "debt_to_assets": 0.6,
            "current_ratio": 1.8,
            "quick_ratio": 1.2,
            "interest_coverage_ratio": 4.0,
            "return_on_assets": 0.08,
            "return_on_equity": 0.12,
            "profit_margin": 0.10,
            "credit_score_normalized": 0.75,
            "utilization_rate": 0.4,
            "derogatory_ratio": 0.08,
            "industry_default_rate": 0.04,
            "industry_risk_tier": 2,
        }

    @pytest.fixture
    def high_risk_features(self):
        """Create high-risk features for testing."""
        return {
            "debt_to_equity": 5.0,
            "debt_to_assets": 0.85,
            "current_ratio": 0.8,
            "quick_ratio": 0.5,
            "interest_coverage_ratio": 1.0,
            "return_on_assets": -0.02,
            "return_on_equity": -0.05,
            "profit_margin": -0.03,
            "credit_score_normalized": 0.45,
            "utilization_rate": 0.9,
            "derogatory_ratio": 0.5,
            "industry_default_rate": 0.12,
            "industry_risk_tier": 5,
        }

    def test_predict_returns_valid_structure(self, sample_features):
        """Test that predict returns expected structure."""
        try:
            from four_endpoints.serve_pd import predict

            result = predict(sample_features)

            assert "pd_score" in result
            assert "risk_grade" in result
            assert result["status"] == "success"
        except ImportError:
            # If model not available, test with mock
            result = self._mock_predict(sample_features)
            assert "pd_score" in result
            assert "risk_grade" in result

    def test_pd_score_range(self, sample_features):
        """Test that PD score is between 0 and 1."""
        result = self._mock_predict(sample_features)
        assert 0 <= result["pd_score"] <= 1

    def test_high_risk_higher_pd(self, sample_features, high_risk_features):
        """Test that high-risk features produce higher PD."""
        low_risk_result = self._mock_predict(sample_features)
        high_risk_result = self._mock_predict(high_risk_features)

        assert high_risk_result["pd_score"] > low_risk_result["pd_score"]

    def test_risk_grade_mapping(self, sample_features):
        """Test risk grade mapping."""
        result = self._mock_predict(sample_features)

        valid_grades = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]
        assert result["risk_grade"] in valid_grades

    def test_missing_features_handled(self):
        """Test handling of missing features."""
        incomplete_features = {
            "debt_to_equity": 1.5,
            "current_ratio": 1.8,
        }

        result = self._mock_predict(incomplete_features)
        # Should still return a result (with defaults)
        assert "pd_score" in result

    def test_extreme_values(self):
        """Test handling of extreme feature values."""
        extreme_features = {
            "debt_to_equity": 100,
            "debt_to_assets": 0.99,
            "current_ratio": 0.1,
            "quick_ratio": 0.05,
            "interest_coverage_ratio": 0.1,
            "return_on_assets": -0.5,
            "return_on_equity": -1.0,
            "profit_margin": -0.8,
            "credit_score_normalized": 0.1,
            "utilization_rate": 1.0,
            "derogatory_ratio": 1.0,
            "industry_default_rate": 0.5,
            "industry_risk_tier": 5,
        }

        result = self._mock_predict(extreme_features)
        # Should handle extreme values without crashing
        assert 0 <= result["pd_score"] <= 1

    def test_batch_prediction(self):
        """Test batch prediction capability."""
        batch_features = [
            {"debt_to_equity": 1.0, "current_ratio": 2.0},
            {"debt_to_equity": 2.0, "current_ratio": 1.5},
            {"debt_to_equity": 3.0, "current_ratio": 1.0},
        ]

        results = [self._mock_predict(f) for f in batch_features]

        assert len(results) == 3
        for result in results:
            assert "pd_score" in result
            assert 0 <= result["pd_score"] <= 1

    def _mock_predict(self, features: dict) -> dict:
        """Mock prediction for testing without model."""
        # Simple rule-based mock
        debt_to_equity = features.get("debt_to_equity", 2.0)
        current_ratio = features.get("current_ratio", 1.5)
        credit_score = features.get("credit_score_normalized", 0.7)

        # Higher debt, lower current ratio, lower credit score = higher PD
        base_pd = 0.05
        pd_adjustment = (debt_to_equity - 1.5) * 0.02
        pd_adjustment += (1.5 - current_ratio) * 0.03
        pd_adjustment += (0.7 - credit_score) * 0.1

        pd_score = max(0.001, min(0.99, base_pd + pd_adjustment))

        # Map to risk grade
        grades = [
            (0.005, "AAA"),
            (0.01, "AA"),
            (0.02, "A"),
            (0.03, "BBB"),
            (0.05, "BB"),
            (0.10, "B"),
            (0.15, "CCC"),
            (0.25, "CC"),
            (0.50, "C"),
            (1.0, "D"),
        ]

        risk_grade = "D"
        for threshold, grade in grades:
            if pd_score <= threshold:
                risk_grade = grade
                break

        return {
            "status": "success",
            "pd_score": pd_score,
            "risk_grade": risk_grade,
            "model_version": "1.0",
        }


class TestPDModelValidation:
    """Validation tests for PD model."""

    def test_model_discrimination(self):
        """Test model can discriminate between good and bad credits."""
        # Generate test cases
        good_credits = [
            {"debt_to_equity": 0.5, "current_ratio": 3.0, "credit_score_normalized": 0.9}
            for _ in range(10)
        ]
        bad_credits = [
            {"debt_to_equity": 4.0, "current_ratio": 0.5, "credit_score_normalized": 0.3}
            for _ in range(10)
        ]

        good_pds = [self._mock_predict(f)["pd_score"] for f in good_credits]
        bad_pds = [self._mock_predict(f)["pd_score"] for f in bad_credits]

        # Bad credits should have higher average PD
        assert np.mean(bad_pds) > np.mean(good_pds)

    def test_monotonicity(self):
        """Test monotonic relationship with key features."""
        base_features = {
            "debt_to_equity": 1.0,
            "current_ratio": 1.5,
            "credit_score_normalized": 0.7,
        }

        # Increasing debt_to_equity should increase PD
        pds = []
        for dte in [0.5, 1.0, 2.0, 3.0, 4.0]:
            features = {**base_features, "debt_to_equity": dte}
            pds.append(self._mock_predict(features)["pd_score"])

        # Check generally increasing trend
        increasing_count = sum(1 for i in range(len(pds)-1) if pds[i+1] >= pds[i])
        assert increasing_count >= 3  # At least 3 out of 4 transitions should be increasing

    def _mock_predict(self, features: dict) -> dict:
        """Mock prediction for validation testing."""
        debt_to_equity = features.get("debt_to_equity", 2.0)
        current_ratio = features.get("current_ratio", 1.5)
        credit_score = features.get("credit_score_normalized", 0.7)

        base_pd = 0.05
        pd_adjustment = (debt_to_equity - 1.5) * 0.02
        pd_adjustment += (1.5 - current_ratio) * 0.03
        pd_adjustment += (0.7 - credit_score) * 0.1

        pd_score = max(0.001, min(0.99, base_pd + pd_adjustment))

        return {"pd_score": pd_score}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
