#!/usr/bin/env python3
"""Machine-owned deterministic Volvo A40J structural-study builder.

The shared fleet generator is imported and hash-bound, but remains frozen. This
wrapper supplies only the A40J-specific reconstructed dump-hoist correction.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import bpy


HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()


def load_shared_generator():
    """Import the frozen shared generator without invoking its CLI entrypoint."""

    module_name = "exo_fleet_shared_volvo_a40j"
    spec = importlib.util.spec_from_file_location(module_name, SHARED_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not import shared fleet generator: {SHARED_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


SHARED = load_shared_generator()


class VolvoA40JBuilder(SHARED.FleetBuilder):
    """Keep the generic 6x6 carrier and replace only its flawed dump hoist."""

    def write_machine_wrapper(self):
        # The base class normally regenerates a runpy shim. This machine-owned
        # subclass is the deterministic wrapper and must preserve itself.
        return None

    def build_articulated_hauler(self):
        super().build_articulated_hauler()

        # The generic cylinder's upper end intersects the bed-floor volume in
        # the stowed pose. Remove it before envelope normalization and replace
        # it with a bounded twin under-bed tipping-hoist study.
        generic = bpy.data.objects.get("Bed_Lift_Cylinder")
        if generic is not None:
            bpy.data.objects.remove(generic, do_unlink=True)

        length, width, height = self.length, self.width, self.height
        rear = bpy.data.objects["Rear_Frame_ROOT"]
        bed = bpy.data.objects["Bed_ROOT"]

        # The fixed saddle and moving clevis coincide at the stowed endpoint.
        # The moving assembly remains rigidly below the dump floor while the
        # bounded viewer rotates Bed_ROOT through the published 0..69 degree
        # presentation range. This is a visual reconstruction, not a solver.
        start = (-length * 0.008, -height * 0.060)
        middle = (-length * 0.125, -height * 0.066)
        finish = (-length * 0.220, -height * 0.055)
        side_offset = width * 0.145
        floor_underside_y = height * 0.010
        barrel_radius = height * 0.030
        rod_radius = height * 0.021
        knuckle_radius = height * 0.032

        saddle_world_x = -length * 0.060 + start[0]
        saddle_world_y = height * 0.430 + start[1]
        self.box(
            "Dump_Hoist_Chassis_Saddle",
            (saddle_world_x, saddle_world_y, 0),
            (length * 0.055, height * 0.070, width * 0.390),
            self.materials["graphite"], rear,
            role="dump_hoist_chassis_saddle", bevel=height * 0.008,
        )
        self.cylinder(
            "Dump_Hoist_Chassis_Pin",
            (saddle_world_x, saddle_world_y, 0),
            knuckle_radius, width * 0.355,
            self.materials["steel"], rear, vertices=24,
            role="dump_hoist_chassis_pin",
        )

        hoist = self.empty("Dump_Hoist_ROOT", parent=bed, role="motion_root")
        self.box(
            "Dump_Hoist_Underbed_Rail",
            (-length * 0.150, -height * 0.030, 0),
            (length * 0.310, height * 0.025, width * 0.410),
            self.materials["graphite"], hoist,
            role="dump_hoist_underbed_rail", bevel=height * 0.005,
        )

        for side, z in (("L", -side_offset), ("R", side_offset)):
            self.pipe_between(
                f"Dump_Hoist_{side}_Barrel",
                (start[0], start[1], z),
                (middle[0], middle[1], z),
                barrel_radius, self.materials["steel"], hoist,
                role="dump_hoist_barrel",
            )
            self.pipe_between(
                f"Dump_Hoist_{side}_Rod",
                (middle[0], middle[1], z),
                (finish[0], finish[1], z),
                rod_radius, self.materials["rod"], hoist,
                role="dump_hoist_rod",
            )
            self.cylinder(
                f"Dump_Hoist_{side}_Lower_Clevis",
                (start[0], start[1], z), knuckle_radius,
                width * 0.070, self.materials["graphite"], hoist,
                vertices=20, role="dump_hoist_lower_clevis",
            )
            self.cylinder(
                f"Dump_Hoist_{side}_Final_Knuckle",
                (finish[0], finish[1], z), knuckle_radius,
                width * 0.075, self.materials["graphite"], hoist,
                vertices=20, role="dump_hoist_final_knuckle",
            )

        highest_hoist_y = max(
            start[1] + max(barrel_radius, knuckle_radius),
            middle[1] + max(barrel_radius, rod_radius),
            finish[1] + max(rod_radius, knuckle_radius),
            -height * 0.030 + height * 0.0125,
        )
        clearance = floor_underside_y - highest_hoist_y
        self.volvo_hoist_clearance = {
            "classification": "reconstructed_underbed_hoist_clearance",
            "floor_underside_local_y_m": round(floor_underside_y, 6),
            "highest_hoist_local_y_m": round(highest_hoist_y, 6),
            "minimum_local_clearance_m": round(clearance, 6),
            "sampled_body_tip_deg": [0, 17.25, 34.5, 51.75, 69],
            "motion_invariance": "Hoist and bed floor share Bed_ROOT; local clearance is invariant over the bounded presentation rotation.",
            "authority": "reconstructed_visualization_not_kinematic_solver",
        }

    def create_validation(self, contract, render_paths, scale_audit):
        validation = super().create_validation(contract, render_paths, scale_audit)
        clearance = self.volvo_hoist_clearance["minimum_local_clearance_m"]
        validation["gates"].insert(
            17,
            {
                "id": "volvo-dump-hoist-underbed-clearance",
                "status": "PASS" if clearance > 0 else "FAIL",
                "detail": self.volvo_hoist_clearance,
            },
        )
        if clearance <= 0:
            validation["verdict"] = "FAIL"
            validation["failed_gate_ids"] = sorted(
                set(validation["failed_gate_ids"] + ["volvo-dump-hoist-underbed-clearance"])
            )
        return validation


def main():
    try:
        design = SHARED.load_design(DESIGN)
    except SHARED.DesignContractError as error:
        raise SystemExit(f"fleet design rejected: {error}") from error
    result = VolvoA40JBuilder(design, DESIGN, OUTPUT_DIR).run()
    print("VOLVO_A40J_BUILD_RESULT=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
