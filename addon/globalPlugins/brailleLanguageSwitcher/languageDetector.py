# -*- coding: UTF-8 -*-
# BrailleLanguageSwitcher: Language Detector
# Hooks into NVDA's speech system to detect language changes

from typing import Optional, Callable, Any, List

from logHandler import log

# Track whether Enhanced Language Switching is available
_enhancedLanguageSwitchingAvailable: bool = False
_elsModule: Any = None


def _checkEnhancedLanguageSwitching() -> bool:
    """
    Check if Enhanced Language Switching add-on is installed.

    Returns:
        True if ELS is available, False otherwise
    """
    global _enhancedLanguageSwitchingAvailable, _elsModule
    try:
        from globalPlugins import enhancedLanguageDetection
        _elsModule = enhancedLanguageDetection
        _enhancedLanguageSwitchingAvailable = True
        log.info("BrailleLanguageSwitcher: Enhanced Language Switching detected")
        return True
    except ImportError:
        pass

    try:
        from globalPlugins import enhanced_language_switching
        _elsModule = enhanced_language_switching
        _enhancedLanguageSwitchingAvailable = True
        log.info("BrailleLanguageSwitcher: Enhanced Language Switching detected (alt name)")
        return True
    except ImportError:
        _enhancedLanguageSwitchingAvailable = False
        log.info("BrailleLanguageSwitcher: Enhanced Language Switching not found, using native detection")
        return False


class LanguageDetector:
    """
    Abstraction for language detection in NVDA.

    Hooks into NVDA's speech sequence filter to detect language changes.
    Works with both NVDA's native language detection and the Enhanced
    Language Switching add-on, as both insert LangChangeCommand objects.
    """

    def __init__(self, onLanguageChange: Callable[[str], None]):
        """
        Initialize the language detector.

        Args:
            onLanguageChange: Callback function called when language changes.
                            Receives normalized language code as argument.
        """
        self._onLanguageChange = onLanguageChange
        self._currentLanguage: Optional[str] = None
        self._registered: bool = False
        self._extensionPoint = None

        # Check for Enhanced Language Switching on init
        _checkEnhancedLanguageSwitching()

    def register(self) -> None:
        """Register the language detection handler with NVDA's speech system."""
        if self._registered:
            log.debug("BrailleLanguageSwitcher: Language detector already registered")
            return

        try:
            # Try to get the extension point from speech module
            # In newer NVDA versions, it's in speech.extensions
            try:
                from speech import extensions
                self._extensionPoint = extensions.filter_speechSequence
                log.info("BrailleLanguageSwitcher: Using speech.extensions.filter_speechSequence")
            except (ImportError, AttributeError):
                pass

            # Fallback: try speech.speech module directly
            if self._extensionPoint is None:
                try:
                    from speech import speech as speechModule
                    if hasattr(speechModule, 'filter_speechSequence'):
                        self._extensionPoint = speechModule.filter_speechSequence
                        log.info("BrailleLanguageSwitcher: Using speech.speech.filter_speechSequence")
                except (ImportError, AttributeError):
                    pass

            # Fallback: try importing from speech directly
            if self._extensionPoint is None:
                try:
                    import speech
                    if hasattr(speech, 'filter_speechSequence'):
                        self._extensionPoint = speech.filter_speechSequence
                        log.info("BrailleLanguageSwitcher: Using speech.filter_speechSequence")
                except (ImportError, AttributeError):
                    pass

            if self._extensionPoint is not None:
                self._extensionPoint.register(self._filterSpeechSequence)
                self._registered = True
                log.info("BrailleLanguageSwitcher: Language detector registered successfully")
            else:
                log.error("BrailleLanguageSwitcher: Could not find speech filter extension point")

        except Exception as e:
            log.error(f"BrailleLanguageSwitcher: Error registering language detector: {e}")
            import traceback
            log.error(traceback.format_exc())

    def unregister(self) -> None:
        """Unregister the language detection handler."""
        if not self._registered:
            return

        try:
            if self._extensionPoint is not None:
                self._extensionPoint.unregister(self._filterSpeechSequence)
            self._registered = False
            self._currentLanguage = None
            log.info("BrailleLanguageSwitcher: Language detector unregistered")
        except Exception as e:
            log.error(f"BrailleLanguageSwitcher: Error unregistering language detector: {e}")

    def _filterSpeechSequence(
        self,
        speechSequence: List[Any],
        *args,
        **kwargs
    ) -> List[Any]:
        """
        Filter function registered with speech filter extension point.

        Inspects speech sequence for LangChangeCommand objects and triggers
        the callback when a language change is detected.
        """
        try:
            # Import LangChangeCommand here to ensure it's available
            from speech.commands import LangChangeCommand

            for item in speechSequence:
                if isinstance(item, LangChangeCommand):
                    newLang = item.lang
                    log.debug(f"BrailleLanguageSwitcher: Found LangChangeCommand: {newLang}")
                    if newLang and newLang != self._currentLanguage:
                        self._currentLanguage = newLang
                        normalizedLang = self._normalizeLanguageCode(newLang)
                        if normalizedLang:
                            log.info(
                                f"BrailleLanguageSwitcher: Language changed to "
                                f"{newLang} (normalized: {normalizedLang})"
                            )
                            try:
                                self._onLanguageChange(normalizedLang)
                            except Exception as e:
                                log.error(f"BrailleLanguageSwitcher: Error in callback: {e}")
        except Exception as e:
            log.error(f"BrailleLanguageSwitcher: Error in speech filter: {e}")
            import traceback
            log.error(traceback.format_exc())

        # Return unchanged sequence - we're only observing
        return speechSequence

    def _normalizeLanguageCode(self, lang: str) -> Optional[str]:
        """
        Normalize language code to ISO 639-1 two-letter format.
        """
        if not lang:
            return None

        lang = lang.lower()

        for sep in ['_', '-', '.']:
            if sep in lang:
                lang = lang.split(sep)[0]
                break

        if len(lang) >= 2:
            return lang[:2] if len(lang) == 2 else lang[:3]

        return None

    @property
    def isEnhancedLanguageSwitchingAvailable(self) -> bool:
        return _enhancedLanguageSwitchingAvailable

    @property
    def currentLanguage(self) -> Optional[str]:
        return self._currentLanguage

    @property
    def isRegistered(self) -> bool:
        return self._registered

    def reset(self) -> None:
        self._currentLanguage = None
