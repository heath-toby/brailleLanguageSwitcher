# -*- coding: UTF-8 -*-
# BrailleLanguageSwitcher: Global Plugin
# Automatically switches braille output tables based on detected text language

"""
BrailleLanguageSwitcher NVDA Add-on

Automatically switches the braille output (and optionally input) table when the language of the text changes.

Three language sources:
- "mixed" (default): each language on a line is shown in its own table, split by the same detectors without
  speaking; the input table follows the language at the cursor.
- "speech": braille follows the language the voice switches to, whatever detected it: Dialingo,
  Enhanced Language Detection, document language tags, or any other add-on that switches speech language.
  Braille that is shown without being spoken (panning, routing) is checked with the same detectors.
- "text": the braille text itself is checked, from document language tags and, if enabled, the Enhanced
  Language Detection add-on.
"""

import globalPluginHandler
import braille
import brailleTables
import config
import gui
from gui.settingsDialogs import NVDASettingsDialog
from logHandler import log
from typing import Optional

from .configManager import ConfigManager, SOURCE_MIXED, SOURCE_SPEECH
from .brailleTableManager import BrailleTableManager
from .settingsPanel import BrailleLanguageSwitcherSettingsPanel
from . import mixedBraille, speechLanguage

PLUGIN_NAME = "BrailleLanguageSwitcher"

_globalPlugin: Optional["GlobalPlugin"] = None

# Store original braille Region.update method for monkey-patching
_originalBrailleRegionUpdate = None

# Enhanced Language Detection integration
_enhancedLangDetectionAvailable = False
_elsDetectLanguage = None
_elsDetectLanguageWithLingua = None
_elsModule = None


def _initEnhancedLanguageDetection():
    """Try to import Enhanced Language Detection add-on functions."""
    global _enhancedLangDetectionAvailable, _elsDetectLanguage, _elsDetectLanguageWithLingua, _elsModule

    for moduleName in ("enhancedLanguageDetection", "enhanced_language_switching"):
        try:
            module = __import__(f"globalPlugins.{moduleName}", fromlist=[moduleName])
            _elsModule = module
            _elsDetectLanguage = module.detectLanguage
            _elsDetectLanguageWithLingua = module.detectLanguageWithLingua
            _enhancedLangDetectionAvailable = True
            log.info(f"{PLUGIN_NAME}: Enhanced Language Detection add-on found ({moduleName})")
            return True
        except (ImportError, AttributeError):
            pass

    _enhancedLangDetectionAvailable = False
    log.info(f"{PLUGIN_NAME}: Enhanced Language Detection not available")
    return False


def isEnhancedLanguageDetectionAvailable() -> bool:
    """Whether the Enhanced Language Detection add-on is available (used by the settings panel)."""
    return _enhancedLangDetectionAvailable


def isDialingoAvailable() -> bool:
    """Whether the Dialingo add-on is running (used by the settings panel's status line)."""
    try:
        from globalPlugins import dialingo  # noqa: F401
        return True
    except ImportError:
        return False


def _detectLanguageWithThreshold(text: str, minWords: int = 3) -> Optional[str]:
    """
    Detect language using Enhanced Language Detection, but only return
    a language if the text has at least minWords words.
    """
    if not _enhancedLangDetectionAvailable or not text:
        return None

    if len(text.split()) < minWords:
        return None

    try:
        model = config.conf["enhancedLanguageDetection"]["model"]
    except KeyError:
        model = 1  # Default to langdetect

    detectedLang = None
    try:
        if model == 0 and _elsDetectLanguageWithLingua:
            detectedLang = _elsDetectLanguageWithLingua(text)
        elif _elsDetectLanguage:
            detectedLang = _elsDetectLanguage(text)
    except Exception as e:
        log.debug(f"{PLUGIN_NAME}: Error detecting language: {e}")
        return None

    return detectedLang.lower() if detectedLang else None


