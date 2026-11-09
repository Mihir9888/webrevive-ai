"""React/JSX Language Plugin for accessibility analysis and refactoring."""

import os
import re
from typing import Any, Dict, List, Optional
from app.plugins.base import LanguagePlugin


class ReactPlugin(LanguagePlugin):
    """Plugin specialized in React JSX and TSX component refactoring."""

    def get_language_name(self) -> str:
        return "react"

    def get_file_extensions(self) -> List[str]:
        return [".jsx", ".tsx"]

    def detect(self, file_path: str) -> bool:
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.get_file_extensions()

    def parse(self, content: str) -> Dict[str, Any]:
        """Extract high-level React component structure and JSX tags."""
        components = re.findall(
            r"(?:function\s+([A-Z]\w*)|const\s+([A-Z]\w*)\s*=\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>)",
            content,
        )
        component_names = [c[0] or c[1] for c in components if c[0] or c[1]]
        has_hooks = bool(re.search(r"\buse(?:State|Effect|Context|Memo|Callback)\b", content))
        has_jsx = bool(re.search(r"<[A-Za-z0-9]+(\s+[^>]*)?>.*?</[A-Za-z0-9]+>|<[A-Za-z0-9]+[^>]*/\s*>", content, re.DOTALL))

        return {
            "type": "react_component",
            "components": component_names,
            "has_hooks": has_hooks,
            "has_jsx": has_jsx,
        }

    def extract_accessibility_elements(self, content: str) -> List[Dict[str, Any]]:
        """Extract JSX elements with accessibility relevance."""
        elements: List[Dict[str, Any]] = []

        # 1. JSX Images (<img ... />)
        img_pattern = re.compile(r"<img\b([^>]*)>", re.IGNORECASE | re.DOTALL)
        for match in img_pattern.finditer(content):
            snippet = match.group(0)
            attrs_str = match.group(1)
            has_alt = bool(re.search(r'\balt\s*=\s*(?:"[^"]*"|\'[^\']*\'|{[^}]+})', attrs_str))
            has_aria_hidden = 'aria-hidden="true"' in attrs_str or "aria-hidden={'true'}" in attrs_str

            elements.append({
                "type": "image",
                "tag": "img",
                "html": snippet,
                "has_alt": has_alt,
                "is_decorative": has_aria_hidden,
                "start": match.start(),
                "end": match.end(),
            })

        # 2. JSX Buttons & Interactive Divs
        btn_pattern = re.compile(r"<button\b([^>]*)>(.*?)</button>", re.IGNORECASE | re.DOTALL)
        for match in btn_pattern.finditer(content):
            snippet = match.group(0)
            attrs = match.group(1)
            inner = match.group(2).strip()
            has_aria = bool(re.search(r'\baria-label\s*=\s*(?:"[^"]*"|\'[^\']*\'|{[^}]+})', attrs))
            elements.append({
                "type": "button",
                "tag": "button",
                "html": snippet,
                "inner_text": inner,
                "has_aria_label": has_aria,
                "is_empty": not inner and not has_aria,
            })

        # Non-semantic clickable elements (div/span onClick without role/tabIndex)
        clickable_pattern = re.compile(r"<(div|span)\b([^>]*onClick[^>]*)>", re.IGNORECASE | re.DOTALL)
        for match in clickable_pattern.finditer(content):
            tag = match.group(1)
            attrs = match.group(2)
            has_role = "role=" in attrs
            has_tabindex = "tabIndex=" in attrs or "tabindex=" in attrs
            elements.append({
                "type": "clickable_non_semantic",
                "tag": tag,
                "html": match.group(0),
                "has_role": has_role,
                "has_tabindex": has_tabindex,
                "needs_keyboard_accessibility": not (has_role and has_tabindex),
            })

        # 3. Form elements & htmlFor labels
        input_pattern = re.compile(r"<input\b([^>]*)>", re.IGNORECASE)
        for match in input_pattern.finditer(content):
            snippet = match.group(0)
            attrs = match.group(1)
            has_id = bool(re.search(r'\bid\s*=\s*(?:"[^"]*"|\'[^\']*\'|{[^}]+})', attrs))
            has_aria_label = bool(re.search(r'\baria-label\s*=\s*(?:"[^"]*"|\'[^\']*\'|{[^}]+})', attrs))
            elements.append({
                "type": "input",
                "tag": "input",
                "html": snippet,
                "has_id": has_id,
                "has_aria_label": has_aria_label,
            })

        return elements

    def apply_fix(self, content: str, fix: Dict[str, Any]) -> str:
        """Apply JSX accessibility fix respecting React naming conventions."""
        original_code = fix.get("original_code", "").strip()
        suggested_code = fix.get("suggested_code", "").strip()

        # Enforce React standard conversions
        # class -> className, for -> htmlFor
        suggested_code = re.sub(r'\bclass\s*=', 'className=', suggested_code)
        suggested_code = re.sub(r'\bfor\s*=', 'htmlFor=', suggested_code)

        if original_code and original_code in content and suggested_code:
            return content.replace(original_code, suggested_code, 1)

        # Whitespace relaxed regex match
        if original_code and suggested_code:
            escaped = re.escape(re.sub(r"\s+", " ", original_code)).replace(r"\ ", r"\s+")
            matched = re.search(escaped, content)
            if matched:
                return content[: matched.start()] + suggested_code + content[matched.end() :]

        return content
