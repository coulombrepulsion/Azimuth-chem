"""The crystal projects in the project tabs — a part of ProjectNavigation (azimuth/project_navigation.py), a mixin of
Studio.

§1 PURPOSE
    A crystal of «Компас · Кристалл» is a project of its own kind (azimuth/crystal_projects.py): its tab, the batch
    of its steps, the empty tab of the crystal and the change between the molecule and the crystal of Compass.
§7 TESTS tests/projects/test_project_navigation.py.
"""

from pathlib import Path

from azimuth import projects
from azimuth.i18n import tr


class ProjectCrystals:
    # -- a crystal as a project (azimuth/crystal_projects.py) ----------------------------------------------
    def crystal_project_opened(self, text, name, path=None):
        """The crystal just built in the tab shown gets its project: a new one (path None) or the one it was read
        from; the tab of the project is chosen."""
        if not hasattr(self, 'project_tabs'):
            return None
        from azimuth import crystal_projects

        current = self.research_path()
        # a project with nothing in it (a new one, left for «Компас · Кристалл» to open this CIF) becomes the
        # project of the crystal — its tab takes the place, no second tab beside an empty one
        empty = self.empty_project(current) or self.empty_project(getattr(self, '_left_for_crystal', None))
        self._left_for_crystal = None
        if current and not crystal_projects.is_crystal(current) and current != empty:
            self.save_research_project()
            self._molecule_research_path = current
        fresh = path is None
        if path is None:
            try:
                # an output of CRYSTAL too — the folder «CAFORM_3GPa», not «CAFORM_3GPa.out»
                path = crystal_projects.create(self.projects_root('crystal'), name.rsplit('.', 1)[0] if name.lower().endswith(
                    ('.cif', '.out', '.outp', '.log')) else name, text)
            except (OSError, ValueError) as exc:
                self.error(exc)
                return None
        path = Path(path).resolve()
        document = self.document()
        document.research_project_path = str(path)
        self.crystal_documents[str(path)] = document
        if hasattr(self, 'remember_recent'):  # among «Недавние файлы»; «Продолжить» of the home
            self.remember_recent('crystal', path)
        elif hasattr(self, 'file_tool'):
            self.file_tool.note_recent(path, document=False)
        if empty is not None and path not in self.project_sessions:
            self.project_sessions[self.project_sessions.index(empty)] = path
            self.project_empty_documents.pop(str(empty), None)
            if getattr(self, '_molecule_research_path', None) == empty:
                self._molecule_research_path = None
            try:  # its folder stays on disk, as of any closed tab
                self.session_registry().close(projects.Project.view(empty).data['id'], save=True)
            except (OSError, ValueError, KeyError):
                pass
        self.register_project_tab(path)
        if fresh:  # a CIF opened only to look at leaves no folder either (discard_untouched_project)
            self.viewed_projects().add(path)
        return path

    @staticmethod
    def crystal_row_id(ident):
        """The row of a crystal of a project in the list — 'crystal' for the first (as before), 'crystal:<id>'
        for the others."""
        from azimuth import crystal_projects

        return 'crystal' if ident == crystal_projects.FIRST else f'crystal:{ident}'

    def crystal_batch_idents(self):
        """The crystals with a tick of the crystal project shown in its batch mode (crystal_batch.py), or
        None (another project, the single mode)."""
        from azimuth import crystal_projects

        path = self.research_path()
        if not path or not crystal_projects.is_crystal(path) or projects.Project.view(path).data.get('mode') != 'batch':
            return None
        return crystal_projects.batch_ids(path)

    def crystal_project_to_add(self):
        """The crystal project whose tab is shown in «Компас · Кристалл» — a
        crystal opened now goes into it; None — it gets a project of its own, as before."""
        if not hasattr(self, 'project_tabs') or getattr(self, '_activating_project', False):
            return None
        from azimuth import crystal_projects

        path = self.research_path()
        if not path or not crystal_projects.is_crystal(path) or getattr(self, 'compass_mode', 'molecule') != 'crystal':
            return None
        path = Path(path).resolve()
        document = self.crystal_documents.get(str(path))
        if document is None or document is not self.document():
            return None
        return path

    def crystal_added_to_project(self, path, text, name):
        """The crystal just built in the tab of the crystal project path is written into it as one more
        crystal, the one shown; the steps of the crystal shown before go. Returns path (None when it could not be
        written: the crystal then gets a project of its own)."""
        from azimuth import crystal_projects

        title = name.rsplit('.', 1)[0] if name.lower().endswith(('.cif', '.out', '.outp', '.log')) else name
        try:
            crystal_projects.add(path, text, title)
        except (OSError, ValueError, KeyError) as exc:
            self.error(exc)
            return None
        self.viewed_projects().discard(Path(path).resolve())  # more than one crystal — not a project only looked at
        if hasattr(self, 'trajectory_tool'):
            self.trajectory_tool.load_crystal_steps([], '')
        self.notify(tr('Кристалл «{}» добавлен в проект «{}» — кристаллы проекта в его списке.').format(
            title, projects.Project.view(path).data.get('name', '')), 10000)
        return path

    def choose_project_crystal(self, row_id):
        """A crystal of the project shown chosen in its list — it is shown in the same tab, with the steps
        and modes of its own runs."""
        from azimuth import crystal_projects

        path = self.research_path()
        if not path or not crystal_projects.is_crystal(path):
            return False
        ident = crystal_projects.FIRST if row_id == 'crystal' else row_id.split(':', 1)[1]
        if ident == crystal_projects.active(path) and getattr(self, 'crystal', None) is not None:
            return False
        try:
            crystal_projects.set_active(path, ident)
            text, title = crystal_projects.cif_text(path), crystal_projects.title(path)
        except (OSError, ValueError, KeyError) as exc:
            self.error(exc)
            return False
        if hasattr(self, 'trajectory_tool'):
            self.trajectory_tool.load_crystal_steps([], '')
        self._activating_project = True
        try:
            self.crystal_tool.open_crystal_text(text, title, project=Path(path).resolve(), same_tab=True)
            self.show_project_crystal_steps(path)
            from modules.compass.actions import crystal_dynamics

            crystal_dynamics.show_modes(self, quiet=True, project=path)
        except (OSError, ValueError) as exc:
            self.error(exc)
        finally:
            self._activating_project = False
        self.refresh_project_navigation()
        return True

    def empty_project(self, path):
        """The path, when it is an open project of molecules with none in it and nothing drawn in its tab."""
        from azimuth import crystal_projects

        if path is None or Path(path) not in self.project_sessions or crystal_projects.is_crystal(path):
            return None
        if projects.Project.view(path).molecules:
            return None
        placeholder = self.project_empty_documents.get(str(path))
        if placeholder is not None and placeholder.molecule.atoms:
            return None
        return Path(path)

    def show_project_crystal_steps(self, target):
        """A project of a crystal opened — the steps of its last optimization (crystal_steps. project_steps: CP2K or
        Quantum ESPRESSO, its supercell read back from its first step) in the panel of the steps of its tab, as after
        the run; «Взять эту геометрию» gives the optimized cell of the file. False without steps."""
        from azimuth import crystal_projects
        from modules.compass.chemistry import crystal_steps

        shown = getattr(self, 'crystal', None)  # (the crystal of the file, the block, …)
        crystal = shown[0] if isinstance(shown, tuple) and shown else shown
        if crystal is None or not hasattr(self, 'trajectory_tool'):
            return False
        try:
            steps, folder = crystal_steps.project_steps(target, crystal, crystal_projects.title(target))
        except (OSError, ValueError, KeyError):
            return False
        if not steps:
            return False
        program = 'CP2K' if folder.name.startswith('cp2k') else 'Quantum ESPRESSO'
        self.trajectory_tool.load_crystal_steps(steps, tr('оптимизация {} · {}').format(program, folder.name), folder)
        self.notify(tr('Шаги последней оптимизации проекта ({}) — в панели шагов; «Взять эту геометрию» — '
                       'оптимизированная ячейка.').format(len(steps) - 1), 8000)
        return True

    def activate_crystal_project(self, target):
        from azimuth import crystal_projects

        section = self.stack.currentIndex()
        current = self.research_path()
        if current and not crystal_projects.is_crystal(current):
            self.save_research_project()
            self._molecule_research_path = current
        target = Path(target).resolve()
        document = self.crystal_documents.get(str(target))
        self._activating_project = True
        try:
            self.crystal_tool.set_compass_mode('crystal')
            if document is not None and document in self.documents:
                self.switch_document(self.documents.index(document))
            else:
                try:
                    self.crystal_tool.open_crystal_text(crystal_projects.cif_text(target), crystal_projects.title(target),
                                                        project=target)
                    self.show_project_crystal_steps(target)
                    from modules.compass.actions import crystal_dynamics

                    crystal_dynamics.show_modes(self, quiet=True, project=target)  # «Частоты» in the drawer
                except (OSError, ValueError) as exc:
                    self.error(exc)
        finally:
            self._activating_project = False
        self._research_path = target
        if hasattr(self, 'remember_recent'):  # the crystal worked on last — «Продолжить» of the home page
            self.remember_recent('crystal', target)
        if section == 2:  # switching project tabs in Spectrum stays in Spectrum: the results of the crystal
            self.navigate(2)
        elif section == 1 and hasattr(self, 'crystal_mode_tool'):
            self.crystal_mode_tool.follow(self.document() if getattr(self, 'crystal', None) is not None else None)
        self.refresh_project_navigation()
        return True

    def activate_empty_crystal_tab(self, target, document):
        """A new project made in «Компас · Кристалл» (nothing opened yet) chosen again: its empty tab there."""
        from azimuth import crystal_projects

        current = self.research_path()
        if current and not crystal_projects.is_crystal(current):
            self.save_research_project()
            self._molecule_research_path = current
        section = self.stack.currentIndex()
        self._activating_project = True
        try:
            self.crystal_tool.set_compass_mode('crystal')
            if document in self.documents:
                self.switch_document(self.documents.index(document))
        finally:
            self._activating_project = False
        self._research_path = Path(target).resolve()
        if section == 2:  # Spectrum stays — the empty Spectrum of a crystal
            self.navigate(2)
        elif section == 1 and hasattr(self, 'crystal_mode_tool'):
            self.crystal_mode_tool.follow(None)
        self.refresh_project_navigation()
        return True

    def close_crystal_project(self, index, target, active):
        """The tab of a crystal project closed: its tab of «Кристалл» goes, its folder stays on disk (unless the
        crystal was only looked at — discard_untouched_project)."""
        try:
            self.session_registry().close(projects.Project.view(target).data['id'], save=True)
        except (OSError, ValueError, KeyError):
            pass
        self.discard_untouched_project(target)
        document = self.crystal_documents.pop(str(Path(target).resolve()), None)
        self.project_sessions.pop(index)
        if document is not None:
            if document in self.documents and getattr(self, 'compass_mode', 'molecule') == 'crystal':
                document.dirty = False
                if len(self.documents) > 1:
                    k = self.documents.index(document)
                    self.documents.pop(k)
                    self.current_document = min(self.current_document, len(self.documents) - 1)
                    self.restore_document(self.documents[self.current_document])
                else:
                    self.crystal_tool.clear_crystal()
                    self.new_document()
                    self.documents.remove(document)
                    self.current_document = 0
            else:
                docs, k = self.shelved_documents.get('crystal', ([], 0))
                if document in docs:
                    docs.remove(document)
                    self.shelved_documents['crystal'] = (docs, min(k, max(0, len(docs) - 1)))
        if not active:
            self.refresh_project_navigation()
            return True
        self._research_path = None
        if self.project_sessions:
            self.activate_project_tab(min(index, len(self.project_sessions) - 1))
        # the last project closed — Compass
        # stays where it was, the crystal one with its empty field (it went to «Молекула» before)
        self.refresh_project_navigation()
        return True

    def follow_compass_kind(self, mode):
        """«Компас · Кристалл» or «Молекула» chosen (not through a tab): the tab of the project of the tab shown."""
        if not hasattr(self, 'project_tabs') or getattr(self, '_activating_project', False):
            return
        from azimuth import crystal_projects

        current = self.research_path()
        own = getattr(self.document(), 'research_project_path', '') if hasattr(self, 'document') else ''
        if mode == 'crystal':
            self._left_for_crystal = current  # an empty one becomes the project of the crystal opened next
            if current and not crystal_projects.is_crystal(current):
                self._molecule_research_path = current
            self._research_path = Path(own).resolve() if own and crystal_projects.is_crystal(own) else None
        else:
            back = getattr(self, '_molecule_research_path', None)
            if own and not crystal_projects.is_crystal(own) and Path(own).resolve() in self.project_sessions:
                self._research_path = Path(own).resolve()
            elif back is not None and back in self.project_sessions:
                self._research_path = back
            elif current and crystal_projects.is_crystal(current):
                self._research_path = None
        self.refresh_project_navigation()
