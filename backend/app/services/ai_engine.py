"""AI Engine service for accessibility remediation powered by Ollama."""

import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIEngine:
    """Interfaces with local Ollama LLM to generate accessibility diagnoses and refactorings."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS

    async def _call_ollama(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> str:
        """Execute a completion query against local Ollama API."""
        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()

    async def analyze_issue(self, issue: Dict[str, Any], source_code: str) -> Dict[str, Any]:
        """Analyze a single accessibility violation and produce explanation and recommended fix."""
        rule_id = issue.get("rule_id", "accessibility-violation")
        impact = issue.get("impact", "moderate")
        description = issue.get("description", "")
        html_snippet = issue.get("html_source", "") or source_code

        system_prompt = (
            "You are an expert Web Accessibility (WCAG 2.1 AA) and Frontend Refactoring engineer. "
            "Analyze the violation and propose an exact remediation code snippet. "
            "Respond in JSON format with keys: 'explanation' (string) and 'suggested_fix' (string code snippet)."
        )

        user_prompt = f"""
Accessibility Issue Detected:
- Rule: {rule_id}
- Impact: {impact}
- Description: {description}

Offending Code Snippet:
```html
{html_snippet}
```

Full Context (if available):
```html
{source_code[:1000]}
```

Provide the explanation of the barrier to disabled users, and the corrected code snippet that resolves the WCAG violation.
"""
        try:
            raw_response = await self._call_ollama(user_prompt, system=system_prompt, json_mode=True)
            try:
                parsed = json.loads(raw_response)
                return {
                    "explanation": parsed.get("explanation", description),
                    "suggested_fix": parsed.get("suggested_fix", html_snippet),
                    "rule_id": rule_id,
                }
            except json.JSONDecodeError:
                return {
                    "explanation": raw_response,
                    "suggested_fix": self._extract_code_block(raw_response) or html_snippet,
                    "rule_id": rule_id,
                }
        except Exception as exc:
            logger.warning(f"Ollama call failed ({exc}). Using rule-based intelligent remediation.")
            return self._heuristic_remediation(issue, source_code)

    async def generate_fix(
        self, issue: Dict[str, Any], code_context: str, language: str = "html"
    ) -> Dict[str, Any]:
        """Generate a production-ready refactored code patch for a detected issue."""
        rule_id = issue.get("rule_id", "wcag-rule")
        original_code = issue.get("html_source") or code_context

        system_prompt = (
            f"You are an expert {language.upper()} and Web Accessibility engineer. "
            "Generate an exact code replacement. Output strictly JSON with keys: "
            "'original_code' (the exact snippet to replace), "
            "'suggested_code' (the accessible replacement), "
            "'explanation' (why this fix satisfies WCAG), "
            "'confidence_score' (number between 0.1 and 1.0)."
        )

        user_prompt = f"""
Language: {language}
Rule: {rule_id}
Impact: {issue.get('impact', 'serious')}
Description: {issue.get('description', '')}

Offending element:
{original_code}

Relevant context:
{code_context[:800]}

