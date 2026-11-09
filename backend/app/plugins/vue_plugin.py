"""Vue Single File Component (SFC) Language Plugin."""

import os
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from app.plugins.base import LanguagePlugin


class VuePlugin(LanguagePlugin):
    """Plugin specialized in Vue Single File Components (.vue)."""

    def get_language_name(self) -> str:
        return "vue"

    def get_file_extensions(self) -> List[str]:
        return [".vue"]

    def detect(self, file_path: str) -> bool:
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.get_file_extensions()

    def parse(self, content: str) -> Dict[str, Any]:
        """Separate Vue SFC into template, script, and style blocks."""
        template_match = re.search(r"<template\b[^>]*>(.*?)</template>", content, re.DOTALL)
        script_match = re.search(r"<script\b[^>]*>(.*?)</script>", content, re.DOTALL)
        style_match = re.search(r"<style\b[^>]*>(.*?)</style>", content, re.DOTALL)

        return {
            "type": "vue_sfc",
            "has_template": bool(template_match),
            "has_script": bool(script_match),
            "has_style": bool(style_match),
            "template_content": template_match.group(1) if template_match else "",
        }

    def extract_accessibility_elements(self, content: str) -> List[Dict[str, Any]]:
        """Extract accessibility elements specifically within the Vue <template> block."""
        elements: List[Dict[str, Any]] = []
        parsed = self.parse(content)
        template_str = parsed.get("template_content", "")
        if not template_str:
            return elements

        # 1. Images with static or dynamic bindings
        img_pattern = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
        for match in img_pattern.finditer(template_str):
            attrs = match.group(1)
            has_static_alt = bool(re.search(r'\balt\s*=', attrs))
            has_bound_alt = bool(re.search(r'(?::alt|v-bind:alt)\s*=', attrs))
            elements.append({
                "type": "image",
                "tag": "img",
                "html": match.group(0),
                "has_alt": has_static_alt or has_bound_alt,
                "is_dynamic": has_bound_alt,
            })

        # 2. Buttons with @click or v-on:click
        btn_pattern = re.compile(r"<(?:button|[a-z0-9-]+-btn)\b([^>]*)>(.*?)</(?:button|[a-z0-9-]+-btn)>", re.IGNORECASE | re.DOTALL)
        for match in btn_pattern.finditer(template_str):
            attrs = match.group(1)
            inner = match.group(2).strip()
            has_aria = bool(re.search(r'(?::aria-label|aria-label|v-bind:aria-label)\s*=', attrs))
            elements.append({
                "type": "button",
                "html": match.group(0),
                "inner_text": inner,
                "has_aria_label": has_aria,
                "is_empty": not inner and not has_aria,
            })

        # 3. Form inputs with v-model
        input_pattern = re.compile(r"<input\b([^>]*)>", re.IGNORECASE)
        for match in input_pattern.finditer(template_str):
            attrs = match.group(1)
            has_vmodel = bool(re.search(r'\bv-model(?:\.[a-z]+)?\s*=', attrs))
            has_aria = bool(re.search(r'(?::aria-label|aria-label)\s*=', attrs))
            has_id = bool(re.search(r'\bid\s*=', attrs))
            elements.append({
                "type": "input",
                "html": match.group(0),
                "has_vmodel": has_vmodel,
                "has_label_or_aria": has_aria or has_id,
            })

        return elements

    def apply_fix(self, content: str, fix: Dict[str, Any]) -> str:
        """Apply accessibility remediation in Vue syntax."""
        original_code = fix.get("original_code", "").strip()
        suggested_code = fix.get("suggested_code", "").strip()

        # If fix is provided as string replacement
        if original_code and original_code in content and suggested_code:
            return content.replace(original_code, suggested_code, 1)

        # Whitespace relaxed regex match
        if original_code and suggested_code:
            escaped = re.escape(re.sub(r"\s+", " ", original_code)).replace(r"\ ", r"\s+")
            matched = re.search(escaped, content)
            if matched:
                return content[: matched.start()] + suggested_code + content[matched.end() :]

        return content
