import argparse

# ruff: noqa: T201
import asyncio
import random
import uuid
from datetime import UTC, datetime

from faker import Faker
from sqlalchemy import text

# Import paths for backend application
from app.infrastructure.database.connection import (
    close_engine,
    create_engine_and_factory,
    get_session_factory,
)
from app.infrastructure.database.models import (
    AssetModel,
    AssetPortModel,
    OrganizationModel,
    RemediationPlanModel,
    ScanFindingModel,
    ScanJobModel,
    UserModel,
    VulnerabilityModel,
)
from app.infrastructure.security.password_handler import password_handler

fake = Faker()

# Common configurations
DEFAULT_PASSWORD = "Password123!"
SEVERITIES = ["critical", "high", "medium", "low", "info"]

async def reset_database(session):
    """Truncate tables to start fresh."""
    print("Resetting database...")
    tables = [
        "remediation_plans",
        "vulnerabilities",
        "scan_findings",
        "scan_jobs",
        "asset_ports",
        "assets",
        "refresh_tokens",
        "users",
        "organizations",
        "audit_logs",
    ]

    for table in tables:
        await session.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
    await session.commit()
    print("Database reset complete.")


async def generate_mock_data(session, orgs_count, users_per_org, assets_per_org, vulns_per_asset):
    """Generate and insert mock data into the database."""

    # 1. Organizations
    organizations = []
    print(f"Generating {orgs_count} Organizations...")
    for _ in range(orgs_count):
        org = OrganizationModel(
            id=str(uuid.uuid4()),
            name=fake.company(),
            slug=fake.slug()[:63],
            plan_tier=random.choice(["free", "pro", "enterprise"]),
            max_assets=1000,
            max_users=100,
            is_active=True,
            created_at=fake.date_time_between(start_date='-1y', end_date='now', tzinfo=UTC),
        )
        session.add(org)
        organizations.append(org)
    await session.flush()

    # 2. Users
    users = []
    print(f"Generating Users ({users_per_org} per Org)...")
    password_hash = password_handler.hash(DEFAULT_PASSWORD)
    for org in organizations:
        for _ in range(users_per_org):
            user = UserModel(
                id=str(uuid.uuid4()),
                organization_id=org.id,
                email=fake.unique.company_email(),
                password_hash=password_hash,
                full_name=fake.name(),
                role=random.choice(["admin", "editor", "viewer"]),
                is_active=True,
                email_verified=True,
                last_login_at=fake.date_time_between(start_date='-1m', end_date='now', tzinfo=UTC),
                created_at=org.created_at,
            )
            session.add(user)
            users.append(user)
    await session.flush()

    # 3. Assets & Ports
    assets = []
    print(f"Generating Assets ({assets_per_org} per Org) and Ports...")
    asset_types = ["server", "workstation", "router", "firewall", "container", "unknown"]
    for org in organizations:
        for _ in range(assets_per_org):
            asset = AssetModel(
                id=str(uuid.uuid4()),
                organization_id=org.id,
                hostname=fake.hostname(),
                ip_address=fake.ipv4(),
                asset_type=random.choice(asset_types),
                os_fingerprint=random.choice(["Linux", "Windows Server 2019", "Ubuntu 22.04", "CentOS", "macOS"]),
                criticality=random.choice(["critical", "high", "medium", "low"]),
                is_active=True,
                last_seen_at=fake.date_time_between(start_date='-1w', end_date='now', tzinfo=UTC),
                created_at=org.created_at,
            )
            session.add(asset)
            assets.append(asset)

            # Ports
            used_ports = set()
            for _ in range(random.randint(0, 3)):
                port_num = random.choice([80, 443, 22, 21, 3306, 5432, 8080])
                protocol = random.choice(["tcp", "udp"])
                if (port_num, protocol) in used_ports:
                    continue
                used_ports.add((port_num, protocol))

                port = AssetPortModel(
                    id=str(uuid.uuid4()),
                    asset_id=asset.id,
                    port=port_num,
                    protocol=protocol,
                    service=random.choice(["http", "https", "ssh", "ftp", "mysql", "postgresql"]),
                    state="open",
                    scanned_at=datetime.now(UTC),
                )
                session.add(port)
    await session.flush()

    # 4. Scan Jobs
    scan_jobs = []
    print("Generating Scan Jobs...")
    for org in organizations:
        for _ in range(random.randint(3, 8)):
            job = ScanJobModel(
                id=str(uuid.uuid4()),
                organization_id=org.id,
                initiated_by_id=random.choice([u.id for u in users if u.organization_id == org.id]),
                scan_type=random.choice(["discovery", "vulnerability", "port_scan"]),
                status="completed",
                target_ips=[fake.ipv4(), fake.ipv4()],
                started_at=fake.date_time_between(start_date='-1m', end_date='-1h', tzinfo=UTC),
                completed_at=datetime.now(UTC),
                created_at=fake.date_time_between(start_date='-1m', end_date='-2h', tzinfo=UTC),
            )
            session.add(job)
            scan_jobs.append(job)
    await session.flush()

    # 5. Vulnerabilities & Findings
    print("Generating Vulnerabilities & Findings...")
    for asset in assets:
        for _ in range(random.randint(0, vulns_per_asset)):
            cve_id = f"CVE-{random.randint(2015, 2024)}-{random.randint(1000, 99999)}"
            severity = random.choice(SEVERITIES)
            cvss = random.uniform(3.0, 10.0) if severity != "info" else None

            # Create a Scan Job reference for the finding
            relevant_jobs = [j for j in scan_jobs if j.organization_id == asset.organization_id]
            job = random.choice(relevant_jobs) if relevant_jobs else None

            finding_id = None
            if job:
                finding = ScanFindingModel(
                    id=str(uuid.uuid4()),
                    scan_job_id=job.id,
                    asset_id=asset.id,
                    severity=severity,
                    title=fake.catch_phrase(),
                    description=fake.paragraph(nb_sentences=3),
                    cve_ids=[cve_id],
                    cvss_score=cvss,
                )
                session.add(finding)
                finding_id = finding.id

            vuln = VulnerabilityModel(
                id=str(uuid.uuid4()),
                organization_id=asset.organization_id,
                asset_id=asset.id,
                finding_id=finding_id,
                cve_id=None, # In a real scenario, this would link to CVECacheModel
                title=fake.catch_phrase(),
                description=fake.paragraph(nb_sentences=3),
                severity=severity,
                cvss_score=cvss,
                risk_score=cvss * 10 if cvss else None,
                status=random.choice(["open", "open", "in_progress", "resolved", "ignored"]),
                detected_at=fake.date_time_between(start_date='-1m', end_date='now', tzinfo=UTC),
            )
            session.add(vuln)

            # Remediation Plan for high/critical vulns
            if severity in ["critical", "high"] and random.choice([True, False]):
                plan = RemediationPlanModel(
                    id=str(uuid.uuid4()),
                    organization_id=asset.organization_id,
                    vulnerability_id=vuln.id,
                    ai_model="groq-llama3",
                    recommendation_markdown=f"### Recommended Fix\n\n1. {fake.sentence()}\n2. {fake.sentence()}\n3. Restart the service.",
                    structured_steps={"steps": ["Update software", "Restart service"]},
                    confidence_score=random.uniform(0.7, 0.99),
                    generated_at=datetime.now(UTC),
                )
                session.add(plan)

    await session.commit()
    print("Database seeding completed successfully!")
    print(f"Use the password '{DEFAULT_PASSWORD}' to log in with any generated email.")


async def main():
    parser = argparse.ArgumentParser(description="Seed the database with mock data.")
    parser.add_argument("--reset", action="store_true", help="Clear all existing data before seeding")
    parser.add_argument("--orgs", type=int, default=3, help="Number of organizations to create")
    parser.add_argument("--users", type=int, default=5, help="Number of users per organization")
    parser.add_argument("--assets", type=int, default=20, help="Number of assets per organization")
    parser.add_argument("--vulns", type=int, default=3, help="Max vulnerabilities per asset")
    args = parser.parse_args()

    # Init DB
    create_engine_and_factory()
    factory = get_session_factory()

    async with factory() as session:
        if args.reset:
            await reset_database(session)

        await generate_mock_data(
            session=session,
            orgs_count=args.orgs,
            users_per_org=args.users,
            assets_per_org=args.assets,
            vulns_per_asset=args.vulns,
        )

    await close_engine()

if __name__ == "__main__":
    asyncio.run(main())
