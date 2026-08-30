#!/usr/bin/env python3
"""Machine-owned deterministic builder for the Komatsu PC210LC-11 study.

The shared fleet generator supplies the frozen excavator carrier. This local
subclass adds a reconstructed, visibly closed arm-crowd and bucket-curl
actuation study before the shared envelope calibration, render, GLB, receipt,
and validation pipeline runs. No manufacturer CAD or hidden geometry is used.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()


def load_shared_generator():
    spec = importlib.util.spec_from_file_location("exo_frozen_fleet_builder", SHARED_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load shared fleet generator: {SHARED_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = load_shared_generator()


class KomatsuPC210LC11Builder(shared.FleetBuilder):
    """Add a plausible static excavator actuation chain to the fleet carrier."""

    REQUIRED_ACTUATION_PARENTS = {
        "Boom_Cylinder": "Upper_ROOT",
        "Arm_Crowd_Actuator_ROOT": "Boom_ROOT",
        "Arm_Crowd_Cylinder_Barrel": "Arm_Crowd_Actuator_ROOT",
        "Arm_Crowd_Cylinder_Rod": "Arm_Crowd_Actuator_ROOT",
        "Arm_Crowd_Cylinder_Base_Pin": "Arm_Crowd_Actuator_ROOT",
        "Arm_Crowd_Cylinder_Rod_End_Pin": "Arm_Crowd_Actuator_ROOT",
        "Arm_Crowd_Boom_Base_Clevis": "Arm_Crowd_Actuator_ROOT",
        "Bucket_Curl_Actuator_ROOT": "Stick_ROOT",
        "Bucket_Curl_Cylinder_Barrel": "Bucket_Curl_Actuator_ROOT",
        "Bucket_Curl_Cylinder_Rod": "Bucket_Curl_Actuator_ROOT",
        "Bucket_Curl_Cylinder_Base_Pin": "Bucket_Curl_Actuator_ROOT",
        "Bucket_Curl_Cylinder_Rod_End_Pin": "Bucket_Curl_Actuator_ROOT",
        "Bucket_H_Link_ROOT": "Stick_ROOT",
        "Bucket_H_Link_L": "Bucket_H_Link_ROOT",
        "Bucket_H_Link_R": "Bucket_H_Link_ROOT",
        "Bucket_H_Link_Upper_Cross_Pin": "Bucket_H_Link_ROOT",
        "Bucket_H_Link_Lower_Cross_Pin": "Bucket_H_Link_ROOT",
        "Bucket_Dogbone_ROOT": "Stick_ROOT",
        "Bucket_Dogbone_L": "Bucket_Dogbone_ROOT",
        "Bucket_Dogbone_R": "Bucket_Dogbone_ROOT",
        "Bucket_Dogbone_End_Pin": "Bucket_Dogbone_ROOT",
        "Bucket_Linkage_Ear_L": "Bucket_ROOT",
        "Bucket_Linkage_Ear_R": "Bucket_ROOT",
    }

    def required_semantics(self):
        """Promote reconstructed actuator roots into the core build contract."""
        return [
            *super().required_semantics(),
            "Arm_Crowd_Actuator_ROOT",
            "Bucket_Curl_Actuator_ROOT",
            "Bucket_H_Link_ROOT",
            "Bucket_Dogbone_ROOT",
        ]

    def write_machine_wrapper(self):
        """Preserve this audited subclass instead of emitting the generic wrapper."""

    def add_hydraulic_assembly(self, prefix, start, end, barrel_radius, parent):
        """Create one overlapping barrel/rod pair with connected clevis pins.

        All coordinates are reconstructed in the selected parent's local space.
        The small overlap prevents a detached-rod read in the neutral study pose.
        """
        start_v = shared.Vector(start)
        end_v = shared.Vector(end)
        axis = end_v - start_v
        if axis.length <= 1e-8:
            raise RuntimeError(f"zero-length hydraulic assembly requested for {prefix}")
        direction = axis.normalized()
        join = start_v + axis * 0.57
        overlap = max(barrel_radius * 0.55, 0.035)
        barrel_end = join + direction * overlap
        rod_start = join - direction * overlap

        barrel = self.pipe_between(
            f"{prefix}_Barrel",
            start_v,
            barrel_end,
            barrel_radius,
            self.materials["graphite"],
            parent,
            role="hydraulic_barrel",
        )
        rod = self.pipe_between(
            f"{prefix}_Rod",
            rod_start,
            end_v,
            barrel_radius * 0.48,
            self.materials["rod"],
            parent,
            role="hydraulic_rod",
        )
        common_length = overlap * 2.0
        barrel["exo_barrel_rod_overlap_local_m"] = common_length
        rod["exo_barrel_rod_overlap_local_m"] = common_length
        pin_depth = self.width * 0.19
        for label, point in (("Base", start_v), ("Rod_End", end_v)):
            self.cylinder(
                f"{prefix}_{label}_Pin",
                point,
                barrel_radius * 0.78,
                pin_depth,
                self.materials["steel"],
                parent,
                vertices=20,
                role="hydraulic_pin",
            )

    def build_excavator(self):
        super().build_excavator()

        length, width, height = self.length, self.width, self.height
        boom = shared.bpy.data.objects["Boom_ROOT"]
        stick = shared.bpy.data.objects["Stick_ROOT"]
        bucket = shared.bpy.data.objects["Bucket_ROOT"]

        # The arm-crowd cylinder is mounted to the boom hierarchy, so the full
        # assembly follows upper-structure swing and boom motion as one closed
        # reconstructed neutral-pose unit.
        arm_actuator = self.empty(
            "Arm_Crowd_Actuator_ROOT", parent=boom, role="hydraulic_motion_root"
        )
        self.add_hydraulic_assembly(
            "Arm_Crowd_Cylinder",
            (length * 0.065, height * 0.205, 0.0),
            (length * 0.375, height * 0.395, 0.0),
            height * 0.030,
            arm_actuator,
        )
        self.box(
            "Arm_Crowd_Boom_Base_Clevis",
            (length * 0.065, height * 0.205, 0.0),
            (length * 0.055, height * 0.095, width * 0.22),
            self.materials["steel"],
            arm_actuator,
            role="hydraulic_clevis",
        )

        # Bucket cylinder and H-link are mounted under Stick_ROOT, preserving
        # Upper -> Boom -> Stick inheritance. The linkage is a static visual
        # closure, not a solved four-bar or a claim about manufacturer anchors.
        bucket_actuator = self.empty(
            "Bucket_Curl_Actuator_ROOT", parent=stick, role="hydraulic_motion_root"
        )
        cylinder_base = shared.Vector((length * 0.030, height * 0.115, 0.0))
        cylinder_rod = shared.Vector((length * 0.184, -height * 0.132, 0.0))
        self.add_hydraulic_assembly(
            "Bucket_Curl_Cylinder",
            cylinder_base,
            cylinder_rod,
            height * 0.026,
            bucket_actuator,
        )

        h_link = self.empty(
            "Bucket_H_Link_ROOT", parent=stick, role="bucket_linkage_root"
        )
        h_upper = shared.Vector((length * 0.184, -height * 0.132, 0.0))
        h_lower = shared.Vector((length * 0.213, -height * 0.226, 0.0))
        link_offset = width * 0.075
        for side, z in (("L", -link_offset), ("R", link_offset)):
            self.pipe_between(
                f"Bucket_H_Link_{side}",
                (h_upper.x, h_upper.y, z),
                (h_lower.x, h_lower.y, z),
                height * 0.018,
                self.materials["steel"],
                h_link,
                role="bucket_h_link",
            )
        for label, point in (("Upper", h_upper), ("Lower", h_lower)):
            self.cylinder(
                f"Bucket_H_Link_{label}_Cross_Pin",
                point,
                height * 0.022,
                link_offset * 2.45,
                self.materials["graphite"],
                h_link,
                vertices=20,
                role="bucket_linkage_pin",
            )

        dogbone = self.empty(
            "Bucket_Dogbone_ROOT", parent=stick, role="bucket_linkage_root"
        )
        dogbone_end = shared.Vector((length * 0.237, -height * 0.276, 0.0))
        for side, z in (("L", -link_offset), ("R", link_offset)):
            self.pipe_between(
                f"Bucket_Dogbone_{side}",
                (h_lower.x, h_lower.y, z),
                (dogbone_end.x, dogbone_end.y, z),
                height * 0.017,
                self.materials["rod"],
                dogbone,
                role="bucket_dogbone",
            )
        self.cylinder(
            "Bucket_Dogbone_End_Pin",
            dogbone_end,
            height * 0.022,
            link_offset * 2.45,
            self.materials["graphite"],
            dogbone,
            vertices=20,
            role="bucket_linkage_pin",
        )

        # Bucket ears belong to Bucket_ROOT, so they inherit bucket curl while
        # meeting the reconstructed dogbone pin in the neutral study pose.
        bucket_pivot_x = length * 0.23
        bucket_pivot_y = -height * 0.30
        ear_local = (
            dogbone_end.x - bucket_pivot_x,
            dogbone_end.y - bucket_pivot_y,
        )
        for side, z in (("L", -link_offset), ("R", link_offset)):
            self.side_profile(
                f"Bucket_Linkage_Ear_{side}",
                [
                    (-length * 0.006, -height * 0.010),
                    (ear_local[0] + length * 0.008, ear_local[1] - height * 0.012),
                    (ear_local[0] + length * 0.012, ear_local[1] + height * 0.018),
                    (length * 0.004, height * 0.020),
                ],
                height * 0.020,
                self.materials["steel"],
                bucket,
                z_center=z,
                role="bucket_linkage_ear",
            )

    def create_validation(self, contract, render_paths, scale_audit):
        """Extend the frozen validation with this machine's blocker gate."""
        validation = super().create_validation(contract, render_paths, scale_audit)
        actual_parents = {}
        hierarchy_ok = True
        for name, expected_parent in self.REQUIRED_ACTUATION_PARENTS.items():
            obj = shared.bpy.data.objects.get(name)
            actual_parent = obj.parent.name if obj is not None and obj.parent is not None else None
            actual_parents[name] = actual_parent
            hierarchy_ok = hierarchy_ok and actual_parent == expected_parent

        overlap_records = {}
        overlap_ok = True
        for name in (
            "Arm_Crowd_Cylinder_Barrel",
            "Arm_Crowd_Cylinder_Rod",
            "Bucket_Curl_Cylinder_Barrel",
            "Bucket_Curl_Cylinder_Rod",
        ):
            obj = shared.bpy.data.objects.get(name)
            overlap = float(obj.get("exo_barrel_rod_overlap_local_m", 0.0)) if obj else 0.0
            overlap_records[name] = round(overlap, 6)
            overlap_ok = overlap_ok and overlap >= 0.07

        gate_pass = hierarchy_ok and overlap_ok
        gate = {
            "id": "komatsu-visible-actuation-chain",
            "status": "PASS" if gate_pass else "FAIL",
            "detail": {
                "scope": "reconstructed static visual closure only; not a solved linkage",
                "parent_hierarchy": actual_parents,
                "barrel_rod_overlap_local_m": overlap_records,
                "fixed_boom_cylinder_retained": actual_parents.get("Boom_Cylinder") == "Upper_ROOT",
            },
        }
        first_pending = next(
            (index for index, item in enumerate(validation["gates"]) if item["status"] == "PENDING"),
            len(validation["gates"]),
        )
        validation["gates"].insert(first_pending, gate)
        validation["failed_gate_ids"] = [
            item["id"] for item in validation["gates"] if item["status"] == "FAIL"
        ]
        validation["verdict"] = "PASS" if not validation["failed_gate_ids"] else "FAIL"
        return validation

    def create_receipt(self, contract, render_paths, validation):
        """Expose every repaired actuation component as receipt-required."""
        receipt = super().create_receipt(contract, render_paths, validation)
        for name in self.REQUIRED_ACTUATION_PARENTS:
            receipt["required_semantic_nodes"][name] = name in contract["node_names"]
        return receipt


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = shared.parse_args(argv)
    design_path = Path(args.design).resolve()
    try:
        design = shared.load_design(design_path)
    except shared.DesignContractError as error:
        raise SystemExit(f"fleet design rejected: {error}") from error
    KomatsuPC210LC11Builder(design, design_path, Path(args.output_dir)).run()


if __name__ == "__main__":
    main()
