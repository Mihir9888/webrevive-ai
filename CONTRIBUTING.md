# Contributing to WebRevive AI

Thank you for your interest in contributing to **WebRevive AI**! We welcome contributions from developers, accessibility advocates, UX designers, and technical writers of all experience levels.

WebRevive AI is dedicated to making the web accessible to everyone by automating WCAG compliance auditing and leveraging local-first LLMs to refactor inaccessible frontend code.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started & Development Setup](#getting-started--development-setup)
3. [Repository Layout](#repository-layout)
4. [Branching and Workflow Strategy](#branching-and-workflow-strategy)
5. [Coding & Style Standards](#coding--style-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Submitting Pull Requests](#submitting-pull-requests)
8. [Reporting Bugs and Requesting Features](#reporting-bugs-and-requesting-features)

---

## Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free experience for everyone. Please be respectful, constructive, and empathetic in all interactions across issues, pull requests, and discussions.

---

## Getting Started & Development Setup

### Prerequisites

- **Python 3.11+**
- **Node.js 20+** and **npm 10+**
- **Docker & Docker Compose** (optional for containerized workflow)
- **Ollama** running locally with `qwen2.5-coder:7b` (for AI refactoring)
- **Git**

### 1. Clone the Repository

```bash
git clone https://github.com/webrevive-ai/webrevive.git
cd webrevive
```

### 2. Set Up the Backend & CLI Environment

```bash
# Create and activate a virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Install core and dev dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install the CLI in editable mode
pip install -e ./cli

# Install Playwright browser binaries
playwright install chromium
```

### 3. Set Up the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dashboard will be available at `http://localhost:3000`.

### 4. Verify Local Ollama AI Setup

```bash
# Start Ollama service (if not already running as a daemon)
ollama serve

# Pull the primary coding LLM
ollama pull qwen2.5-coder:7b
```

Verify your setup with the WebRevive CLI:
```bash
webrevive init
```

---

## Repository Layout

```text
webrevive-ai/
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI/CD pipeline
├── backend/                   # FastAPI backend application
│   ├── __init__.py
│   └── main.py                # REST API endpoints & middleware
├── cli/                       # Standalone Click + Rich CLI tool
│   ├── setup.py               # Setuptools entrypoints
│   ├── requirements.txt
│   └── webrevive_cli/
│       ├── __init__.py
│       ├── main.py            # CLI root group & init command
│       └── commands/
│           ├── scan.py        # Playwright + axe-core scanner
│           ├── analyze.py     # Local Ollama AI refactoring
│           └── report.py      # HTML / Markdown / JSON report engine
├── frontend/                  # React + Vite web dashboard
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
├── tests/                     # Pytest suite
│   ├── conftest.py
│   ├── test_cli.py
│   └── test_report.py
├── docker-compose.yml         # Microservices composition
├── Dockerfile                 # Multi-stage backend container
├── requirements.txt           # Core Python dependencies
├── .env.example               # Config template
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
└── README.md
```

---

## Branching and Workflow Strategy

1. **Fork the repository** on GitHub.
2. **Create a topic branch** from `main`:
   ```bash
   git checkout -b feat/add-angular-refactor-plugin
   ```
3. Use conventional commit messages:
   - `feat: add Svelte component refactoring rule`
   - `fix: resolve viewport clipping in Playwright scanner`
   - `docs: update CLI scan flags documentation`
   - `test: add unit tests for HTML report generator`

---

## Coding & Style Standards

### Python (Backend & CLI)

- Conforms to **PEP 8**.
- Use strict type hints (`from typing import Optional, List, Dict`).
- Format code using `black` and `isort`:
  ```bash
  black .
  isort .
  flake8 .
  ```
- Keep all CLI output compatible across Windows, macOS, and Linux terminals (avoid non-standard Unicode symbols without fallbacks).

### JavaScript & React (Frontend)

- Use modern React 18+ functional components with hooks.
- Follow ESLint configurations:
  ```bash
  cd frontend
  npm run lint
  ```
- Ensure all custom UI elements are accessible:
  - Correct ARIA roles and landmarks.
  - Full keyboard navigation (`Tab`, `Enter`, `Space`, `Escape`).
  - High color contrast ratio (WCAG 2.1 AA >= 4.5:1).

---

## Testing Guidelines

Always run the full test suite before pushing commits:

```bash
# Run backend & CLI tests
pytest -v

# Run frontend test suite
cd frontend && npm test
```

When contributing new features:
- Add corresponding unit tests under `tests/`.
- Ensure test coverage remains >= 85%.
- Validate that the CLI commands work standalone without requiring the backend server or external network access.

---

## Submitting Pull Requests

1. Rebase your branch onto the latest `main`:
   ```bash
   git fetch origin
   git rebase origin/main
   ```
2. Push your topic branch to your fork:
   ```bash
   git push origin feat/your-feature-name
   ```
3. Open a Pull Request against `main` on GitHub.
4. Fill in the Pull Request template:
   - Summary of changes.
   - Related issue numbers (`Fixes #42`).
   - Manual testing steps performed.
   - Verification that CI tests pass.
5. Address reviewer feedback promptly. Once approved, a maintainer will squash and merge your PR.

---

## Reporting Bugs and Requesting Features

- **Bug Reports:** Open an issue using the Bug Report template. Include your OS version, Python version, target URL (if applicable), and CLI logs.
- **Feature Requests:** Open an issue with the Feature Request label. Explain the accessibility benefit, use case, and proposed interface.
