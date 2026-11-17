# -*- coding: UTF-8 -*-
# BrailleLanguageSwitcher: follow the language of speech
#
# Every language detector for NVDA (Dialingo, Enhanced Language Detection, NVDA's own document tags) works the
# same way: it inserts LangChangeCommand items into the speech sequence, and the synthesizer switches voice on
# them. This module reads those commands instead of detecting anything itself, so braille follows whatever
# made the voice change, and needs no knowledge of any particular detector.
#
# Two sources:
# - pre_speech: NVDA notifies it with the sequence after every speech filter has run, whatever order the
#   add-ons loaded in, and even when speech mode is off or on beeps. This covers focus, caret and browse mode
#   movement, say all, and anything else NVDA speaks.
# - braille text no speech accompanied (panning the display, routing): the region's text is run through the
#   same speech filters, so the same detector decides, without anything being spoken.

import time
from typing import Iterable, List, Optional, Tuple

from logHandler import log

# The language a sequence is spoken in when it carries no language command: the synthesizer's default voice.
DEFAULT = None


def dominantLanguage(sequence: Iterable, minWords: int) -> Tuple[bool, Optional[str]]:
    """The language most of a speech sequence's words are spoken in.

    Returns (decided, language). `decided` is False when the sequence has fewer than `minWords` words, as for
    a bare "button"; a single character never decides: too little to move braille away from what it shows.
    `language` is DEFAULT (None) for text left in the default voice's language, else the command's language.
    """
    from speech.commands import LangChangeCommand

    words = {}
    characters = 0
    current = DEFAULT
    for item in sequence:
        if isinstance(item, LangChangeCommand):
            current = DEFAULT if item.isDefault or not item.lang else item.lang
        elif isinstance(item, str):
            count = len(item.split())
            if count:
                words[current] = words.get(current, 0) + count
                characters += len("".join(item.split()))
    # A single character (typing echo, character navigation, spelling) never switches, even with a minimum of
    # one word: its language is a guess, and switching the input table in the middle of a word would hurt.
    if characters <= 1 or sum(words.values()) < max(1, minWords):
        return False, DEFAULT
    return True, max(words, key=words.get)


def _isLanguageReporter(handler) -> bool:
    """NVDA's own filter that adds "German" before German text. It changes speech state (the last language
    reported), so running it on braille text would stop the next real language change being announced."""
    return getattr(handler, "__name__", "") == "getSpeechSequenceWithLangs"


def filteredSequence(text: str) -> list:
    """`text` as the installed speech detectors would hand it to the synthesizer, with their language commands,
    without speaking it. NVDA's language reporter is skipped (see _isLanguageReporter)."""
    sequence = [text]
    try:
        from extensionPoints.util import callWithSupportedKwargs
        from speech.extensions import filter_speechSequence
    except Exception:
        log.debugWarning("BrailleLanguageSwitcher: speech filters unavailable", exc_info=True)
        return sequence
    for handler in list(filter_speechSequence.handlers):
        if _isLanguageReporter(handler):
            continue
        try:
            result = callWithSupportedKwargs(handler, sequence)
            if result is not None:
                sequence = result
        except Exception:
            log.debugWarning("BrailleLanguageSwitcher: a speech filter failed on braille text", exc_info=True)
    return sequence


def languageRuns(sequence: Iterable) -> List[Tuple[Optional[str], str]]:
    """The strings of a speech sequence in order, each with the language it is spoken in (DEFAULT: None)."""
    from speech.commands import LangChangeCommand

    runs = []
    current = DEFAULT
    for item in sequence:
        if isinstance(item, LangChangeCommand):
            current = DEFAULT if item.isDefault or not item.lang else item.lang
        elif isinstance(item, str) and item.strip():
            runs.append((current, item))
    return runs


def detectWithSpeechFilters(text: str, minWords: int) -> Tuple[bool, Optional[str]]:
    """The language the installed speech detectors would speak most of `text` in, without speaking it."""
    if not text or not text.strip():
        return False, DEFAULT
    try:
        return dominantLanguage(filteredSequence(text), minWords)
    except Exception:
        log.debugWarning("BrailleLanguageSwitcher: braille text could not be checked", exc_info=True)
        return False, DEFAULT


class SpeechLanguageFollower:
    """Listens to pre_speech and reports the language each spoken sequence is mostly in."""

    #: Braille regions updated this soon after speech belong to what was just spoken (focus and caret
    #: movement speak first, then update braille), so speech has already decided their language.
    SPEECH_WINDOW = 0.5

    def __init__(self, onLanguage, getMinWords):
        """
        Args:
            onLanguage: called on NVDA's main thread with the language code, or None for the default voice.
            getMinWords: returns the configured minimum word count.
        """
        self._onLanguage = onLanguage
        self._getMinWords = getMinWords
        self._registered = False
        self._lastSpeechTime = 0.0

    def register(self) -> None:
        if self._registered:
            return
        try:
            from speech.extensions import pre_speech
        except ImportError:
            # NVDA before 2024.2: braille text is still checked with the speech detectors, without speech.
            log.warning("BrailleLanguageSwitcher: this NVDA has no pre_speech; checking braille text only")
            return
        pre_speech.register(self._preSpeech)
        self._registered = True
        log.info("BrailleLanguageSwitcher: following the language of speech")

    def unregister(self) -> None:
        if not self._registered:
            return
        from speech.extensions import pre_speech

        try:
            pre_speech.unregister(self._preSpeech)
        except Exception:
            pass
        self._registered = False
        log.info("BrailleLanguageSwitcher: stopped following the language of speech")

    @property
    def registered(self) -> bool:
        return self._registered

    def speechIsRecent(self) -> bool:
        return time.monotonic() - self._lastSpeechTime < self.SPEECH_WINDOW

    def _preSpeech(self, speechSequence=None, **kwargs) -> None:
        if not speechSequence:
            return
        try:
            decided, language = dominantLanguage(speechSequence, self._getMinWords())
        except Exception:
            log.debugWarning("BrailleLanguageSwitcher: could not read a speech sequence", exc_info=True)
            return
        if not decided:
            return
        # Only sequences long enough to decide count as speech covering the braille, so a short announcement
        # does not stop panned text from being detected.
        self._lastSpeechTime = time.monotonic()
        import core

        # speak() runs on the main thread in practice; anything else is moved there, as tables are not thread safe.
        if core.isMainThread():
            self._onLanguage(language)
        else:
            import wx

            wx.CallAfter(self._onLanguage, language)