def _extractLanguageFromRegion(regionSelf, configManager):
    """Extract language from a braille region (the "text" language source).

    Tries, in order: a _detectedLanguage attribute, document language tags (formatChange fields),
    the object's language, and Enhanced Language Detection if enabled.
    """
    detectedLang = getattr(regionSelf, "_detectedLanguage", None)
    if detectedLang:
        return detectedLang

    selection = getattr(regionSelf, "_selection", None)
    if selection is None:
        getSelection = getattr(regionSelf, "_getSelection", None)
        if getSelection:
            try:
                selection = getSelection()
            except Exception:
                pass

    if selection:
        try:
            from textInfos import FieldCommand
            for field in selection.getTextWithFields():
                if isinstance(field, FieldCommand) and field.command == "formatChange" and field.field:
                    lang = field.field.get("language")
                    if lang:
                        return lang
        except Exception as e:
            log.debug(f"{PLUGIN_NAME}: Error extracting language from selection: {e}")

    obj = getattr(regionSelf, "obj", None)
    if obj:
        try:
            lang = getattr(obj, "language", None)
            if lang:
                return lang
        except Exception:
            pass

    if configManager.useEnhancedDetection and _enhancedLangDetectionAvailable:
        rawText = getattr(regionSelf, "rawText", None)
        if rawText:
            detectedLang = _detectLanguageWithThreshold(rawText, configManager.minWordThreshold)
            if detectedLang:
                return detectedLang

    return None


def _patchedBrailleRegionUpdate(regionSelf, *args, **kwargs):
    """Replaces braille.Region.update: switches tables for the region's language before it is translated."""
    plugin = _globalPlugin
    if plugin and plugin._configManager.enabled and plugin._configManager.languageSource == SOURCE_MIXED:
        plugin._mixed.beginRegion()
        try:
            return _originalBrailleRegionUpdate(regionSelf, *args, **kwargs)
        finally:
            hadCursor, language = plugin._mixed.endRegion()
            if hadCursor:
                try:
                    plugin._setInputForLanguage(language)
                except Exception:
                    log.debugWarning(f"{PLUGIN_NAME}: could not set the input table", exc_info=True)
    if plugin and plugin._configManager.enabled:
        try:
            if plugin._configManager.languageSource == SOURCE_SPEECH:
                plugin._checkUnspokenRegion(regionSelf)
            else:
                plugin._checkRegionText(regionSelf)
        except Exception:
            log.debugWarning(f"{PLUGIN_NAME}: language check failed for a braille region", exc_info=True)

    return _originalBrailleRegionUpdate(regionSelf, *args, **kwargs)


def _regionClass():
    """The base braille region class: braille.regions.base.Region since NVDA 2026.3, braille.Region before."""
    try:
        from braille.regions.base import Region
        return Region
    except ImportError:
        return braille.Region


def _setOutputTable(table) -> None:
    """Set the braille output table for this session only.

    braille.handler.table's setter also writes config.conf["braille"]["translationTable"], so the user's own
    default would be replaced by whatever language was last read whenever NVDA saved its configuration.
    """
    if hasattr(braille.handler, "_table"):
        braille.handler._table = table
    else:
        braille.handler.table = table


def _inputHandler():
    """The braille input handler: braille.input.handler since NVDA 2026.3, brailleInput.handler before."""
    try:
        import braille.input
        handler = getattr(braille.input, "handler", None)
        if handler is not None:
            return handler
    except ImportError:
        pass
    import brailleInput
    return brailleInput.handler


def _setInputTable(table) -> None:
    """Set the braille input table for this session only, as _setOutputTable."""
    handler = _inputHandler()
    if hasattr(handler, "_table"):
        handler._table = table
    else:
        handler.table = table


def _currentOutputTableName() -> Optional[str]:
    table = getattr(braille.handler, "table", None) if braille.handler else None
    return getattr(table, "fileName", None)


def _currentInputTableName() -> Optional[str]:
    handler = _inputHandler()
    table = getattr(handler, "table", None) if handler else None
    return getattr(table, "fileName", None)


