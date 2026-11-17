# -*- coding: UTF-8 -*-
# BrailleLanguageSwitcher: each language in its own braille table
#
# NVDA turns every braille region into cells with a single call, louisHelper.translate, in Region.update. It
# returns the cells and two maps: the text position of every cell, and the cell of every text position. Cursor,
# selection, routing and panning all work from those maps.
#
# While a region updates, this module wraps that call: the text is split into language runs by the installed
# speech detectors (Dialingo, Enhanced Language Detection, ...), each run is translated with its language's
# table, and the cells and maps are joined again, shifted so they still point at the right characters. A line
# of English then Russian shows English braille, then Russian braille.

import threading
import time
from collections import OrderedDict
from typing import Callable, List, Optional, Sequence, Tuple

from logHandler import log

from . import speechLanguage

# A segment of the text: (start, end, language), language None for the default.
Segment = Tuple[int, int, Optional[str]]

_CACHE_SIZE = 256
#: Seconds a line's languages are remembered: a changed detector setting is picked up within this time.
_CACHE_SECONDS = 60.0
#: Longer texts (a whole document in one region) are shown in the default table without detection.
_MAX_DETECT_LENGTH = 10000


def alignRuns(text: str, runs: Sequence[Tuple[Optional[str], str]]) -> List[Segment]:
    """Where each run of `runs` lies in `text`, as segments covering all of `text` without gaps.

    A run starts at its first non-space character and lasts until the next run starts, so the space between two
    languages stays with the first. Runs a filter changed beyond recognition (a voice dictionary, say) are not
    found and their text stays with the run before. Text before the first run found takes that run's language.
    """
    starts: List[Tuple[int, Optional[str]]] = []
    position = 0
    for language, runText in runs:
        needle = runText.strip()
        if not needle:
            continue
        index = text.find(needle, position)
        if index < 0:
            continue
        if not starts or starts[-1][1] != language:
            starts.append((index, language))
        position = index + len(needle)
    if not starts:
        return [(0, len(text), None)] if text else []
    segments: List[Segment] = []
    for i, (start, language) in enumerate(starts):
        if i == 0:
            start = 0
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        if end > start:
            segments.append((start, end, language))
    return segments


def trustSegments(text: str, segments: List[Segment], minWords: int) -> List[Segment]:
    """A run in another language with fewer than `minWords` words is shown in the default table; then
    neighbouring segments with the same language are joined."""
    trusted = []
    for start, end, language in segments:
        if language is not None and len(text[start:end].split()) < max(1, minWords):
            language = None
        if trusted and trusted[-1][2] == language:
            trusted[-1] = (trusted[-1][0], end, language)
        else:
            trusted.append((start, end, language))
    return trusted


def segmentAt(segments: Sequence[Segment], position: int) -> Optional[Segment]:
    """The segment holding `position`; the last one for the end of the text."""
    for segment in segments:
        if segment[0] <= position < segment[1]:
            return segment
    return segments[-1] if segments else None


def translateSegments(
    translate: Callable,
    segments: Sequence[Tuple[int, int, str]],
    inbuf: str,
    typeform,
    cursorPos: Optional[int],
    mode,
    cursorModeFlag: int,
    otherTables: Sequence[str],
):
    """Translate each (start, end, table) segment of `inbuf` with its own table and join the results, with the
    same return value as louisHelper.translate for the whole text."""
    cells: List[int] = []
    brailleToRawPos: List[int] = []
    rawToBraillePos: List[int] = []
    brailleCursorPos = None
    cursorSegment = None
    if cursorPos is not None:
        for index, (start, end, _table) in enumerate(segments):
            if start <= cursorPos < end:
                cursorSegment = index
                break
        else:
            cursorSegment = len(segments) - 1
    for index, (start, end, table) in enumerate(segments):
        part = inbuf[start:end]
        partTypeform = typeform[start:end] if typeform is not None else None
        hasCursor = index == cursorSegment
        partMode = mode if hasCursor else (mode & ~cursorModeFlag)
        partCells, partB2R, partR2B, partCursor = translate(
            [table, *otherTables],
            part,
            typeform=partTypeform,
            cursorPos=(cursorPos - start) if hasCursor else None,
            mode=partMode,
        )
        offset = len(cells)
        if hasCursor and partCursor is not None:
            brailleCursorPos = partCursor + offset
        cells.extend(partCells)
        brailleToRawPos.extend(pos + start for pos in partB2R)
        rawToBraillePos.extend(pos + offset for pos in partR2B)
    return cells, brailleToRawPos, rawToBraillePos, brailleCursorPos


