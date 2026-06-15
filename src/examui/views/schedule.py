# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  Massimo Santini

import dataclasses
from datetime import datetime, timedelta
from urllib.parse import urlencode

from flask import Blueprint, jsonify, render_template
from examui import config
from examui.models.store import all_students, UnderEvaluationEvent

bp = Blueprint('schedule', __name__, url_prefix='')


@bp.get('/schedule')
def schedule():
  today = datetime.strptime(config.TODAY, '%y%m%d').strftime('%Y-%m-%d')
  students = all_students()

  rows = []
  for s in sorted(
    (s for s in students.values() if s.events and isinstance(s.events[0], UnderEvaluationEvent)),
    key=lambda s: (s.events[0].metrics.slot or datetime.max, s.name),
  ):
    live = s.events[0]
    sm = s.summary_mark
    rows.append(
      {
        'email': s.email,
        'name': s.name,
        'matricola': s.matricola,
        'summary_mark': dataclasses.asdict(sm) if sm else None,
        'current_mark': live.mark.provisional,
        **dataclasses.asdict(live.metrics),
        'slot': live.metrics.slot.isoformat() if live.metrics.slot else None,
      }
    )

  unmarked = [r for r in rows if not r['current_mark'] and r['slot']]
  current_email = unmarked[0]['email'] if unmarked else None
  next_email    = unmarked[1]['email'] if len(unmarked) > 1 else None
  for r in rows:
    r['is_current'] = r['email'] == current_email
    r['is_next']    = r['email'] == next_email

  slot_dates = sorted({r['slot'][:10] for r in rows if r['slot']})

  return render_template(
    'schedule.html',
    rows=rows,
    today=today,
    slot_dates=slot_dates,
    email_domain=config.EMAIL_DOMAIN,
    teacher_email=config.TEACHER_EMAIL,
    teacher_name=config.TEACHER_NAME,
    subject_prefix=config.SUBJECT_PREFIX,
    titoli=config.TITOLI,
    slot_minutes=config.SLOT_MINUTES,
  )


_GIORNI = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
_MESI   = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno',
           'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']


def _fmt_slot(slot: datetime) -> str:
  return f'{_GIORNI[slot.weekday()]} {slot.day} {_MESI[slot.month - 1]}, {slot.strftime("%H:%M")}'


@bp.get('/api/schedule/public')
def public_schedule():
  now      = datetime.now()
  exam_dt  = datetime.strptime(config.TODAY, '%y%m%d')
  exam_fmt = f'{exam_dt.day} {_MESI[exam_dt.month - 1]} {exam_dt.year}'

  rows = []
  for s in sorted(
    (s for s in all_students().values() if s.events and isinstance(s.events[0], UnderEvaluationEvent)),
    key=lambda s: s.matricola,
  ):
    slot = s.events[0].metrics.slot
    cal_url = None
    if config.CAL_URL:
      cal_url = config.CAL_URL + '?' + urlencode({
        'name':      s.name,
        'email':     f'{s.email}@{config.EMAIL_DOMAIN}',
        'matricola': s.matricola,
      })
    rows.append({'matricola': s.matricola, 'slot': _fmt_slot(slot) if slot else None, 'cal_url': cal_url})

  booked = sum(1 for r in rows if r['slot'])
  return render_template(
    'public_schedule.html',
    rows=rows,
    course_name=config.COURSE_NAME,
    exam_date=exam_fmt,
    cal_url=config.CAL_URL,
    total=len(rows),
    booked=booked,
    generated_at=f"{now.strftime('%d/%m/%Y')} alle ore {now.strftime('%H:%M')}",
  )


@bp.get('/api/pace')
def pace():
  now = config.now()
  slot_delta = timedelta(minutes=config.SLOT_MINUTES)
  with_slots = [
    s.events[0]
    for s in all_students().values()
    if s.events
    and isinstance(s.events[0], UnderEvaluationEvent)
    and s.events[0].metrics.slot is not None
  ]
  if not with_slots:
    return jsonify(has_slots=False)
  expected_done = sum(1 for ev in with_slots if ev.metrics.slot + slot_delta <= now)
  actual_done = sum(1 for ev in with_slots if ev.mark.provisional)
  return jsonify(
    has_slots=True,
    delta=(actual_done - expected_done) * config.SLOT_MINUTES,
    done=actual_done,
    expected=expected_done,
    total=len(with_slots),
  )
