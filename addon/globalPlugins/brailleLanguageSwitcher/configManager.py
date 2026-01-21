# -*- coding: UTF-8 -*-
# BrailleLanguageSwitcher: Configuration Manager
# Handles persistent storage of language-to-braille-table mappings

import os
import json
from typing import Dict, List, Optional, Any

import globalVars
from logHandler import log

CONFIG_FILE_NAME = "brailleLanguageSwitcher.json"


class ConfigManager:
    """
    Manages persistent configuration for the BrailleLanguageSwitcher add-on.

    Configuration is stored as JSON in NVDA's user configuration directory.
    """

    _defaultConfig: Dict[str, Any] = {
        "enabled": True,
        "languageProfiles": {},
        "fallbackToDefault": True,
    }

    def __init__(self):
        """Initialize the configuration manager."""
        self._configPath = os.path.join(
            globalVars.appArgs.configPath,
            CONFIG_FILE_NAME
        )
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from disk."""
        try:
            if os.path.exists(self._configPath):
                with open(self._configPath, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                log.debug(f"BrailleLanguageSwitcher: Loaded config from {self._configPath}")
            else:
                self._config = self._defaultConfig.copy()
                self._config["languageProfiles"] = {}
                log.debug("BrailleLanguageSwitcher: Using default config (no file found)")
        except (json.JSONDecodeError, IOError) as e:
            log.error(f"BrailleLanguageSwitcher: Error loading config: {e}")
            self._config = self._defaultConfig.copy()
            self._config["languageProfiles"] = {}

    def save(self) -> None:
        """Save configuration to disk."""
        try:
            with open(self._configPath, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            log.debug(f"BrailleLanguageSwitcher: Saved config to {self._configPath}")
        except IOError as e:
            log.error(f"BrailleLanguageSwitcher: Error saving config: {e}")

    @property
    def enabled(self) -> bool:
        """Get whether the add-on is enabled."""
        return self._config.get("enabled", True)

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set whether the add-on is enabled."""
        self._config["enabled"] = value

    @property
    def fallbackToDefault(self) -> bool:
        """Get whether to fall back to default table for unconfigured languages."""
        return self._config.get("fallbackToDefault", True)

    @fallbackToDefault.setter
    def fallbackToDefault(self, value: bool) -> None:
        """Set whether to fall back to default table for unconfigured languages."""
        self._config["fallbackToDefault"] = value

    def getLanguageProfile(self, langCode: str) -> Optional[Dict[str, Any]]:
        """
        Get the braille profile for a language code.

        Args:
            langCode: ISO 639-1 language code (e.g., "en", "de")

        Returns:
            Dictionary with profile settings, or None if not configured.
            Profile contains: enabled, tableFileName, tableType
        """
        return self._config.get("languageProfiles", {}).get(langCode, None)

    def setLanguageProfile(
        self,
        langCode: str,
        tableFileName: str,
        tableType: str,
        enabled: bool = True
    ) -> None:
        """
        Set the braille profile for a language.

        Args:
            langCode: ISO 639-1 language code
            tableFileName: Name of the braille table file
            tableType: Type of table ("contracted", "uncontracted", "computer")
            enabled: Whether this profile is active
        """
        if "languageProfiles" not in self._config:
            self._config["languageProfiles"] = {}

        self._config["languageProfiles"][langCode] = {
            "enabled": enabled,
            "tableFileName": tableFileName,
            "tableType": tableType,
        }

    def removeLanguageProfile(self, langCode: str) -> None:
        """
        Remove a language profile.

        Args:
            langCode: ISO 639-1 language code to remove
        """
        if "languageProfiles" in self._config:
            self._config["languageProfiles"].pop(langCode, None)

    def getEnabledLanguages(self) -> List[str]:
        """
        Get list of language codes that have enabled profiles.

        Returns:
            List of enabled language codes
        """
        return [
            lang for lang, profile
            in self._config.get("languageProfiles", {}).items()
            if profile.get("enabled", False)
        ]

    def getAllLanguageProfiles(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all configured language profiles.

        Returns:
            Dictionary mapping language codes to their profiles
        """
        return self._config.get("languageProfiles", {}).copy()

    def updateLanguageEnabled(self, langCode: str, enabled: bool) -> None:
        """
        Update the enabled state for a language profile.

        Args:
            langCode: ISO 639-1 language code
            enabled: Whether the profile should be enabled
        """
        profiles = self._config.get("languageProfiles", {})
        if langCode in profiles:
            profiles[langCode]["enabled"] = enabled
