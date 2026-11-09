"""Angular Language Plugin for template and component refactoring."""

import os
import re
from typing import Any, Dict, List, Optional
from app.plugins.base import LanguagePlugin


class AngularPlugin(LanguagePlugin):
    """Plugin specialized in Angular component templates (.component.html) and TypeScript."""

    def get_language_name(self) -> str:
        return "angular"

    def get_file_extensions(self) -> List[str]:
        return [".component.html", ".component.ts"]

    def detect(self, file_path: str) -> bool:
        path_lower = file_path.lower()
        if path_lower.endswith(".component.html") or path_lower.endswith(".component.ts"):
            return True
        return False

    def parse(self, content: str) -> Dict[str, Any]:
        """Detect Angular metadata and template directives."""
        is_ts_component = "@Component(" in content
        has_ng_directives = bool(re.search(r"\*(?:ngIf|ngFor|ngSwitch)", content))
        has_event_bindings = bool(re.search(r"\([a-zA-Z]+\)\s*=", content))
        has_property_bindings = bool(re.search(r"\[(?:[a-zA-Z0-9.-]+)\]\s*=", content))

        return {
            "type": "angular_template" if not is_ts_component else "angular_ts_component",
            "is_ts": is_ts_component,
            "has_ng_directives": has_ng_directives,
            "has_event_bindings": has_event_bindings,
            "has_property_bindings": has_property_bindings,
        }

    def extract_accessibility_elements(self, content: str) -> List[Dict[str, Any]]:
        """Extract accessibility elements with Angular syntax consideration."""
        elements: List[Dict[str, Any]] = []

        # 1. Images with Angular property or attribute binding
        img_pattern = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
        for match in img_pattern.finditer(content):
            attrs = match.group(1)
            has_alt = bool(re.search(r'(?:\[alt\]|\[attr\.alt\]|\balt)\s*=', attrs))
            elements.append({
                "type": "image",
                "tag": "img",
                "html": match.group(0),
                "has_alt": has_alt,
            })

        # 2. Angular Buttons and (click) handlers
        btn_pattern = re.compile(r"<(?:button|mat-button|a)\b([^>]*)>(.*?)</(?:button|mat-button|a)>", re.IGNORECASE | re.DOTALL)
        for match in btn_pattern.finditer(content):
            attrs = match.group(1)
            inner = match.group(2).strip()
            has_aria = bool(re.search(r'(?:\[attr\.aria-label\]|aria-label)\s*=', attrs))
            elements.append({
                "type": "button_or_link",
                "html": match.group(0),
                "inner_text": inner,
                "has_aria_label": has_aria,
                "is_empty": not inner and not has_aria,
            })

        # 3. Angular Forms: [(ngModel)], formControlName
        input_pattern = re.compile(r"<(?:input|mat-input|textarea)\b([^>]*)>", re.IGNORECASE)
        for match in input_pattern.finditer(content):
            attrs = match.group(1)
            has_aria = bool(re.search(r'(?:\[attr\.aria-label\]|aria-label)\s*=', attrs))
            has_id = bool(re.search(r'\bid\s*=', attrs))
            elements.append({
                "type": "input",
                "html": match.group(0),
                "has_accessible_name": has_aria or has_id,
            })

        return elements

    def apply_fix(self, content: str, fix: Dict[str, Any]) -> str:
        """Apply Angular accessibility remediation."""
        original_code = fix.get("original_code", "").strip()
        suggested_code = fix.get("suggested_code", "").strip()

        if original_code and original_code in content and suggested_code:
            return content.replace(original_code, suggested_code, 1)

        if original_code and suggested_code:
            escaped = re.escape(re.sub(r"\s+", " ", original_code)).replace(r"\ ", r"\s+")
            matched = re.search(escaped, content)
            if matched:
                return content[: matched.start()] + suggested_code + content[matched.end() :]

        return content
