# OTP Service

Standardized microservice for handling One-Time Password (OTP) generation and verification for the QuickHaul application.

## 🚀 CI/CD Pipeline & Troubleshooting

This service has been standardized to match the QuickHaul modular architecture. Below is a log of the troubleshooting steps taken during the setup:

### 1. Module Resolution Fix
*   **Issue**: `ModuleNotFoundError: No module named 'app'` during CI test runs.
*   **Solution**: Explicitly set `PYTHONPATH: .` in the GitHub Actions environment to allow `pytest` to locate the root `app.py`.

### 2. Snyk Security Scanning Fix
*   **Issue**: The default Snyk template (`_snyk.yml`) was hardcoded for Node.js, causing `Failed to test pip project` errors.
*   **Solution**: Switched to a Python-specific template (`_snyk-python.yml`) that utilizes `snyk/actions/python@master` and ensures dependencies are installed before scanning.

### 3. Dependency & Security Patching
*   **Vulnerability Resolution**: Resolved high-severity vulnerabilities identified by Snyk:
    *   **python-multipart**: Upgraded to `0.0.22`.
    *   **starlette**: Explicitly pinned to `0.49.1` (which required upgrading `fastapi` to `0.115.4+` to resolve dependency conflicts).
*   **Coverage**: Achieved **77% overall code coverage** with 16 automated test cases.

### 4. Pipeline Visualization
*   **Alignment**: Refactored `ci-otp.yml` to match the `location-service` visual style, using parallel branching for security notifications and standardized job IDs (`sast`, `sca`, `build`, etc.).

## 🛠 Local Setup

### Requirements
- Python 3.12+
- Redis

### Installation
```bash
pip install -r requirements.txt
```

### Running Tests
```bash
pytest --cov=. --cov-report=term-missing tests/
```

### Git Identity (Local)
To push commits with the correct project identity without changing your global settings:
```bash
git config --local user.name "sath2003"
git config --local user.email "sathvik.vbn@gmail.com"
```
