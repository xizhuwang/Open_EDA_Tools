"""Native Tk dashboard. Editor/advanced viewers remain independent desktop apps."""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .project import ROOT, load_project
from .reports import ANSI
from .runner import Runner, RunError, doctor, latest_run, open_view


class Workbench(tk.Tk):
    def __init__(self, project):
        super().__init__()
        self.project = project
        self.runner = None
        self.events = queue.Queue(maxsize=3000)
        self.artifacts = {}
        self.path_data = {}
        self.selected_run = None
        self.title('Open EDA Tools  ·  WSL Desktop Workbench')
        self.geometry('1320x850')
        self.minsize(960, 650)
        self.configure(bg='#101a27')
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', background='#172434', foreground='#dce8f6', fieldbackground='#101a27', font=('sans-serif', 10))
        style.configure('TButton', padding=(10, 7), background='#29435d')
        style.map('TButton', background=[('active', '#326a89')])
        style.configure('Treeview', rowheight=27, background='#101a27', fieldbackground='#101a27')
        style.configure('Treeview.Heading', background='#29435d', padding=5)
        style.map('Treeview', background=[('selected', '#286383')])
        style.configure('TNotebook', background='#172434', borderwidth=0)
        style.configure('TNotebook.Tab', background='#24374c', foreground='#dce8f6', padding=(12, 7))
        style.map('TNotebook.Tab', background=[('selected', '#315f79')], foreground=[('selected', '#ffffff')])
        style.map('TCombobox', fieldbackground=[('readonly', '#101a27')], foreground=[('readonly', '#dce8f6')])
        self._build()
        self.reload()
        self.after(100, self._pump)
        self.protocol('WM_DELETE_WINDOW', self._close)

    def _build(self):
        header = ttk.Frame(self, padding=15)
        header.pack(fill='x')
        ttk.Label(header, text='OPEN EDA TOOLS', font=('sans-serif', 19, 'bold')).pack(side='left')
        ttk.Label(header, text='  LOCAL / REAL TOOL OUTPUT / NO CLOUD UPLOAD', foreground='#78c9db').pack(side='left')
        ttk.Button(header, text='Open Project', command=self.choose).pack(side='right')
        self.project_label = ttk.Label(self, padding=(16, 2))
        self.project_label.pack(fill='x')
        self.info_label = ttk.Label(self, padding=(16, 5), foreground='#9fb8d3')
        self.info_label.pack(fill='x')
        toolbar = ttk.Frame(self, padding=(14, 8))
        toolbar.pack(fill='x')
        stages = [('sim', 'Simulation'), ('lint', 'Lint'), ('cdc', 'CDC Review'),
                  ('synth', 'Synthesis'), ('sta', 'STA'), ('apr', 'APR'), ('verify', 'DRC / LVS'), ('ttcheck', 'TT Check'), ('full', 'Full Flow')]
        self.run_buttons = []
        for index, (name, label) in enumerate(stages):
            b = ttk.Button(toolbar, text=label, command=lambda s=name: self.start(s))
            b.grid(row=index // 6, column=index % 6, padx=2, pady=2, sticky='ew')
            self.run_buttons.append(b)
        ttk.Button(toolbar, text='Stop', command=self.stop).grid(row=1, column=5, padx=2, sticky='ew')
        for column in range(6):
            toolbar.columnconfigure(column, weight=1)
        viewers = ttk.Frame(self, padding=(14, 0))
        viewers.pack(fill='x')
        for label, fn in [('VS Code ↗', self.editor), ('GTKWave ↗', lambda: self.viewer('wave')),
                          ('OpenROAD ↗', lambda: self.viewer('openroad')), ('KLayout ↗', lambda: self.viewer('layout')),
                          ('Reload Reports', self.reload), ('Tool Status', self.show_doctor), ('TT Export', self.export_tt)]:
            ttk.Button(viewers, text=label, command=fn).pack(side='left', padx=2)
        self.status = ttk.Label(self, text='READY', padding=(16, 10), foreground='#79d8b1')
        self.status.pack(fill='x')
        history = ttk.Frame(self, padding=(16, 0, 16, 8))
        history.pack(fill='x')
        ttk.Label(history, text='Run history  ').pack(side='left')
        self.run_choice = ttk.Combobox(history, state='readonly', width=60)
        self.run_choice.pack(side='left', fill='x', expand=True)
        self.run_choice.bind('<<ComboboxSelected>>', self.choose_run)
        pane = ttk.Panedwindow(self, orient='horizontal')
        pane.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        left = ttk.Frame(pane)
        pane.add(left, weight=1)
        ttk.Label(left, text='Sources & Artifacts', padding=6).pack(anchor='w')
        self.files = ttk.Treeview(left, show='tree', selectmode='browse')
        self.files.pack(fill='both', expand=True)
        self.files.bind('<Double-1>', self.open_file)
        self.notebook = ttk.Notebook(pane)
        pane.add(self.notebook, weight=4)
        self.console = self._text_tab('Console')
        self.metrics = self._table_tab('PPA / Checks', ('metric', 'value'), (430, 250))
        self.paths = self._table_tab('Timing Paths', ('type', 'startpoint', 'endpoint', 'slack'), (75, 220, 220, 85))
        self.paths.bind('<<TreeviewSelect>>', self.path_selected)
        self.detail = self._text_tab('Report Detail')
        self._append(self.detail, 'Select a report or timing path. Double-click source files to edit in VS Code.\n'
                     'DRC / LVS runs the real physical flow including extraction; this is not Calibre sign-off.\n'
                     'CDC is a conservative structural review, not a commercial protocol/MTBF engine.')

    def _text_tab(self, title):
        frame = ttk.Frame(self.notebook)
        text = tk.Text(frame, wrap='none', background='#09131e', foreground='#d8e9f4', insertbackground='white',
                       font=('DejaVu Sans Mono', 10), relief='flat', state='disabled')
        y = ttk.Scrollbar(frame, command=text.yview)
        x = ttk.Scrollbar(frame, orient='horizontal', command=text.xview)
        text.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        y.pack(side='right', fill='y')
        x.pack(side='bottom', fill='x')
        text.pack(fill='both', expand=True)
        self.notebook.add(frame, text=title)
        return text

    def _table_tab(self, title, columns, widths):
        frame = ttk.Frame(self.notebook)
        tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col, width in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, minwidth=55)
        bar = ttk.Scrollbar(frame, command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        bar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
        self.notebook.add(frame, text=title)
        return tree

    def _append(self, text, value, replace=False):
        text.configure(state='normal')
        if replace:
            text.delete('1.0', 'end')
        text.insert('end', value)
        # Keep the UI bounded; full tool output remains in console.log on disk.
        if int(text.index('end-1c').split('.')[0]) > 5000:
            text.delete('1.0', '1000.0')
        text.see('end')
        text.configure(state='disabled')

    def emit(self, value):
        try:
            self.events.put_nowait(('line', ANSI.sub('', value)))
        except queue.Full:
            pass  # Drop only live preview, never the persisted log.

    def start(self, stage):
        if self.runner:
            return
        try:
            self.project = load_project(self.project['file'])
        except Exception as e:
            messagebox.showerror('Project', str(e))
            return
        self.runner = Runner(self.project, emit=self.emit)
        for b in self.run_buttons:
            b.configure(state='disabled')
        self.status.configure(text=f'RUNNING: {stage}  ·  inputs are snapshotted; editing will not alter this run')
        self.notebook.select(0)

        def work():
            try:
                result = self.runner.run(stage)
                message = f'COMPLETED — {result.name} (check warnings and reports)'
            except Exception as e:
                message = f'STOPPED / FAILED — {e}'
            self.events.put(('done', message))
        threading.Thread(target=work, daemon=True).start()

    def _pump(self):
        lines = []
        for _ in range(150):
            try:
                event, value = self.events.get_nowait()
            except queue.Empty:
                break
            if event == 'line':
                lines.append(value)
            else:
                self.runner = None
                for b in self.run_buttons:
                    b.configure(state='normal')
                self.status.configure(text=value)
                self.selected_run = None
                self.reload()
        if lines:
            self._append(self.console, '\n'.join(lines) + '\n')
        self.after(100, self._pump)

    def stop(self):
        if self.runner:
            self.runner.cancel()
            self.status.configure(text='Stopping tool process group…')

    def choose(self):
        if self.runner:
            messagebox.showinfo('Busy', 'Stop the current job before changing projects.')
            return
        path = filedialog.askopenfilename(filetypes=[('EDA project', '*.json')], initialdir=ROOT / 'examples')
        if path:
            try:
                self.project = load_project(path)
                self.selected_run = None
                self.reload()
            except Exception as e:
                messagebox.showerror('Project', str(e))

    def editor(self, path=None):
        code = shutil.which('code')
        if not code:
            messagebox.showinfo('VS Code', 'Install Windows VS Code + the WSL extension, then run code . inside WSL.\nSource directory: ' + self.project['base'])
            return
        subprocess.Popen([code, '--reuse-window', str(path or self.project['base'])], start_new_session=True)

    def viewer(self, kind):
        try:
            open_view(self.project, kind, self.selected_run)
            self.status.configure(text=f'Opening {kind}. If no window appears, inspect {kind}-viewer.log.')
        except Exception as e:
            messagebox.showerror('Viewer', str(e))

    def show_doctor(self):
        self._append(self.detail, json.dumps(doctor(), indent=2, ensure_ascii=False), replace=True)
        self.notebook.select(3)

    def export_tt(self):
        if self.runner:
            messagebox.showinfo('Busy', 'Finish the current job first.')
            return
        if self.project['top'] != 'tt_um_openeda_counter':
            messagebox.showinfo('Tiny Tapeout', 'Open examples/tiny_tapeout/project.json first. This exporter prepares the counter example; custom designs need their own wrapper, documentation and tests.')
            return
        folder = filedialog.askdirectory(title='Choose a parent directory for a NEW Tiny Tapeout handoff')
        if not folder:
            return
        destination = Path(folder) / ('tt-openeda-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
        # A subprocess keeps network cloning / preflight from blocking Tk.
        self.runner = Runner(self.project, emit=self.emit)
        for b in self.run_buttons:
            b.configure(state='disabled')
        self.status.configure(text='Exporting official template. No booking, payment or submission…')
        def work():
            try:
                self.runner.run('ttcheck')
                from .tapeout import export
                out = export(self.project, destination)
                msg = f'PREPARED: {out} — fill author; official checks and acceptance still required'
            except Exception as e:
                msg = f'Export failed: {e}'
            self.events.put(('done', msg))
        threading.Thread(target=work, daemon=True).start()

    def reload(self):
        p = self.project
        self.project_label.configure(text=p['file'])
        self.info_label.configure(text=f'TOP {p["top"]}  ·  CLOCK {p["clock"]} / {p["clock_period_ns"]} ns / {1000 / p["clock_period_ns"]:.2f} MHz  ·  {p.get("pdk", "sky130A")} / {p.get("scl", "sky130_fd_sc_hd")}')
        for tree in (self.files, self.metrics, self.paths):
            tree.delete(*tree.get_children())
        self.artifacts.clear()
        self.path_data.clear()
        sources = self.files.insert('', 'end', text='Sources — double-click to edit', open=True)
        for f in p['rtl'] + p['testbench'] + p.get('support_files', []) + [p['sdc'], 'project.json']:
            item = self.files.insert(sources, 'end', text=f)
            self.artifacts[item] = Path(p['base']) / f
        try:
            runs = sorted((Path(p['base']) / '.runs').glob('*/manifest.json'), reverse=True)
            self.run_choice.configure(values=[f.parent.name for f in runs])
            run = self.selected_run or latest_run(p)
            self.selected_run = run
            self.run_choice.set(run.name)
            data = json.loads((run / 'summary.json').read_text())
        except (RunError, OSError, ValueError):
            return
        files = self.files.insert('', 'end', text=f'Latest run — {run.name}', open=True)
        for f in ['manifest.json', 'console.log', 'summary.json', 'cdc.json', 'tt-preflight.json'] + data['artifacts'][:700]:
            if (run / f).is_file():
                item = self.files.insert(files, 'end', text=f)
                self.artifacts[item] = run / f
        for key, value in data['physical_checks'].items():
            self.metrics.insert('', 'end', values=(key, value))
        for key, value in sorted(data['metrics'].items()):
            self.metrics.insert('', 'end', values=(key, value))
        for path in data['paths']:
            item = self.paths.insert('', 'end', values=(path['type'], path['startpoint'], path['endpoint'], path['slack']))
            self.path_data[item] = path

    def choose_run(self, _event=None):
        tag = self.run_choice.get()
        run = (Path(self.project['base']) / '.runs' / tag).resolve()
        if run.parent == (Path(self.project['base']) / '.runs').resolve() and run.is_dir():
            self.selected_run = run
            self.reload()

    def open_file(self, _event=None):
        selection = self.files.selection()
        if not selection:
            return
        path = self.artifacts.get(selection[0])
        if not path:
            return
        if path.suffix in ('.v', '.sv', '.sdc') and '.runs' not in path.parts:
            self.editor(path)
        elif path.suffix in ('.vcd', '.fst'):
            self.viewer('wave')
        elif path.suffix == '.gds':
            self.viewer('layout')
        elif path.suffix == '.odb':
            self.viewer('openroad')
        elif path.stat().st_size <= 2_000_000 and path.suffix not in ('.png', '.gds', '.odb'):
            self._append(self.detail, str(path) + '\n\n' + path.read_text(errors='replace'), replace=True)
            self.notebook.select(3)
        else:
            self.editor(path)

    def path_selected(self, _event=None):
        selected = self.paths.selection()
        if selected and selected[0] in self.path_data:
            p = self.path_data[selected[0]]
            self._append(self.detail, p['report'] + '\n\n' + p['detail'], replace=True)
            # Keep the timing table selected; Detail is a separate readable tab.

    def _close(self):
        if self.runner:
            if messagebox.askyesno('Running', 'Stop the running EDA job and close after it exits?'):
                self.stop()
                self.after(300, self._wait_close)
            return
        self.destroy()

    def _wait_close(self):
        if self.runner:
            self.after(200, self._wait_close)
        else:
            self.destroy()
