# -*- coding: UTF-8 -*-
# Build variables for BrailleLanguageSwitcher NVDA add-on

addon_info = {
    "addon_name": "brailleLanguageSwitcher",
    "addon_summary": "Braille Language Switcher",
    "addon_description": "Automatically switches braille output tables based on detected text language. Integrates with Enhanced Language Switching add-on when available.",
    "addon_version": "1.0.0",
    "addon_author": "Tobias <your.email@example.com>",
    "addon_url": "https://github.com/yourusername/brailleLanguageSwitcher",
    "addon_docFileName": "readme.md",
    "addon_minimumNVDAVersion": "2024.1.0",
    "addon_lastTestedNVDAVersion": "2025.1.0",
}

# Files that contain translatable strings
i18nSources = ["addon/globalPlugins/brailleLanguageSwitcher/*.py"]

# Markdown documentation files
markdownFiles = ["addon/doc/*/readme.md"]
