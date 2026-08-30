#!/usr/bin/env python3
"""Run deterministic Blender fleet builds from one or more design JSON files."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
from pathlib import Path

from design_contract import DesignContractError, load_design


SCRIPT_DIR = Path(__file__).resolve().parent
BUILDER = SCRIPT_DIR / "build_machine.py"
DEFAULT_BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")
RESULT_PREFIX = "FLEET_BUILD_RESULT="


def collect_design_paths(args) -> list[Path]:
    paths = [Path(value).resolve() for value in args.design]
    if args.design_dir:
        paths.extend(sorted(Path(args.design_dir).resolve().glob("*.json")))
    unique = []
    seen = set()
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    if not unique:
        raise DesignContractError("provide --design or --design-dir with at least one JSON design")
    return unique


def build_command(blender: Path, design_path: Path, output_dir: Path) -> list[str]:
    return [
        str(blender), "--factory-startup", "--background", "--python", str(BUILDER), "--",
        "--design", str(design_path), "--output-dir", str(output_dir),
    ]


def run_one(blender: Path, design_path: Path, design: dict, output_root: Path) -> dict:
    output_dir = output_root / design["machine_id"]
    command = build_command(blender, design_path, output_dir)
    process = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    marker = None
    for line in process.stdout.splitlines():
        if line.startswith(RESULT_PREFIX):
            marker = line[len(RESULT_PREFIX):]
    result = {
        "machine_id": design["machine_id"],
        "design": str(design_path),
        "output_dir": str(output_dir),
        "command": command,
        "returncode": process.returncode,
        "status": "FAIL",
    }
    if process.returncode == 0 and marker:
        try:
            build_result = json.loads(marker)
            if build_result.get("status") == "PASS":
                result["status"] = "PASS"
                result["build_result"] = build_result
        except json.JSONDecodeError as error:
            result["error"] = f"invalid result marker: {error}"
    if result["status"] != "PASS":
        result.setdefault("error", "Blender did not emit a PASS result marker")
        result["output_tail"] = "\n".join(process.stdout.splitlines()[-80:])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", action="append", default=[], help="Design JSON path; repeatable")
    parser.add_argument("--design-dir", help="Directory containing design JSON files")
    parser.add_argument("--output-root", required=True, help="Parent directory for generated machine packages")
    parser.add_argument("--blender", default=str(DEFAULT_BLENDER), help="Blender executable")
    parser.add_argument("--jobs", type=int, default=1, help="Concurrent Blender processes (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Validate designs and print commands only")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable summary")
    args = parser.parse_args()
    if args.jobs < 1 or args.jobs > 8:
        parser.error("--jobs must be between 1 and 8")
    try:
        design_paths = collect_design_paths(args)
        entries = [(path, load_design(path)) for path in design_paths]
    except DesignContractError as error:
        parser.error(str(error))
    output_root = Path(args.output_root).resolve()
    blender = Path(args.blender).resolve()
    if not args.dry_run and not blender.is_file():
        parser.error(f"Blender executable is unavailable: {blender}")
    plans = [
        {
            "machine_id": design["machine_id"],
            "design": str(path),
            "output_dir": str(output_root / design["machine_id"]),
            "command": build_command(blender, path, output_root / design["machine_id"]),
        }
        for path, design in entries
    ]
    if args.dry_run:
        summary = {"status": "PASS", "dry_run": True, "builds": plans}
    else:
        output_root.mkdir(parents=True, exist_ok=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.jobs, len(entries))) as executor:
            futures = [
                executor.submit(run_one, blender, path, design, output_root)
                for path, design in entries
            ]
            results = [future.result() for future in futures]
        failed = [result["machine_id"] for result in results if result["status"] != "PASS"]
        summary = {"status": "FAIL" if failed else "PASS", "failed": failed, "builds": results}
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for item in summary["builds"]:
            print(f"{item.get('status', 'PLAN')} {item['machine_id']}: {item['output_dir']}")
            if item.get("error"):
                print(item["error"], file=sys.stderr)
        print(f"{summary['status']} {len(summary['builds'])} fleet build(s)")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
