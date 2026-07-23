# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-23

### Added
- **Core Platform:** Initial release of the VulnAssess platform.
- **AI Integration:** LLM-powered vulnerability remediation suggestions using Groq API (Llama 3 70b).
- **Scanner Integration:** Fast network and port scanning using Nmap.
- **Vulnerability Data:** Direct integration with NIST NVD API for CVE lookups and metadata.
- **Asset Management:** Add, monitor, and group IT assets for scanning.
- **Reporting Engine:** Generate automated PDF and DOCX reports summarizing findings and AI remediation steps.
- **DevOps:** Docker-compose setup for local development (FastAPI, Postgres, Redis, Celery).
- **Security:** Automated CI/CD pipeline using GitHub Actions (Linting, Testing, Secret Scanning).
