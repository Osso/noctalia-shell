#!/usr/bin/env python3

import json
import os
from pathlib import Path


PROC_ROOT = Path("/proc")
CLOCK_TICKS = os.sysconf("SC_CLK_TCK")
PAGE_SIZE_KB = os.sysconf("SC_PAGE_SIZE") / 1024


def read_memory_total_kb() -> int:
    for line in (PROC_ROOT / "meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            return int(line.split()[1])
    raise RuntimeError("MemTotal missing from /proc/meminfo")


def read_process(process_dir: Path, memory_total_kb: int) -> dict[str, int | float | str]:
    stat = (process_dir / "stat").read_text()
    command_end = stat.rfind(")")
    command_name = stat[stat.find("(") + 1 : command_end]
    fields = stat[command_end + 2 :].split()

    cpu_ticks = int(fields[11]) + int(fields[12])
    start_time = int(fields[19])
    resident_pages = int((process_dir / "statm").read_text().split()[1])
    memory_kb = resident_pages * PAGE_SIZE_KB

    command_bytes = (process_dir / "cmdline").read_bytes()
    command = command_bytes.replace(b"\0", b" ").decode(errors="replace").strip()
    if not command:
        command = f"[{command_name}]"

    return {
        "pid": int(process_dir.name),
        "cpuTime": cpu_ticks / CLOCK_TICKS,
        "startTime": start_time,
        "memoryPercent": memory_kb / memory_total_kb * 100,
        "memoryKB": memory_kb,
        "command": command,
    }


def collect_snapshot() -> dict[str, float | list[dict[str, int | float | str]]]:
    sample_time = float((PROC_ROOT / "uptime").read_text().split()[0])
    memory_total_kb = read_memory_total_kb()
    processes = []

    for process_dir in PROC_ROOT.iterdir():
        if not process_dir.name.isdigit():
            continue
        try:
            processes.append(read_process(process_dir, memory_total_kb))
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
            continue

    return {"sampleTime": sample_time, "processes": processes}


def main() -> None:
    print(json.dumps(collect_snapshot(), separators=(",", ":")))


if __name__ == "__main__":
    main()
