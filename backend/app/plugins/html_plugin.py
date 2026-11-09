"""HTML Language Plugin for accessibility analysis and refactoring."""

import os
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup, Tag

from app.plugins.base import LanguagePlugin


class HTMLPlugin(LanguagePlugin):
    """Plugin specialized in standard HTML/HTM parsing and remediation."""

    def get_language_name(self) -> str:
        return "html"

    def get_file_extensions(self) -> List[str]:
        return [".html", ".htm"]

    def detect(self, file_path: str) -> bool:
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.get_file_extensions()

    def parse(self, content: str) -> Dict[str, Any]:
        """Parse HTML content with BeautifulSoup and return document metadata."""
        soup = BeautifulSoup(content, "html.parser")
        has_doctype = bool(re.search(r"<!DOCTYPE\s+html", content, re.IGNORECASE))
        has_html = soup.find("html") is not None
        has_head = soup.find("head") is not None
        has_body = soup.find("body") is not None
        title_tag = soup.find("title")

        return {
            "type": "html_document",
            "has_doctype": has_doctype,
            "has_html": has_html,
            "has_head": has_head,
            "has_body": has_body,
            "title": title_tag.get_text(strip=True) if title_tag else None,
            "total_elements": len(soup.find_all(True)),
        }

    def extract_accessibility_elements(self, content: str) -> List[Dict[str, Any]]:
        """Extract all accessibility-sensitive elements from HTML."""
        soup = BeautifulSoup(content, "html.parser")
        elements: List[Dict[str, Any]] = []

        # 1. Images
        for img in soup.find_all("img"):
            has_alt = img.has_attr("alt")
            alt_val = img.get("alt", "")
            elements.append({
                "type": "image",
                "tag": "img",
                "html": str(img),
                "src": img.get("src", ""),
                "alt": alt_val if has_alt else None,
                "has_alt": has_alt,
                "is_empty_alt": has_alt and not alt_val.strip(),
                "role": img.get("role"),
            })

        # 2. Form controls
        labels = soup.find_all("label")
        label_for_map = {lbl.get("for"): lbl.get_text(strip=True) for lbl in labels if lbl.has_attr("for")}

        for form_control in soup.find_all(["input", "select", "textarea"]):
            # Ignore hidden inputs
            if form_control.get("type") == "hidden":
                continue

            elem_id = form_control.get("id")
            has_explicit_label = elem_id in label_for_map if elem_id else False
            has_parent_label = form_control.find_parent("label") is not None
            aria_label = form_control.get("aria-label")
            aria_labelledby = form_control.get("aria-labelledby")
            has_label = has_explicit_label or has_parent_label or bool(aria_label) or bool(aria_labelledby)

            elements.append({
                "type": "form_control",
                "tag": form_control.name,
                "html": str(form_control),
                "name": form_control.get("name"),
                "id": elem_id,
                "input_type": form_control.get("type", "text"),
                "has_label": has_label,
                "aria_label": aria_label,
            })

        # 3. Headings structure
        headings = soup.find_all(re.compile(r"^h[1-6]$"))
        heading_structure = []
        for h in headings:
            level = int(h.name[1])
            heading_structure.append({
                "type": "heading",
                "tag": h.name,
                "level": level,
                "text": h.get_text(strip=True),
                "html": str(h),
            })
        elements.extend(heading_structure)

        # 4. Links and Buttons
        for a in soup.find_all("a"):
            text = a.get_text(strip=True)
            aria_label = a.get("aria-label")
            href = a.get("href")
            elements.append({
                "type": "link",
                "tag": "a",
                "html": str(a),
                "href": href,
                "text": text,
                "aria_label": aria_label,
                "is_empty": not text and not aria_label and not a.find("img"),
                "is_generic_text": text.lower() in ["click here", "read more", "more", "learn more", "here"],
            })

        for btn in soup.find_all("button"):
            text = btn.get_text(strip=True)
            aria_label = btn.get("aria-label")
            elements.append({
                "type": "button",
                "tag": "button",
                "html": str(btn),
                "text": text,
                "aria_label": aria_label,
                "is_empty": not text and not aria_label and not btn.find("img"),
            })

        # 5. Tables
        for tbl in soup.find_all("table"):
            has_caption = tbl.find("caption") is not None
            has_th = tbl.find("th") is not None
            elements.append({
                "type": "table",
                "tag": "table",
                "html": str(tbl)[:200] + "...",
                "has_caption": has_caption,
                "has_headers": has_th,
            })

        return elements

    def apply_fix(self, content: str, fix: Dict[str, Any]) -> str:
        """Apply accessibility remediation fix to HTML content."""
        original_code = fix.get("original_code", "").strip()
        suggested_code = fix.get("suggested_code", "").strip()

        # Direct string replacement strategy
        if original_code and original_code in content and suggested_code:
            return content.replace(original_code, suggested_code, 1)

        # Selector-based attribute mutation strategy
        css_selector = fix.get("css_selector")
        attributes_to_add = fix.get("attributes", {})

        if css_selector and attributes_to_add:
            soup = BeautifulSoup(content, "html.parser")
            try:
                target_node = soup.select_one(css_selector)
                if target_node and isinstance(target_node, Tag):
                    for attr_name, attr_val in attributes_to_add.items():
                        target_node[attr_name] = attr_val
                    return str(soup)
            except Exception:
                pass

        # Normalized whitespace string match fallback
        if original_code and suggested_code:
            pattern = re.escape(re.sub(r"\s+", " ", original_code)).replace(r"\ ", r"\s+")
            matched = re.search(pattern, content)
            if matched:
                return content[: matched.start()] + suggested_code + content[matched.end() :]

        return content
