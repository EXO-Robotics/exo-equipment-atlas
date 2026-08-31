#!/usr/bin/env python3
"""Deterministic machine-local JCB Fastrac 8330 iCON study builder."""

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

spec = importlib.util.spec_from_file_location("exo_fleet_jcb_8330", SHARED_GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load frozen shared builder: {SHARED_GENERATOR}")
fleet = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fleet
spec.loader.exec_module(fleet)


class JCBFastrac8330Builder(fleet.FleetBuilder):
    WHEELBASE_M = 3.13
    GROUND_CLEARANCE_M = 0.60
    FRONT_TRACK_M = 2.0
    REAR_TRACK_M = 1.835
    FRONT_WIDTH_M = 0.540
    REAR_WIDTH_M = 0.710
    FRONT_RADIUS_M = (38 * 0.0254 + 2 * 0.540 * 0.65) / 2
    REAR_RADIUS_M = (42 * 0.0254 + 2 * 0.710 * 0.60) / 2
    TOLERANCE_M = 0.003

    def write_machine_wrapper(self):
        """Keep this audited machine-local implementation."""

    def required_semantics(self):
        names = list(super().required_semantics())
        for name in (
            "Rear_Axle_Oscillation_Pivot",
            "Rear_Axle_ROOT",
            "Front_Hitch_Pivot",
            "Front_Hitch_ROOT",
            "Front_Hitch_Coupler",
            "Rear_Hitch_Coupler",
            "Front_Hitch_L_Lower_Link",
            "Front_Hitch_R_Lower_Link",
            "Front_Hitch_Top_Link",
            "Rear_Hitch_L_Lower_Link",
            "Rear_Hitch_R_Lower_Link",
            "Rear_Hitch_Top_Link",
            "PTO_Shaft_ROTATION_ROOT",
            "Front_L_Suspension_Strut",
            "Front_R_Suspension_Strut",
            "Rear_L_Suspension_Strut",
            "Rear_R_Suspension_Strut",
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
        """Replace generic tire geometry without scaled wheel motion nodes."""
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
        front_x, rear_x = self.WHEELBASE_M / 2, -self.WHEELBASE_M / 2
        front_z, rear_z = self.FRONT_TRACK_M / 2, self.REAR_TRACK_M / 2
        generic_rear_radius = min(height * 0.29, length * 0.145)
        generic_front_radius = generic_rear_radius * 0.72

        front_pivot = fleet.bpy.data.objects["Front_Axle_Oscillation_Pivot"]
        front_pivot.location = (front_x, self.FRONT_RADIUS_M, 0)
        front_axle = fleet.bpy.data.objects["Front_Axle_ROOT"]
        fleet.bpy.data.objects["Front_Axle_Beam"].dimensions = (0.28, 0.18, 2.46)
        self.cylinder(
            "Front_Axle_Center_Knuckle", (0, 0, 0), 0.16, 0.42,
            self.materials["graphite"], front_axle, vertices=22,
            rotation=(math.pi / 2, 0, 0), role="differential",
        )
        for side, sign in (("L", -1), ("R", 1)):
            steering = fleet.bpy.data.objects[f"Steering_{side}_Pivot"]
            steering.location = (0, 0, sign * front_z)
            self._rebuild_wheel_geometry(
                f"Front_{side}", self.FRONT_RADIUS_M,
                self.FRONT_WIDTH_M, 16,
            )
            self.box(
                f"Front_{side}_Suspension_Frame_Bracket",
                (front_x - 0.12, 0.87, sign * 0.43),
                (0.34, 0.38, 0.22), self.materials["graphite"],
                self.fixed_root, role="suspension_mount", bevel=0.015,
            )
            self.pipe_between(
                f"Front_{side}_Suspension_Strut", (-0.04, 0.03, sign * 0.56),
                (-0.16, 0.26, sign * 0.43), 0.063 / 2,
                self.materials["rod"], front_axle, role="suspension_strut",
            )

        # Rear suspension owns the complete rear wheel subtrees.
        rear_pivot = self.empty(
            "Rear_Axle_Oscillation_Pivot", (rear_x, self.REAR_RADIUS_M, 0),
            self.running_root, role="pivot",
        )
        rear_axle = self.empty("Rear_Axle_ROOT", parent=rear_pivot, role="motion_root")
        self.box(
            "Rear_Axle_Beam", (0, 0, 0), (0.28, 0.18, 2.53),
            self.materials["steel"], rear_axle, role="axle", bevel=0.015,
        )
        for side, sign in (("L", -1), ("R", 1)):
            wheel_pivot = fleet.bpy.data.objects[f"Rear_{side}_Wheel_Pivot"]
            wheel_pivot.parent = rear_axle
            wheel_pivot.location = (0, 0, sign * rear_z)
            self._rebuild_wheel_geometry(
                f"Rear_{side}", self.REAR_RADIUS_M,
                self.REAR_WIDTH_M, 18,
            )
            self.box(
                f"Rear_Axle_End_Cap_{side}", (0, 0, sign * 1.265),
                (0.12, 0.12, 0.02), self.materials["steel"],
                rear_axle, role="axle_end", bevel=0.004,
            )
            self.box(
                f"Rear_{side}_Suspension_Frame_Bracket",
                (rear_x + 0.12, 0.94, sign * 0.43),
                (0.34, 0.42, 0.22), self.materials["graphite"],
                self.fixed_root, role="suspension_mount", bevel=0.015,
            )
            self.pipe_between(
                f"Rear_{side}_Suspension_Strut", (0.04, 0.03, sign * 0.56),
                (0.16, 0.26, sign * 0.43), 0.063 / 2,
                self.materials["rod"], rear_axle, role="suspension_strut",
            )
        self.cylinder(
            "Rear_Differential_Housing", (0, 0, 0), 0.19, 0.44,
            self.materials["graphite"], rear_axle, vertices=22,
            rotation=(math.pi / 2, 0, 0), role="differential",
        )

        # Exact 0.60 m frame underside and official 3.45 m cab-height datum.
        frame = fleet.bpy.data.objects["Tractor_Main_Frame"]
        frame.location = (0, 0.72, 0)
        frame.dimensions = (4.55, 0.24, 1.18)
        fleet.bpy.data.objects["Operator_Station_ROOT"].location.y = 0.585
        self.box(
            "Published_Height_Roof", (-0.72, height - 0.025, 0),
            (1.18, 0.05, 1.12), self.materials["body"],
            self.fixed_root, role="cab_structure", bevel=0.008,
        )

        # Fenders remain inside the official width envelope and clear the tire
        # carcasses through the reconstructed steering presentation.
        for axle_name, axle_x, radius, wheel_z, fender_width in (
            ("Front", front_x, self.FRONT_RADIUS_M, front_z, 0.44),
            ("Rear", rear_x, self.REAR_RADIUS_M, rear_z, 0.58),
        ):
            for side, sign in (("L", -1), ("R", 1)):
                self.box(
                    f"{axle_name}_{side}_Fender",
                    (axle_x, radius * 2.14, sign * wheel_z),
                    (radius * 1.58, 0.11, fender_width),
                    self.materials["body_dark"], self.fixed_root,
                    role="fender", bevel=0.02,
                )

        # Rebuild both three-point interfaces as closed mount-link-coupler chains.
        for name in (
            "Rear_Hitch_Drawbar",
            "Rear_Hitch_L_Lower_Link",
            "Rear_Hitch_R_Lower_Link",
            "Rear_Hitch_Top_Link",
        ):
            self._remove(name)
        rear_pivot_hitch = fleet.bpy.data.objects["Rear_Hitch_Pivot"]
        rear_pivot_hitch.location = (-2.22, 0.83, 0)
        rear_hitch = fleet.bpy.data.objects["Rear_Hitch_ROOT"]
        self.box(
            "Rear_Hitch_Chassis_Mount", (-2.20, 0.84, 0),
            (0.30, 0.40, 0.98), self.materials["graphite"],
            self.fixed_root, role="hitch_mount", bevel=0.014,
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Rear_Hitch_{side}_Lower_Link", (0.02, 0, sign * 0.26),
                (-0.48, -0.10, sign * 0.34), 0.046,
                self.materials["steel"], rear_hitch, role="hitch_link",
            )
        self.pipe_between(
            "Rear_Hitch_Top_Link", (0.02, 0.19, 0), (-0.48, 0.04, 0),
            0.041, self.materials["steel"], rear_hitch, role="hitch_link",
        )
        self.box(
            "Rear_Hitch_Coupler", (-0.48, -0.06, 0),
            (0.16, 0.34, 0.84), self.materials["graphite"],
            rear_hitch, role="hitch_coupler", bevel=0.012,
        )

        front_hitch_pivot = self.empty(
            "Front_Hitch_Pivot", (2.22, 0.83, 0), self.fixed_root, role="pivot",
        )
        front_hitch = self.empty("Front_Hitch_ROOT", parent=front_hitch_pivot, role="motion_root")
        self.box(
            "Front_Hitch_Chassis_Mount", (2.20, 0.84, 0),
            (0.30, 0.40, 0.98), self.materials["graphite"],
            self.fixed_root, role="hitch_mount", bevel=0.014,
        )
        self.box(
            "Front_Hitch_Crossmember", (0.02, 0, 0),
            (0.20, 0.20, 0.72), self.materials["steel"],
            front_hitch, role="hitch",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Front_Hitch_{side}_Lower_Link", (0.02, 0, sign * 0.26),
                (0.48, -0.10, sign * 0.34), 0.046,
                self.materials["steel"], front_hitch, role="hitch_link",
            )
        self.pipe_between(
            "Front_Hitch_Top_Link", (0.02, 0.19, 0), (0.48, 0.04, 0),
            0.041, self.materials["steel"], front_hitch, role="hitch_link",
        )
        self.box(
            "Front_Hitch_Coupler", (0.48, -0.06, 0),
            (0.16, 0.34, 0.84), self.materials["graphite"],
            front_hitch, role="hitch_coupler", bevel=0.012,
        )

        # Guard remains fixed and connected; shaft alone owns rotary motion.
        pto = fleet.bpy.data.objects["PTO_ROOT"]
        pto.location = (-2.22, 0.84, 0)
        shaft = fleet.bpy.data.objects["PTO_Shaft"]
        shaft.name = "Rear_540E_1000_PTO_Shaft"
        shaft_root = self.empty("PTO_Shaft_ROTATION_ROOT", parent=pto, role="rotary_root")
        shaft.parent = shaft_root
        shaft.location = (-0.10, 0, 0)
        guard = fleet.bpy.data.objects["PTO_Guard"]
        guard.parent = pto
        guard.location = (-0.01, 0, 0)
        self.box(
            "PTO_Frame_Housing", (0, 0, 0), (0.30, 0.32, 0.34),
            self.materials["graphite"], pto, role="pto_housing", bevel=0.016,
        )

        # Connected linkage end structures establish the official X envelope.
        self.box(
            "Front_Linkage_End_Structure", (length / 2 - 0.03, 0.78, 0),
            (0.06, 0.20, 0.88), self.materials["graphite"],
            self.fixed_root, role="hitch", bevel=0.008,
        )
        self.box(
            "Rear_Linkage_End_Structure", (-length / 2 + 0.03, 0.78, 0),
            (0.06, 0.20, 0.88), self.materials["graphite"],
            self.fixed_root, role="hitch", bevel=0.008,
        )
        self.pipe_between(
            "Hydraulic_Manifold_Line", (-1.32, 1.04, -0.35),
            (-0.54, 1.08, -0.35), 0.028,
            self.materials["rod"], self.hydraulics_root, role="hydraulic",
        )
        self.box(
            "Service_Access_Step", (-0.86, 1.16, -0.78),
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
        self.apply_public_modifiers()
        fleet.bpy.context.view_layer.update()
        for pivot_name, root_name in (
            ("Front_Axle_Oscillation_Pivot", "Front_Axle_ROOT"),
            ("Rear_Axle_Oscillation_Pivot", "Rear_Axle_ROOT"),
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
        rear_center = fleet.bpy.data.objects["Rear_Axle_Oscillation_Pivot"].matrix_world.translation
        wheelbase = abs(front_center.x - rear_center.x)
        contacts = {}
        widths = {}
        centers = {}
        wheel_root_scales = {}
        for axle, expected_width, expected_track in (
            ("Front", self.FRONT_WIDTH_M, self.FRONT_TRACK_M),
            ("Rear", self.REAR_WIDTH_M, self.REAR_TRACK_M),
        ):
            centers[axle] = round(abs(
                fleet.bpy.data.objects[f"{axle}_R_Wheel_Pivot"].matrix_world.translation.z
                - fleet.bpy.data.objects[f"{axle}_L_Wheel_Pivot"].matrix_world.translation.z
            ), 6)
            for side in ("L", "R"):
                root_name = f"{axle}_{side}_Wheel_ROOT"
                low, high = self._bounds(self._subtree_meshes(root_name))
                contacts[root_name] = round(low[1], 6)
                wheel_root_scales[root_name] = [
                    round(value, 8)
                    for value in fleet.bpy.data.objects[root_name].scale
                ]
                tire_low, tire_high = self._bounds([f"{axle}_{side}_Tire"])
                widths[f"{axle}_{side}"] = round(tire_high[2] - tire_low[2], 6)

        frame_low, frame_high = self._bounds(["Tractor_Main_Frame"])
        frame_clearance = frame_low[1]
        pto_frame = self._overlap("PTO_Frame_Housing", "Tractor_Main_Frame")
        pto_guard_shaft = self._overlap("PTO_Guard", "Rear_540E_1000_PTO_Shaft")
        linkage_overlaps = {}
        for end in ("Front", "Rear"):
            linkage_overlaps[end] = {
                "mount_frame": [round(v, 6) for v in self._overlap(f"{end}_Hitch_Chassis_Mount", "Tractor_Main_Frame")],
                "left_coupler": [round(v, 6) for v in self._overlap(f"{end}_Hitch_L_Lower_Link", f"{end}_Hitch_Coupler")],
                "right_coupler": [round(v, 6) for v in self._overlap(f"{end}_Hitch_R_Lower_Link", f"{end}_Hitch_Coupler")],
                "top_coupler": [round(v, 6) for v in self._overlap(f"{end}_Hitch_Top_Link", f"{end}_Hitch_Coupler")],
            }

        suspension_mount_overlaps = {}
        for axle in ("Front", "Rear"):
            for side in ("L", "R"):
                key = f"{axle}_{side}"
                suspension_mount_overlaps[key] = [
                    round(value, 6) for value in self._overlap(
                        f"{axle}_{side}_Suspension_Strut",
                        f"{axle}_{side}_Suspension_Frame_Bracket",
                    )
                ]

        viewer = json.loads(VIEWER.read_text(encoding="utf-8"))
        viewer_nodes = {node for channel in viewer["motion"]["channels"] for node in channel["nodes"]}
        suspension_samples = {}
        for root_name, offsets in (("Front_Axle_ROOT", (0.0, 0.02, 0.04)), ("Rear_Axle_ROOT", (0.0, 0.0175, 0.035))):
            root = fleet.bpy.data.objects[root_name]
            original_y = root.location.y
            samples = []
            for offset in offsets:
                root.location.y = original_y + offset
                fleet.bpy.context.view_layer.update()
                low, _ = self._bounds(self._subtree_meshes(root_name))
                samples.append(round(low[1], 6))
            root.location.y = original_y
            suspension_samples[root_name] = samples

        linkage_samples = {}
        for root_name, values in (("Front_Hitch_ROOT", (0.0, 0.06, 0.12)), ("Rear_Hitch_ROOT", (0.0, -0.09, -0.18))):
            root = fleet.bpy.data.objects[root_name]
            original = root.rotation_euler.z
            samples = []
            for angle in values:
                root.rotation_euler.z = angle
                fleet.bpy.context.view_layer.update()
                low, _ = self._bounds(self._subtree_meshes(root_name))
                samples.append(round(low[1], 6))
            root.rotation_euler.z = original
            linkage_samples[root_name] = samples
        fleet.bpy.context.view_layer.update()
        all_low, _ = self._bounds([obj.name for obj in self.public_objects() if obj.type == "MESH"])

        front_fender_clearance = {}
        for side in ("L", "R"):
            _, tire_high = self._bounds([f"Front_{side}_Tire"])
            fender_low, _ = self._bounds([f"Front_{side}_Fender"])
            front_fender_clearance[side] = round(fender_low[1] - tire_high[1], 6)
        rear_inner_half = self.REAR_TRACK_M / 2 - self.REAR_WIDTH_M / 2
        hitch_tire_clearance = rear_inner_half - 0.84 / 2

        return [
            self._gate("authored_static_envelope_and_source_boundary", "decoded GLB AABB plus explicit unresolved-envelope source boundary", {"aabb_xyz_m": size, "authored_target_xyz_m": [self.length, self.height, self.width], "authored_wheelbase_m": round(wheelbase, 6), "authored_ground_clearance_m": round(frame_clearance, 6), "tolerance_m": tolerance, "public_envelope_authority": "unresolved; retired French locator is reference-only"}, ["Front_Linkage_End_Structure", "Rear_Linkage_End_Structure", "Published_Height_Roof", "Tractor_Main_Frame"], [], all(abs(size[index] - expected) <= tolerance for index, expected in enumerate((self.length, self.height, self.width))) and abs(wheelbase - self.WHEELBASE_M) <= tolerance and abs(frame_clearance - self.GROUND_CLEARANCE_M) <= tolerance),
            self._gate("four_tire_contact", "evaluated wheel-subtree ground contact, tire section width, track-center measurement, and identity-transform audit", {"minimum_y_m": contacts, "tire_width_m": widths, "target_width_m": {"Front": self.FRONT_WIDTH_M, "Rear": self.REAR_WIDTH_M}, "track_centers_m": centers, "target_track_centers_m": {"Front": self.FRONT_TRACK_M, "Rear": self.REAR_TRACK_M}, "wheel_root_scale_xyz": wheel_root_scales}, ["Front_L_Wheel_ROOT", "Front_R_Wheel_ROOT", "Rear_L_Wheel_ROOT", "Rear_R_Wheel_ROOT"], [], all(abs(value) <= tolerance for value in contacts.values()) and all(abs(widths[key] - (self.FRONT_WIDTH_M if key.startswith("Front") else self.REAR_WIDTH_M)) <= tolerance for key in widths) and abs(centers["Front"] - self.FRONT_TRACK_M) <= tolerance and abs(centers["Rear"] - self.REAR_TRACK_M) <= tolerance and all(scale == [1.0, 1.0, 1.0] for scale in wheel_root_scales.values())),
            self._gate("rigid_full_length_chassis", "frame AABB and linkage-mount overlap", {"frame_x_span_m": round(frame_high[0] - frame_low[0], 6), "frame_minimum_y_m": round(frame_clearance, 6), "front_mount_overlap_xyz_m": linkage_overlaps["Front"]["mount_frame"], "rear_mount_overlap_xyz_m": linkage_overlaps["Rear"]["mount_frame"]}, ["Tractor_Main_Frame", "Front_Hitch_Chassis_Mount", "Rear_Hitch_Chassis_Mount"], [], frame_high[0] - frame_low[0] >= 4.54 and min(linkage_overlaps["Front"]["mount_frame"] + linkage_overlaps["Rear"]["mount_frame"]) >= 0),
            self._gate("front_rear_suspension_continuity", "wheel-owned axle hierarchy, strut-to-frame AABB attachment, and three-position ground-safe sweep", {"front_wheel_owner": fleet.bpy.data.objects["Front_L_Wheel_Pivot"].parent.parent.name, "rear_wheel_owner": fleet.bpy.data.objects["Rear_L_Wheel_Pivot"].parent.name, "strut_to_frame_bracket_overlap_xyz_m": suspension_mount_overlaps, "minimum_y_samples_m": suspension_samples}, ["Front_Axle_ROOT", "Rear_Axle_ROOT", "Front_L_Suspension_Strut", "Rear_L_Suspension_Strut"], [], fleet.bpy.data.objects["Rear_L_Wheel_Pivot"].parent == fleet.bpy.data.objects["Rear_Axle_ROOT"] and min(value for values in suspension_samples.values() for value in values) >= -tolerance and all(min(values) >= -tolerance for values in suspension_mount_overlaps.values())),
            self._gate("steering_clearance", "tire/fender AABB clearance with exact selected tire and track geometry", {"front_fender_vertical_clearance_m": front_fender_clearance, "steering_range_rad": [-0.24, 0.24], "front_track_m": centers["Front"], "front_tire_width_m": widths["Front_L"]}, ["Steering_L_Pivot", "Steering_R_Pivot", "Front_L_Fender", "Front_R_Fender"], [], min(front_fender_clearance.values()) >= 0.02),
            self._gate("front_rear_linkage_clearance", "three-axis mount-link-coupler overlap plus endpoint ground sweep", {"overlaps_xyz_m": linkage_overlaps, "minimum_y_samples_m": linkage_samples, "rear_coupler_to_inner_tire_clearance_m": round(hitch_tire_clearance, 6), "capacity_facts_bind_selection_not_geometry": True}, ["Front_Hitch_ROOT", "Rear_Hitch_ROOT", "Front_Hitch_Coupler", "Rear_Hitch_Coupler"], ["front-linkage-capacity", "rear-linkage-capacity"], all(min(values) >= 0 for end in linkage_overlaps.values() for values in end.values()) and min(value for values in linkage_samples.values() for value in values) >= -tolerance and hitch_tire_clearance >= 0.10),
            self._gate("ground_collision", "rest AABB plus suspension/linkage endpoint minima", {"rest_minimum_y_m": round(all_low[1], 6), "suspension_minimum_y_m": min(value for values in suspension_samples.values() for value in values), "linkage_minimum_y_m": min(value for values in linkage_samples.values() for value in values)}, ["Front_Axle_ROOT", "Rear_Axle_ROOT", "Front_Hitch_ROOT", "Rear_Hitch_ROOT"], [], all_low[1] >= -tolerance and min(value for values in suspension_samples.values() for value in values) >= -tolerance and min(value for values in linkage_samples.values() for value in values) >= -tolerance),
            self._gate("self_collision", "fixed PTO guard ownership, PTO connection, and central hitch/tire separation", {"pto_housing_frame_overlap_xyz_m": [round(v, 6) for v in pto_frame], "pto_guard_shaft_overlap_xyz_m": [round(v, 6) for v in pto_guard_shaft], "pto_guard_rotates": "PTO_ROOT" in viewer_nodes, "rear_hitch_tire_clearance_m": round(hitch_tire_clearance, 6)}, ["PTO_ROOT", "PTO_Shaft_ROTATION_ROOT", "Rear_Hitch_ROOT", "Rear_Axle_ROOT"], [], min(pto_frame + pto_guard_shaft) >= 0 and "PTO_ROOT" not in viewer_nodes and "PTO_Shaft_ROTATION_ROOT" in viewer_nodes and hitch_tire_clearance >= 0.10),
            self._gate("swept_volume_collision", "combined suspension and linkage endpoint sampling", {"suspension_samples_m": suspension_samples, "linkage_samples_m": linkage_samples, "minimum_sample_m": min([value for values in suspension_samples.values() for value in values] + [value for values in linkage_samples.values() for value in values])}, ["Front_Axle_ROOT", "Rear_Axle_ROOT", "Front_Hitch_ROOT", "Rear_Hitch_ROOT"], [], min([value for values in suspension_samples.values() for value in values] + [value for values in linkage_samples.values() for value in values]) >= -tolerance),
        ]

    def render_views(self):
        self.setup_render_scene()
        camera = fleet.bpy.data.objects["Review_Camera"]
        center = fleet.Vector((0, self.height * 0.46, 0))
        span = max(self.length, self.width, self.height)
        views = [
            ("operator-side", (0, self.height * 0.62, -span * 1.55), span * 1.06),
            ("front-three-quarter", (span * 1.10, self.height * 0.88, -span * 1.02), span * 1.16),
            ("rear-three-quarter", (-span * 1.12, self.height * 0.84, span * 0.98), span * 1.16),
            ("elevated-technical", (span * 0.67, span * 1.46, -span * 0.96), span * 1.25),
            ("articulation-detail", (-span * 0.92, self.height * 0.62, span * 0.72), span * 0.82),
            ("right-side", (0, self.height * 0.62, span * 1.55), span * 1.06),
        ]
        paths = []
        for label, location, ortho_scale in views:
            camera.location = location
            self.point_at(camera, center)
            camera.data.ortho_scale = ortho_scale
            path = self.render_dir / f"{self.machine_id}-{label}.png"
            fleet.bpy.context.scene.render.filepath = str(path)
            fleet.bpy.ops.render.render(write_still=True)
            paths.append(path)
        return paths


if __name__ == "__main__":
    design = fleet.load_design(DESIGN)
    JCBFastrac8330Builder(design, DESIGN, OUTPUT_DIR).run()
