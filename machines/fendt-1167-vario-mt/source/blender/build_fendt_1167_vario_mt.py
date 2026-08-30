#!/usr/bin/env python3
"""Machine-owned deterministic entrypoint for fendt-1167-vario-mt.

The frozen shared generator remains the authoring implementation and is
hash-bound separately in asset-receipt.json. This wrapper applies one
machine-local reconstructed rest-pose continuity repair: the rear hitch and
drawbar pivots are raised to overlap the chassis and each other.
"""
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()

sys.path.insert(0, str(SHARED_GENERATOR.parent))
spec = importlib.util.spec_from_file_location("exo_fleet_shared_builder", SHARED_GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load frozen shared generator: {SHARED_GENERATOR}")
shared = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)

original_build = shared.FleetBuilder.build_twin_track_tractor
original_create_validation = shared.FleetBuilder.create_validation
REQUIRED_CONTINUITY_OVERLAP_M = 0.001


def build_with_attached_rear_interface(builder):
    """Preserve shared topology, then close two visible rest-pose gaps."""
    original_build(builder)
    values = builder.design.get("reconstructed_values", {})
    hitch_ratio = float(values["rear_hitch_pivot_height_ratio"])
    drawbar_ratio = float(values["drawbar_pivot_height_ratio"])
    shared.bpy.data.objects["Rear_Hitch_Pivot"].location.y = builder.height * hitch_ratio
    shared.bpy.data.objects["Drawbar_Pivot"].location.y = builder.height * drawbar_ratio


def mesh_world_bounds(name):
    """Return one public mesh's evaluated world AABB in metres."""
    obj = shared.bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"Required rear-interface mesh is absent: {name}")
    points = [obj.matrix_world @ shared.Vector(corner) for corner in obj.bound_box]
    minimum = [min(point[axis] for point in points) for axis in range(3)]
    maximum = [max(point[axis] for point in points) for axis in range(3)]
    return minimum, maximum


def continuity_pair(first_name, second_name):
    first_min, first_max = mesh_world_bounds(first_name)
    second_min, second_max = mesh_world_bounds(second_name)
    overlaps = [
        min(first_max[axis], second_max[axis])
        - max(first_min[axis], second_min[axis])
        for axis in range(3)
    ]
    minimum_overlap = min(overlaps)
    return {
        "objects": [first_name, second_name],
        "first_bounds_m": {
            "min_xyz": [round(value, 6) for value in first_min],
            "max_xyz": [round(value, 6) for value in first_max],
        },
        "second_bounds_m": {
            "min_xyz": [round(value, 6) for value in second_min],
            "max_xyz": [round(value, 6) for value in second_max],
        },
        "overlap_xyz_m": {
            axis: round(overlaps[index], 6)
            for index, axis in enumerate(("x", "y", "z"))
        },
        "minimum_overlap_m": round(minimum_overlap, 6),
        "passes_required_overlap": all(
            overlap >= REQUIRED_CONTINUITY_OVERLAP_M for overlap in overlaps
        ),
    }


def create_validation_with_rear_continuity(builder, contract, render_paths, scale_audit):
    """Add a fail-closed, reconstructed rest-pose continuity gate."""
    validation = original_create_validation(builder, contract, render_paths, scale_audit)
    try:
        chassis_to_hitch = continuity_pair("Rigid_Main_Frame", "Rear_Hitch_Links")
        hitch_to_drawbar = continuity_pair("Rear_Hitch_Links", "Drawbar")
        passes = (
            chassis_to_hitch["passes_required_overlap"]
            and hitch_to_drawbar["passes_required_overlap"]
        )
        detail = {
            "classification": "reconstructed_rest_pose_aabb_continuity_only",
            "authority": "Visualization continuity check only; not manufacturer-published pivot geometry, an operating limit, a load path, or engineering authority.",
            "required_minimum_overlap_m": REQUIRED_CONTINUITY_OVERLAP_M,
            "chassis_to_hitch": chassis_to_hitch,
            "hitch_to_drawbar": hitch_to_drawbar,
            "measured_minimum_overlap_m": min(
                chassis_to_hitch["minimum_overlap_m"],
                hitch_to_drawbar["minimum_overlap_m"],
            ),
        }
    except Exception as error:
        passes = False
        detail = {
            "classification": "reconstructed_rest_pose_aabb_continuity_only",
            "authority": "Visualization continuity check only; not manufacturer-published pivot geometry, an operating limit, a load path, or engineering authority.",
            "required_minimum_overlap_m": REQUIRED_CONTINUITY_OVERLAP_M,
            "error": str(error),
        }
    gate = {
        "id": "fendt-rear-interface-continuity",
        "status": "PASS" if passes else "FAIL",
        "detail": detail,
    }
    pending_index = next(
        (index for index, item in enumerate(validation["gates"]) if item["status"] == "PENDING"),
        len(validation["gates"]),
    )
    validation["gates"].insert(pending_index, gate)
    validation["failed_gate_ids"] = [
        item["id"] for item in validation["gates"] if item["status"] == "FAIL"
    ]
    validation["verdict"] = "PASS" if not validation["failed_gate_ids"] else "FAIL"
    return validation


shared.FleetBuilder.build_twin_track_tractor = build_with_attached_rear_interface
shared.FleetBuilder.create_validation = create_validation_with_rear_continuity
# Keep this audited machine-owned wrapper intact so the receipt hashes the
# actual deterministic entrypoint instead of regenerating the generic wrapper.
shared.FleetBuilder.write_machine_wrapper = lambda builder: None

sys.argv = [str(SHARED_GENERATOR), "--", "--design", str(DESIGN), "--output-dir", str(OUTPUT_DIR)]
shared.main()