class MixedTranslator:
    """Installs the wrapper around louisHelper.translate and decides each region's segments."""

    def __init__(self, tableFor: Callable[[Optional[str]], Optional[str]], getMinWords: Callable[[], int]):
        """
        Args:
            tableFor: the output table for a language, or None to keep the table NVDA asked for (the default).
            getMinWords: the configured minimum word count.
        """
        self._tableFor = tableFor
        self._getMinWords = getMinWords
        self._original = None
        self._installed = False
        self._local = threading.local()
        self._failed = set()
        self._cache: "OrderedDict[str, List[Segment]]" = OrderedDict()

    # --- installation ---

    def install(self) -> None:
        if self._installed:
            return
        if self._original is None:
            import louisHelper

            self._original = louisHelper.translate
            louisHelper.translate = self._translate
        # Else the wrapper is still in the chain under another add-on's (see uninstall): just switch it on again.
        self._installed = True
        log.info("BrailleLanguageSwitcher: mixed language braille on")

    def uninstall(self) -> None:
        if not self._installed:
            return
        self._installed = False
        import louisHelper

        if louisHelper.translate == self._translate:
            louisHelper.translate = self._original
            self._original = None
        # Else another add-on wrapped translate after this one and calls this wrapper. It stays in the chain,
        # passing straight through, and must keep the original: forgetting it would make it call
        # louisHelper.translate, the other wrapper, which calls this one again, without end.
        self.clearCache()
        log.info("BrailleLanguageSwitcher: mixed language braille off")

    @property
    def installed(self) -> bool:
        return self._installed

    def clearCache(self) -> None:
        self._cache.clear()

    # --- one region update ---

    def beginRegion(self) -> None:
        """Called before a braille region updates: its translation is split by language."""
        self._local.depth = getattr(self._local, "depth", 0) + 1
        self._local.cursorLanguage = None
        self._local.sawCursor = False

    def endRegion(self) -> Tuple[bool, Optional[str]]:
        """Called after the region updated. Returns (the region had a cursor, the language at the cursor)."""
        self._local.depth = max(0, getattr(self._local, "depth", 1) - 1)
        return self._local.sawCursor, self._local.cursorLanguage

    def _active(self) -> bool:
        return getattr(self._local, "depth", 0) > 0

    # --- segmentation ---

    @staticmethod
    def _context():
        """What else decides a text's languages: the default voice's language, whether language commands are
        made at all, and the synthesizer."""
        try:
            import config
            import speech
            import synthDriverHandler

            synth = synthDriverHandler.getSynth()
            return (
                speech.getCurrentLanguage(),
                bool(config.conf["speech"]["autoLanguageSwitching"]),
                getattr(synth, "name", None),
            )
        except Exception:
            return None

    def segments(self, text: str) -> List[Segment]:
        """The language segments of `text`. A line is detected once and remembered for a while (see
        _CACHE_SECONDS), not again on every caret movement."""
        whole = [(0, len(text), None)]
        if len(text) > _MAX_DETECT_LENGTH:
            return whole
        key = (text, self._context(), self._getMinWords())
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached is not None and now - cached[0] < _CACHE_SECONDS:
            self._cache.move_to_end(key)
            return cached[1]
        try:
            runs = speechLanguage.languageRuns(speechLanguage.filteredSequence(text))
            segments = trustSegments(text, alignRuns(text, runs), self._getMinWords())
        except Exception:
            # Not remembered: the next update tries again.
            log.debugWarning("BrailleLanguageSwitcher: braille text could not be split by language", exc_info=True)
            return whole
        self._cache[key] = (now, segments)
        self._cache.move_to_end(key)
        while len(self._cache) > _CACHE_SIZE:
            self._cache.popitem(last=False)
        return segments

    def dominantLanguage(self, text: str, minWords: int):
        """(decided, language) for the language most of `text`'s words are in, from the remembered segments;
        not decided below `minWords` words or for a single character."""
        if not text or len("".join(text.split())) <= 1 or len(text.split()) < max(1, minWords):
            return False, None
        words = {}
        for start, end, language in self.segments(text):
            words[language] = words.get(language, 0) + len(text[start:end].split())
        if not words:
            return False, None
        return True, max(words, key=words.get)

    # --- the wrapper ---

    def _translate(self, tableList, inbuf, typeform=None, cursorPos=None, mode=0):
        original = self._original
        if original is None:
            import louisHelper
            original = louisHelper.translate
        if not self._installed or not self._active() or not inbuf or "\0" in inbuf or not tableList:
            return original(tableList, inbuf, typeform=typeform, cursorPos=cursorPos, mode=mode)
        tabled = []
        try:
            segments = self.segments(inbuf)
            if cursorPos is not None:
                self._local.sawCursor = True
                atCursor = segmentAt(segments, cursorPos)
                self._local.cursorLanguage = atCursor[2] if atCursor else None
            defaultTable = tableList[0]
            tabled = []
            for start, end, language in segments:
                table = (self._tableFor(language) if language is not None else None) or defaultTable
                if tabled and tabled[-1][2] == table:
                    tabled[-1] = (tabled[-1][0], end, table)
                else:
                    tabled.append((start, end, table))
            if len(tabled) == 1 and tabled[0][2] == defaultTable:
                return original(tableList, inbuf, typeform=typeform, cursorPos=cursorPos, mode=mode)
            # louisHelper.TranslationMode.COMPBRL_AT_CURSOR is this same flag, but only exists since NVDA 2026.3;
            # before, Region.update puts louis.compbrlAtCursor into mode itself. Left set on a segment without the
            # cursor (cursorPos 0), its first word would be shown in computer braille.
            import louis

            return translateSegments(
                original, tabled, inbuf, typeform, cursorPos, mode, louis.compbrlAtCursor, list(tableList[1:])
            )
        except Exception:
            # A missing or broken table would fail on every update: report it once per set of tables.
            failedKey = tuple(t[2] for t in tabled)
            if failedKey not in self._failed:
                self._failed.add(failedKey)
                log.error("BrailleLanguageSwitcher: mixed language translation failed; using one table", exc_info=True)
            return original(tableList, inbuf, typeform=typeform, cursorPos=cursorPos, mode=mode)
