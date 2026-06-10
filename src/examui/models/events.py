# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  Massimo Santini

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from examui.models.store import LiveCurrentExamEvent


@dataclass(frozen=True)
class ExamEvent:
    date: str
    mark: str        # 'AS' | 'RI?' | 'RE?' | '19V' | '19R' | ...
    note: str | None


@dataclass(frozen=True)
class Metrics:
    tests_fail:   bool           # True = FAILURE
    javadoc_fail: bool           # True = FAILURE
    has_cycles:   bool           # True = cycles present
    main_sloc:    int            # source lines of code, clients excluded
    main_docs:    int            # documentation lines, clients excluded
    main_files:   int            # file count, clients excluded
    client_sloc:  int            # source lines of code, clients only
    client_files: int            # file count, clients only
    slot:         datetime | None  # booked oral slot (None if not booked)
    upload:       datetime | None  # submission timestamp

    @classmethod
    def from_row(cls, row: dict) -> Metrics:
        def _dt(val) -> datetime | None:
            s = str(val).strip()
            if not s:
                return None
            try:
                return datetime.strptime(s, '%y%m%d-%H%M')
            except ValueError:
                return None

        return cls(
            tests_fail=str(row.get('tests',   '')).strip().upper() != 'SUCCESS',
            javadoc_fail=str(row.get('javadoc', '')).strip().upper() != 'SUCCESS',
            has_cycles=str(row.get('cyclic',  '')).strip().upper() == 'YES',
            main_sloc=int(row.get('code',  0) or 0),
            main_docs=int(row.get('docs',  0) or 0),
            main_files=int(row.get('file',  0) or 0),
            client_sloc=int(row.get('ccode', 0) or 0),
            client_files=int(row.get('cfile', 0) or 0),
            slot=_dt(row.get('date',   '')),
            upload=_dt(row.get('upload', '')),
        )


class AbsentCurrentExamEvent:
    """Enrolled in current exam but no source turned in — immutable."""

    def __init__(self, date: str) -> None:
        self.date = date

    @property
    def mark(self) -> str:
        return 'AS'

    @mark.setter
    def mark(self, value: str) -> None:
        raise AttributeError('No source turned in')

    @property
    def short_note(self) -> str:
        return ''

    @short_note.setter
    def short_note(self, value: str) -> None:
        raise AttributeError('No source turned in')

    @property
    def long_note(self) -> str:
        return ''

    @long_note.setter
    def long_note(self, text: str) -> None:
        raise AttributeError('No source turned in')


@dataclass(frozen=True)
class Student:
    email:     str
    matricola: str
    name:      str
    events:    list[ExamEvent] = field(default_factory=list)
    current:   AbsentCurrentExamEvent | LiveCurrentExamEvent | None = None

    @property
    def verbali_mark(self) -> dict | None:
        passing = next((e for e in self.events if e.mark[-1:] == 'V'), None)
        if passing:
            return {'value': passing.mark[:-1], 'kind': 'pass'}
        tilde = next(
            (e for e in self.events
             if e.mark[-1:] == 'R' and e.mark[:2] not in ('RI', 'RE')),
            None,
        )
        if tilde:
            return {'value': tilde.mark[:-1] + '~', 'kind': 'tilde'}
        last = next(
            (e for e in self.events if e.mark[:2] in ('RE', 'RI')),
            None,
        )
        if last:
            return {'value': last.mark[:2], 'kind': last.mark[:2]}
        return None
