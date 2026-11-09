"""Accessibility scanner service utilizing Playwright and axe-core."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from playwright.async_api import Browser, Playwright, async_playwright

from app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback minimal axe-loader script if cdn is unreachable or evaluated directly
AXE_LOADER_SCRIPT = """
async () => {
    if (!window.axe) {
        await new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js';
            script.onload = resolve;
            script.onerror = () => reject(new Error('Failed to load axe-core from CDN'));
            document.head.appendChild(script);
        });
    }
    return await window.axe.run(document, {
        runOnly: {
            type: 'tag',
            values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']
        }
    });
}
"""


class AccessibilityScanner:
    """Orchestrates headless browser navigation, axe-core evaluation, and result parsing."""

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Launch playwright and chromium browser instance."""
        async with self._lock:
            if self._browser is None:
                try:
                    self._playwright = await async_playwright().start()
                    self._browser = await self._playwright.chromium.launch(
                        headless=settings.PLAYWRIGHT_HEADLESS,
                        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
                    )
                    logger.info("Playwright Chromium browser initialized.")
                except Exception as exc:
                    logger.warning(
                        f"Failed to launch Playwright browser directly: {exc}. Heuristic scanning will be used if needed."
                    )

    async def close(self) -> None:
        """Close browser instance and stop playwright daemon."""
        async with self._lock:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception as exc:
                    logger.error(f"Error closing browser: {exc}")
                self._browser = None

            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as exc:
                    logger.error(f"Error stopping playwright: {exc}")
                self._playwright = None
            logger.info("Playwright browser resources released.")

    async def _get_browser(self) -> Optional[Browser]:
        """Lazy browser initializer."""
        if self._browser is None:
            await self.initialize()
        return self._browser

    async def scan_url(self, url: str) -> List[Dict[str, Any]]:
        """Navigate to a public or local HTTP URL, inject axe-core, and return parsed violations."""
        browser = await self._get_browser()
        if not browser:
            logger.warning("Browser unavailable. Attempting heuristic scan for URL.")
            return await self._scan_heuristic_url(url)

        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) WebRevive-AccessibilityScanner/1.0",
        )
        page = await context.new_page()

        try:
            logger.info(f"Navigating to URL for scan: {url}")
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.PLAYWRIGHT_TIMEOUT_MS,
            )
            # Allow dynamic client-side hydration (e.g. React/Vue apps)
            await page.wait_for_timeout(2000)

            axe_results = await page.evaluate(AXE_LOADER_SCRIPT)
            return self.parse_axe_results(axe_results)

        except Exception as exc:
            logger.error(f"Playwright axe scan failed on {url}: {exc}. Falling back to heuristic scan.")
            # Retrieve page content if possible, or fetch via HTTP
            try:
                content = await page.content()
                return self._scan_html_heuristics(content)
            except Exception:
                return await self._scan_heuristic_url(url)
        finally:
            await page.close()
            await context.close()

    async def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Scan a local source file by rendering it in headless browser or heuristic parsing."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Target file not found: {file_path}")

        file_url = path.as_uri()
        browser = await self._get_browser()

        if browser and path.suffix.lower() in [".html", ".htm"]:
            context = await browser.new_context()
            page = await context.new_page()
            try:
                await page.goto(file_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(1000)
                axe_results = await page.evaluate(AXE_LOADER_SCRIPT)
                return self.parse_axe_results(axe_results)
            except Exception as exc:
                logger.warning(f"File Playwright scan error: {exc}. Using file heuristic parser.")
            finally:
                await page.close()
                await context.close()

        # Fallback reading content directly
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return self._scan_html_heuristics(content)
        except Exception as exc:
            logger.error(f"Failed to read file for scanning: {exc}")
            return []

    def parse_axe_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform raw axe-core JSON violations into structured issue dictionaries."""
        parsed_issues: List[Dict[str, Any]] = []
        violations = results.get("violations", []) if isinstance(results, dict) else []

        for violation in violations:
            rule_id = violation.get("id", "unknown-rule")
            impact = violation.get("impact", "moderate") or "moderate"
            description = violation.get("description", "")
            help_text = violation.get("help", "")
            help_url = violation.get("helpUrl", "")
            tags = violation.get("tags", [])

            nodes = violation.get("nodes", [])
            if not nodes:
                # Capture violation even if node list is empty
                parsed_issues.append({
                    "rule_id": rule_id,
                    "impact": impact,
                    "description": description,
                    "help_text": help_text,
                    "help_url": help_url,
                    "wcag_tags": tags,
                    "html_source": "",
                    "css_selector": "",
                    "target": [],
                })
            else:
                for node in nodes:
                    html_source = node.get("html", "")
                    target = node.get("target", [])
                    css_selector = " > ".join(target) if isinstance(target, list) else str(target)
                    failure_summary = node.get("failureSummary", "")

                    detailed_desc = f"{description}. {failure_summary}".strip() if failure_summary else description

                    parsed_issues.append({
                        "rule_id": rule_id,
                        "impact": impact,
                        "description": detailed_desc,
                        "help_text": help_text,
                        "help_url": help_url,
                        "wcag_tags": tags,
                        "html_source": html_source,
                        "css_selector": css_selector,
                        "target": target if isinstance(target, list) else [str(target)],
                    })

        return parsed_issues

    async def _scan_heuristic_url(self, url: str) -> List[Dict[str, Any]]:
        """Fetch URL via httpx and run heuristic analysis when browser is unavailable."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return self._scan_html_heuristics(resp.text)
        except Exception as exc:
            logger.error(f"Heuristic URL fetch failed: {exc}")
            return []

    def _scan_html_heuristics(self, html_content: str) -> List[Dict[str, Any]]:
        """Static accessibility heuristics parser for offline/fallback operation."""
        issues: List[Dict[str, Any]] = []
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Missing page language
        html_tag = soup.find("html")
        if not html_tag or not html_tag.get("lang"):
            issues.append({
                "rule_id": "html-has-lang",
                "impact": "serious",
                "description": "<html> element must have a valid lang attribute.",
                "help_text": "Ensure <html> has lang='en' or the appropriate language code.",
                "help_url": "https://dequeuniversity.com/rules/axe/4.9/html-has-lang",
                "wcag_tags": ["wcag2a", "wcag311"],
                "html_source": str(html_tag)[:100] if html_tag else "<html>",
                "css_selector": "html",
                "target": ["html"],
            })

        # 2. Missing title
        if not soup.find("title") or not soup.find("title").get_text(strip=True):
            issues.append({
                "rule_id": "document-title",
                "impact": "serious",
                "description": "Documents must have <title> element to aid in navigation.",
                "help_text": "Add a descriptive <title> in <head>.",
                "help_url": "https://dequeuniversity.com/rules/axe/4.9/document-title",
                "wcag_tags": ["wcag2a", "wcag242"],
                "html_source": "<head></head>",
                "css_selector": "head",
                "target": ["head"],
            })

        # 3. Images missing alt
        for img in soup.find_all("img"):
            if not img.has_attr("alt"):
                issues.append({
                    "rule_id": "image-alt",
                    "impact": "critical",
                    "description": "Images must have alt attribute specifying alternate text or empty alt for decorative images.",
                    "help_text": "Provide meaningful alt text for image.",
                    "help_url": "https://dequeuniversity.com/rules/axe/4.9/image-alt",
                    "wcag_tags": ["wcag2a", "wcag111"],
                    "html_source": str(img),
                    "css_selector": f"img[src='{img.get('src', '')}']",
                    "target": [f"img[src='{img.get('src', '')}']"],
                })

        # 4. Form inputs missing labels
        labels = soup.find_all("label")
        label_for_ids = {lbl.get("for") for lbl in labels if lbl.has_attr("for")}
        for inp in soup.find_all(["input", "select", "textarea"]):
            if inp.get("type") in ["hidden", "submit", "button"]:
                continue
            inp_id = inp.get("id")
            has_label = (inp_id and inp_id in label_for_ids) or inp.find_parent("label") or inp.get("aria-label") or inp.get("aria-labelledby")
            if not has_label:
                issues.append({
                    "rule_id": "label",
                    "impact": "critical",
                    "description": "Form elements must have accessible labels.",
                    "help_text": "Associate input with <label for='...'> or aria-label.",
                    "help_url": "https://dequeuniversity.com/rules/axe/4.9/label",
                    "wcag_tags": ["wcag2a", "wcag412"],
                    "html_source": str(inp),
                    "css_selector": f"input#{inp_id}" if inp_id else "input",
                    "target": [f"input#{inp_id}" if inp_id else "input"],
                })

        # 5. Empty buttons
        for btn in soup.find_all("button"):
            if not btn.get_text(strip=True) and not btn.get("aria-label") and not btn.find("img"):
                issues.append({
                    "rule_id": "button-name",
                    "impact": "critical",
                    "description": "Buttons must have discernible text or aria-label.",
                    "help_text": "Add text or aria-label to button.",
                    "help_url": "https://dequeuniversity.com/rules/axe/4.9/button-name",
                    "wcag_tags": ["wcag2a", "wcag412"],
                    "html_source": str(btn),
                    "css_selector": "button",
                    "target": ["button"],
                })

        # 6. Links missing accessible names
        for a in soup.find_all("a"):
            if not a.get_text(strip=True) and not a.get("aria-label") and not a.find("img"):
                issues.append({
                    "rule_id": "link-name",
                    "impact": "serious",
                    "description": "Links must have discernible text.",
                    "help_text": "Provide descriptive text or aria-label for anchor link.",
                    "help_url": "https://dequeuniversity.com/rules/axe/4.9/link-name",
                    "wcag_tags": ["wcag2a", "wcag244", "wcag412"],
                    "html_source": str(a),
                    "css_selector": "a",
                    "target": ["a"],
                })

        return issues


# Singleton scanner instance
scanner = AccessibilityScanner()
