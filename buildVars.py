# -*- coding: UTF-8 -*-
# Build variables for BrailleLanguageSwitcher NVDA add-on

addon_info = {
    "addon_name": "brailleLanguageSwitcher",
    "addon_summary": "Braille Language Switcher",
    "addon_description": "Automatically switches braille output tables based on document language tags. Works independently of speech by reading language markup directly from documents.",
    "addon_version": "1.1.0",
    "addon_author": "Tobias",
    "addon_url": "https://github.com/heath-toby/brailleLanguageSwitcher",
    "addon_docFileName": "readme.md",
    "addon_minimumNVDAVersion": "2024.1.0",
    "addon_lastTestedNVDAVersion": "2026.1",
}

# Files that contain translatable strings
i18nSources = ["addon/globalPlugins/brailleLanguageSwitcher/*.py"]

# Markdown documentation files
markdownFiles = ["addon/doc/*/readme.md"]
