# -*- coding: UTF-8 -*-
# Build variables for BrailleLanguageSwitcher NVDA add-on

addon_info = {
    "addon_name": "brailleLanguageSwitcher",
    "addon_summary": "Braille Language Switcher",
    "addon_description": "Automatically switches braille output and input tables when the language changes: shows each language on a line in its own braille table, using Dialingo or Enhanced Language Detection, with the input table following the language at the cursor.",
    "addon_version": "2.0.0",
    "addon_author": "Tobias",
    "addon_url": "https://github.com/heath-toby/brailleLanguageSwitcher",
    "addon_docFileName": "readme.md",
    "addon_minimumNVDAVersion": "2024.3.0",
    "addon_lastTestedNVDAVersion": "2026.3",
}

# Files that contain translatable strings
i18nSources = ["addon/globalPlugins/brailleLanguageSwitcher/*.py"]

# Markdown documentation files
markdownFiles = ["addon/doc/*/readme.md"]
