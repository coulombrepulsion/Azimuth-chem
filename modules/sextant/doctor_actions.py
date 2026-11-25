"""DoctorTool: the doctor of a calculation in the window — after a calculation that failed (or an optimization
that ran out of cycles) the remedy the doctor knows (modules/sextant/doctor.py) is offered as one button of the window
of the calculation; pressing it puts the changed settings into the form of Sextant (the last geometry onto the model
when the remedy asks for it) and starts the calculation again. A part of the window with its own port.

Not offered: a queue (its rows are repeated by «Подготовить повтор…»), an input file edited by hand unless the remedy
is to build it anew (the changed settings would not reach a hand-made file), a problem with advice only.
"""

from dataclasses import replace

from azimuth.i18n import tr
from modules.sextant import doctor


class DoctorTool:
    PORT = (
        'apply_calculation',
        'calculation',
        'coordinate_tool',
        'document',
        'documents',
        'input_tool',
        'job_window',
        'load_molecule',
        'notify',
        'run_tool',
        'switch_document',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)

    def _molecule(self):
        try:
            return self.w.coordinate_tool.table_molecule()
        except ValueError:
            return None

    def offer(self, job, text, ended=''):
        """The remedies for the end of job (doctor.examine); the first one with a repeat becomes the button of the
        window of the calculation (none: the button is hidden). Returns the remedies. Ended 'stopped' —
        an optimization stopped goes on from its last geometry; 'finished' — an imaginary frequency of a minimum."""
        calc = getattr(job, '_calc', None) or self.w.calculation()
        edited = bool(getattr(job, '_edited', False))
        if ended == 'stopped':
            remedy = doctor.stopped(calc)
            remedies = [remedy] if remedy is not None and doctor.last_geometry(text or '', str(job.spec.output)) else []
        elif ended == 'finished':
            remedy = doctor.imaginary(job.spec.kind, text or '', calc, str(job.spec.output))
            remedies = [remedy] if remedy is not None else []
        else:
            remedies = doctor.examine(job.spec.kind, text or '', getattr(job, 'code', None), calc, self._molecule(),
                                      edited)
        fix = next((r for r in remedies if r.label and (r.rebuild_input or not edited)), None)
        self.w.job_window.show_remedy(fix.label if fix else '', (lambda: self.repeat(job, fix)) if fix else None)
        return remedies

    def repeat(self, job, remedy):
        """The calculation again with the remedy: in the tab of the calculation, the settings of its form changed, the
        last geometry of the output on the model when asked (Ctrl+Z gives back the one before). Returns the new job
        or None (another calculation runs here, the geometry does not fit the molecule of the tab)."""
        if self.w.run_tool.job_running():
            self.w.notify(tr('Здесь уже идёт расчёт: дождитесь его конца или остановите.'), 6000)
            return None
        target = self.w.run_tool.result_tab_of(job)
        if target is not None and target is not self.w.document() and target in self.w.documents:
            self.w.switch_document(self.w.documents.index(target))
        if remedy.last_geometry or remedy.displace:
            geometry = (doctor.displaced(job.text(), str(job.spec.output)) if remedy.displace else
                        doctor.last_geometry(job.text(), str(job.spec.output)))
            own = self._molecule()
            if geometry is None or own is None or [a.symbol for a in geometry.atoms] != [a.symbol for a in own.atoms]:
                self.w.notify(tr('Последняя геометрия расчёта не подходит к молекуле вкладки — повтор не начат.'), 10000)
                return None
            self.w.load_molecule(replace(geometry, title=own.title, bonds=own.bonds), record=True)
        self.w.apply_calculation(doctor.apply(self.w.calculation(), remedy))
        if remedy.rebuild_input:
            self.w.input_tool.reset_input()
        else:
            self.w.input_tool.refresh_input()
        self.w.notify(tr('Повтор с исправлением: ') + remedy.label, 10000)
        return self.w.run_tool.run_calculation()
