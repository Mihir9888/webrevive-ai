"""Source code analysis and contextual extraction service."""

import logging
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup, Tag

from app.plugins.registry import plugin_registry

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """Extracts contextual snippets and semantic structures from multi-language source files."""

    def __init__(self) -> None:
        self.registry = plugin_registry

    def detect_language(self, file_path: str) -> str:
        """Identify language identifier (html, react, vue, angular) from file extension or content."""
        return self.registry.detect_language(file_path)

    def analyze_html(self, html_content: str, css_selector: str) -> Dict[str, Any]:
        """Analyze an HTML document to locate and extract details for a specific CSS selector."""
        soup = BeautifulSoup(html_content, "html.parser")
        node: Optional[Tag] = None

        if css_selector:
            try:
                node = soup.select_one(css_selector)
            except Exception as exc:
                logger.debug(f"Selector query error for '{css_selector}': {exc}")

        if not node:
            # Fallback regex search if selector is a tag or simple attribute
            cleaned = css_selector.strip().split(">")[-1].strip()
            try:
                node = soup.select_one(cleaned)
            except Exception:
                node = None

        if node:
            parent_tag = node.parent.name if node.parent else None
            children_tags = [c.name for c in node.find_all(True, recursive=False)]
            return {
                "found": True,
                "tag": node.name,
                "attributes": node.attrs,
                "outer_html": str(node),
                "inner_text": node.get_text(strip=True),
                "parent_tag": parent_tag,
                "children_count": len(children_tags),
            }

        return {
            "found": False,
            "tag": None,
            "attributes": {},
            "outer_html": "",
            "inner_text": "",
            "parent_tag": None,
            "children_count": 0,
        }

    def get_code_context(
        self,
        file_content: str,
        selector_or_snippet: str,
        language: str = "html",
        context_lines: int = 5,
    ) -> str:
        """Extract lines of code surrounding an accessibility issue target for LLM comprehension."""
        if not file_content:
            return ""

        lines = file_content.splitlines()

        # If selector is a CSS selector and language is HTML, attempt to find exact outer HTML first
        target_str = selector_or_snippet
        if language == "html" and (">" in selector_or_snippet or "." in selector_or_snippet or "#" in selector_or_snippet):
            analysis = self.analyze_html(file_content, selector_or_snippet)
            if analysis.get("found") and analysis.get("outer_html"):
                target_str = analysis["outer_html"].splitlines()[0]

        # Locate matching line index
        target_line_idx = -1
        cleaned_target = target_str.strip()

        if cleaned_target:
            for idx, line in enumerate(lines):
                if cleaned_target in line or (len(cleaned_target) > 20 and cleaned_target[:20] in line):
                    target_line_idx = idx
                    break

        # Fallback search if exact line wasn't found
        if target_line_idx == -1:
            # Return first N lines if target cannot be located
            return "\n".join(lines[: context_lines * 2])

        start_idx = max(0, target_line_idx - context_lines)
        end_idx = min(len(lines), target_line_idx + context_lines + 1)

        numbered_lines = []
        for i in range(start_idx, end_idx):
            marker = ">>" if i == target_line_idx else "  "
            numbered_lines.append(f"{marker} {i + 1:4d} | {lines[i]}")

        return "\n".join(numbered_lines)

    def extract_language_elements(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Dispatch element extraction to the appropriate LanguagePlugin."""
        plugin = self.registry.get_plugin(file_path)
        if plugin:
            return plugin.extract_accessibility_elements(content)
        return []


code_analyzer = CodeAnalyzer()
