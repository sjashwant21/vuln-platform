from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ScanStatus
from app.infrastructure.database.models import AssetModel, ScanFindingModel, ScanJobModel
from app.workers.tasks.analyst import _run_ai_analysis_async


@pytest.fixture
def mock_ai_service():
    with patch("app.workers.tasks.analyst.create_analyst_service") as mock_create:
        svc_mock = MagicMock()
        mock_create.return_value = svc_mock

        # Setup a dummy response using MagicMock to avoid dataclass init errors
        response_mock = MagicMock()
        response_mock.model_name = "test-model"

        # Executive & Management summaries (can be just dicts or simple objects for jsonable_encoder)
        response_mock.executive_summary = {"overall_risk": "High"}
        response_mock.management_summary = {"risk_trend": "Stable"}

        # Technical analysis
        finding_mock = MagicMock()
        finding_mock.cve_id = "CVE-2024-1234"
        finding_mock.title = "Test Vuln"
        finding_mock.technical_detail = "A vulnerability for testing"
        finding_mock.affected_service = "http"
        finding_mock.affected_port = 80
        response_mock.technical_analysis.findings = [finding_mock]

        # Remediation
        plan_mock = MagicMock()
        plan_mock.cve_id = "CVE-2024-1234"
        plan_mock.title = "Fix Test Vuln"
        plan_mock.effort.value = "low"
        plan_mock.priority = 1
        plan_mock.prerequisites = []
        plan_mock.references = []

        step_mock = MagicMock()
        step_mock.step_number = 1
        step_mock.title = "Run update"
        step_mock.description = "Update the package"
        step_mock.commands = ["apt-get update"]
        plan_mock.steps = [step_mock]

        response_mock.remediation_recommendations.short_term_actions = [plan_mock]
        response_mock.remediation_recommendations.long_term_actions = []

        # Risk prioritization
        response_mock.risk_prioritization.prioritized_vulnerabilities = []

        svc_mock.analyse = AsyncMock(return_value=response_mock)
        yield svc_mock


@pytest.fixture
def patch_session_factory(db_session: AsyncSession):
    """Patch get_session_factory to return a dummy async context manager that yields the test session."""

    class DummyContextManager:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.workers.tasks.analyst.get_session_factory") as mock_factory:
        mock_factory.return_value = lambda: DummyContextManager()
        yield mock_factory


@pytest.mark.asyncio
async def test_run_ai_analysis_job_not_found(patch_session_factory, mock_ai_service):
    """Test that it exits gracefully if the scan job is not found."""
    await _run_ai_analysis_async("invalid-id")
    mock_ai_service.analyse.assert_not_called()


@pytest.mark.asyncio
async def test_run_ai_analysis_no_findings(
    db_session: AsyncSession, patch_session_factory, mock_ai_service
):
    """Test that it exits gracefully if there are no findings."""
    from app.infrastructure.database.models import OrganizationModel, UserModel

    org = OrganizationModel(name="test-org", slug="test-org")
    db_session.add(org)
    await db_session.flush()
    user = UserModel(
        email="test@test.com", password_hash="hash", full_name="Test User", organization_id=org.id
    )
    db_session.add(user)
    await db_session.flush()

    job = ScanJobModel(
        organization_id=org.id,
        initiated_by_id=user.id,
        status=ScanStatus.COMPLETED.value,
        scan_type="network",
        target_ips=["127.0.0.1"],
    )
    db_session.add(job)
    await db_session.flush()

    await _run_ai_analysis_async(job.id)
    mock_ai_service.analyse.assert_not_called()


@pytest.mark.asyncio
async def test_run_ai_analysis_success(
    db_session: AsyncSession, patch_session_factory, mock_ai_service
):
    """Test that it processes findings, creates vulnerabilities, and updates the job."""
    from app.infrastructure.database.models import OrganizationModel, UserModel

    org = OrganizationModel(name="test-org-2", slug="test-org-2")
    db_session.add(org)
    await db_session.flush()
    user = UserModel(
        email="test2@test.com",
        password_hash="hash",
        full_name="Test User 2",
        organization_id=org.id,
    )
    db_session.add(user)
    await db_session.flush()

    asset = AssetModel(organization_id=org.id, ip_address="127.0.0.1", hostname="localhost")
    db_session.add(asset)
    await db_session.flush()

    job = ScanJobModel(
        organization_id=org.id,
        initiated_by_id=user.id,
        status=ScanStatus.COMPLETED.value,
        scan_type="network",
        target_ips=["127.0.0.1"],
    )
    db_session.add(job)
    await db_session.flush()

    from app.infrastructure.database.models import CVECacheModel

    cve = CVECacheModel(
        cve_id="CVE-2024-1234", description="A vulnerability for testing", severity="medium"
    )
    db_session.add(cve)
    await db_session.flush()

    finding = ScanFindingModel(
        scan_job_id=job.id,
        asset_id=asset.id,
        port=80,
        protocol="tcp",
        severity="info",
        title="Test finding",
        description="test",
        cve_ids=["CVE-2024-1234"],
        raw_output={"service": "http", "version": "1.0"},
    )
    db_session.add(finding)
    await db_session.flush()

    # Run the worker task
    await _run_ai_analysis_async(job.id)

    # 1. Verify that the ai service was called
    mock_ai_service.analyse.assert_called_once()

    # 2. Verify vulnerabilities were created
    from app.infrastructure.database.models import RemediationPlanModel, VulnerabilityModel

    vuln_count = (await db_session.execute(select(VulnerabilityModel))).scalars().all()
    assert len(vuln_count) == 1
    assert vuln_count[0].title == "Test Vuln"
    assert vuln_count[0].cve_id == "CVE-2024-1234"

    # 3. Verify remediation plan was created
    plans = (await db_session.execute(select(RemediationPlanModel))).scalars().all()
    assert len(plans) == 1
    assert "Fix Test Vuln" in plans[0].recommendation_markdown
    assert "apt-get update" in plans[0].recommendation_markdown

    # 4. Verify job result_summary was updated
    await db_session.refresh(job)
    assert job.result_summary is not None
    assert "executive_summary" in job.result_summary
    assert job.result_summary["executive_summary"]["overall_risk"] == "High"
