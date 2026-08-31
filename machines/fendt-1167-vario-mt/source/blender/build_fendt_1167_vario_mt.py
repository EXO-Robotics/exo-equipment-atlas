#!/usr/bin/env python3
"""Deterministic machine-local builder for the Fendt 1167 Vario MT study.

Published dimensions are used only where the package cites them. Hidden
structure, suspension pivots, linkage coordinates, and motion curves remain
reconstructed presentation geometry and are measured fail-closed below.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()
VIEWER = OUTPUT_DIR / "viewer.json"

spec = importlib.util.spec_from_file_location("exo_fleet_fendt_1167", SHARED_GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load frozen shared builder: {SHARED_GENERATOR}")
fleet = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fleet
spec.loader.exec_module(fleet)


class Fendt1167Builder(fleet.FleetBuilder):
    BELT_WIDTH_M = 0.762
    TRACK_WHEELBASE_M = 3.0
    GROUND_CLEARANCE_M = 0.359
    FRONT_IDLER_RADIUS_M = 0.64
    REAR_DRIVE_RADIUS_M = 0.76
    TOLERANCE_M = 0.003

    def write_machine_wrapper(self):
        """Keep this audited machine-local implementation."""

    @staticmethod
    def _remove(name):
        obj = fleet.bpy.data.objects.get(name)
        if obj is not None:
            fleet.bpy.data.objects.remove(obj, do_unlink=True)

    def required_semantics(self):
        names = list(super().required_semantics())
        for name in (
            "Track_L_Hardbar_ROOT",
            "Track_R_Hardbar_ROOT",
            "SmartRide_Visual_ROOT",
            "Rear_PTO_Shaft_ROOT",
            "Ground_Clearance_Crossmember",
            "Rear_Hitch_L_Lower_Link",
            "Rear_Hitch_R_Lower_Link",
            "Rear_Hitch_Top_Link",
        ):
            if name not in names:
                names.append(name)
        return names

    def build_twin_track_tractor(self):
        super().build_twin_track_tractor()
        length, width, height = self.length, self.width, self.height
        # Replace the generic monolithic hood and tower cab with a lower,
        # stepped power-module silhouette and an independently authored cab
        # shell with sloped corners.  These are neutral study forms, not copied
        # manufacturer surfacing.
        self._remove("Engine_House")
        self.side_profile(
            "Power_Module_Profile",
            [(0.18, 1.42), (2.48, 1.42), (3.08, 1.68),
             (2.88, 2.43), (0.52, 2.55), (0.18, 2.30)],
            1.62, self.materials["body"], self.fixed_root,
            role="engine_house",
        )
        self.side_profile(
            "Hood_Top_Service_Cowl",
            [(0.55, 2.47), (2.78, 2.37), (2.62, 2.57), (0.72, 2.66)],
            1.40, self.materials["body_dark"], self.fixed_root,
            role="service_cowl",
        )
        self.box(
            "Underhood_Engine_Block", (1.30, 1.76, 0),
            (1.48, 0.58, 1.10), self.materials["graphite"],
            self.fixed_root, role="powertrain", bevel=0.028,
        )
        self.cylinder(
            "Transmission_Case", (0.08, 1.31, 0), 0.34, 0.92,
            self.materials["steel"], self.fixed_root, vertices=24,
            rotation=(math.pi / 2, 0, 0), role="powertrain",
        )
        self.box(
            "Front_Cooling_Core", (2.82, 2.00, 0),
            (0.22, 0.66, 1.34), self.materials["graphite"],
            self.fixed_root, role="cooling_core", bevel=0.016,
        )
        for index in range(9):
            self.box(
                f"Front_Cooling_Grille_Slat_{index + 1}",
                (2.945, 1.73 + index * 0.068, 0),
                (0.035, 0.035, 1.27), self.materials["steel"],
                self.fixed_root, role="cooling_grille", bevel=0.004,
            )
        self.cylinder(
            "Neutral_Exhaust_Stack", (1.87, 2.88, 0.56),
            0.075, 0.76, self.materials["graphite"], self.fixed_root,
            vertices=20, rotation=(math.pi / 2, 0, 0), role="exhaust",
        )

        station = fleet.bpy.data.objects["Operator_Station_ROOT"]
        for obj in list(station.children_recursive):
            if obj.type == "MESH":
                fleet.bpy.data.objects.remove(obj, do_unlink=True)
        self.side_profile(
            "Cab_Structural_Shell",
            [(-0.88, 0.08), (0.54, 0.08), (0.74, 1.32),
             (0.48, 2.08), (0.12, 2.22), (-0.73, 2.13),
             (-0.96, 1.34)],
            1.72, self.materials["graphite"], station,
            role="cab_structure",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.side_profile(
                f"Cab_{side}_Corner_Glass",
                [(-0.72, 0.38), (0.44, 0.38), (0.60, 1.31),
                 (0.38, 1.91), (-0.61, 1.91), (-0.78, 1.28)],
                0.045, self.materials["glass"], station,
                z_center=sign * 0.875, role="glazing",
            )
        self.side_profile(
            "Cab_Front_Windscreen",
            [(0.47, 0.42), (0.69, 1.30), (0.44, 1.91),
             (0.32, 1.86), (0.29, 0.48)],
            1.58, self.materials["glass"], station, role="glazing",
        )
        self.side_profile(
            "Cab_Roof_Profile",
            [(-0.80, 2.04), (0.48, 2.04), (0.62, 2.18),
             (0.14, 2.28), (-0.70, 2.20)],
            1.82, self.materials["body"], station,
            role="cab_structure",
        )
        self.box(
            "Operator_Seat", (-0.20, 0.58, 0),
            (0.46, 0.76, 0.58), self.materials["graphite"], station,
            role="operator_cue", bevel=0.025,
        )
        cab_suspension = fleet.bpy.data.objects["Cab_Suspension_ROOT"]
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Cab_Rear_Suspension_Strut_{side}",
                (-0.64, 0.02, sign * 0.56), (-0.50, 0.34, sign * 0.62),
                0.035, self.materials["rod"], cab_suspension,
                role="cab_suspension",
            )

        # Full platform, fenders, steps, and handrails tie the cab to the
        # running gear instead of leaving an empty chassis shelf.
        for side, sign in (("L", -1), ("R", 1)):
            self.box(
                f"Service_Platform_{side}", (-0.52, 1.34, sign * 1.08),
                (2.26, 0.10, 0.34), self.materials["steel"],
                self.fixed_root, role="service_platform", bevel=0.010,
            )
            self.side_profile(
                f"Track_Fender_{side}",
                [(-2.05, 1.24), (1.55, 1.24), (1.38, 1.52),
                 (-1.82, 1.56)],
                0.16, self.materials["body_dark"], self.fixed_root,
                z_center=sign * 1.16, role="fender",
            )
            for index in range(3):
                self.box(
                    f"Access_Step_{side}_{index + 1}",
                    (-1.33 + index * 0.16, 0.66 + index * 0.22,
                     sign * (1.20 + index * 0.02)),
                    (0.36, 0.075, 0.32), self.materials["steel"],
                    self.fixed_root, role="access_step", bevel=0.008,
                )
            self.pipe_between(
                f"Platform_Handrail_{side}", (-1.50, 1.33, sign * 1.30),
                (-1.50, 2.12, sign * 1.30), 0.026,
                self.materials["steel"], self.fixed_root, role="handrail",
            )
            self.pipe_between(
                f"Platform_Handrail_Top_{side}", (-1.50, 2.12, sign * 1.30),
                (-0.64, 2.12, sign * 1.30), 0.026,
                self.materials["steel"], self.fixed_root, role="handrail",
            )
        # Applied bevels can extend a nominally grounded pad a few millimetres;
        # this deterministic offset keeps the evaluated public mesh nonnegative.
        fleet.bpy.data.objects["SmartRide_Level_ROOT"].location.y = 0.006

        # The two belt roots retain independent propulsion identity. Their
        # reconstructed gauge places the published 30 in belt surfaces exactly
        # on the published 2.950 m standard-width envelope.
        track_z = width / 2 - self.BELT_WIDTH_M / 2
        for side, sign in (("L", -1), ("R", 1)):
            root = fleet.bpy.data.objects[f"Track_{side}_ROOT"]
            root.location.z = sign * track_z
            for obj in list(root.children_recursive):
                if obj.name.startswith(f"Track_{side}_Pad_"):
                    obj.dimensions.z = self.BELT_WIDTH_M
            for label, x, radius in (
                ("Front", self.TRACK_WHEELBASE_M / 2, self.FRONT_IDLER_RADIUS_M),
                ("Rear", -self.TRACK_WHEELBASE_M / 2, self.REAR_DRIVE_RADIUS_M),
            ):
                wheel = fleet.bpy.data.objects[f"Track_{side}_{label}_Wheel"]
                wheel.location.x = x
                wheel.location.y = radius
                wheel.dimensions = (2 * radius, 2 * radius, self.BELT_WIDTH_M * 0.78)

            # Additional support-wheel and bogie-arm anatomy makes the belt
            # carrier legible as a loaded undercarriage rather than two discs
            # inside a rubber loop.
            for index, x in enumerate((-0.68, 0.0, 0.68), 1):
                self.cylinder(
                    f"Track_{side}_Upper_Support_Wheel_{index}",
                    (x, 0.91, 0), 0.18, self.BELT_WIDTH_M * 0.64,
                    self.materials["steel"], root, vertices=20,
                    role="track_support_wheel",
                )
            for index, x in enumerate((-1.02, -0.34, 0.34, 1.02), 1):
                self.pipe_between(
                    f"Track_{side}_Bogie_Arm_{index}",
                    (x, 0.82, 0), (x * 0.88, 0.42, 0), 0.043,
                    self.materials["steel"], root, role="bogie_arm",
                )
            self.pipe_between(
                f"Track_{side}_Tension_Link", (1.10, 0.84, 0),
                (1.48, 0.70, 0), 0.052, self.materials["rod"],
                root, role="track_tension_link",
            )
            self.box(
                f"Track_{side}_Carrier_Gusset", (0, 0.82, 0),
                (2.55, 0.16, self.BELT_WIDTH_M * 0.48),
                self.materials["graphite"], root, role="track_frame",
                bevel=0.018,
            )

            # Hardbar motion is shown by an attached rocker/cylinder assembly,
            # not by rotating the ground-contacting belt through the ground.
            hardbar = self.empty(
                f"Track_{side}_Hardbar_ROOT",
                (-0.20, 1.03, sign * (track_z - 0.18)),
                self.fixed_root,
                role="suspension_motion_root",
            )
            self.pipe_between(
                f"Track_{side}_Hardbar_Rocker",
                (-0.52, 0, 0),
                (0.52, 0.10, 0),
                0.055,
                self.materials["steel"],
                hardbar,
                role="suspension_link",
            )
            self.pipe_between(
                f"Track_{side}_Hardbar_Cylinder",
                (-0.18, 0.02, 0),
                (0.24, 0.46, -sign * 0.11),
                0.047,
                self.materials["rod"],
                hardbar,
                role="hydraulic",
            )

        # A named chassis datum makes the brochure clearance independently
        # measurable. Four vertical supports visibly connect it to the frame.
        self.box(
            "Ground_Clearance_Crossmember",
            (0, self.GROUND_CLEARANCE_M + 0.04, 0),
            (2.20, 0.08, 1.34),
            self.materials["graphite"],
            self.fixed_root,
            role="chassis_clearance_datum",
            bevel=0.012,
        )
        for index, (x, z) in enumerate(((-0.86, -0.48), (-0.86, 0.48), (0.86, -0.48), (0.86, 0.48)), 1):
            self.pipe_between(
                f"Clearance_Support_{index}",
                (x, self.GROUND_CLEARANCE_M + 0.07, z),
                (x, height * 0.31, z),
                0.045,
                self.materials["steel"],
                self.fixed_root,
                role="chassis_support",
            )

        # SmartRide is represented by a distinct, ground-safe visible hydraulic
        # cross-link; it does not own either rigid belt loop.
        smartride = self.empty(
            "SmartRide_Visual_ROOT", (0.92, 1.04, 0), self.fixed_root,
            role="suspension_motion_root",
        )
        self.box(
            "SmartRide_Cross_Link", (0, 0, 0), (0.82, 0.10, 1.22),
            self.materials["steel"], smartride, role="suspension_link",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"SmartRide_{side}_Cylinder", (-0.24, 0.04, sign * 0.45),
                (0.23, 0.42, sign * 0.55), 0.048,
                self.materials["rod"], smartride, role="hydraulic",
            )

        # Preserve the previously proved rear-interface positions and add a
        # legible connected three-point triangle around the retained hitch box.
        values = self.design["reconstructed_values"]
        hitch_pivot = fleet.bpy.data.objects["Rear_Hitch_Pivot"]
        hitch_pivot.location.y = height * float(values["rear_hitch_pivot_height_ratio"])
        drawbar_pivot = fleet.bpy.data.objects["Drawbar_Pivot"]
        drawbar_pivot.location.y = height * float(values["drawbar_pivot_height_ratio"])
        hitch_root = fleet.bpy.data.objects["Rear_Hitch_ROOT"]
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Rear_Hitch_{side}_Lower_Link", (0.22, 0.03, sign * 0.18),
                (-0.55, -0.04, sign * 0.27), 0.042,
                self.materials["steel"], hitch_root, role="hitch_link",
            )
        self.pipe_between(
            "Rear_Hitch_Top_Link", (0.20, 0.18, 0), (-0.52, 0.08, 0),
            0.037, self.materials["steel"], hitch_root, role="hitch_link",
        )
        self.box(
            "Rear_Hitch_Coupler_Frame", (-0.52, -0.02, 0),
            (0.16, 0.34, 0.72), self.materials["graphite"],
            hitch_root, role="hitch_coupler", bevel=0.012,
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Rear_Hitch_{side}_Lift_Cylinder",
                (0.18, 0.16, sign * 0.28), (-0.30, 0.06, sign * 0.25),
                0.035, self.materials["rod"], hitch_root,
                role="hydraulic",
            )
        self.box(
            "Rear_Implement_Interface_Crossbar", (-2.85, 1.08, 0),
            (0.26, 0.22, 0.86), self.materials["steel"],
            self.fixed_root, role="hitch_mount", bevel=0.012,
        )
        self.pipe_between(
            "Drawbar_Tongue", (-2.60, 0.88, 0), (-3.28, 0.70, 0),
            0.055, self.materials["steel"], self.fixed_root,
            role="drawbar_support",
        )

        # Guard stays fixed; only this child root rotates in the public viewer.
        pto_housing = self.empty(
            "Rear_PTO_Housing_ROOT", (-2.55, 1.23, 0), self.fixed_root,
            role="fixed_guard_root",
        )
        self.cylinder(
            "Rear_PTO_Guard", (0, 0, 0), 0.12, 0.24,
            self.materials["warning"], pto_housing, vertices=20,
            rotation=(0, math.pi / 2, 0), role="pto_guard",
        )
        pto_shaft = self.empty(
            "Rear_PTO_Shaft_ROOT", (-0.07, 0, 0), pto_housing,
            role="rotary_root",
        )
        self.cylinder(
            "Rear_PTO_Shaft", (0, 0, 0), 0.052, 0.34,
            self.materials["steel"], pto_shaft, vertices=16,
            rotation=(0, math.pi / 2, 0), role="pto_shaft",
        )

        # Connected structural end members establish the published retained
        # longitudinal envelope without detached measurement witnesses.
        self.pipe_between(
            "Front_Frame_Extension", (2.05, 1.16, 0),
            (length / 2 - 0.05, 1.06, 0), 0.065,
            self.materials["graphite"], self.fixed_root, role="chassis",
        )
        self.box(
            "Front_End_Structure", (length / 2 - 0.025, 1.06, 0),
            (0.05, 0.18, 0.78), self.materials["graphite"],
            self.fixed_root, role="chassis", bevel=0.008,
        )
        self.pipe_between(
            "Rear_Frame_Extension", (-2.48, 0.94, 0),
            (-length / 2 + 0.05, 0.94, 0), 0.055,
            self.materials["steel"], self.fixed_root, role="drawbar_support",
        )
        self.box(
            "Rear_End_Structure", (-length / 2 + 0.025, 0.94, 0),
            (0.05, 0.16, 0.34), self.materials["steel"],
            self.fixed_root, role="drawbar_support", bevel=0.008,
        )
        self.box(
            "Published_Height_Roof", (0, height * 0.61 - 0.025, 0),
            (1.18, 0.05, 1.18), self.materials["body"],
            fleet.bpy.data.objects["Cab_Suspension_ROOT"],
            role="cab_structure", bevel=0.008,
        )
        self.pipe_between(
            "Hydraulic_Manifold_Line", (-0.72, 1.16, -0.32),
            (-0.08, 1.20, -0.32), 0.028,
            self.materials["rod"], self.hydraulics_root, role="hydraulic",
        )
        self.box(
            "Service_Access_Step", (-1.36, 1.04, -0.72),
            (0.48, 0.08, 0.20), self.materials["steel"],
            self.detail_root, role="service_step", bevel=0.01,
        )

    @staticmethod
    def _object_bounds(obj):
        points = [obj.matrix_world @ fleet.Vector(corner) for corner in obj.bound_box]
        return (
            [min(point[axis] for point in points) for axis in range(3)],
            [max(point[axis] for point in points) for axis in range(3)],
        )

    def _bounds(self, names):
        minimum = [math.inf, math.inf, math.inf]
        maximum = [-math.inf, -math.inf, -math.inf]
        for name in names:
            obj = fleet.bpy.data.objects.get(name)
            if obj is None or obj.type != "MESH":
                raise RuntimeError(f"missing measured mesh {name}")
            low, high = self._object_bounds(obj)
            for axis in range(3):
                minimum[axis] = min(minimum[axis], low[axis])
                maximum[axis] = max(maximum[axis], high[axis])
        return minimum, maximum

    def _subtree_meshes(self, root_name):
        root = fleet.bpy.data.objects.get(root_name)
        if root is None:
            raise RuntimeError(f"missing motion root {root_name}")
        return [obj.name for obj in root.children_recursive if obj.type == "MESH"]

    def _overlap(self, first, second):
        first_low, first_high = self._bounds([first])
        second_low, second_high = self._bounds([second])
        return [
            min(first_high[axis], second_high[axis])
            - max(first_low[axis], second_low[axis])
            for axis in range(3)
        ]

    @staticmethod
    def _gate(gate_id, method, evidence, semantic_nodes, fact_ids=(), passed=True):
        return {
            "id": gate_id,
            "status": "PASS" if passed else "FAIL",
            "detail": {
                "method": method,
                "evidence": evidence,
                "semantic_nodes": list(semantic_nodes),
                "fact_ids": list(fact_ids),
                "authority": "Computed visualization evidence only; not engineering or operating authority.",
            },
        }

    def machine_specific_validation_gates(self, contract):
        tolerance = self.TOLERANCE_M
        size = contract["bounds"]["size_m"]
        track_centers = {}
        belt_widths = {}
        wheelbase = {}
        for side in ("L", "R"):
            front = fleet.bpy.data.objects[f"Track_{side}_Front_Wheel"].matrix_world.translation
            rear = fleet.bpy.data.objects[f"Track_{side}_Rear_Wheel"].matrix_world.translation
            track_centers[side] = round(abs(front.z), 6)
            wheelbase[side] = round(abs(front.x - rear.x), 6)
            pad = fleet.bpy.data.objects[f"Track_{side}_Pad_01"]
            low, high = self._object_bounds(pad)
            belt_widths[side] = round(high[2] - low[2], 6)

        clearance_low, _ = self._bounds(["Ground_Clearance_Crossmember"])
        # Blender Euler components are sampled explicitly so the validation is
        # independent of the browser implementation.
        dynamic_minima = {}
        for root_name, axis, values in (
            ("Track_L_Hardbar_ROOT", 2, (-0.08, 0.0, 0.08)),
            ("Track_R_Hardbar_ROOT", 2, (-0.08, 0.0, 0.08)),
        ):
            root = fleet.bpy.data.objects[root_name]
            original = root.rotation_euler[axis]
            samples = []
            for value in values:
                root.rotation_euler[axis] = value
                fleet.bpy.context.view_layer.update()
                low, _ = self._bounds(self._subtree_meshes(root_name))
                samples.append(round(low[1], 6))
            root.rotation_euler[axis] = original
            dynamic_minima[root_name] = samples
        smartride = fleet.bpy.data.objects["SmartRide_Visual_ROOT"]
        original_y = smartride.location.y
        smart_samples = []
        for offset in (0.0, 0.12):
            smartride.location.y = original_y + offset
            fleet.bpy.context.view_layer.update()
            low, _ = self._bounds(self._subtree_meshes("SmartRide_Visual_ROOT"))
            smart_samples.append(round(low[1], 6))
        smartride.location.y = original_y
        fleet.bpy.context.view_layer.update()

        hitch_overlap = self._overlap("Rigid_Main_Frame", "Rear_Hitch_Links")
        drawbar_overlap = self._overlap("Rear_Hitch_Links", "Drawbar")
        viewer = json.loads(VIEWER.read_text(encoding="utf-8"))
        viewer_nodes = {
            node
            for channel in viewer["motion"]["channels"]
            for node in channel["nodes"]
        }
        all_mesh_low, _ = self._bounds([obj.name for obj in self.public_objects() if obj.type == "MESH"])
        materials_ok = all(
            material.get("exo_rights") == "neutral_unbranded"
            for material in self.materials.values()
        )

        return [
            self._gate("published_length_envelope", "decoded GLB visible AABB X span", {"measured_m": size[0], "target_m": self.length, "tolerance_m": tolerance}, ["Front_End_Structure", "Rear_End_Structure"], ["public-envelope-x"], abs(size[0] - self.length) <= tolerance),
            self._gate("published_standard_width_envelope", "decoded GLB visible AABB Z span", {"measured_m": size[2], "target_m": self.width, "tolerance_m": tolerance}, ["Track_L_ROOT", "Track_R_ROOT"], ["public-envelope-z"], abs(size[2] - self.width) <= tolerance),
            self._gate("published_height_envelope", "decoded GLB visible AABB Y span", {"measured_m": size[1], "target_m": self.height, "tolerance_m": tolerance}, ["Published_Height_Roof"], ["public-envelope-y"], abs(size[1] - self.height) <= tolerance),
            self._gate("track_wheelbase", "world-space front/rear wheel-center subtraction", {"measured_m": wheelbase, "target_m": self.TRACK_WHEELBASE_M, "tolerance_m": tolerance}, ["Track_L_Front_Wheel", "Track_L_Rear_Wheel", "Track_R_Front_Wheel", "Track_R_Rear_Wheel"], ["track-wheelbase"], all(abs(value - self.TRACK_WHEELBASE_M) <= tolerance for value in wheelbase.values())),
            self._gate("ground_clearance", "named chassis-datum minimum Y", {"measured_m": round(clearance_low[1], 6), "target_m": self.GROUND_CLEARANCE_M, "tolerance_m": tolerance}, ["Ground_Clearance_Crossmember"], ["ground-clearance"], abs(clearance_low[1] - self.GROUND_CLEARANCE_M) <= tolerance),
            self._gate("left_right_track_separation", "belt-pad world AABB width and mirrored root centers", {"belt_width_m": belt_widths, "target_belt_width_m": self.BELT_WIDTH_M, "absolute_root_centers_z_m": track_centers}, ["Track_L_ROOT", "Track_R_ROOT"], ["selected-track-belt-width"], all(abs(value - self.BELT_WIDTH_M) <= tolerance for value in belt_widths.values()) and abs(track_centers["L"] - track_centers["R"]) <= tolerance),
            self._gate("track_component_continuity", "named loop component inventory plus ground-contact equality", {"left_meshes": len(self._subtree_meshes("Track_L_ROOT")), "right_meshes": len(self._subtree_meshes("Track_R_ROOT")), "front_radius_m": self.FRONT_IDLER_RADIUS_M, "rear_radius_m": self.REAR_DRIVE_RADIUS_M, "rest_minimum_y_m": round(all_mesh_low[1], 6)}, ["Track_L_ROOT", "Track_R_ROOT"], ["midwheel-sets-per-side"], len(self._subtree_meshes("Track_L_ROOT")) >= 45 and len(self._subtree_meshes("Track_R_ROOT")) >= 45 and all_mesh_low[1] >= -tolerance),
            self._gate("independent_hardbar_compliance", "three-pose subtree ground-clearance sweep", {"presentation_angles_rad": [-0.08, 0.0, 0.08], "minimum_y_samples_m": dynamic_minima, "distinct_roots": True, "published_travel_not_converted_to_angle": True}, ["Track_L_Hardbar_ROOT", "Track_R_Hardbar_ROOT"], ["smartride-hardbar-travel"], all(value >= -tolerance for values in dynamic_minima.values() for value in values)),
            self._gate("smartride_plus_leveling_continuity", "two-endpoint visible hydraulic subtree sweep", {"presentation_offsets_m": [0.0, 0.12], "minimum_y_samples_m": smart_samples, "visible_meshes": len(self._subtree_meshes("SmartRide_Visual_ROOT")), "published_leveling_range_unresolved": True}, ["SmartRide_Visual_ROOT"], [], min(smart_samples) >= -tolerance and len(self._subtree_meshes("SmartRide_Visual_ROOT")) >= 3),
            self._gate("cab_suspension_continuity", "motion-root hierarchy and nonempty visible subtree", {"parent": fleet.bpy.data.objects["Cab_Suspension_ROOT"].parent.name, "visible_meshes": len(self._subtree_meshes("Cab_Suspension_ROOT")), "viewer_range_m": [0.0, 0.08], "published_rear_travel_m": 0.10, "mapping_to_viewer_axis_reconstructed": True}, ["Cab_Suspension_ROOT"], ["cab-rear-suspension-travel"], len(self._subtree_meshes("Cab_Suspension_ROOT")) >= 8),
            self._gate("three_point_linkage_continuity", "rest-pose three-axis AABB overlap for chassis-hitch-drawbar chain", {"chassis_to_hitch_overlap_xyz_m": [round(v, 6) for v in hitch_overlap], "hitch_to_drawbar_overlap_xyz_m": [round(v, 6) for v in drawbar_overlap]}, ["Rear_Hitch_Pivot", "Rear_Hitch_ROOT"], [], min(hitch_overlap) >= 0.001 and min(drawbar_overlap) >= 0.001),
            self._gate("drawbar_range_not_claimed", "viewer-channel ownership scan", {"drawbar_nodes_animated": sorted(viewer_nodes & {"Drawbar_Pivot", "Drawbar"}), "numeric_limit_withheld": True}, [], [], not bool(viewer_nodes & {"Drawbar_Pivot", "Drawbar"})),
            self._gate("ground_collision", "rest AABB plus all exposed suspension endpoint samples", {"rest_minimum_y_m": round(all_mesh_low[1], 6), "hardbar_minimum_y_m": min(value for values in dynamic_minima.values() for value in values), "smartride_minimum_y_m": min(smart_samples)}, ["Track_L_ROOT", "Track_R_ROOT", "Track_L_Hardbar_ROOT", "Track_R_Hardbar_ROOT", "SmartRide_Visual_ROOT"], [], all_mesh_low[1] >= -tolerance and min(value for values in dynamic_minima.values() for value in values) >= -tolerance and min(smart_samples) >= -tolerance),
            self._gate("self_collision", "separate motion-root ownership and bounded endpoint sweep", {"belt_roots_static": not bool(viewer_nodes & {"Track_L_ROOT", "Track_R_ROOT", "SmartRide_Level_ROOT"}), "rear_interface_minimum_overlap_m": round(min(hitch_overlap + drawbar_overlap), 6)}, ["Track_L_Hardbar_ROOT", "Track_R_Hardbar_ROOT", "SmartRide_Visual_ROOT", "Rear_Hitch_Pivot"], [], not bool(viewer_nodes & {"Track_L_ROOT", "Track_R_ROOT", "SmartRide_Level_ROOT"}) and min(hitch_overlap + drawbar_overlap) >= 0.001),
            self._gate("neutral_unbranded_material_review", "procedural material rights-tag scan", {"material_count": len(self.materials), "all_neutral_unbranded": materials_ok}, [], [], materials_ok),
        ]

    def render_views(self):
        """Render rest and clearly articulated hardbar/SmartRide/hitch poses."""
        self.setup_render_scene()
        camera = fleet.bpy.data.objects["Review_Camera"]
        span = max(self.length, self.width, self.height)
        center = fleet.Vector((0, self.height * 0.46, 0))
        views = [
            ("operator-side", (0, self.height * 0.64, -span * 1.55), span * 1.06, "left"),
            ("front-three-quarter", (span * 1.10, self.height * 0.88, -span * 1.02), span * 1.15, "rest"),
            ("rear-three-quarter", (-span * 1.08, self.height * 0.82, span * 0.92), span * 1.12, "rear"),
            ("elevated-technical", (span * 0.64, span * 1.44, -span * 0.94), span * 1.24, "ride"),
            ("articulation-detail", (-span * 0.92, self.height * 0.64, span * 0.66), span * 0.70, "rear"),
            ("right-side", (0, self.height * 0.64, span * 1.55), span * 1.06, "right"),
        ]
        left = fleet.bpy.data.objects["Track_L_Hardbar_ROOT"]
        right = fleet.bpy.data.objects["Track_R_Hardbar_ROOT"]
        smart = fleet.bpy.data.objects["SmartRide_Visual_ROOT"]
        cab = fleet.bpy.data.objects["Cab_Suspension_ROOT"]
        hitch = fleet.bpy.data.objects["Rear_Hitch_Pivot"]
        smart_base, cab_base = smart.location.y, cab.location.y
        paths = []
        for label, location, ortho_scale, pose in views:
            left.rotation_euler.z = 0.08 if pose in {"left", "ride"} else (-0.08 if pose == "right" else 0.0)
            right.rotation_euler.z = -0.08 if pose in {"right", "ride"} else (0.08 if pose == "left" else 0.0)
            smart.location.y = smart_base + (0.12 if pose in {"left", "right", "ride"} else 0.0)
            cab.location.y = cab_base + (0.08 if pose in {"ride", "rear"} else 0.0)
            hitch.rotation_euler.z = 0.22 if pose == "rear" else (-0.10 if pose == "ride" else 0.0)
            fleet.bpy.context.view_layer.update()
            camera.location = location
            self.point_at(camera, center)
            camera.data.ortho_scale = ortho_scale
            path = self.render_dir / f"{self.machine_id}-{label}.png"
            fleet.bpy.context.scene.render.filepath = str(path)
            fleet.bpy.ops.render.render(write_still=True)
            paths.append(path)
        left.rotation_euler.z = 0.0
        right.rotation_euler.z = 0.0
        smart.location.y = smart_base
        cab.location.y = cab_base
        hitch.rotation_euler.z = 0.0
        fleet.bpy.context.view_layer.update()
        return paths


if __name__ == "__main__":
    design = fleet.load_design(DESIGN)
    Fendt1167Builder(design, DESIGN, OUTPUT_DIR).run()
