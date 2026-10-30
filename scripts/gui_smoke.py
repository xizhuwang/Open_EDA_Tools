"""Use WSLg or xvfb-run -a bash eda ...; exercise widgets without a web browser."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edaworkbench.project import ROOT, load_project
from edaworkbench.gui import Workbench

window = Workbench(load_project(ROOT / 'examples/counter/project.json'))
window.update()
assert window.winfo_width() >= 960
window.show_doctor()
window.update()
window.notebook.select(2)
window.update()
window.reload()
window.update()
window.destroy()
print('PASS: native Tk workbench creates, renders tabs, reloads reports and closes')
