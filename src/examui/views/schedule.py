# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  Massimo Santini

import dataclasses
from datetime import datetime

from flask import Blueprint, render_template
from examui.models.store import all_students, LiveCurrentExamEvent

bp = Blueprint('schedule', __name__, url_prefix='')


@bp.get('/schedule')
def schedule():
    today    = datetime.now().strftime('%Y-%m-%d')
    students = all_students()

    rows = []
    for s in sorted(
        (s for s in students.values() if isinstance(s.current, LiveCurrentExamEvent)),
        key=lambda s: (s.current.metrics.slot or datetime.max, s.name),
    ):
        rows.append({
            'email':        s.email,
            'name':         s.name,
            'matricola':    s.matricola,
            'verbali_mark': s.verbali_mark,
            'current_mark': s.current.mark,
            **dataclasses.asdict(s.current.metrics),
        })

    return render_template('schedule.html',
                           rows=rows,
                           today=today)