Generate the JSON response with corrected, fully accessible code.
"""

        try:
            raw_response = await self._call_ollama(user_prompt, system=system_prompt, json_mode=True)
            try:
                parsed = json.loads(raw_response)
                return {
                    "original_code": parsed.get("original_code") or original_code,
                    "suggested_code": parsed.get("suggested_code") or original_code,
                    "explanation": parsed.get("explanation", f"Fixed {rule_id} violation according to WCAG 2.1 AA."),
                    "confidence_score": float(parsed.get("confidence_score", 0.9)),
                    "language": language,
                }
            except json.JSONDecodeError:
                suggested = self._extract_code_block(raw_response) or original_code
                return {
                    "original_code": original_code,
                    "suggested_code": suggested,
                    "explanation": raw_response,
                    "confidence_score": 0.8,
                    "language": language,
                }
        except Exception as exc:
            logger.warning(f"Ollama unavailable for fix generation: {exc}. Using heuristic fix.")
            return self._heuristic_fix_generator(issue, code_context, language)

    async def batch_analyze(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a list of accessibility violations in batch."""
        results: List[Dict[str, Any]] = []
        for issue in issues:
            source = issue.get("html_source", "")
            res = await self.generate_fix(issue, source, language="html")
            results.append(res)
        return results

    async def stream_fix(
        self, issue: Dict[str, Any], code_context: str, language: str = "html"
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response tokens for live UI feedback."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"Fix accessibility issue {issue.get('rule_id')} in {language}:\n{issue.get('html_source')}",
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    async for chunk in response.aiter_lines():
                        if not chunk.strip():
                            continue
                        try:
                            data = json.loads(chunk)
                            yield data.get("response", "")
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            yield f"Streaming error: {exc}"

    def _extract_code_block(self, text: str) -> Optional[str]:
        """Extract code from markdown code fences if present."""
        match = re.search(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _heuristic_remediation(self, issue: Dict[str, Any], source_code: str) -> Dict[str, Any]:
        """Rule-based remediation fallback when LLM is offline."""
        fix_info = self._heuristic_fix_generator(issue, source_code, "html")
        return {
            "explanation": fix_info["explanation"],
            "suggested_fix": fix_info["suggested_code"],
            "rule_id": issue.get("rule_id", "wcag-violation"),
        }

    def _heuristic_fix_generator(
        self, issue: Dict[str, Any], code_context: str, language: str
    ) -> Dict[str, Any]:
        """Generate high-precision rule-based fixes for standard WCAG rules."""
        rule_id = issue.get("rule_id", "")
        original_code = issue.get("html_source") or code_context or ""
        suggested_code = original_code
        explanation = f"Remediated {rule_id} according to WCAG 2.1 AA guidelines."

        if rule_id == "image-alt":
            if "<img" in original_code and "alt=" not in original_code:
                suggested_code = re.sub(r"<img\b", '<img alt="Descriptive illustration"', original_code, count=1)
                explanation = "Added alt attribute describing image content for screen readers (WCAG 1.1.1)."
            elif 'alt=""' in original_code:
                suggested_code = original_code.replace('alt=""', 'alt="Meaningful description"')
                explanation = "Replaced empty alt attribute with meaningful alternate text."

        elif rule_id == "html-has-lang":
            if "<html" in original_code and "lang=" not in original_code:
                suggested_code = re.sub(r"<html\b", '<html lang="en"', original_code, count=1)
                explanation = "Added lang='en' attribute to root <html> tag for speech synthesizers (WCAG 3.1.1)."
            else:
                suggested_code = '<html lang="en">'

        elif rule_id in ["label", "form-field-multiple-labels"]:
            if "<input" in original_code and "aria-label" not in original_code:
                suggested_code = re.sub(r"<input\b", '<input aria-label="Input field"', original_code, count=1)
                explanation = "Added aria-label attribute to provide an accessible name for screen readers (WCAG 4.1.2)."

        elif rule_id in ["button-name", "link-name"]:
            if "<button" in original_code and "aria-label" not in original_code:
                suggested_code = re.sub(r"<button\b", '<button aria-label="Perform action"', original_code, count=1)
                explanation = "Added aria-label to ensure assistive technology announces button purpose (WCAG 4.1.2)."
            elif "<a" in original_code and "aria-label" not in original_code:
                suggested_code = re.sub(r"<a\b", '<a aria-label="Navigate to section"', original_code, count=1)
                explanation = "Added aria-label to anchor element for clear navigation context."

        elif rule_id == "document-title":
            suggested_code = "<title>Accessible Web Application - WebRevive</title>"
            explanation = "Added a descriptive document <title> inside <head> (WCAG 2.4.2)."

        elif rule_id == "color-contrast":
            suggested_code = original_code + ' <!-- Note: Ensure minimum 4.5:1 contrast ratio -->'
            explanation = "Ensure text and interactive foreground elements have at least 4.5:1 contrast ratio (WCAG 1.4.3)."

        else:
            # Generic accessibility enhancement: add role or aria-label
            if "<" in original_code and ">" in original_code and "aria-label" not in original_code:
                tag_match = re.match(r"<([a-zA-Z0-9]+)\b", original_code)
                if tag_match:
                    tag = tag_match.group(1)
                    suggested_code = original_code.replace(f"<{tag}", f'<{tag} aria-label="Accessible element"', 1)
                    explanation = f"Added accessible label to <{tag}> element."

        return {
            "original_code": original_code,
            "suggested_code": suggested_code,
            "explanation": explanation,
            "confidence_score": 0.88,
            "language": language,
        }


ai_engine = AIEngine()
