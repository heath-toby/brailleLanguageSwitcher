# -*- coding: UTF-8 -*-
# BrailleLanguageSwitcher: Global Plugin
# Automatically switches braille output tables based on detected text language

"""
BrailleLanguageSwitcher NVDA Add-on

Automatically switches the braille output table when language changes are
detected from document language tags. Works independently of speech by
hooking directly into braille region processing.
"""

import globalPluginHandler
import braille
import brailleInput
import brailleTables
import config
from gui.settingsDialogs import NVDASettingsDialog
from logHandler import log
from typing import Optional

from .configManager import ConfigManager
from .brailleTableManager import BrailleTableManager
from .settingsPanel import BrailleLanguageSwitcherSettingsPanel

PLUGIN_NAME = "BrailleLanguageSwitcher"

_globalPlugin: Optional["GlobalPlugin"] = None

# Store original braille Region.update method for monkey-patching
_originalBrailleRegionUpdate = None


def _extractLanguageFromRegion(regionSelf):
    """Extract language from a braille region by examining format fields.

    This replicates the logic used in NVDA source modifications.
    """
    # 1. Check for _detectedLanguage attribute (set by modified NVDA or other add-ons)
    detectedLang = getattr(regionSelf, "_detectedLanguage", None)
    if detectedLang:
        return detectedLang

    # 2. For TextInfoRegion, get language from format fields
    # Check if this is a TextInfoRegion by looking for _selection attribute
    selection = getattr(regionSelf, "_selection", None)
    if selection is None:
        # Try _getSelection method
        getSelection = getattr(regionSelf, "_getSelection", None)
        if getSelection:
            try:
                selection = getSelection()
            except Exception:
                pass

    if selection:
        try:
            from textInfos import FieldCommand
            # Get text with format fields
            fields = selection.getTextWithFields()
            for field in fields:
                if isinstance(field, FieldCommand):
                    if field.command == "formatChange" and field.field:
                        lang = field.field.get("language")
                        if lang:
                            return lang
        except Exception as e:
            log.debug(f"{PLUGIN_NAME}: Error extracting language from selection: {e}")

    # 3. Try to get from the object's language property if available
    obj = getattr(regionSelf, "obj", None)
    if obj:
        try:
            # Some objects have a language property
            lang = getattr(obj, "language", None)
            if lang:
                return lang
        except Exception:
            pass

    return None


