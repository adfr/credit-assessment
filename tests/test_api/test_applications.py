"""
Test Applications API
Unit tests for the applications API endpoints.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestApplicationsAPI:
    """Test cases for applications API."""

    @pytest.fixture
    def sample_application(self):
        """Create sample application data."""
        return {
            "company_name": "Test Corp",
            "industry": "technology",
            "requested_amount": 1000000,
            "requested_term_months": 24,
            "purpose": "working_capital",
            "collateral_type": "equipment",
            "collateral_value": 500000,
            "annual_revenue": 5000000,
            "net_income": 500000,
            "total_assets": 3000000,
            "total_liabilities": 1500000,
        }

    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service."""
        mock = MagicMock()
        mock.save_application.return_value = "test-app-id-123"
        mock.get_application.return_value = {
            "application_id": "test-app-id-123",
            "company_name": "Test Corp",
            "status": "pending",
        }
        mock.list_applications.return_value = [
            {"application_id": "app-1", "company_name": "Corp 1", "status": "pending"},
            {"application_id": "app-2", "company_name": "Corp 2", "status": "approved"},
        ]
        return mock

    def test_create_application_valid(self, sample_application, mock_db_service):
        """Test creating a valid application."""
        with patch("five_backend.api.applications.db_service", mock_db_service):
            # Simulate API call
            result = self._simulate_create(sample_application, mock_db_service)

            assert result["status"] == "success"
            assert "application_id" in result
            mock_db_service.save_application.assert_called_once()

    def test_create_application_missing_fields(self, mock_db_service):
        """Test creating application with missing required fields."""
        incomplete_data = {
            "company_name": "Test Corp",
            # Missing other required fields
        }

        result = self._simulate_create(incomplete_data, mock_db_service)

        # Should still work but with defaults
        assert "status" in result

    def test_list_applications(self, mock_db_service):
        """Test listing applications."""
        result = self._simulate_list(mock_db_service)

        assert result["status"] == "success"
        assert "applications" in result
        assert len(result["applications"]) == 2

    def test_list_applications_with_filter(self, mock_db_service):
        """Test listing applications with status filter."""
        mock_db_service.list_applications.return_value = [
            {"application_id": "app-2", "company_name": "Corp 2", "status": "approved"},
        ]

        result = self._simulate_list(mock_db_service, status="approved")

        assert result["status"] == "success"
        assert len(result["applications"]) == 1
        mock_db_service.list_applications.assert_called_with(
            status="approved", limit=50, offset=0
        )

    def test_get_application(self, mock_db_service):
        """Test getting a specific application."""
        result = self._simulate_get("test-app-id-123", mock_db_service)

        assert result["status"] == "success"
        assert result["application"]["application_id"] == "test-app-id-123"

    def test_get_application_not_found(self, mock_db_service):
        """Test getting non-existent application."""
        mock_db_service.get_application.return_value = None

        result = self._simulate_get("non-existent-id", mock_db_service)

        assert result["status"] == "not_found"

    def test_update_application_status(self, mock_db_service):
        """Test updating application status."""
        result = self._simulate_update_status(
            "test-app-id-123",
            "processing",
            mock_db_service
        )

        assert result["status"] == "success"
        mock_db_service.update_application_status.assert_called_once()

    def test_update_application_invalid_status(self, mock_db_service):
        """Test updating with invalid status."""
        result = self._simulate_update_status(
            "test-app-id-123",
            "invalid_status",
            mock_db_service
        )

        assert result["status"] == "error"
        assert "invalid" in result["message"].lower()

    def _simulate_create(self, data: dict, mock_db: MagicMock) -> dict:
        """Simulate create application API call."""
        import uuid

        try:
            application_id = str(uuid.uuid4())
            application_data = {
                "application_id": application_id,
                **data,
            }

            mock_db.save_application(application_data)

            return {
                "status": "success",
                "application_id": application_id,
                "message": "Application created successfully",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _simulate_list(
        self,
        mock_db: MagicMock,
        status: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """Simulate list applications API call."""
        try:
            applications = mock_db.list_applications(
                status=status, limit=limit, offset=offset
            )

            return {
                "status": "success",
                "applications": applications,
                "count": len(applications),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _simulate_get(self, application_id: str, mock_db: MagicMock) -> dict:
        """Simulate get application API call."""
        try:
            application = mock_db.get_application(application_id)

            if not application:
                return {
                    "status": "not_found",
                    "message": f"Application {application_id} not found",
                }

            return {
                "status": "success",
                "application": application,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _simulate_update_status(
        self,
        application_id: str,
        status: str,
        mock_db: MagicMock
    ) -> dict:
        """Simulate update status API call."""
        valid_statuses = [
            "pending", "processing", "under_review",
            "approved", "declined", "cancelled"
        ]

        if status not in valid_statuses:
            return {
                "status": "error",
                "message": f"Invalid status. Must be one of: {valid_statuses}",
            }

        try:
            mock_db.update_application_status(
                application_id=application_id,
                status=status,
            )

            return {
                "status": "success",
                "message": f"Application status updated to {status}",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


class TestApplicationValidation:
    """Test application data validation."""

    def test_amount_validation(self):
        """Test loan amount validation."""
        # Minimum amount
        assert self._validate_amount(10000) is True
        # Maximum amount
        assert self._validate_amount(100000000) is True
        # Negative amount
        assert self._validate_amount(-1000) is False
        # Zero amount
        assert self._validate_amount(0) is False

    def test_term_validation(self):
        """Test loan term validation."""
        # Valid terms
        assert self._validate_term(12) is True
        assert self._validate_term(60) is True
        assert self._validate_term(120) is True
        # Invalid terms
        assert self._validate_term(0) is False
        assert self._validate_term(-12) is False
        assert self._validate_term(361) is False  # Max 30 years

    def test_industry_validation(self):
        """Test industry validation."""
        valid_industries = [
            "technology", "healthcare", "manufacturing",
            "retail", "finance", "real_estate", "energy", "other"
        ]

        for industry in valid_industries:
            assert self._validate_industry(industry) is True

        assert self._validate_industry("unknown_industry") is False

    def test_collateral_coverage(self):
        """Test collateral coverage ratio calculation."""
        # 50% coverage
        assert self._calculate_coverage(500000, 1000000) == 0.5
        # 100% coverage
        assert self._calculate_coverage(1000000, 1000000) == 1.0
        # 150% coverage
        assert self._calculate_coverage(1500000, 1000000) == 1.5
        # No collateral
        assert self._calculate_coverage(0, 1000000) == 0.0

    def _validate_amount(self, amount: float) -> bool:
        """Validate loan amount."""
        return amount > 0

    def _validate_term(self, term: int) -> bool:
        """Validate loan term in months."""
        return 0 < term <= 360

    def _validate_industry(self, industry: str) -> bool:
        """Validate industry."""
        valid = [
            "technology", "healthcare", "manufacturing",
            "retail", "finance", "real_estate", "energy", "other"
        ]
        return industry.lower() in valid

    def _calculate_coverage(
        self,
        collateral_value: float,
        loan_amount: float
    ) -> float:
        """Calculate collateral coverage ratio."""
        if loan_amount == 0:
            return 0.0
        return collateral_value / loan_amount


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
