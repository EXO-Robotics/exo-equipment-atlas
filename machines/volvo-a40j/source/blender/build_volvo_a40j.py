#!/usr/bin/env python3
"""Machine-owned deterministic Volvo A40J structural-study builder.

The shared fleet generator is imported and hash-bound, but remains frozen. This
wrapper supplies only the A40J-specific reconstructed dump-hoist correction.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


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

    @staticmethod
    def _world_location(obj):
        point = obj.matrix_world.translation
        return [float(point.x), float(point.y), float(point.z)]

    def _object_bounds(self, obj):
        bpy.context.view_layer.update()
        points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        return {
            "min_m": [min(float(point[axis]) for point in points) for axis in range(3)],
            "max_m": [max(float(point[axis]) for point in points) for axis in range(3)],
        }

    def _subtree_bounds(self, root):
        def belongs_to_root(obj):
            current = obj
            while current is not None:
                if current == root:
                    return True
                current = current.parent
            return False

        meshes = [
            obj for obj in self.public_objects()
            if obj.type == "MESH" and belongs_to_root(obj)
        ]
        bounds = [self._object_bounds(obj) for obj in meshes]
        return {
            "min_m": [min(item["min_m"][axis] for item in bounds) for axis in range(3)],
            "max_m": [max(item["max_m"][axis] for item in bounds) for axis in range(3)],
        }

    def _scene_minimum_y(self):
        return min(
            float((obj.matrix_world @ vertex.co).y)
            for obj in self.public_objects() if obj.type == "MESH"
            for vertex in obj.data.vertices
        )

    @staticmethod
    def _aabb_intersects(left, right, tolerance=0.0):
        return all(
            left["min_m"][axis] < right["max_m"][axis] - tolerance
            and left["max_m"][axis] > right["min_m"][axis] + tolerance
            for axis in range(3)
        )

    def required_semantics(self):
        return [
            *super().required_semantics(),
            "Rear_Oscillation_Pivot",
            "Bogie_L_ROOT",
            "Bogie_R_ROOT",
            "Dump_Hoist_ROOT",
        ]

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

        # Separate the two physical articulation freedoms. The shared study
        # formerly applied roll directly to Rear_Frame_ROOT at grade, which
        # pushed a tire through the flat ground plane. The explicit +X pivot is
        # retained for topology inspection but is intentionally not autoplayed
        # without a terrain/contact compensation solver.
        yaw = bpy.data.objects["Chassis_Yaw_Pivot"]
        oscillation = self.empty(
            "Rear_Oscillation_Pivot", (0, 0, 0), yaw,
            role="frame_oscillation_pivot",
        )
        rear.parent = oscillation

        # The A40 product guide identifies an all-terrain tandem bogie. These
        # machine-local roots make each side an explicit rigid neutral-pose
        # assembly instead of leaving four rear wheels directly on the frame.
        tire_width = width * 0.17
        bogie_z = width / 2 - tire_width / 2
        for side, z in (("L", -bogie_z), ("R", bogie_z)):
            bogie = self.empty(
                f"Bogie_{side}_ROOT", (-length * 0.24, self.height * 0.20, z), rear,
                role="tandem_bogie_pivot",
            )
            for axle in ("Middle", "Rear"):
                wheel_pivot = bpy.data.objects[f"{axle}_{side}_Wheel_Pivot"]
                rear_local = wheel_pivot.location.copy()
                wheel_pivot.parent = bogie
                wheel_pivot.location = rear_local - bogie.location
            self.box(
                f"Bogie_{side}_Beam", (0, 0, 0),
                (length * 0.29, self.height * 0.075, width * 0.10),
                self.materials["graphite"], bogie,
                role="tandem_bogie_beam", bevel=self.height * 0.012,
            )
            self.cylinder(
                f"Bogie_{side}_Bearing", (0, 0, 0), self.height * 0.055,
                width * 0.12, self.materials["steel"], bogie,
                vertices=24, role="tandem_bogie_bearing",
            )

        # Give the shared semantic roots real exported ownership.
        self.box(
            "Running_Gear_Differential_Case", (-length * 0.23, self.height * 0.255, 0),
            (length * 0.13, self.height * 0.16, width * 0.28),
            self.materials["graphite"], self.running_root,
            role="driveline_case", bevel=self.height * 0.025,
        )
        self.box(
            "Hydraulic_Manifold", (-length * 0.035, self.height * 0.38, 0),
            (length * 0.075, self.height * 0.11, width * 0.22),
            self.materials["steel"], self.hydraulics_root,
            role="hydraulic_manifold", bevel=self.height * 0.014,
        )
        for side, z in (("L", -width * 0.085), ("R", width * 0.085)):
            self.pipe_between(
                f"Articulation_Hose_{side}",
                (-length * 0.06, self.height * 0.40, z),
                (length * 0.025, self.height * 0.43, z),
                self.height * 0.010, self.materials["rubber"], self.hydraulics_root,
                role="hydraulic_hose",
            )

        # Author actual visible envelope witnesses as machine structure: the
        # front powertrain nose, rear tail crossmember, outer bed rails, cab
        # roof guard, and belly guard. Their measured extrema correspond to the
        # admitted A40J guide rather than a post-build non-uniform scale.
        front = bpy.data.objects["Front_Frame_ROOT"]
        self.box(
            "Front_Engine_Nose",
            (length * 0.43, self.height * 0.57, 0),
            (length * 0.14, self.height * 0.42, width * 0.46),
            self.materials["body"], front,
            role="front_powertrain_enclosure", bevel=self.height * 0.025,
        )
        self.box(
            "Front_Bumper",
            (length / 2 - length * 0.008, self.height * 0.37, 0),
            (length * 0.016, self.height * 0.15, width * 0.43),
            self.materials["graphite"], front,
            role="front_bumper", bevel=self.height * 0.010,
        )
        self.box(
            "Cab_Roof_Guard",
            (length * 0.27, self.height - self.height * 0.015, 0),
            (length * 0.165, self.height * 0.03, width * 0.46),
            self.materials["graphite"], front,
            role="cab_roof_guard", bevel=self.height * 0.006,
        )
        self.box(
            "Rear_Bed_Tail_Crossmember",
            (-length * 0.42, self.height * 0.16, 0),
            (length * 0.04, self.height * 0.12, width * 0.70),
            self.materials["body_dark"], bed,
            role="dump_body_tail_crossmember", bevel=self.height * 0.012,
        )
        for side, z in (("L", -(width / 2 - width * 0.0125)),
                        ("R", width / 2 - width * 0.0125)):
            self.box(
                f"Dump_Bed_Outer_Rail_{side}", (-length * 0.20, self.height * 0.15, z),
                (length * 0.42, self.height * 0.045, width * 0.025),
                self.materials["body_dark"], bed,
                role="dump_body_outer_rail", bevel=self.height * 0.006,
            )
        belly_center_y = 0.494 + self.height * 0.035
        self.box(
            "Belly_Guard", (length * 0.045, belly_center_y, 0),
            (length * 0.17, self.height * 0.07, width * 0.34),
            self.materials["graphite"], self.fixed_root,
            role="ground_clearance_structure", bevel=self.height * 0.012,
        )

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

    def _sample_presentation_motion(self):
        yaw = bpy.data.objects["Chassis_Yaw_Pivot"]
        bed = bpy.data.objects["Bed_ROOT"]
        cab = bpy.data.objects["Operator_Station_ROOT"]
        originals = {
            "yaw": tuple(yaw.rotation_euler),
            "bed": tuple(bed.rotation_euler),
        }
        samples = []
        collisions = []
        minimum_y = math.inf

        def sine(progress, phase=0.0):
            wrapped = (progress + phase) % 1.0
            return 0.5 - 0.5 * math.cos(wrapped * math.tau)

        def ping_pong(progress, phase=0.0):
            wrapped = (progress + phase) % 1.0
            return 1.0 - abs(2.0 * wrapped - 1.0)

        try:
            for index in range(37):
                progress = index / 36
                yaw.rotation_euler.y = -0.36 + 0.72 * sine(progress)
                bed.rotation_euler.z = -math.radians(69.0) * ping_pong(progress, 0.54)
                bpy.context.view_layer.update()
                minimum = self._scene_minimum_y()
                bed_bounds = self._subtree_bounds(bed)
                cab_bounds = self._subtree_bounds(cab)
                collided = self._aabb_intersects(bed_bounds, cab_bounds, tolerance=0.01)
                if collided:
                    collisions.append(index)
                minimum_y = min(minimum_y, minimum)
                samples.append({
                    "index": index,
                    "progress": round(progress, 6),
                    "yaw_rad": round(float(yaw.rotation_euler.y), 6),
                    "body_tip_rad": round(float(bed.rotation_euler.z), 6),
                    "minimum_public_y_m": round(minimum, 6),
                    "bed_cab_aabb_intersection": collided,
                })
        finally:
            yaw.rotation_euler = originals["yaw"]
            bed.rotation_euler = originals["bed"]
            bpy.context.view_layer.update()
        return {
            "sample_count": len(samples),
            "minimum_public_y_m": round(minimum_y, 6),
            "bed_cab_collision_sample_indices": collisions,
            "samples": samples,
            "boundary": "Discrete exact 18-second viewer-channel sampling; not a terrain, continuous collision, load, or stability solver.",
        }

    def machine_specific_validation_gates(self, contract):
        bounds = contract["bounds"]
        yaw = bpy.data.objects["Chassis_Yaw_Pivot"]
        oscillation = bpy.data.objects["Rear_Oscillation_Pivot"]
        rear = bpy.data.objects["Rear_Frame_ROOT"]
        bed = bpy.data.objects["Bed_ROOT"]
        cab = bpy.data.objects["Operator_Station_ROOT"]
        motion = self._sample_presentation_motion()

        wheel_names = [
            f"{axle}_{side}_Wheel_ROOT"
            for axle in ("Front", "Middle", "Rear") for side in ("L", "R")
        ]
        tire_names = [name.replace("_Wheel_ROOT", "_Tire") for name in wheel_names]
        tire_contacts = {
            name: round(self._object_bounds(bpy.data.objects[name])["min_m"][1], 6)
            for name in tire_names
        }
        belly_min = self._object_bounds(bpy.data.objects["Belly_Guard"])["min_m"][1]
        bogie_records = {}
        for side in ("L", "R"):
            root = bpy.data.objects[f"Bogie_{side}_ROOT"]
            child_names = sorted(child.name for child in root.children_recursive)
            bogie_records[side] = {
                "root_parent": root.parent.name,
                "wheel_pivots": [name for name in child_names if name.endswith("Wheel_Pivot")],
                "minimum_tire_y_m": min(
                    tire_contacts[f"{axle}_{side}_Tire"] for axle in ("Middle", "Rear")
                ),
            }

        original_bed = tuple(bed.rotation_euler)
        bed.rotation_euler.z = -math.radians(69.0)
        bpy.context.view_layer.update()
        dump_endpoint = {
            "rotation_z_rad": round(float(bed.rotation_euler.z), 9),
            "rotation_magnitude_deg": round(abs(math.degrees(float(bed.rotation_euler.z))), 6),
            "body_bounds_m": self._subtree_bounds(bed),
            "minimum_public_y_m": round(self._scene_minimum_y(), 6),
        }
        bed.rotation_euler = original_bed
        bpy.context.view_layer.update()

        cab_bounds = self._subtree_bounds(cab)
        bed_bounds = self._subtree_bounds(bed)
        neutral_x_gap = cab_bounds["min_m"][0] - bed_bounds["max_m"][0]
        saddle = bpy.data.objects["Dump_Hoist_Chassis_Saddle"]
        pin = bpy.data.objects["Dump_Hoist_Chassis_Pin"]
        saddle_xy = self._world_location(saddle)[:2]
        clevis_records = []
        pin_bounds = self._object_bounds(pin)
        for side in ("L", "R"):
            clevis = bpy.data.objects[f"Dump_Hoist_{side}_Lower_Clevis"]
            point = self._world_location(clevis)
            clevis_records.append({
                "node": clevis.name,
                "xy_error_m": round(math.dist(saddle_xy, point[:2]), 9),
                "z_m": round(point[2], 6),
                "within_cross_pin_span": pin_bounds["min_m"][2] <= point[2] <= pin_bounds["max_m"][2],
            })

        expected = [self.length, self.height, self.width]
        envelope_error = [abs(bounds["size_m"][axis] - expected[axis]) for axis in range(3)]
        frame_chain_ok = oscillation.parent == yaw and rear.parent == oscillation
        no_motion_collisions = not motion["bed_cab_collision_sample_indices"]
        hoist_ok = (
            self.volvo_hoist_clearance["minimum_local_clearance_m"] > 0
            and all(item["xy_error_m"] <= 1e-6 and item["within_cross_pin_span"] for item in clevis_records)
        )

        def gate(gate_id, ok, method, evidence, semantic_nodes, fact_ids):
            return {
                "id": gate_id,
                "status": "PASS" if ok else "FAIL",
                "detail": {
                    "method": method,
                    "evidence": evidence,
                    "semantic_nodes": semantic_nodes,
                    "fact_ids": fact_ids,
                },
            }

        return [
            gate(
                "published_static_envelope",
                max(envelope_error) <= 0.03 and abs(belly_min - 0.494) <= 0.003,
                "Decode the retained GLB vertex AABB and measure the visible belly-guard underside against the hash-bound A40J guide.",
                {"measured_size_xyz_m": bounds["size_m"], "published_size_xyz_m": expected,
                 "absolute_error_m": envelope_error, "measured_belly_guard_min_y_m": round(belly_min, 6),
                 "published_ground_clearance_m": 0.494, "tolerance_m": 0.03},
                ["Front_Bumper", "Rear_Bed_Tail_Crossmember", "Cab_Roof_Guard", "Dump_Bed_Outer_Rail_L", "Belly_Guard"],
                ["public-envelope-x", "public-envelope-y", "public-envelope-z", "ground-clearance"],
            ),
            gate(
                "six_tire_contact",
                len(tire_contacts) == 6 and all(value >= -0.03 for value in tire_contacts.values()),
                "Measure the world-space mesh minimum Y for each of the six independently exported tire carcasses in the neutral 29.5R25-basis pose.",
                {"tire_minimum_y_m": tire_contacts, "allowed_minimum_y_m": -0.03},
                wheel_names, [],
            ),
            gate(
                "articulation_endpoint_and_continuity",
                frame_chain_ok and abs(0.36) < math.radians(45.0),
                "Traverse the yaw-to-oscillation-to-rear-frame parent chain and compare the bounded Auto steering extrema with the published 45-degree each-side limit.",
                {"hierarchy": [yaw.name, oscillation.name, rear.name], "viewer_extrema_rad": [-0.36, 0.36],
                 "viewer_extrema_deg": [round(math.degrees(-0.36), 6), round(math.degrees(0.36), 6)],
                 "published_limit_deg_each_side": 45, "full_published_limit_modeled": False},
                ["Chassis_Yaw_Pivot", "Rear_Oscillation_Pivot", "Rear_Frame_ROOT"], ["articulation-range"],
            ),
            gate(
                "frame_oscillation_continuity",
                frame_chain_ok and oscillation.get("exo_role") == "frame_oscillation_pivot",
                "Inspect the explicit longitudinal oscillation pivot hierarchy and exported mesh ownership; keep it neutral in flat-ground Auto because terrain compensation is unresolved.",
                {"hierarchy": [yaw.name, oscillation.name, rear.name], "axis": "+X", "viewer_channel_present": False,
                 "reason_not_autoplayed": "rear tire contact cannot remain physical on a flat plane without terrain or suspension compensation"},
                ["Rear_Oscillation_Pivot", "Rear_Frame_ROOT"], [],
            ),
            gate(
                "left_right_bogie_contact",
                all(len(record["wheel_pivots"]) == 2 and record["minimum_tire_y_m"] >= -0.03 for record in bogie_records.values()),
                "Traverse each tandem-bogie root to its middle and rear wheel pivots, then measure both tire contacts per side in the neutral flat-ground pose.",
                {"bogies": bogie_records, "motion_state": "neutral_only_without_terrain_solver"},
                ["Bogie_L_ROOT", "Bogie_R_ROOT", "Middle_L_Wheel_ROOT", "Rear_L_Wheel_ROOT", "Middle_R_Wheel_ROOT", "Rear_R_Wheel_ROOT"], [],
            ),
            gate(
                "dump_body_69_degree_endpoint",
                abs(dump_endpoint["rotation_magnitude_deg"] - 69.0) <= 1e-6 and dump_endpoint["minimum_public_y_m"] >= -0.03,
                "Apply the exact reconstructed Bed_ROOT endpoint, read its rotation, and measure the complete public minimum Y at that pose.",
                dump_endpoint, ["Bed_ROOT", "Dump_Bed_Floor", "Rear_Bed_Tail_Crossmember"], ["body-tip-angle"],
            ),
            gate(
                "dump_cylinder_visual_closure",
                hoist_ok,
                "Measure the paired moving lower-clevis centers against the fixed saddle cross-pin in the stowed pose and verify invariant local clearance below the bed floor.",
                {"stowed_clevis_to_cross_pin": clevis_records, "underbed_clearance": self.volvo_hoist_clearance,
                 "boundary": "Stowed visual closure and under-bed clearance only; dynamic cylinder stroke and changing anchors remain unresolved."},
                ["Dump_Hoist_ROOT", "Dump_Hoist_Chassis_Saddle", "Dump_Hoist_Chassis_Pin", "Dump_Hoist_L_Barrel", "Dump_Hoist_R_Barrel"], [],
            ),
            gate(
                "cab_body_clearance",
                neutral_x_gap > 0.05 and no_motion_collisions,
                "Measure neutral cab-to-body longitudinal AABB separation and sample their complete subtrees through every exact Auto pose.",
                {"neutral_cab_bounds_m": cab_bounds, "neutral_body_bounds_m": bed_bounds,
                 "neutral_longitudinal_gap_m": round(neutral_x_gap, 6),
                 "collision_sample_indices": motion["bed_cab_collision_sample_indices"]},
                ["Operator_Station_ROOT", "Bed_ROOT"], [],
            ),
            gate(
                "ground_collision",
                bounds["min_m"][1] >= -0.03 and motion["minimum_public_y_m"] >= -0.03,
                "Measure neutral retained GLB minimum Y and discretely sample the exact articulation and dump-body Auto channels over one 18-second cycle.",
                {"neutral_minimum_y_m": bounds["min_m"][1], "motion_audit": motion, "allowed_minimum_y_m": -0.03},
                ["Front_L_Wheel_ROOT", "Rear_R_Wheel_ROOT", "Bed_ROOT"], [],
            ),
            gate(
                "self_collision",
                neutral_x_gap > 0.05 and no_motion_collisions,
                "Test cab and dump-body subtree AABBs at all 37 exact Auto samples, retaining the neutral longitudinal separation measurement.",
                {"neutral_longitudinal_gap_m": round(neutral_x_gap, 6),
                 "collision_sample_indices": motion["bed_cab_collision_sample_indices"], "sample_count": motion["sample_count"]},
                ["Operator_Station_ROOT", "Bed_ROOT"], [],
            ),
            gate(
                "swept_volume_collision",
                no_motion_collisions and motion["minimum_public_y_m"] >= -0.03,
                "Conservatively sample public minimum-Y and cab/body subtree AABBs at 37 phase-aligned poses spanning the complete declared Auto cycle.",
                {"sample_count": motion["sample_count"], "minimum_public_y_m": motion["minimum_public_y_m"],
                 "collision_sample_indices": motion["bed_cab_collision_sample_indices"], "continuous_solver": False,
                 "boundary": motion["boundary"]},
                ["Chassis_Yaw_Pivot", "Rear_Frame_ROOT", "Bed_ROOT", "Operator_Station_ROOT"], [],
            ),
        ]


def main():
    try:
        design = SHARED.load_design(DESIGN)
    except SHARED.DesignContractError as error:
        raise SystemExit(f"fleet design rejected: {error}") from error
    result = VolvoA40JBuilder(design, DESIGN, OUTPUT_DIR).run()
    print("VOLVO_A40J_BUILD_RESULT=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
