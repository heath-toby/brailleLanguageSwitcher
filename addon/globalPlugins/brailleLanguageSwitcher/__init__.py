# -*- coding: UTF-8 -*-
# BrailleLanguageSwitcher: Global Plugin
# Automatically switches braille output tables based on detected text language

"""
BrailleLanguageSwitcher NVDA Add-on

Automatically switches the default braille output table when language changes
are detected in speech. The braille table stays changed until a new language
is detected.
"""

import globalPluginHandler
import api
import braille
import brailleTables
import config
import gui
import treeInterceptorHandler
from gui.settingsDialogs import NVDASettingsDialog
from logHandler import log
from typing import Optional, List, Any

from .configManager import ConfigManager
from .brailleTableManager import BrailleTableManager
from .settingsPanel import BrailleLanguageSwitcherSettingsPanel

PLUGIN_NAME = "BrailleLanguageSwitcher"

_globalPlugin: Optional["GlobalPlugin"] = None


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    """Global plugin for automatic braille language switching."""

    def __init__(self):
        super().__init__()
        global _globalPlugin
        _globalPlugin = self

        log.info(f"{PLUGIN_NAME}: Initializing...")

        self._configManager = ConfigManager()
        self._tableManager = BrailleTableManager()
        self._originalTable = self._getCurrentTableFileName()
        self._currentLanguage: Optional[str] = None
        self._currentTable: Optional[str] = None
        self._speechFilterRegistered = False
        self._speechExtensionPoint = None

        # Register settings panel
        NVDASettingsDialog.categoryClasses.append(
            BrailleLanguageSwitcherSettingsPanel
        )

        if self._configManager.enabled:
            self._registerSpeechFilter()
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

        self._unregisterSpeechFilter()

        try:
            NVDASettingsDialog.categoryClasses.remove(
                BrailleLanguageSwitcherSettingsPanel
            )
        except ValueError:
            pass

        # Restore original table
        if self._originalTable:
            config.conf["braille"]["translationTable"] = self._originalTable
            log.info(f"{PLUGIN_NAME}: Restored original table: {self._originalTable}")

        _globalPlugin = None
        log.info(f"{PLUGIN_NAME}: Terminated")

    def _registerSpeechFilter(self) -> None:
        """Register speech filter to detect language changes."""
        if self._speechFilterRegistered:
            return

        try:
            try:
                from speech import extensions
                self._speechExtensionPoint = extensions.filter_speechSequence
            except (ImportError, AttributeError):
                pass

            if self._speechExtensionPoint is None:
                import speech
                if hasattr(speech, 'filter_speechSequence'):
                    self._speechExtensionPoint = speech.filter_speechSequence

            if self._speechExtensionPoint:
                self._speechExtensionPoint.register(self._speechFilter)
                self._speechFilterRegistered = True
                log.info(f"{PLUGIN_NAME}: Speech filter registered")
        except Exception as e:
            log.error(f"{PLUGIN_NAME}: Error registering speech filter: {e}")

    def _unregisterSpeechFilter(self) -> None:
        if self._speechFilterRegistered and self._speechExtensionPoint:
            try:
                self._speechExtensionPoint.unregister(self._speechFilter)
                self._speechFilterRegistered = False
            except Exception:
                pass

    def _speechFilter(self, speechSequence: List[Any], *args, **kwargs) -> List[Any]:
        """Detect language changes and switch braille table."""
        if not self._configManager.enabled:
            return speechSequence

        try:
            from speech.commands import LangChangeCommand

            for item in speechSequence:
                if isinstance(item, LangChangeCommand) and item.lang:
                    normalizedLang = self._normalizeLanguageCode(item.lang)
                    if normalizedLang and normalizedLang != self._currentLanguage:
                        self._currentLanguage = normalizedLang
                        self._switchBrailleTable(normalizedLang)

        except Exception as e:
            log.error(f"{PLUGIN_NAME}: Error in speech filter: {e}")

        return speechSequence

    def _switchBrailleTable(self, langCode: str) -> None:
        """Switch the braille table for the given language."""
        profile = self._configManager.getLanguageProfile(langCode)
        newTable = None

        if profile and profile.get("enabled", False):
            tableFileName = profile.get("tableFileName")
            if tableFileName and tableFileName != self._currentTable:
                try:
                    brailleTables.getTable(tableFileName)
                    newTable = tableFileName
                except LookupError:
                    log.warning(f"{PLUGIN_NAME}: Table not found: {tableFileName}")
        elif self._configManager.fallbackToDefault:
            if self._originalTable and self._currentTable != self._originalTable:
                newTable = self._originalTable

        if newTable:
            self._currentTable = newTable
            # Schedule the table change for after current processing
            import wx
            wx.CallAfter(self._applyTableChange, newTable, langCode)

    def _applyTableChange(self, tableName: str, langCode: str) -> None:
        """Apply the braille table change (called via wx.CallAfter)."""
        try:
            # Get the BrailleTable object and set it directly on the handler
            # This updates both handler._table AND config.conf automatically
            tableObj = brailleTables.getTable(tableName)
            braille.handler.table = tableObj
            self._refreshBrailleDisplay()
            log.info(f"{PLUGIN_NAME}: Applied braille table {tableName} for {langCode}")
        except LookupError:
            log.error(f"{PLUGIN_NAME}: Table not found: {tableName}")
        except Exception as e:
            log.error(f"{PLUGIN_NAME}: Error applying table change: {e}")

    def _refreshBrailleDisplay(self) -> None:
        """Refresh the braille display to apply table changes.

        Uses the same technique as BrailleExtender: update tree interceptor
        and re-trigger handleGainFocus on the current focus object.
        """
        try:
            focus = api.getFocusObject()
            if focus is None:
                return

            # Update tree interceptor if present (matches BrailleExtender approach)
            if focus.treeInterceptor is not None:
                ti = treeInterceptorHandler.update(focus)
                if ti and not ti.passThrough:
                    braille.handler.handleGainFocus(ti)
                    return

            braille.handler.handleGainFocus(focus)
        except Exception as e:
            log.debug(f"{PLUGIN_NAME}: Error refreshing braille display: {e}")

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
            self._registerSpeechFilter()
        else:
            self._unregisterSpeechFilter()
            if self._originalTable:
                config.conf["braille"]["translationTable"] = self._originalTable

    def _getCurrentTableFileName(self) -> str:
        table = config.conf["braille"]["translationTable"]
        if table == "auto":
            table = brailleTables.getDefaultTableForCurLang(brailleTables.TableType.OUTPUT)
        return table

    def reloadConfiguration(self) -> None:
        self._configManager.load()
        if self._configManager.enabled:
            self._registerSpeechFilter()
        else:
            self._unregisterSpeechFilter()
