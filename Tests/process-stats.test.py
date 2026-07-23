#!/usr/bin/env python3

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "Bin" / "process-stats.py"


class ProcessStatsTest(unittest.TestCase):
    def test_reports_live_proc_snapshot(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=True,
            capture_output=True,
            text=True,
        )
        snapshot = json.loads(result.stdout)

        self.assertGreater(snapshot["sampleTime"], 0)
        self.assertGreater(len(snapshot["processes"]), 0)

        script_process = next(
            process
            for process in snapshot["processes"]
            if "process-stats.py" in process["command"]
        )
        self.assertGreater(script_process["pid"], 0)
        self.assertGreaterEqual(script_process["cpuTime"], 0)
        self.assertGreater(script_process["startTime"], 0)
        self.assertGreater(script_process["memoryKB"], 0)
        self.assertGreater(script_process["memoryPercent"], 0)


if __name__ == "__main__":
    unittest.main()