def _patchedBrailleRegionUpdate(regionSelf, *args, **kwargs):
    """Patched version of braille.Region.update that switches tables based on detected language.

    This is a standalone function (not a method) that replaces braille.Region.update.
    regionSelf is the braille Region instance.
    """
    global _globalPlugin

    if _globalPlugin and _globalPlugin._configManager.enabled:
        detectedLang = _extractLanguageFromRegion(regionSelf)

        if detectedLang:
            normalizedLang = _globalPlugin._normalizeLanguageCode(detectedLang)
            if normalizedLang:
                log.info(f"{PLUGIN_NAME}: Detected language '{detectedLang}' -> '{normalizedLang}'")
                _globalPlugin._handleLanguageChange(normalizedLang)
        elif _globalPlugin._currentLanguage is not None:
            # No language detected, revert to default
            _globalPlugin._revertToDefaultTables()
            _globalPlugin._currentLanguage = None

    # Call the original update method
    return _originalBrailleRegionUpdate(regionSelf, *args, **kwargs)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    """Global plugin for automatic braille language switching."""

    def __init__(self):
        super().__init__()
        global _globalPlugin
        _globalPlugin = self

        log.info(f"{PLUGIN_NAME}: Initializing...")

        self._configManager = ConfigManager()
        self._tableManager = BrailleTableManager()
        self._originalOutputTable = self._getCurrentOutputTableFileName()
        self._originalInputTable = self._getCurrentInputTableFileName()
        self._currentLanguage: Optional[str] = None
        self._currentTable: Optional[str] = None
        self._brailleHookInstalled = False

        # Register settings panel
        NVDASettingsDialog.categoryClasses.append(
            BrailleLanguageSwitcherSettingsPanel
        )

        if self._configManager.enabled:
            self._installBrailleHook()
            log.info(f"{PLUGIN_NAME}: Started (enabled)")
        else:
            log.info(f"{PLUGIN_NAME}: Initialized but disabled")

        try:
            config.post_configProfileSwitch.register(self._onConfigProfileSwitch)
        except Exception as e:
            log.warning(f"{PLUGIN_NAME}: Could not register config profile handler: {e}")

    def terminate(self):
        global _globalPlugin
        log.info(f"{PLUGIN_NAME}: Terminating...")

        try:
            config.post_configProfileSwitch.unregister(self._onConfigProfileSwitch)
        except Exception:
            pass

        self._uninstallBrailleHook()

        try:
            NVDASettingsDialog.categoryClasses.remove(
                BrailleLanguageSwitcherSettingsPanel
            )
        except ValueError:
            pass

        # Restore original tables
        if self._originalOutputTable:
            try:
                tableObj = brailleTables.getTable(self._originalOutputTable)
                braille.handler.table = tableObj
                log.info(f"{PLUGIN_NAME}: Restored original output table: {self._originalOutputTable}")
            except LookupError:
                pass

        if self._originalInputTable:
            try:
                tableObj = brailleTables.getTable(self._originalInputTable)
                brailleInput.handler.table = tableObj
                log.info(f"{PLUGIN_NAME}: Restored original input table: {self._originalInputTable}")
            except LookupError:
                pass

        _globalPlugin = None
        log.info(f"{PLUGIN_NAME}: Terminated")

    def _installBrailleHook(self) -> None:
        """Install the monkey-patch for braille language detection."""
        global _originalBrailleRegionUpdate
        if self._brailleHookInstalled:
            return

        if _originalBrailleRegionUpdate is None:
            _originalBrailleRegionUpdate = braille.Region.update
            braille.Region.update = _patchedBrailleRegionUpdate
            self._brailleHookInstalled = True
            log.info(f"{PLUGIN_NAME}: Braille region hook installed")

    def _uninstallBrailleHook(self) -> None:
        """Remove the monkey-patch for braille language detection."""
        global _originalBrailleRegionUpdate
        if _originalBrailleRegionUpdate is not None:
            braille.Region.update = _originalBrailleRegionUpdate
            _originalBrailleRegionUpdate = None
            self._brailleHookInstalled = False
            log.info(f"{PLUGIN_NAME}: Braille region hook removed")

    def _handleLanguageChange(self, langCode: str) -> None:
        """Handle a language change by switching braille tables if needed."""
        if langCode == self._currentLanguage:
            return  # No change

        self._currentLanguage = langCode
        profile = self._configManager.getLanguageProfile(langCode)

        if profile and profile.get("enabled", False):
            tableFileName = profile.get("tableFileName")
            if tableFileName:
                self._applyTableChange(tableFileName, langCode)
        elif self._configManager.fallbackToDefault:
            self._revertToDefaultTables()

    def _applyTableChange(self, tableName: str, langCode: str) -> None:
        """Apply the braille table change."""
        if tableName == self._currentTable:
            return  # Already using this table

        try:
            tableObj = brailleTables.getTable(tableName)
            braille.handler.table = tableObj
            self._currentTable = tableName
            log.info(f"{PLUGIN_NAME}: Switched output table to {tableName} for {langCode}")

            # Also switch input table if enabled
            if self._configManager.autoInputSwitching:
                profile = self._configManager.getLanguageProfile(langCode)
                inputTable = profile.get("inputTableFileName") if profile else None
                if not inputTable:
                    # No specific input table configured, use the same as output
                    inputTable = tableName

                try:
                    inputTableObj = brailleTables.getTable(inputTable)
                    brailleInput.handler.table = inputTableObj
                    log.info(f"{PLUGIN_NAME}: Switched input table to {inputTable} for {langCode}")
                except LookupError:
                    log.warning(f"{PLUGIN_NAME}: Input table not found: {inputTable}")

        except LookupError:
            log.error(f"{PLUGIN_NAME}: Table not found: {tableName}")
        except Exception as e:
            log.error(f"{PLUGIN_NAME}: Error applying table change: {e}")

    def _revertToDefaultTables(self) -> None:
        """Revert braille tables to the user's configured defaults."""
        if self._originalOutputTable and self._currentTable != self._originalOutputTable:
            try:
                tableObj = brailleTables.getTable(self._originalOutputTable)
                braille.handler.table = tableObj
                self._currentTable = self._originalOutputTable
                log.info(f"{PLUGIN_NAME}: Reverted output table to default: {self._originalOutputTable}")
            except LookupError:
                log.warning(f"{PLUGIN_NAME}: Default output table not found: {self._originalOutputTable}")

        if self._configManager.autoInputSwitching and self._originalInputTable:
            try:
                currentInputTable = brailleInput.handler.table.fileName if brailleInput.handler.table else None
                if currentInputTable != self._originalInputTable:
                    inputTableObj = brailleTables.getTable(self._originalInputTable)
                    brailleInput.handler.table = inputTableObj
                    log.info(f"{PLUGIN_NAME}: Reverted input table to default: {self._originalInputTable}")
            except LookupError:
                log.warning(f"{PLUGIN_NAME}: Default input table not found: {self._originalInputTable}")

    def _normalizeLanguageCode(self, lang: str) -> Optional[str]:
        if not lang:
            return None
        lang = lang.lower()
        for sep in ['_', '-', '.']:
            if sep in lang:
                lang = lang.split(sep)[0]
                break
        return lang[:3] if len(lang) >= 2 else None

    def _onConfigProfileSwitch(self) -> None:
        self._configManager.load()
        if self._configManager.enabled:
            self._installBrailleHook()
        else:
            self._uninstallBrailleHook()
            self._revertToDefaultTables()

    def _getCurrentOutputTableFileName(self) -> str:
        """Get the current output braille table filename."""
        table = config.conf["braille"]["translationTable"]
        if table == "auto":
            table = brailleTables.getDefaultTableForCurLang(brailleTables.TableType.OUTPUT)
        return table

    def _getCurrentInputTableFileName(self) -> str:
        """Get the current input braille table filename."""
        table = config.conf["braille"]["inputTable"]
        if table == "auto":
            table = brailleTables.getDefaultTableForCurLang(brailleTables.TableType.INPUT)
        return table

    def reloadConfiguration(self) -> None:
        self._configManager.load()
        if self._configManager.enabled:
            self._installBrailleHook()
        else:
            self._uninstallBrailleHook()
            self._revertToDefaultTables()
