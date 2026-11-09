"""Code refactoring service applying patches, generating diffs, and managing backups."""

import difflib
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional
from bs4 import BeautifulSoup

from app.plugins.registry import plugin_registry

logger = logging.getLogger(__name__)


class CodeRefactorer:
    """Applies accessibility code transformations, tracks diffs, and provides rollback safety."""

    def __init__(self) -> None:
        self.registry = plugin_registry

    def generate_diff(
        self, original: str, modified: str, fromfile: str = "original", tofile: str = "refactored"
    ) -> str:
        """Produce standard unified diff text comparing original and modified source content."""
        orig_lines = original.splitlines(keepends=True)
        mod_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=fromfile,
            tofile=tofile,
            lineterm="\n",
        )
        return "".join(diff)

    def apply_fix(
        self,
        original_code: str,
        suggested_code: str,
        target_selector: str = "",
        language: str = "html",
    ) -> Dict[str, Any]:
        """Apply an individual fix using the matching language plugin or BeautifulSoup."""
        if not original_code or not suggested_code:
            return {
                "success": False,
                "modified_code": original_code,
                "diff": "",
                "error": "Empty original or suggested code provided.",
            }

        plugin = self.registry.get_plugin_by_name(language)
        fix_dict = {
            "original_code": original_code,
            "suggested_code": suggested_code,
            "css_selector": target_selector,
        }

        modified_code = original_code
        if plugin:
            try:
                modified_code = plugin.apply_fix(original_code, fix_dict)
            except Exception as exc:
                logger.warning(f"Plugin {language} fix failed: {exc}. Trying fallback replacement.")

        # If plugin didn't change content or wasn't found, perform robust string substitution
        if modified_code == original_code:
            if original_code in original_code:  # simple replacement if exact snippet
                if suggested_code != original_code:
                    modified_code = suggested_code

        diff_str = self.generate_diff(original_code, modified_code)
        success = (modified_code != original_code)

        return {
            "success": success,
            "modified_code": modified_code,
            "diff": diff_str,
            "error": None if success else "No changes could be applied.",
        }

    def apply_fix_to_file(
        self,
        file_path: str,
        original_snippet: str,
        suggested_snippet: str,
        selector: str = "",
    ) -> Dict[str, Any]:
        """Apply accessibility transformation directly to a local file with automatic backup."""
        path = Path(file_path).resolve()
        if not path.exists():
            return {
                "success": False,
                "error": f"File does not exist: {file_path}",
                "diff": "",
                "backup_path": None,
            }

        original_content = path.read_text(encoding="utf-8", errors="replace")
        language = self.registry.detect_language(file_path)

        # Create safety backup
        backup_path = self.create_backup(str(path))

        plugin = self.registry.get_plugin(file_path)
        fix_dict = {
            "original_code": original_snippet,
            "suggested_code": suggested_snippet,
            "css_selector": selector,
        }

        if plugin:
            modified_content = plugin.apply_fix(original_content, fix_dict)
        else:
            modified_content = original_content.replace(original_snippet, suggested_snippet, 1)

        diff = self.generate_diff(original_content, modified_content, fromfile=path.name, tofile=f"{path.name} (refactored)")

        if modified_content != original_content:
            path.write_text(modified_content, encoding="utf-8")
            return {
                "success": True,
                "error": None,
                "diff": diff,
                "backup_path": backup_path,
                "modified_file": str(path),
            }
        else:
            return {
                "success": False,
                "error": "Pattern not found in source file; content unchanged.",
                "diff": "",
                "backup_path": backup_path,
                "modified_file": str(path),
            }

    def create_backup(self, file_path: str) -> str:
        """Create a timestamped backup copy of a target file."""
        src = Path(file_path).resolve()
        backup_dir = src.parent / ".webrevive_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time())
        backup_file = backup_dir / f"{src.name}.bak.{timestamp}"
        shutil.copy2(src, backup_file)
        logger.info(f"Created safety backup at {backup_file}")
        return str(backup_file)

    def rollback(self, backup_path: str, target_path: str) -> bool:
        """Restore a previously saved backup file over the target file."""
        b_path = Path(backup_path).resolve()
        t_path = Path(target_path).resolve()

        if not b_path.exists():
            logger.error(f"Cannot rollback: backup file does not exist: {backup_path}")
            return False

        try:
            shutil.copy2(b_path, t_path)
            logger.info(f"Successfully restored {target_path} from backup {backup_path}")
            return True
        except Exception as exc:
            logger.error(f"Rollback operation failed: {exc}")
            return False


code_refactorer = CodeRefactorer()
