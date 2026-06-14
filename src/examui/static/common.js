const MARK_CSS = {
  passato:   'bg-success',
  rifiutato: 'bg-primary',
  respinto:  'bg-danger',
  ritirato:  'bg-orange',
  assente:   'bg-secondary',
};

const MARK_LABEL = {
  assente:  'AS',
  respinto: 'RE',
  ritirato: 'RI',
};

function renderMark(vm, cm) {
  const inSchedule = cm !== undefined;
  const hasProvisional = inSchedule && !!cm;

  if (hasProvisional) {
    return `<span class="badge bg-warning text-dark">${cm}</span>`;
  }
  if (vm) {
    const label = MARK_LABEL[vm.kind] ?? String(vm.value);
    return `<span class="badge ${MARK_CSS[vm.kind] ?? 'bg-secondary'}">${label}</span>`;
  }
  if (inSchedule) {
    return `<span class="badge bg-info" style="min-width:2.2em;">&nbsp;</span>`;
  }
  return '';
}
