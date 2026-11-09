"""Base class for multi-language syntax plugins."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LanguagePlugin(ABC):
    """Abstract base class defining the contract for language-specific accessibility plugins."""

    @abstractmethod
    def detect(self, file_path: str) -> bool:
        """Return True if this plugin can handle the given file path or extension."""
        pass

    @abstractmethod
    def parse(self, content: str) -> Dict[str, Any]:
        """Parse source file content into a structured syntax tree representation."""
        pass

    @abstractmethod
    def extract_accessibility_elements(self, content: str) -> List[Dict[str, Any]]:
        """Extract elements relevant to accessibility checks (images, forms, buttons, links, etc.)."""
        pass

    @abstractmethod
    def apply_fix(self, content: str, fix: Dict[str, Any]) -> str:
        """Apply a suggested accessibility fix to the source code and return modified content."""
        pass

    @abstractmethod
    def get_language_name(self) -> str:
        """Return canonical language name (e.g., 'html', 'react', 'vue', 'angular')."""
        pass

    @abstractmethod
    def get_file_extensions(self) -> List[str]:
        """Return list of supported file extensions including dot (e.g. ['.html', '.htm'])."""
        pass
