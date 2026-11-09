"""Plugins initialization and automatic registry configuration."""

from app.plugins.base import LanguagePlugin
from app.plugins.registry import PluginRegistry, plugin_registry
from app.plugins.html_plugin import HTMLPlugin
from app.plugins.react_plugin import ReactPlugin
from app.plugins.vue_plugin import VuePlugin
from app.plugins.angular_plugin import AngularPlugin

# Initialize and register default plugins
plugin_registry.register(HTMLPlugin())
plugin_registry.register(ReactPlugin())
plugin_registry.register(VuePlugin())
plugin_registry.register(AngularPlugin())

__all__ = [
    "LanguagePlugin",
    "PluginRegistry",
    "plugin_registry",
    "HTMLPlugin",
    "ReactPlugin",
    "VuePlugin",
    "AngularPlugin",
]
