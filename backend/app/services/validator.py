"""Validation service comparing accessibility status before and after refactoring."""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.scanner import scanner

logger = logging.getLogger(__name__)


class Validator:
    """Verifies that refactored source code eliminates accessibility violations without introducing regressions."""

    def __init__(self) -> None:
        self.scanner = scanner

    async def validate_refactoring(
        self,
        scan_id: int,
        original_issues: List[Dict[str, Any]],
        modified_code: str,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform a comparative re-scan of modified source code against original baseline violations."""
        # 1. Re-scan modified code
        new_issues: List[Dict[str, Any]] = []

        if modified_code.strip():
            # Create a temporary file to run scan_file through Playwright / heuristics
            suffix = Path(file_path).suffix if file_path else ".html"
            with tempfile.NamedTemporaryFile("w", suffix=suffix, encoding="utf-8", delete=False) as tmp:
                tmp.write(modified_code)
                tmp_path = tmp.name

            try:
                new_issues = await self.scanner.scan_file(tmp_path)
            finally:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass
        elif file_path and Path(file_path).exists():
            new_issues = await self.scanner.scan_file(file_path)

        # 2. Build fingerprints for matching (rule_id + target/css_selector)
        def make_key(issue: Dict[str, Any]) -> str:
            rule = issue.get("rule_id", "")
            selector = issue.get("css_selector", "") or str(issue.get("target", ""))
            return f"{rule}::{selector}"

        original_map = {make_key(i): i for i in original_issues}
        new_map = {make_key(i): i for i in new_issues}

        issues_fixed: List[Dict[str, Any]] = []
        issues_remaining: List[Dict[str, Any]] = []
        regressions: List[Dict[str, Any]] = []

        for key, orig_issue in original_map.items():
            if key in new_map:
                issues_remaining.append(orig_issue)
            else:
                issues_fixed.append(orig_issue)

        for key, fresh_issue in new_map.items():
            if key not in original_map:
                regressions.append(fresh_issue)

        passed = (len(issues_fixed) > 0 and len(regressions) == 0) or (len(new_issues) == 0)

        result = {
            "scan_id": scan_id,
            "passed": passed,
            "issues_fixed": issues_fixed,
            "issues_remaining": issues_remaining,
            "new_issues": regressions,
            "fixed_count": len(issues_fixed),
            "remaining_count": len(issues_remaining),
            "new_count": len(regressions),
            "details": f"Successfully resolved {len(issues_fixed)} issue(s). {len(issues_remaining)} remaining, {len(regressions)} new regression(s).",
        }

        logger.info(
            f"Scan #{scan_id} validation complete. Passed={passed}, Fixed={len(issues_fixed)}, Remaining={len(issues_remaining)}, Regressions={len(regressions)}"
        )
        return result


validator = Validator()