def _refreshBraille() -> None:
    """Translate what the display already shows again, with the table just selected.

    Speech usually comes before braille for the same event, but not always; without this the display could keep
    showing text in the previous table until the next update.
    """
    handler = braille.handler
    if not handler or not getattr(handler, "enabled", False):
        return
    try:
        pending = handler._regionsPendingUpdate
        for region in handler.mainBuffer.visibleRegions:
            # Only object and text regions can be queued (the update reads region.obj).
            if hasattr(region, "obj"):
                pending.add(region)
        import core
        core.requestPump()
    except Exception:
        log.debugWarning(f"{PLUGIN_NAME}: could not refresh the braille display", exc_info=True)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    """Global plugin for automatic braille language switching."""

    def __init__(self):
        super().__init__()
        global _globalPlugin
        _globalPlugin = self

        log.info(f"{PLUGIN_NAME}: Initializing...")

        self._configManager = ConfigManager()
        self._tableManager = BrailleTableManager()
        self._currentLanguage: Optional[str] = None
        self._brailleHookInstalled = False
        self._speechFollower = speechLanguage.SpeechLanguageFollower(
            self._onSpeechLanguage,
            lambda: self._configManager.minWordThreshold,
        )

        self._mixed = mixedBraille.MixedTranslator(
            self._outputTableForLanguage,
            lambda: self._configManager.minWordThreshold,
        )

        _initEnhancedLanguageDetection()
        self._checkEnhancedDetectionStillAvailable()

        NVDASettingsDialog.categoryClasses.append(BrailleLanguageSwitcherSettingsPanel)

        self._applyConfiguration()

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

        self._speechFollower.unregister()
        self._mixed.uninstall()
        self._uninstallBrailleHook()

        try:
            NVDASettingsDialog.categoryClasses.remove(BrailleLanguageSwitcherSettingsPanel)
        except ValueError:
            pass

        self._revertToDefaultTables(force=True)

        _globalPlugin = None
        log.info(f"{PLUGIN_NAME}: Terminated")

    # --- configuration ---

    def _applyConfiguration(self) -> None:
        """Install the hooks the configuration asks for and remove the rest."""
        self._mixed.clearCache()
        if not self._configManager.enabled:
            self._speechFollower.unregister()
            self._mixed.uninstall()
            self._uninstallBrailleHook()
            self._revertToDefaultTables(force=True)
            self._currentLanguage = None
            log.info(f"{PLUGIN_NAME}: disabled")
            return

        # The region hook serves both sources: it reads the text in "text" mode, and catches braille that was
        # never spoken in "speech" mode.
        self._installBrailleHook()
        source = self._configManager.languageSource
        if source == SOURCE_SPEECH:
            self._speechFollower.register()
        else:
            self._speechFollower.unregister()
        if source == SOURCE_MIXED:
            self._mixed.install()
        else:
            self._mixed.uninstall()
        # Start from the user's tables; the next text read sets the language again.
        self._revertToDefaultTables(force=True)
        self._currentLanguage = None
        log.info(f"{PLUGIN_NAME}: enabled, language source: {self._configManager.languageSource}")

    def _checkEnhancedDetectionStillAvailable(self) -> None:
        """Turn the Enhanced Language Detection option off, with a warning, if the add-on has gone."""
        if not (self._configManager.useEnhancedDetection and not _enhancedLangDetectionAvailable):
            return
        self._configManager.useEnhancedDetection = False
        self._configManager.save()
        log.warning(f"{PLUGIN_NAME}: Enhanced Language Detection not found, integration disabled")
        if self._configManager.languageSource == SOURCE_SPEECH:
            return  # It plays no part in following speech, so there is nothing to warn about.
        import wx
        wx.CallAfter(
            gui.messageBox,
            # Translators: Warning when Enhanced Language Detection add-on was removed
            _("Enhanced Language Detection add-on could not be found. "
              "Text-based language detection has been automatically disabled.\n\n"
              "Only document language tags will be used for detection. "
              "Install the Enhanced Language Detection add-on to re-enable this feature."),
            # Translators: Title of warning dialog
            _("Braille Language Switcher"),
            wx.OK | wx.ICON_WARNING
        )

    def reloadConfiguration(self) -> None:
        """Reload configuration and apply changes immediately (called after the settings panel saves)."""
        self._configManager.load()
        _initEnhancedLanguageDetection()
        self._checkEnhancedDetectionStillAvailable()
        self._applyConfiguration()

    def _onConfigProfileSwitch(self) -> None:
        self._configManager.load()
        self._applyConfiguration()

    # --- hooks ---

    def _installBrailleHook(self) -> None:
        global _originalBrailleRegionUpdate
        if self._brailleHookInstalled:
            return
        if _originalBrailleRegionUpdate is None:
            region = _regionClass()
            _originalBrailleRegionUpdate = region.update
            region.update = _patchedBrailleRegionUpdate
            log.info(f"{PLUGIN_NAME}: Braille region hook installed")
        # Else the hook was left in place under another add-on's patch (see _uninstallBrailleHook) and is used again.
        self._brailleHookInstalled = True

    def _uninstallBrailleHook(self) -> None:
        global _originalBrailleRegionUpdate
        if _originalBrailleRegionUpdate is None:
            return
        self._brailleHookInstalled = False
        region = _regionClass()
        if region.__dict__.get("update") is _patchedBrailleRegionUpdate:
            region.update = _originalBrailleRegionUpdate
            _originalBrailleRegionUpdate = None
            log.info(f"{PLUGIN_NAME}: Braille region hook removed")
        else:
            # Another add-on patched update after this one and calls this hook. Putting the original back would
            # remove its patch, so the hook stays and passes straight through while the add-on is off.
            log.info(f"{PLUGIN_NAME}: Braille region hook left in place under another add-on's patch")

    # --- language sources ---

    def _onSpeechLanguage(self, language: Optional[str]) -> None:
        """The voice switched to `language` (None: the default voice). Called on the main thread."""
        if not self._configManager.enabled:
            return
        if self._setLanguage(language):
            _refreshBraille()

    def _checkUnspokenRegion(self, regionSelf) -> None:
        """Speech source: a region updated with no speech just before (panning, routing, a braille-only
        update) is run through the speech detectors, so the same detector decides as for spoken text."""
        if self._speechFollower.speechIsRecent():
            return
        rawText = getattr(regionSelf, "rawText", None)
        # Through the mixed translator's cache: a clock or progress bar updating does not detect again each time.
        decided, language = self._mixed.dominantLanguage(rawText, self._configManager.minWordThreshold)
        if decided:
            self._setLanguage(language)

    def _checkRegionText(self, regionSelf) -> None:
        """Text source: the region's own tags or Enhanced Language Detection; nothing found means default."""
        language = _extractLanguageFromRegion(regionSelf, self._configManager)
        self._setLanguage(language)

    # --- mixed language braille ---

    def _outputTableForLanguage(self, language: Optional[str]) -> Optional[str]:
        """The output table for text in `language`, or None for the default table."""
        normalized = self._normalizeLanguageCode(language) if language else None
        if not normalized or normalized == self._defaultLanguage():
            return None
        profile = self._configManager.getLanguageProfile(normalized)
        if profile and profile.get("enabled", False):
            return profile.get("tableFileName") or None
        return None

    def _setInputForLanguage(self, language: Optional[str]) -> None:
        """Select the input table for the language at the cursor (None: the default input table)."""
        if not self._configManager.autoInputSwitching:
            return
        if getattr(_inputHandler(), "bufferBraille", None):
            # Cells typed but not yet translated (contracted input): the text at the cursor includes them, and
            # changing the input table now would translate the rest of the word with another table.
            return
        normalized = self._normalizeLanguageCode(language) if language else None
        inputTable = None
        if normalized and normalized != self._defaultLanguage():
            profile = self._configManager.getLanguageProfile(normalized)
            if profile and profile.get("enabled", False):
                inputTable = profile.get("inputTableFileName") or profile.get("tableFileName")
        if not inputTable:
            inputTable = self._getConfiguredInputTableFileName()
        if inputTable and _currentInputTableName() != inputTable:
            try:
                _setInputTable(brailleTables.getTable(inputTable))
                log.info(f"{PLUGIN_NAME}: input table {inputTable} for the language at the cursor ({language})")
            except LookupError:
                log.warning(f"{PLUGIN_NAME}: Input table not found: {inputTable}")

    # --- switching ---

    def _setLanguage(self, language: Optional[str]) -> bool:
        """Select the tables for `language` (None or the default voice's language: the user's own tables).

        Returns True when a table changed.
        """
        normalized = self._normalizeLanguageCode(language) if language else None
        if normalized is None:
            normalized = self._defaultLanguage()
        if normalized == self._currentLanguage:
            return False
        self._currentLanguage = normalized

        profile = self._configManager.getLanguageProfile(normalized) if normalized else None
        if profile and profile.get("enabled", False) and profile.get("tableFileName"):
            log.debug(f"{PLUGIN_NAME}: language {language!r} -> {normalized}")
            return self._applyTableChange(profile, normalized)
        if language is None or normalized == self._defaultLanguage() or self._configManager.fallbackToDefault:
            return self._revertToDefaultTables()
        return False

    def _defaultLanguage(self) -> Optional[str]:
        """The default voice's language, normalized: text spoken without a language command is in it."""
        try:
            import speech
            return self._normalizeLanguageCode(speech.getCurrentLanguage())
        except Exception:
            return None

    def _applyTableChange(self, profile: dict, langCode: str) -> bool:
        changed = False
        tableName = profile["tableFileName"]
        try:
            if _currentOutputTableName() != tableName:
                _setOutputTable(brailleTables.getTable(tableName))
                changed = True
                log.info(f"{PLUGIN_NAME}: Switched output table to {tableName} for {langCode}")
        except LookupError:
            log.error(f"{PLUGIN_NAME}: Table not found: {tableName}")
            return False
        except Exception as e:
            log.error(f"{PLUGIN_NAME}: Error applying table change: {e}")
            return False

        if self._configManager.autoInputSwitching:
            inputTable = profile.get("inputTableFileName") or tableName
            try:
                if _currentInputTableName() != inputTable:
                    _setInputTable(brailleTables.getTable(inputTable))
                    changed = True
                    log.info(f"{PLUGIN_NAME}: Switched input table to {inputTable} for {langCode}")
            except LookupError:
                log.warning(f"{PLUGIN_NAME}: Input table not found: {inputTable}")
        return changed

    def _revertToDefaultTables(self, force: bool = False) -> bool:
        """Go back to the tables chosen in NVDA's braille settings.

        Those are read from the configuration each time, which this add-on never writes, so a change the user
        makes in braille settings, or a configuration profile switch, is followed.
        """
        changed = False
        output = self._getConfiguredOutputTableFileName()
        if output and _currentOutputTableName() != output:
            try:
                _setOutputTable(brailleTables.getTable(output))
                changed = True
                log.info(f"{PLUGIN_NAME}: Reverted output table to default: {output}")
            except LookupError:
                log.warning(f"{PLUGIN_NAME}: Default output table not found: {output}")

        if self._configManager.autoInputSwitching or force:
            inputTable = self._getConfiguredInputTableFileName()
            if inputTable and _currentInputTableName() != inputTable:
                try:
                    _setInputTable(brailleTables.getTable(inputTable))
                    changed = True
                    log.info(f"{PLUGIN_NAME}: Reverted input table to default: {inputTable}")
                except LookupError:
                    log.warning(f"{PLUGIN_NAME}: Default input table not found: {inputTable}")
        return changed

    def _normalizeLanguageCode(self, lang: str) -> Optional[str]:
        if not lang:
            return None
        lang = lang.lower()
        for sep in ['_', '-', '.']:
            if sep in lang:
                lang = lang.split(sep)[0]
                break
        return lang[:3] if len(lang) >= 2 else None

    def _getConfiguredOutputTableFileName(self) -> str:
        table = config.conf["braille"]["translationTable"]
        if table == "auto":
            table = brailleTables.getDefaultTableForCurLang(brailleTables.TableType.OUTPUT)
        return table

    def _getConfiguredInputTableFileName(self) -> str:
        table = config.conf["braille"]["inputTable"]
        if table == "auto":
            table = brailleTables.getDefaultTableForCurLang(brailleTables.TableType.INPUT)
        return table
