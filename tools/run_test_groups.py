"""Run every group of the tests in a process of its own.

A group run after others may pass only because of what they left (a QApplication, a setting, a module imported).
Here each folder of tests/ (and each file at its top) runs alone; the summary says which group failed alone.
The same as «tools/test.py isolated» — its runner (tools/testkit.py): a report
of each group, nothing collected is a failure, a crash shows the end of its log, Ctrl+C stops only the child.

Usage: python tools/run_test_groups.py [pytest options] e.g. .venv/bin/python tools/run_test_groups.py -x
Exit code: 0 when every group passed, 1 otherwise.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test as runner  # noqa: E402 — tools/test.py (this folder first in the path, not the test package of Python)

if __name__ == '__main__':
    sys.exit(runner.main(['isolated', '--', *sys.argv[1:]]))
