#!/usr/bin/env python3
"""Independently verify hashes and public GLB structure for generated packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
from pathlib import Path


MINIMUMS = {"nodes": 200, "mesh_nodes": 180, "triangles": 10_000, "renders": 5}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(base: Path, declared: str) -> Path:
    return (base / declared).resolve()


def verify_file(errors, base: Path, label: str, record: dict):
    if not isinstance(record, dict) or not record.get("path"):
        errors.append(f"{label}: missing file record")
        return None
    path = resolve(base, record["path"])
    try:
        size = path.stat().st_size
        digest = sha256(path)
    except OSError as error:
        errors.append(f"{label}: unavailable ({error})")
        return None
    if size != record.get("bytes"):
        errors.append(f"{label}: byte mismatch")
    if digest != record.get("sha256"):
        errors.append(f"{label}: SHA-256 mismatch")
    return path


def read_glb(path: Path):
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("truncated GLB")
    magic, version, total = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or total != len(raw):
        raise ValueError("invalid GLB header")
    offset = 12
    document = None
    binary = None
    while offset < len(raw):
        length, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        chunk = raw[offset:offset + length]
        offset += length
        if kind == 0x4E4F534A:
            document = json.loads(chunk.decode("utf-8").rstrip(" \t\r\n\x00"))
        elif kind == 0x004E4942:
            binary = chunk
    if document is None or binary is None:
        raise ValueError("GLB lacks JSON or BIN chunk")
    return document


def inspect_glb(document: dict) -> dict:
    scenes = document.get("scenes", [])
    roots = scenes[document.get("scene", 0)].get("nodes", []) if scenes else []
    nodes = document.get("nodes", [])
    root = nodes[roots[0]] if len(roots) == 1 else {}
    accessors = document.get("accessors", [])
    triangles = 0
    mesh_nodes = 0
    nonidentity = []
    for index, node in enumerate(nodes):
        if "mesh" not in node:
            continue
        mesh_nodes += 1
        if any(abs(value - 1.0) > 1e-4 for value in node.get("scale", [1, 1, 1])):
            nonidentity.append(node.get("name", str(index)))
        for primitive in document["meshes"][node["mesh"]].get("primitives", []):
            if primitive.get("mode", 4) != 4:
                raise ValueError("non-triangle primitive")
            accessor_index = primitive.get("indices", primitive["attributes"]["POSITION"])
            count = accessors[accessor_index]["count"]
            if count % 3:
                raise ValueError("triangle count is not divisible by three")
            triangles += count // 3
    return {
        "nodes": len(nodes), "mesh_nodes": mesh_nodes, "triangles": triangles,
        "root_count": len(roots), "root_name": root.get("name"),
        "identity_root": not any(key in root for key in ("translation", "rotation", "scale", "matrix")),
        "cameras": len(document.get("cameras", [])),
        "lights": "KHR_lights_punctual" in document.get("extensionsUsed", []),
        "images": len(document.get("images", [])), "textures": len(document.get("textures", [])),
        "nonidentity_mesh_scales": nonidentity,
    }


def validate_package(base: Path) -> dict:
    errors = []
    receipt_path = base / "production" / "asset-receipt.json"
    validation_path = base / "production" / "validation.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"status": "FAIL", "errors": [f"production documents unavailable: {error}"]}
    machine_id = receipt.get("machine_id")
    if not machine_id or validation.get("machine_id") != machine_id:
        errors.append("machine identity drift")
    if receipt.get("candidate_class") != "technical_structural_study":
        errors.append("candidate class is not technical_structural_study")
    if receipt.get("release_status") != "PENDING" or receipt.get("higher_stage_gates") != "PENDING":
        errors.append("release gates are not PENDING")
    verify_file(errors, base, "builder", receipt.get("builder", {}))
    verify_file(errors, base, "shared-generator", receipt.get("shared_generator", {}))
    verify_file(errors, base, "design", receipt.get("design", {}))
    verify_file(errors, base, "blend", receipt.get("artifacts", {}).get("blend", {}))
    glb_path = verify_file(errors, base, "glb", receipt.get("artifacts", {}).get("glb", {}))
    verify_file(errors, base, "validation", receipt.get("artifacts", {}).get("validation", {}))
    renders = receipt.get("renders", [])
    if len(renders) < MINIMUMS["renders"]:
        errors.append("too few review renders")
    for index, record in enumerate(renders):
        verify_file(errors, base, f"render-{index + 1}", record)
    contract = None
    if glb_path:
        try:
            contract = inspect_glb(read_glb(glb_path))
            if contract["nodes"] < MINIMUMS["nodes"]:
                errors.append("GLB node floor missed")
            if contract["mesh_nodes"] < MINIMUMS["mesh_nodes"]:
                errors.append("GLB mesh-node floor missed")
            if contract["triangles"] < MINIMUMS["triangles"]:
                errors.append("GLB triangle floor missed")
            if contract["root_count"] != 1 or contract["root_name"] != "Machine_Root" or not contract["identity_root"]:
                errors.append("GLB identity-root contract failed")
            if contract["cameras"] or contract["lights"] or contract["images"] or contract["textures"]:
                errors.append("GLB contains camera, light, image, or texture payload")
            if contract["nonidentity_mesh_scales"]:
                errors.append("GLB contains nonidentity mesh scales")
            if receipt.get("scene", {}).get("triangles") != contract["triangles"]:
                errors.append("receipt triangle metric does not match GLB")
        except (OSError, ValueError, KeyError, IndexError, struct.error) as error:
            errors.append(f"GLB inspection failed: {error}")
    gates = validation.get("gates", [])
    if validation.get("verdict") != "PASS" or any(gate.get("status") == "FAIL" for gate in gates):
        errors.append("technical-study validation is not PASS")
    if not any(gate.get("status") == "PENDING" for gate in gates):
        errors.append("higher-stage PENDING gates are absent")
    return {"status": "FAIL" if errors else "PASS", "machine_id": machine_id, "errors": errors, "glb_contract": contract}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packages", nargs="+", help="Generated machine package directories")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = [validate_package(Path(value).resolve()) for value in args.packages]
    failed = [result for result in results if result["status"] != "PASS"]
    if args.json:
        print(json.dumps({"status": "FAIL" if failed else "PASS", "results": results}, indent=2))
    else:
        for package, result in zip(args.packages, results):
            print(f"{result['status']} {package}: {result.get('machine_id') or '; '.join(result['errors'])}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
