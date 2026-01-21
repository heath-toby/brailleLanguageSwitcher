# -*- coding: UTF-8 -*-
# BrailleLanguageSwitcher: Braille Table Manager
# Handles discovery and enumeration of available braille tables

import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import brailleTables
from logHandler import log

# Table type constants
TABLE_TYPE_UNCONTRACTED = 0
TABLE_TYPE_CONTRACTED = 1
TABLE_TYPE_COMPUTER = 2


@dataclass
class TableInfo:
    """Information about a braille table."""
    fileName: str
    displayName: str
    contracted: bool
    output: bool
    input: bool
    languageCode: Optional[str] = None


class BrailleTableManager:
    """
    Manages braille table discovery and selection.

    Enumerates available braille tables from NVDA and organizes them
    by language and table type.
    """

    # Pattern to extract language codes from table filenames
    # Matches: en-ueb-g2.ctb, de-g0.utb, fr-bfu-comp8.utb, etc.
    LANG_CODE_PATTERN = re.compile(r'^([a-z]{2,3})(?:-|_|$)')

    # Mapping of common language codes to display names
    # This is used when we can't get the name from NVDA
    LANGUAGE_NAMES: Dict[str, str] = {
        "af": "Afrikaans",
        "ar": "Arabic",
        "as": "Assamese",
        "awa": "Awadhi",
        "be": "Belarusian",
        "bg": "Bulgarian",
        "bh": "Bihari",
        "bn": "Bengali",
        "bo": "Tibetan",
        "bra": "Braj",
        "ca": "Catalan",
        "chr": "Cherokee",
        "ckb": "Central Kurdish",
        "cs": "Czech",
        "cy": "Welsh",
        "da": "Danish",
        "de": "German",
        "dra": "Dravidian",
        "el": "Greek",
        "en": "English",
        "eo": "Esperanto",
        "es": "Spanish",
        "et": "Estonian",
        "ethio": "Ethiopic",
        "fa": "Persian",
        "fi": "Finnish",
        "fr": "French",
        "ga": "Irish",
        "gd": "Scottish Gaelic",
        "gez": "Ge'ez",
        "gon": "Gondi",
        "gr": "Greek",
        "gu": "Gujarati",
        "haw": "Hawaiian",
        "he": "Hebrew",
        "hi": "Hindi",
        "hr": "Croatian",
        "hu": "Hungarian",
        "hy": "Armenian",
        "is": "Icelandic",
        "it": "Italian",
        "iu": "Inuktitut",
        "ja": "Japanese",
        "ka": "Georgian",
        "kha": "Khasi",
        "kk": "Kazakh",
        "km": "Khmer",
        "kn": "Kannada",
        "ko": "Korean",
        "kok": "Konkani",
        "kru": "Kurukh",
        "ks": "Kashmiri",
        "lt": "Lithuanian",
        "lv": "Latvian",
        "mg": "Malagasy",
        "mi": "Maori",
        "ml": "Malayalam",
        "mn": "Mongolian",
        "mni": "Manipuri",
        "mr": "Marathi",
        "ms": "Malay",
        "mt": "Maltese",
        "mun": "Munda",
        "mwr": "Marwari",
        "my": "Burmese",
        "ne": "Nepali",
        "nl": "Dutch",
        "no": "Norwegian",
        "or": "Oriya",
        "pa": "Punjabi",
        "pi": "Pali",
        "pl": "Polish",
        "pt": "Portuguese",
        "ro": "Romanian",
        "ru": "Russian",
        "sa": "Sanskrit",
        "sat": "Santali",
        "sd": "Sindhi",
        "si": "Sinhala",
        "sk": "Slovak",
        "sl": "Slovenian",
        "snd": "Sindhi",
        "sr": "Serbian",
        "sv": "Swedish",
        "sw": "Swahili",
        "ta": "Tamil",
        "te": "Telugu",
        "th": "Thai",
        "tr": "Turkish",
        "uk": "Ukrainian",
        "ur": "Urdu",
        "uz": "Uzbek",
        "vi": "Vietnamese",
        "zh": "Chinese",
        "zu": "Zulu",
    }

    def __init__(self):
        """Initialize the braille table manager."""
        self._tables: List[TableInfo] = []
        self._languageTables: Dict[str, List[TableInfo]] = {}
        self._loadTables()

    def _loadTables(self) -> None:
        """Load all available braille tables from NVDA."""
        try:
            # brailleTables.listTables() returns a generator of BrailleTable objects
            for table in brailleTables.listTables():
                tableInfo = TableInfo(
                    fileName=table.fileName,
                    displayName=table.displayName,
                    contracted=table.contracted,
                    output=table.output,
                    input=table.input,
                    languageCode=self._extractLanguageCode(table.fileName)
                )
                self._tables.append(tableInfo)

                # Group by language
                if tableInfo.languageCode:
                    if tableInfo.languageCode not in self._languageTables:
                        self._languageTables[tableInfo.languageCode] = []
                    self._languageTables[tableInfo.languageCode].append(tableInfo)

            log.debug(
                f"BrailleLanguageSwitcher: Loaded {len(self._tables)} braille tables "
                f"for {len(self._languageTables)} languages"
            )
        except Exception as e:
            log.error(f"BrailleLanguageSwitcher: Error loading braille tables: {e}")

    def _extractLanguageCode(self, fileName: str) -> Optional[str]:
        """
        Extract language code from table filename.

        Args:
            fileName: Braille table filename (e.g., "en-ueb-g2.ctb")

        Returns:
            ISO 639-1/639-2 language code, or None if not found
        """
        match = self.LANG_CODE_PATTERN.match(fileName.lower())
        if match:
            return match.group(1)
        return None

    def getAvailableLanguages(self) -> Dict[str, str]:
        """
        Get dictionary of available language codes to display names.

        Returns:
            Dictionary mapping language codes to their display names
        """
        languages: Dict[str, str] = {}
        for langCode in self._languageTables.keys():
            displayName = self.LANGUAGE_NAMES.get(
                langCode,
                langCode.upper()
            )
            languages[langCode] = displayName
        return languages

    def getTablesForLanguage(
        self,
        langCode: str,
        tableType: Optional[int] = None
    ) -> List[TableInfo]:
        """
        Get tables for a language, optionally filtered by type.

        Args:
            langCode: Language code (e.g., "en", "de")
            tableType: Optional filter:
                       TABLE_TYPE_UNCONTRACTED (0) = uncontracted
                       TABLE_TYPE_CONTRACTED (1) = contracted
                       TABLE_TYPE_COMPUTER (2) = computer braille
                       None = all types

        Returns:
            List of matching TableInfo objects
        """
        tables = self._languageTables.get(langCode, [])

        if tableType is None:
            # Return all output tables for the language
            return [t for t in tables if t.output]
        elif tableType == TABLE_TYPE_UNCONTRACTED:
            # Uncontracted: not contracted and supports output
            return [t for t in tables if not t.contracted and t.output]
        elif tableType == TABLE_TYPE_CONTRACTED:
            # Contracted: is contracted and supports output
            return [t for t in tables if t.contracted and t.output]
        elif tableType == TABLE_TYPE_COMPUTER:
            # Computer braille: filename contains "comp" and supports output
            return [
                t for t in tables
                if "comp" in t.fileName.lower() and t.output
            ]

        return tables

    def getTable(self, fileName: str) -> Optional[TableInfo]:
        """
        Get table info by filename.

        Args:
            fileName: Braille table filename

        Returns:
            TableInfo object, or None if not found
        """
        for table in self._tables:
            if table.fileName == fileName:
                return table
        return None

    def getAllOutputTables(self) -> List[TableInfo]:
        """
        Get all tables that support output.

        Returns:
            List of all output-capable braille tables
        """
        return [t for t in self._tables if t.output]

    def getTableTypeForFile(self, fileName: str) -> str:
        """
        Determine the table type for a given filename.

        Args:
            fileName: Braille table filename

        Returns:
            Table type string: "contracted", "uncontracted", or "computer"
        """
        table = self.getTable(fileName)
        if table:
            if "comp" in fileName.lower():
                return "computer"
            elif table.contracted:
                return "contracted"
            else:
                return "uncontracted"
        return "uncontracted"

    def refresh(self) -> None:
        """Refresh the table cache (e.g., after add-on installation)."""
        self._tables = []
        self._languageTables = {}
        self._loadTables()
