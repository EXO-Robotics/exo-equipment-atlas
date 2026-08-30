#!/usr/bin/env python3
"""Validate one or more fleet design JSON files without Blender."""

from __future__ import annotations

import argparse
import json

from design_contract import ARCHETYPES, DesignContractError, load_design


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("designs", nargs="+", help="Design JSON path(s) to validate")
    parser.add_argument("--json", action="store_true", help="Emit one JSON summary")
    args = parser.parse_args()
    results = []
    failed = False
    for design_path in args.designs:
        try:
            design = load_design(design_path)
            results.append({
                "path": design_path,
                "status": "PASS",
                "machine_id": design["machine_id"],
                "archetype": design["archetype"],
            })
        except DesignContractError as error:
            failed = True
            results.append({"path": design_path, "status": "FAIL", "error": str(error)})
    if args.json:
        print(json.dumps({"status": "FAIL" if failed else "PASS", "results": results}, indent=2))
    else:
        for result in results:
            suffix = result.get("machine_id") or result.get("error")
            print(f"{result['status']} {result['path']}: {suffix}")
        print(f"Supported archetypes: {', '.join(ARCHETYPES)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
