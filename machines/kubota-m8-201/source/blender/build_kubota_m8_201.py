#!/usr/bin/env python3
"""Deterministic machine-local Kubota M8-201 structural-study builder."""

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

spec = importlib.util.spec_from_file_location("exo_fleet_kubota_m8", SHARED_GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load frozen shared builder: {SHARED_GENERATOR}")
fleet = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fleet
spec.loader.exec_module(fleet)


class KubotaM8201Builder(fleet.FleetBuilder):
    WHEELBASE_M = 2.895
    REAR_BAR_AXLE_M = 2.489
    FRONT_RADIUS_M = 0.71
    REAR_RADIUS_M = 0.96
    TOLERANCE_M = 0.003

    def write_machine_wrapper(self):
        """Keep this audited machine-local implementation."""

    def required_semantics(self):
        names = list(super().required_semantics())
        for name in (
            "Rear_Axle_ROOT",
            "Rear_Bar_Axle",
            "Front_L_Suspension_Strut",
            "Front_R_Suspension_Strut",
            "Rear_Hitch_Coupler",
            "Rear_Hitch_L_Lower_Link",
            "Rear_Hitch_R_Lower_Link",
            "Rear_Hitch_Top_Link",
            "PTO_Shaft_ROTATION_ROOT",
        ):
            if name not in names:
                names.append(name)
        return names

    @staticmethod
    def _remove(name):
        obj = fleet.bpy.data.objects.get(name)
        if obj is not None:
            fleet.bpy.data.objects.remove(obj, do_unlink=True)

    def _rebuild_wheel_geometry(self, prefix, radius, width, tread_count):
        """Replace generic tire geometry without scaled semantic roots."""
        root = fleet.bpy.data.objects[f"{prefix}_Wheel_ROOT"]
        for obj in reversed(list(root.children_recursive)):
            fleet.bpy.data.objects.remove(obj, do_unlink=True)
        root.scale = (1.0, 1.0, 1.0)
        self.wheel_tire(
            f"{prefix}_Tire", radius, width / 2,
            self.materials["rubber"], root,
        )
        self.cylinder(
            f"{prefix}_Rim", (0, 0, 0), radius * 0.48, width * 0.82,
            self.materials["steel"], root, vertices=20,
        )
        self.cylinder(
            f"{prefix}_Hub", (0, 0, 0), radius * 0.18, width * 0.90,
            self.materials["graphite"], root, vertices=16,
        )
        for index in range(tread_count):
            angle = math.tau * index / tread_count
            self.box(
                f"{prefix}_Tread_{index + 1:02d}",
                (math.cos(angle) * radius * 0.94,
                 math.sin(angle) * radius * 0.94, 0),
                (radius * 0.10, radius * 0.15, width * 0.96),
                self.materials["rubber"], root,
                rotation=(0, 0, angle), role="tire_tread",
                bevel=radius * 0.015,
            )
        for index in range(8):
            angle = math.tau * index / 8
            self.cylinder(
                f"{prefix}_Lug_{index + 1:02d}",
                (math.cos(angle) * radius * 0.29,
                 math.sin(angle) * radius * 0.29, -width * 0.43),
                radius * 0.027, width * 0.055,
                self.materials["steel"], root, vertices=12,
                role="wheel_fastener",
            )

    def build_wheeled_tractor(self):
        super().build_wheeled_tractor()
        length, width, height = self.length, self.width, self.height
        front_x = self.WHEELBASE_M / 2
        rear_x = -self.WHEELBASE_M / 2
        front_width = 0.42
        rear_width = 0.52
        front_z = width / 2 - front_width / 2
        rear_z = width / 2 - rear_width / 2

        generic_rear_radius = min(height * 0.29, length * 0.145)
        generic_front_radius = generic_rear_radius * 0.72
        generic_rear_width = width * 0.20
        generic_front_width = width * 0.15

        front_pivot = fleet.bpy.data.objects["Front_Axle_Oscillation_Pivot"]
        front_pivot.location = (front_x, self.FRONT_RADIUS_M, 0)
        front_axle = fleet.bpy.data.objects["Front_Axle_ROOT"]
        for side, sign in (("L", -1), ("R", 1)):
            steering = fleet.bpy.data.objects[f"Steering_{side}_Pivot"]
            steering.location = (0, 0, sign * front_z)
            self._rebuild_wheel_geometry(
                f"Front_{side}", self.FRONT_RADIUS_M, front_width, 16,
            )

        # The standard 98 in bar axle is visible and owns both rear wheel roots.
        rear_pivot = self.empty(
            "Rear_Axle_Pivot", (rear_x, self.REAR_RADIUS_M, 0),
            self.running_root, role="axle_mount",
        )
        rear_axle = self.empty("Rear_Axle_ROOT", parent=rear_pivot, role="fixed_axle_root")
        self.cylinder(
            "Rear_Bar_Axle", (0, 0, 0), 0.095, self.REAR_BAR_AXLE_M,
            self.materials["steel"], rear_axle, vertices=24,
            role="rear_bar_axle",
        )
        self.cylinder(
            "Rear_Differential_Housing", (0, 0, 0), 0.22, 0.42,
            self.materials["graphite"], rear_axle, vertices=24,
            role="differential",
        )
        for side, sign in (("L", -1), ("R", 1)):
            wheel_pivot = fleet.bpy.data.objects[f"Rear_{side}_Wheel_Pivot"]
            wheel_pivot.parent = rear_axle
            wheel_pivot.location = (0, 0, sign * rear_z)
            self._rebuild_wheel_geometry(
                f"Rear_{side}", self.REAR_RADIUS_M, rear_width, 18,
            )

        # Connected front differential, suspension struts, and broad brackets.
        fleet.bpy.data.objects["Front_Axle_Beam"].dimensions = (0.28, 0.20, 2.08)
        self.cylinder(
            "Front_Differential_Housing", (0, 0, 0), 0.18, 0.40,
            self.materials["graphite"], front_axle, vertices=22,
            rotation=(math.pi / 2, 0, 0), role="differential",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.box(
                f"Front_{side}_Suspension_Frame_Bracket",
                (front_x - 0.10, 0.94, sign * 0.44),
                (0.34, 0.34, 0.20), self.materials["graphite"],
                self.fixed_root, role="suspension_mount", bevel=0.015,
            )
            self.pipe_between(
                f"Front_{side}_Suspension_Strut", (-0.02, 0.03, sign * 0.48),
                (-0.12, 0.28, sign * 0.42), 0.052,
                self.materials["rod"], front_axle, role="suspension_strut",
            )
            self.box(
                f"Front_{side}_Fender", (front_x, 1.53, sign * front_z),
                (1.18, 0.10, 0.36), self.materials["body_dark"],
                self.fixed_root, role="fender", bevel=0.02,
            )

        # Replace the generic rear linkage with a closed, central three-point
        # chain whose inner ends overlap a fixed chassis mount and whose outer
        # ends overlap a common coupler.
        for name in (
            "Rear_Hitch_Drawbar",
            "Rear_Hitch_L_Lower_Link",
            "Rear_Hitch_R_Lower_Link",
            "Rear_Hitch_Top_Link",
        ):
            self._remove(name)
        hitch_pivot = fleet.bpy.data.objects["Rear_Hitch_Pivot"]
        hitch_pivot.location = (-1.55, 1.02, 0)
        hitch_root = fleet.bpy.data.objects["Rear_Hitch_ROOT"]
        self.box(
            "Rear_Hitch_Chassis_Mount", (-1.54, 1.03, 0),
            (0.30, 0.48, 1.02), self.materials["graphite"],
            self.fixed_root, role="hitch_mount", bevel=0.015,
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Rear_Hitch_{side}_Lower_Link", (0.02, 0, sign * 0.27),
                (-1.02, -0.15, sign * 0.36), 0.050,
                self.materials["steel"], hitch_root, role="hitch_link",
            )
        self.pipe_between(
            "Rear_Hitch_Top_Link", (0.02, 0.20, 0), (-1.02, 0.05, 0),
            0.044, self.materials["steel"], hitch_root, role="hitch_link",
        )
        self.box(
            "Rear_Hitch_Coupler", (-1.02, -0.10, 0),
            (0.18, 0.38, 0.90), self.materials["graphite"],
            hitch_root, role="hitch_coupler", bevel=0.012,
        )
        self.box(
            "Rear_Hitch_Drawbar", (-0.49, -0.20, 0),
            (1.02, 0.10, 0.18), self.materials["steel"],
            hitch_root, role="drawbar", bevel=0.012,
        )

        # PTO guard/housing is fixed and attached to the frame; the shaft alone
        # is owned by the rotating semantic root.
        pto = fleet.bpy.data.objects["PTO_ROOT"]
        pto.location = (-1.61, 1.15, 0)
        shaft = fleet.bpy.data.objects["PTO_Shaft"]
        shaft_root = self.empty("PTO_Shaft_ROTATION_ROOT", parent=pto, role="rotary_root")
        shaft.parent = shaft_root
        shaft.location = (-0.12, 0, 0)
        guard = fleet.bpy.data.objects["PTO_Guard"]
        guard.parent = pto
        guard.location = (-0.02, 0, 0)
        self.box(
            "PTO_Frame_Housing", (-0.01, 0, 0), (0.28, 0.32, 0.34),
            self.materials["graphite"], pto, role="pto_housing", bevel=0.018,
        )

        # Exact published height and reconstructed horizontal retained envelope.
        self.pipe_between(
            "Front_Frame_Extension", (1.40, 1.02, 0),
            (length / 2 - 0.05, 1.03, 0), 0.055,
            self.materials["graphite"], self.fixed_root, role="chassis",
        )
        self.box(
            "Front_End_Structure", (length / 2 - 0.025, 1.03, 0),
            (0.05, 0.18, 0.72), self.materials["graphite"],
            self.fixed_root, role="chassis", bevel=0.008,
        )
        self.pipe_between(
            "Rear_Frame_Extension", (-1.52, 0.93, 0),
            (-length / 2 + 0.05, 0.91, 0), 0.050,
            self.materials["steel"], self.fixed_root, role="hitch_support",
        )
        self.box(
            "Rear_End_Structure", (-length / 2 + 0.025, 0.91, 0),
            (0.05, 0.16, 0.30), self.materials["steel"],
            self.fixed_root, role="hitch_support", bevel=0.008,
        )
        self.box(
            "Published_Height_Roof", (-0.75, height - 0.025, 0),
            (1.15, 0.05, 1.12), self.materials["body"],
            self.fixed_root, role="cab_structure", bevel=0.008,
        )
        self.box(
            "Reconstructed_Ground_Clearance_Datum", (0.05, 0.56, 0),
            (1.70, 0.08, 0.88), self.materials["graphite"],
            self.fixed_root, role="chassis_clearance_datum", bevel=0.012,
        )
        self.pipe_between(
            "Hydraulic_Valve_Line", (-1.18, 1.09, -0.34),
            (-0.48, 1.12, -0.34), 0.027,
            self.materials["rod"], self.hydraulics_root, role="hydraulic",
        )
        self.box(
            "Service_Access_Step", (-1.05, 1.14, -0.75),
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
        root = fleet.bpy.data.objects[root_name]
        return [obj.name for obj in root.children_recursive if obj.type == "MESH"]

    def normalize_visible_envelope(self):
        # Apply bevels first, then place both complete axle/wheel subtrees on the
        # common ground plane using evaluated public geometry.
        self.apply_public_modifiers()
        fleet.bpy.context.view_layer.update()
        for pivot_name, root_name in (
            ("Front_Axle_Oscillation_Pivot", "Front_Axle_ROOT"),
            ("Rear_Axle_Pivot", "Rear_Axle_ROOT"),
        ):
            low, _ = self._bounds(self._subtree_meshes(root_name))
            fleet.bpy.data.objects[pivot_name].location.y -= low[1]
            fleet.bpy.context.view_layer.update()
        return super().normalize_visible_envelope()

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
                "authority": "Computed reconstructed-study evidence only; not engineering or operating authority.",
            },
        }

    def machine_specific_validation_gates(self, contract):
        tolerance = self.TOLERANCE_M
        size = contract["bounds"]["size_m"]
        front_center = fleet.bpy.data.objects["Front_Axle_Oscillation_Pivot"].matrix_world.translation
        rear_center = fleet.bpy.data.objects["Rear_Axle_Pivot"].matrix_world.translation
        wheelbase = abs(front_center.x - rear_center.x)
        bar = fleet.bpy.data.objects["Rear_Bar_Axle"]
        bar_low, bar_high = self._object_bounds(bar)
        bar_span = bar_high[2] - bar_low[2]
        contact = {}
        wheel_root_scales = {}
        for name in ("Front_L_Wheel_ROOT", "Front_R_Wheel_ROOT", "Rear_L_Wheel_ROOT", "Rear_R_Wheel_ROOT"):
            low, _ = self._bounds(self._subtree_meshes(name))
            contact[name] = round(low[1], 6)
            wheel_root_scales[name] = [
                round(value, 8) for value in fleet.bpy.data.objects[name].scale
            ]

        mount_to_frame = self._overlap("Rear_Hitch_Chassis_Mount", "Tractor_Main_Frame")
        left_to_coupler = self._overlap("Rear_Hitch_L_Lower_Link", "Rear_Hitch_Coupler")
        right_to_coupler = self._overlap("Rear_Hitch_R_Lower_Link", "Rear_Hitch_Coupler")
        top_to_coupler = self._overlap("Rear_Hitch_Top_Link", "Rear_Hitch_Coupler")
        pto_frame = self._overlap("PTO_Frame_Housing", "Tractor_Main_Frame")
        pto_shaft_guard = self._overlap("PTO_Shaft", "PTO_Guard")
        fender_gaps = {}
        for side in ("L", "R"):
            _, tire_high = self._bounds([f"Front_{side}_Tire"])
            fender_low, _ = self._bounds([f"Front_{side}_Fender"])
            fender_gaps[side] = round(fender_low[1] - tire_high[1], 6)

        axle = fleet.bpy.data.objects["Front_Axle_ROOT"]
        original_y = axle.location.y
        axle_minima = []
        strut_overlaps = []
        for offset in (0.0, 0.02, 0.04):
            axle.location.y = original_y + offset
            fleet.bpy.context.view_layer.update()
            low, _ = self._bounds(self._subtree_meshes("Front_Axle_ROOT"))
            axle_minima.append(round(low[1], 6))
            strut_overlaps.append({
                side: round(min(self._overlap(f"Front_{side}_Suspension_Strut", f"Front_{side}_Suspension_Frame_Bracket")), 6)
                for side in ("L", "R")
            })
        axle.location.y = original_y

        hitch = fleet.bpy.data.objects["Rear_Hitch_Pivot"]
        original_angle = hitch.rotation_euler.z
        hitch_minima = []
        for angle in (0.0, -0.09, -0.18):
            hitch.rotation_euler.z = angle
            fleet.bpy.context.view_layer.update()
            low, _ = self._bounds(self._subtree_meshes("Rear_Hitch_ROOT"))
            hitch_minima.append(round(low[1], 6))
        hitch.rotation_euler.z = original_angle
        fleet.bpy.context.view_layer.update()

        all_low, _ = self._bounds([obj.name for obj in self.public_objects() if obj.type == "MESH"])
        rear_inner_gap = 2 * (abs(fleet.bpy.data.objects["Rear_L_Wheel_Pivot"].matrix_world.translation.z) - 0.52 / 2)
        coupler_half_width = 0.90 / 2
        hitch_tire_clearance = rear_inner_gap / 2 - coupler_half_width
        viewer = json.loads(VIEWER.read_text(encoding="utf-8"))
        viewer_nodes = {node for channel in viewer["motion"]["channels"] for node in channel["nodes"]}

        return [
            self._gate("published_height_and_wheelbase", "decoded height, axle-center subtraction, and rear bar-axle AABB span", {"height_m": size[1], "height_target_m": self.height, "wheelbase_m": round(wheelbase, 6), "wheelbase_target_m": self.WHEELBASE_M, "rear_bar_axle_span_m": round(bar_span, 6), "rear_bar_axle_target_m": self.REAR_BAR_AXLE_M, "tolerance_m": tolerance}, ["Published_Height_Roof", "Front_Axle_Oscillation_Pivot", "Rear_Axle_ROOT"], ["public-envelope-y", "wheelbase", "standard-rear-bar-axle-length"], abs(size[1] - self.height) <= tolerance and abs(wheelbase - self.WHEELBASE_M) <= tolerance and abs(bar_span - self.REAR_BAR_AXLE_M) <= tolerance),
            self._gate("four_tire_ground_contact", "evaluated wheel-subtree minimum Y after axle grounding plus identity-transform audit", {"minimum_y_m": contact, "wheel_root_scale_xyz": wheel_root_scales, "tolerance_m": tolerance}, ["Front_L_Wheel_ROOT", "Front_R_Wheel_ROOT", "Rear_L_Wheel_ROOT", "Rear_R_Wheel_ROOT"], [], all(abs(value) <= tolerance for value in contact.values()) and all(scale == [1.0, 1.0, 1.0] for scale in wheel_root_scales.values())),
            self._gate("front_steering_continuity", "parent-child topology and paired visible wheel descendants", {"left_parent": fleet.bpy.data.objects["Steering_L_Pivot"].parent.name, "right_parent": fleet.bpy.data.objects["Steering_R_Pivot"].parent.name, "viewer_owned": {"Steering_L_Pivot", "Steering_R_Pivot"}.issubset(viewer_nodes)}, ["Steering_L_Pivot", "Steering_R_Pivot"], [], fleet.bpy.data.objects["Steering_L_Pivot"].parent == fleet.bpy.data.objects["Front_Axle_ROOT"] and fleet.bpy.data.objects["Steering_R_Pivot"].parent == fleet.bpy.data.objects["Front_Axle_ROOT"]),
            self._gate("front_suspension_continuity", "three-position axle sweep with strut-to-bracket AABB overlap", {"axle_minimum_y_samples_m": axle_minima, "strut_bracket_minimum_overlap_m": strut_overlaps}, ["Front_Axle_ROOT", "Front_L_Suspension_Strut", "Front_R_Suspension_Strut"], [], min(axle_minima) >= -tolerance and all(value >= 0 for sample in strut_overlaps for value in sample.values())),
            self._gate("rear_hitch_linkage_continuity", "three-axis mount/frame and link/coupler overlap chain", {"mount_frame_overlap_xyz_m": [round(v, 6) for v in mount_to_frame], "left_coupler_overlap_xyz_m": [round(v, 6) for v in left_to_coupler], "right_coupler_overlap_xyz_m": [round(v, 6) for v in right_to_coupler], "top_coupler_overlap_xyz_m": [round(v, 6) for v in top_to_coupler]}, ["Rear_Hitch_Pivot", "Rear_Hitch_ROOT", "Rear_Hitch_Coupler"], [], min(mount_to_frame + left_to_coupler + right_to_coupler + top_to_coupler) >= 0),
            self._gate("pto_axis_continuity", "fixed housing/frame and shaft/guard AABB overlap plus motion ownership", {"housing_frame_overlap_xyz_m": [round(v, 6) for v in pto_frame], "shaft_guard_overlap_xyz_m": [round(v, 6) for v in pto_shaft_guard], "rotating_node": "PTO_Shaft_ROTATION_ROOT", "guard_rotates": "PTO_ROOT" in viewer_nodes}, ["PTO_ROOT", "PTO_Shaft_ROTATION_ROOT"], [], min(pto_frame + pto_shaft_guard) >= 0 and "PTO_Shaft_ROTATION_ROOT" in viewer_nodes and "PTO_ROOT" not in viewer_nodes),
            self._gate("steering_tire_fender_clearance", "rest tire/fender vertical AABB separation", {"clearance_m": fender_gaps, "viewer_range_rad": [-0.48, 0.48]}, ["Steering_L_Pivot", "Steering_R_Pivot"], [], min(fender_gaps.values()) >= 0.02),
            self._gate("rear_hitch_chassis_clearance", "three-position hitch ground sweep and central tire-gap calculation", {"minimum_y_samples_m": hitch_minima, "coupler_to_inner_tire_clearance_m": round(hitch_tire_clearance, 6)}, ["Rear_Hitch_ROOT", "Rear_Hitch_Coupler"], [], min(hitch_minima) >= -tolerance and hitch_tire_clearance >= 0.10),
            self._gate("ground_collision", "rest public AABB and all moving-subtree endpoint minima", {"rest_minimum_y_m": round(all_low[1], 6), "front_axle_minimum_y_m": min(axle_minima), "rear_hitch_minimum_y_m": min(hitch_minima)}, ["Front_Axle_ROOT", "Rear_Axle_ROOT", "Rear_Hitch_ROOT"], [], all_low[1] >= -tolerance and min(axle_minima) >= -tolerance and min(hitch_minima) >= -tolerance),
            self._gate("self_collision", "measured hitch/tire separation and fixed PTO guard ownership", {"hitch_to_rear_tire_clearance_m": round(hitch_tire_clearance, 6), "pto_guard_fixed": "PTO_ROOT" not in viewer_nodes}, ["Rear_Hitch_ROOT", "PTO_ROOT", "Rear_Axle_ROOT"], [], hitch_tire_clearance >= 0.10 and "PTO_ROOT" not in viewer_nodes),
            self._gate("swept_volume_collision", "combined front-axle and rear-hitch endpoint sampling", {"front_offsets_m": [0.0, 0.02, 0.04], "front_minimum_y_m": axle_minima, "hitch_angles_rad": [0.0, -0.09, -0.18], "hitch_minimum_y_m": hitch_minima}, ["Front_Axle_ROOT", "Rear_Hitch_ROOT"], [], min(axle_minima + hitch_minima) >= -tolerance),
        ]


if __name__ == "__main__":
    design = fleet.load_design(DESIGN)
    KubotaM8201Builder(design, DESIGN, OUTPUT_DIR).run()
