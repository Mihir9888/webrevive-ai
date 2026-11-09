# Security Policy & Privacy Guarantees

WebRevive AI was designed from day one with a **Local-First, Zero-Telemetry Privacy Architecture**. This document outlines our security policies, vulnerability reporting procedures, and data handling guarantees.

---

## Supported Versions

We actively provide security patches and updates for the following versions:

| Version | Supported          | Security Status |
| :--- | :--- | :--- |
| `1.0.x` | :white_check_mark: | Current Stable Release |
| `< 1.0` | :x:                | Deprecated |

---

## Privacy & Local-First Guarantees

Unlike traditional accessibility assessment tools that send target DOM trees, screenshots, and internal corporate intranet source code to multi-tenant cloud platforms, **WebRevive AI runs completely on your infrastructure**:

1. **Local-Only AI Inference:**
   - All AI explanations, root cause diagnoses, and code refactorings are performed locally via Ollama (`qwen2.5-coder`, `llama3`, or any local GGUF model).
   - Zero prompts, HTML fragments, or code snippets leave your local machine or air-gapped network.
2. **No External Telemetry or Tracking:**
   - The CLI, backend, and frontend containers do not transmit analytics, telemetry, or user behavior metrics to third parties.
3. **Intranet & Staging Safe:**
   - You can safely audit staging environments, pre-production portals, password-protected testing branches, and internal dashboards without risk of IP leakage.
4. **Sandboxed Headless Execution:**
   - Automated browser audits run within isolated Playwright Chromium sandboxes with restricted permissions.

---

## Reporting a Security Vulnerability

We take the security of WebRevive AI and its users seriously. If you discover a security vulnerability or exploit, please **do not open a public GitHub issue**.

### Reporting Process

1. Email the core security team directly at **security@webrevive.ai**.
2. Include the following details in your report:
   - Type of vulnerability (e.g., SSRF, arbitrary code execution, path traversal).
   - Affected component (CLI, Backend API, Frontend, or Docker stack).
   - Step-by-step reproduction instructions or Proof-of-Concept (PoC).
   - Potential impact on end users or host systems.
3. We will acknowledge receipt of your vulnerability report within **48 hours**.
4. We will provide regular status updates every **72 hours** while validating and patching the issue.
5. Once a fix is verified, a patched release will be published, and you will be credited in the security advisory (unless you prefer anonymity).

---

## Best Practices for Deployment

When deploying WebRevive AI in team or shared production environments:

- **Change Default Credentials:** Always override `POSTGRES_PASSWORD` and `SECRET_KEY` in `.env` before running `docker compose up`.
- **Network Isolation:** Run database and Ollama containers within a private bridge network without exposing unnecessary host ports.
- **Role-Based Access:** When proxying WebRevive backend endpoints through corporate firewalls, apply API authentication tokens (OAuth2/JWT).
- **Keep Playwright & Browsers Updated:** Regularly update browser dependencies to patch underlying Chromium engine CVEs.
