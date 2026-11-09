"""Plugin registry for managing and resolving language plugins."""

import os
from typing import Dict, List, Optional
from app.plugins.base import LanguagePlugin


class PluginRegistry:
    """Thread-safe singleton registry storing active language plugins."""

    _instance: Optional["PluginRegistry"] = None

    def __new__(cls) -> "PluginRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = []
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        # Prevent re-initialization in singleton
        if getattr(self, "_initialized", False):
            return
        self._plugins: List[LanguagePlugin] = []
        self._initialized = True

    def register(self, plugin: LanguagePlugin) -> None:
        """Register a new language plugin instance if not already registered."""
        for p in self._plugins:
            if p.get_language_name().lower() == plugin.get_language_name().lower():
                # Replace with newer instance
                self._plugins.remove(p)
                break
        self._plugins.append(plugin)

    def get_plugin(self, file_path: str) -> Optional[LanguagePlugin]:
        """Resolve the appropriate LanguagePlugin for a given file path."""
        normalized_path = file_path.lower()
        # Direct detection match
        for plugin in self._plugins:
            if plugin.detect(normalized_path):
                return plugin

        # Extension match fallback
        _, ext = os.path.splitext(normalized_path)
        for plugin in self._plugins:
            if ext in plugin.get_file_extensions():
                return plugin

        # Return HTML plugin as default if available
        return self.get_plugin_by_name("html")

    def get_plugin_by_name(self, name: str) -> Optional[LanguagePlugin]:
        """Fetch plugin instance by canonical language name."""
        name_lower = name.lower()
        for plugin in self._plugins:
            if plugin.get_language_name().lower() == name_lower:
                return plugin
        return None

    def get_all_plugins(self) -> List[LanguagePlugin]:
        """Return all registered plugins."""
        return list(self._plugins)

    def detect_language(self, file_path: str) -> str:
        """Determine language identifier string for given file path."""
        plugin = self.get_plugin(file_path)
        if plugin:
            return plugin.get_language_name()
        _, ext = os.path.splitext(file_path.lower())
        if ext in [".jsx", ".tsx"]:
            return "react"
        elif ext == ".vue":
            return "vue"
        elif ".component.html" in file_path.lower() or ".component.ts" in file_path.lower():
            return "angular"
        return "html"

    def auto_discover(self) -> None:
        """Auto-discover and instantiate default plugins."""
        from app.plugins.html_plugin import HTMLPlugin
        from app.plugins.react_plugin import ReactPlugin
        from app.plugins.vue_plugin import VuePlugin
        from app.plugins.angular_plugin import AngularPlugin

        self.register(HTMLPlugin())
        self.register(ReactPlugin())
        self.register(VuePlugin())
        self.register(AngularPlugin())


plugin_registry = PluginRegistry()
