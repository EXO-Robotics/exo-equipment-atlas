#!/usr/bin/env python3
"""Build the neutral MY2025 John Deere 9RX 640 structural study.

The selected 9540RW/JD14/e18/four 762 mm AG3500 belt/2.218 m spacing/
less-PTO/less-hitch configuration is bound to admitted first-party evidence.
Hidden track geometry, frame shapes, joint centers, cylinders, and motion are
independently reconstructed and are not manufacturer CAD or an engineering,
traction, terrain, load, or safety model.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy


HERE = Path(__file__).resolve().parent
MACHINE_DIR = HERE.parents[1]
SHARED_PATH = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN_PATH = (HERE / "../design.json").resolve()

spec = importlib.util.spec_from_file_location("exo_fleet_build_machine_9rx640", SHARED_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load shared fleet builder: {SHARED_PATH}")
fleet = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fleet
spec.loader.exec_module(fleet)


class Deere9RX640Builder(fleet.FleetBuilder):
    BELT_WIDTH_M = 0.762
    TRACK_CENTER_SPACING_M = 2.218
    TRACK_LENGTH_M = 2.360  # reconstructed visible pod envelope
    TRACK_HEIGHT_M = 1.120  # reconstructed visible pod envelope
    TRACK_BOTTOM_Y_M = 0.035
    TRACK_CENTER_Y_M = TRACK_BOTTOM_Y_M + TRACK_HEIGHT_M / 2
    FRONT_TRACK_X_M = 2.10
    REAR_TRACK_X_M = -2.10
    INTERFACE_Y_M = 1.32
    ARTICULATION_REVIEW_LIMIT_RAD = 0.20
    FRAME_ROLL_REVIEW_LIMIT_RAD = 0.006
    POD_PITCH_REVIEW_LIMIT_RAD = 0.006
    DRAWBAR_PIN_DIAMETER_M = 0.070

    def write_machine_wrapper(self):
        """Preserve this checked-in machine-local implementation."""

    def torus(self, name, location, major_radius, minor_radius, material, parent=None,
              rotation=(0, 0, 0), role="geometry", major_segments=24, minor_segments=8):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=major_radius,
            minor_radius=minor_radius,
            major_segments=major_segments,
            minor_segments=minor_segments,
            location=location,
            rotation=rotation,
        )
        obj = bpy.context.object
        obj.name = name
        if parent is not None:
            obj.parent = parent
        obj.data.materials.append(material)
        return self.tag(obj, role=role)

    @staticmethod
    def descendants(obj):
        result = []
        pending = list(obj.children)
        while pending:
            item = pending.pop()
            result.append(item)
            pending.extend(item.children)
        return result

    @staticmethod
    def world_location(obj):
        point = obj.matrix_world.translation
        return [float(point.x), float(point.y), float(point.z)]

    def object_world_bounds(self, obj):
        bpy.context.view_layer.update()
        points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        return {
            "min": [min(float(point[axis]) for point in points) for axis in range(3)],
            "max": [max(float(point[axis]) for point in points) for axis in range(3)],
        }

    def scene_min_y(self):
        bpy.context.view_layer.update()
        minimum = math.inf
        for obj in self.public_objects():
            if obj.type != "MESH":
                continue
            for vertex in obj.data.vertices:
                minimum = min(minimum, float((obj.matrix_world @ vertex.co).y))
        return minimum

    def add_track_pod(self, prefix, center, parent):
        """Author one rigid visual pod around an axle-height pivot, not ground."""
        root = self.empty(f"{prefix}_ROOT", center, parent, role="independent_track_pod_pivot")
        half_l = self.TRACK_LENGTH_M / 2
        half_h = self.TRACK_HEIGHT_M / 2
        pad_length = 0.165
        pad_depth = 0.055
        pad_count = 12
        for surface, y in (("Bottom", -half_h + pad_depth / 2), ("Top", half_h - pad_depth / 2)):
            for index in range(pad_count):
                x = -half_l + pad_length / 2 + index * ((self.TRACK_LENGTH_M - pad_length) / (pad_count - 1))
                self.box(f"{prefix}_Belt_{surface}_{index + 1:02d}", (x, y, 0),
                         (pad_length, pad_depth, self.BELT_WIDTH_M), self.materials["rubber"], root,
                         role="track_pad", bevel=0.012)
        end_count = 6
        for end, x in (("Rear", -half_l + pad_depth / 2), ("Front", half_l - pad_depth / 2)):
            for index in range(end_count):
                y = -half_h + 0.13 + index * ((self.TRACK_HEIGHT_M - 0.26) / (end_count - 1))
                self.box(f"{prefix}_Belt_{end}_{index + 1:02d}", (x, y, 0),
                         (pad_depth, 0.17, self.BELT_WIDTH_M), self.materials["rubber"], root,
                         role="track_pad", bevel=0.012)

        for label, x in (("Rear_Idler", -0.84), ("Drive", 0.84)):
            self.cylinder(f"{prefix}_{label}", (x, 0, 0), 0.39, self.BELT_WIDTH_M * 0.76,
                          self.materials["steel"], root, vertices=28, role="track_wheel")
            self.cylinder(f"{prefix}_{label}_Hub", (x, 0, 0), 0.13, self.BELT_WIDTH_M * 0.82,
                          self.materials["graphite"], root, vertices=20, role="track_hub")
        for index in range(5):
            x = -0.56 + index * 0.28
            self.cylinder(f"{prefix}_Midroller_{index + 1:02d}", (x, -0.24, 0), 0.19,
                          self.BELT_WIDTH_M * 0.68, self.materials["graphite"], root,
                          vertices=20, role="track_midroller")
        self.box(f"{prefix}_Undercarriage_Frame", (0, 0.13, 0), (1.72, 0.20, 0.47),
                 self.materials["graphite"], root, role="track_frame", bevel=0.055)
        self.pipe_between(f"{prefix}_Tension_Link", (-0.72, 0.16, 0), (-0.98, 0.02, 0),
                          0.045, self.materials["rod"], root, role="track_tension_cue")
        return root

    def sampled_ground_clearance(self):
        roll = bpy.data.objects["Chassis_Roll_Pivot"]
        pods = [bpy.data.objects[name] for name in
                ("Track_FL_ROOT", "Track_FR_ROOT", "Track_RL_ROOT", "Track_RR_ROOT")]
        roll_original = tuple(roll.rotation_euler)
        pod_originals = {pod.name: tuple(pod.rotation_euler) for pod in pods}
        samples = []
        for pod in pods:
            for roll_value in (-self.FRAME_ROLL_REVIEW_LIMIT_RAD, self.FRAME_ROLL_REVIEW_LIMIT_RAD):
                for pitch_value in (-self.POD_PITCH_REVIEW_LIMIT_RAD, self.POD_PITCH_REVIEW_LIMIT_RAD):
                    roll.rotation_euler = roll_original
                    roll.rotation_euler.x = roll_value
                    pod.rotation_euler = pod_originals[pod.name]
                    pod.rotation_euler.z = pitch_value
                    samples.append({
                        "roll_rad": roll_value,
                        "pod": pod.name,
                        "pod_pitch_rad": pitch_value,
                        "minimum_y_m": self.scene_min_y(),
                    })
                    pod.rotation_euler = pod_originals[pod.name]
        roll.rotation_euler = roll_original
        for pod in pods:
            pod.rotation_euler = pod_originals[pod.name]
        bpy.context.view_layer.update()
        return samples

    def sampled_track_separation(self):
        yaw = bpy.data.objects["Chassis_Yaw_Pivot"]
        original = tuple(yaw.rotation_euler)
        samples = []
        for value in (-self.ARTICULATION_REVIEW_LIMIT_RAD, 0.0, self.ARTICULATION_REVIEW_LIMIT_RAD):
            yaw.rotation_euler = original
            yaw.rotation_euler.y = value
            bpy.context.view_layer.update()
            fronts = [self.world_location(bpy.data.objects[name]) for name in ("Track_FL_ROOT", "Track_FR_ROOT")]
            rears = [self.world_location(bpy.data.objects[name]) for name in ("Track_RL_ROOT", "Track_RR_ROOT")]
            minimum = min(math.hypot(front[0] - rear[0], front[2] - rear[2])
                          for front in fronts for rear in rears)
            samples.append({"yaw_rad": value, "minimum_track_center_separation_xz_m": minimum})
        yaw.rotation_euler = original
        bpy.context.view_layer.update()
        return samples

    def build_model(self):
        self.build_common_roots()
        body = self.materials["body"]
        dark = self.materials["body_dark"]
        graphite = self.materials["graphite"]
        steel = self.materials["steel"]
        rod = self.materials["rod"]

        rear = self.empty("Rear_Frame_ROOT", parent=self.fixed_root, role="rear_frame_motion_root")
        roll = self.empty("Chassis_Roll_Pivot", (0, self.INTERFACE_Y_M, 0), rear,
                          role="frame_oscillation_pivot")
        yaw = self.empty("Chassis_Yaw_Pivot", parent=roll, role="articulation_yaw_pivot")
        front = self.empty("Front_Frame_ROOT", (0, -self.INTERFACE_Y_M, 0), yaw,
                           role="front_frame_motion_root")

        self.box("Rear_Chassis_Box", (-1.73, 1.20, 0), (3.30, 0.38, 1.22), graphite,
                 rear, role="rear_chassis", bevel=0.08)
        self.box("Rear_Yoke_L", (-0.08, 1.32, -0.42), (0.48, 0.34, 0.22), steel,
                 rear, role="articulation_yoke", bevel=0.045)
        self.box("Rear_Yoke_R", (-0.08, 1.32, 0.42), (0.48, 0.34, 0.22), steel,
                 rear, role="articulation_yoke", bevel=0.045)
        self.box("Front_Yoke_Tongue", (0.11, 1.32, 0), (0.48, 0.28, 0.66), steel,
                 front, role="articulation_tongue", bevel=0.055)
        self.cylinder("Articulation_Vertical_Pin", (0, 1.32, 0), 0.105, 0.70, rod,
                      rear, vertices=28, rotation=(math.pi / 2, 0, 0), role="articulation_pin")
        self.cylinder("Oscillation_Longitudinal_Bearing", (0, 1.32, 0), 0.15, 0.50, graphite,
                      rear, vertices=28, rotation=(0, math.pi / 2, 0), role="oscillation_bearing")

        self.box("Front_Main_Frame", (1.80, 1.18, 0), (3.46, 0.40, 1.25), graphite,
                 front, role="front_chassis", bevel=0.08)
        self.side_profile(
            "JD14_Engine_Hood_Profile",
            [(0.90, 1.32), (3.66, 1.32), (4.00, 1.62), (3.76, 2.38),
             (1.28, 2.50), (0.90, 2.25)],
            1.42, body, front, role="engine_house",
        )
        self.box("Front_Nose_End_Plate", (4.060, 1.08, 0), (0.189, 0.52, 0.94), steel,
                 front, role="front_ballast_carrier", bevel=0.03)
        for index, z in enumerate((-0.36, -0.18, 0.0, 0.18, 0.36), start=1):
            self.box(f"Front_Weight_{index:02d}", (3.97, 1.05, z), (0.30, 0.44, 0.12),
                     graphite, front, role="reconstructed_ballast", bevel=0.012)
        for index in range(12):
            self.box(f"Cooling_Slot_{index + 1:02d}", (3.12 - index * 0.11, 1.78, -0.724),
                     (0.060, 0.48, 0.018), graphite, front, role="cooling_louver", bevel=0.003)
        self.box("JD14_Aftertreatment_Cue", (1.10, 2.35, 0.49), (0.40, 0.82, 0.34),
                 graphite, front, role="aftertreatment_cue", bevel=0.06)
        self.cylinder("Exhaust_Stack", (1.10, 2.96, 0.48), 0.075, 0.54, graphite,
                      front, vertices=20, rotation=(math.pi / 2, 0, 0), role="exhaust")

        cab_floor = 1.46
        cab_height = self.height + self.TRACK_BOTTOM_Y_M - cab_floor
        self.add_cab(0.44, cab_floor, 1.76, 1.78, cab_height, front)
        self.box("Cab_Fender_L", (0.18, 1.75, -1.00), (1.32, 0.19, 0.42), body,
                 front, role="fender", bevel=0.055)
        self.box("Cab_Fender_R", (0.18, 1.75, 1.00), (1.32, 0.19, 0.42), body,
                 front, role="fender", bevel=0.055)

        track_z = self.TRACK_CENTER_SPACING_M / 2
        for axle, frame, x in (("F", front, self.FRONT_TRACK_X_M),
                               ("R", rear, self.REAR_TRACK_X_M)):
            for side, z in (("L", -track_z), ("R", track_z)):
                self.add_track_pod(f"Track_{axle}{side}", (x, self.TRACK_CENTER_Y_M, z), frame)

        # Cross-frame hydraulic cues make the neutral articulation interface
        # legible without pretending to solve changing cylinder endpoints.
        for side, z in (("L", -0.51), ("R", 0.51)):
            self.pipe_between(f"Steering_{side}_Cylinder_Barrel", (-0.42, 1.14, z),
                              (-0.04, 1.18, z), 0.062, graphite, rear, role="hydraulic_barrel")
            self.pipe_between(f"Steering_{side}_Cylinder_Rod", (-0.04, 1.18, z),
                              (0.42, 1.18, z), 0.035, rod, front, role="hydraulic_rod")
        self.box("Hydraulic_Valve_Block", (-0.33, 1.58, 0), (0.32, 0.22, 0.42), steel,
                 self.hydraulics_root, role="hydraulic_valve_block", bevel=0.035)
        for side, z in (("L", -0.18), ("R", 0.18)):
            self.pipe_between(f"Hydraulic_Hose_{side}", (-0.45, 1.60, z),
                              (0.38, 1.62, z), 0.022, self.materials["rubber"],
                              self.hydraulics_root, role="hydraulic_hose")
        self.box("Running_Gear_Center_Bearing_Cue", (0, 0.82, 0), (0.38, 0.24, 0.56),
                 graphite, self.running_root, role="running_gear_interface", bevel=0.055)

        drawbar = self.empty("Drawbar_Pivot", (-3.40, 0.62, 0), rear, role="drawbar_mount")
        self.box("Category_5_Drawbar_Two_Position", (-0.45, 0, 0), (0.609, 0.16, 0.24),
                 steel, drawbar, role="category_5_drawbar", bevel=0.025)
        for label, x in (("Short", -0.57), ("Long", -0.38)):
            self.torus(f"Drawbar_{label}_Position_Ring", (x, 0.085, 0), 0.055, 0.018,
                       graphite, drawbar, rotation=(math.pi / 2, 0, 0), role="drawbar_position")
        self.cylinder("Category_5_70mm_Pin", (-0.57, 0.085, 0), self.DRAWBAR_PIN_DIAMETER_M / 2,
                      0.20, rod, drawbar, vertices=32, rotation=(math.pi / 2, 0, 0), role="drawbar_pin")
        self.box("Drawbar_HD_Support_L", (-0.20, 0.18, -0.18), (0.54, 0.15, 0.11),
                 graphite, drawbar, role="drawbar_support", bevel=0.02)
        self.box("Drawbar_HD_Support_R", (-0.20, 0.18, 0.18), (0.54, 0.15, 0.11),
                 graphite, drawbar, role="drawbar_support", bevel=0.02)

        for index in range(4):
            self.box(f"Access_Step_{index + 1:02d}", (0.20 + index * 0.03, 0.64 + index * 0.18, -0.99),
                     (0.38, 0.055, 0.34), steel, self.detail_root,
                     role="access_step", bevel=0.008)
        self.pipe_between("Cab_Left_Handrail", (-0.18, 1.25, -0.93), (0.44, 2.12, -0.93),
                          0.026, steel, self.detail_root, role="handrail")

        missing = [name for name in self.required_semantics() if bpy.data.objects.get(name) is None]
        if missing:
            raise RuntimeError(f"9RX 640 builder omitted semantic nodes: {', '.join(missing)}")
        return self.root

    def machine_specific_validation_gates(self, contract):
        config = json.loads((self.output_dir / "configuration.json").read_text(encoding="utf-8"))
        bounds = contract["bounds"]
        track_names = ("Track_FL_ROOT", "Track_FR_ROOT", "Track_RL_ROOT", "Track_RR_ROOT")
        tracks = [bpy.data.objects[name] for name in track_names]
        centers = {track.name: self.world_location(track) for track in tracks}
        front_spacing = abs(centers["Track_FR_ROOT"][2] - centers["Track_FL_ROOT"][2])
        rear_spacing = abs(centers["Track_RR_ROOT"][2] - centers["Track_RL_ROOT"][2])
        belt_bounds = self.object_world_bounds(bpy.data.objects["Track_FL_Belt_Bottom_01"])
        belt_width = belt_bounds["max"][2] - belt_bounds["min"][2]
        roll = bpy.data.objects["Chassis_Roll_Pivot"]
        yaw = bpy.data.objects["Chassis_Yaw_Pivot"]
        front = bpy.data.objects["Front_Frame_ROOT"]
        ground_samples = self.sampled_ground_clearance()
        min_ground = min(sample["minimum_y_m"] for sample in ground_samples)
        separation_samples = self.sampled_track_separation()
        min_track_separation = min(sample["minimum_track_center_separation_xz_m"] for sample in separation_samples)
        node_names = set(contract["node_names"])
        forbidden = sorted(name for name in node_names if "pto" in name.lower() or "hitch" in name.lower())
        material_names = sorted(material.name for material in bpy.data.materials)
        width_unresolved = any("overall width" in item.lower() for item in config["unresolved_choices"])
        height_unresolved = any("height" in item.lower() and "unresolved" in item.lower()
                                for item in config["unresolved_choices"])
        expected_outer_width = self.TRACK_CENTER_SPACING_M + self.BELT_WIDTH_M

        gates = [
            {"id": "published_length_envelope", "status": "PASS" if abs(bounds["size_m"][0] - 8.309) <= 0.003 else "FAIL",
             "detail": {"measured_m": bounds["size_m"][0], "published_m": 8.309,
                        "tolerance_m": 0.003, "source_id": "JD-9RX640-CA-PAGE",
                        "source_market": "Canada", "declared_market": "North America",
                        "dimension_scope": "overall length with front weights, excluding three-point hitch and coupler",
                        "selected_rear_interface": "code 4000 less hitch/coupler with Category 5 drawbar"}},
            {"id": "overall_width_unresolved", "status": "PASS" if width_unresolved else "FAIL",
             "detail": {"manufacturer_overall_width_claim": None, "derived_belt_outer_width_m": expected_outer_width,
                        "configuration_records_unresolved": width_unresolved}},
            {"id": "overall_height_unresolved", "status": "PASS" if height_unresolved else "FAIL",
             "detail": {"manufacturer_overall_height_claim": None, "presentation_height_m": bounds["size_m"][1],
                        "configuration_records_unresolved": height_unresolved}},
            {"id": "four_track_identity",
             "status": "PASS" if len(tracks) == 4 and all(len(self.descendants(track)) >= 38 for track in tracks) else "FAIL",
             "detail": {"track_roots": list(track_names),
                        "descendant_counts": {track.name: len(self.descendants(track)) for track in tracks}}},
            {"id": "track_spacing_and_belt_width",
             "status": "PASS" if abs(front_spacing - self.TRACK_CENTER_SPACING_M) <= 0.001 and
                       abs(rear_spacing - self.TRACK_CENTER_SPACING_M) <= 0.001 and
                       abs(belt_width - self.BELT_WIDTH_M) <= 0.001 and
                       abs(bounds["size_m"][2] - expected_outer_width) <= 0.003 else "FAIL",
             "detail": {"front_center_spacing_m": front_spacing, "rear_center_spacing_m": rear_spacing,
                        "published_center_spacing_m": self.TRACK_CENTER_SPACING_M,
                        "measured_belt_width_m": belt_width, "published_belt_width_m": self.BELT_WIDTH_M,
                        "measured_outer_width_m": bounds["size_m"][2], "derived_outer_width_m": expected_outer_width}},
            {"id": "articulation_continuity",
             "status": "PASS" if yaw.parent is roll and front.parent is yaw and
                       all(abs(value) <= 0.001 for value in self.world_location(yaw)[:1]) else "FAIL",
             "detail": {"hierarchy": [roll.name, yaw.name, front.name],
                        "pivot_world_m": self.world_location(yaw), "review_limit_rad": self.ARTICULATION_REVIEW_LIMIT_RAD,
                        "cross_market_reference_deg": 36,
                        "reference_market": "Australia and New Zealand",
                        "applicable_to_selected_na_configuration": False,
                        "steering_cylinder_cues": 2}},
            {"id": "frame_oscillation_continuity",
             "status": "PASS" if yaw.parent is roll and abs(self.world_location(roll)[0]) <= 0.001 else "FAIL",
             "detail": {"roll_pivot_world_m": self.world_location(roll), "axis": "+X",
                        "review_limit_rad": self.FRAME_ROLL_REVIEW_LIMIT_RAD,
                        "cross_market_reference_deg": 15,
                        "reference_market": "Australia and New Zealand",
                        "applicable_to_selected_na_configuration": False,
                        "cross_market_angle_convention": "unresolved"}},
            {"id": "independent_track_pod_continuity",
             "status": "PASS" if all(track.get("exo_role") == "independent_track_pod_pivot" and
                       len(self.descendants(track)) >= 38 for track in tracks) else "FAIL",
             "detail": {"independent_roots": list(track_names),
                        "pivot_height_m": self.TRACK_CENTER_Y_M,
                        "cross_market_reference_deg": [-10, 10],
                        "reference_market": "Australia and New Zealand",
                        "applicable_to_selected_na_configuration": False,
                        "flat-ground_review_pitch_rad": self.POD_PITCH_REVIEW_LIMIT_RAD}},
            {"id": "less_pto_less_hitch_configuration", "status": "PASS" if not forbidden else "FAIL",
             "detail": {"selected_rear_pto": "less PTO", "selected_rear_hitch": "less hitch",
                        "forbidden_export_nodes": forbidden}},
            {"id": "ground_collision", "status": "PASS" if min_ground >= -0.002 else "FAIL",
             "detail": {"minimum_sampled_y_m": min_ground, "sample_count": len(ground_samples),
                        "sampled_roll_rad": self.FRAME_ROLL_REVIEW_LIMIT_RAD,
                        "sampled_pod_pitch_rad": self.POD_PITCH_REVIEW_LIMIT_RAD,
                        "terrain_solver": False, "tolerance_m": 0.002}},
            {"id": "self_collision", "status": "PASS" if min_track_separation > self.TRACK_LENGTH_M else "FAIL",
             "detail": {"articulation_samples": separation_samples,
                        "minimum_track_center_separation_xz_m": min_track_separation,
                        "reconstructed_track_length_m": self.TRACK_LENGTH_M,
                        "scope": "track-to-track clearance over the declared viewer articulation range"}},
            {"id": "neutral_unbranded_material_review",
             "status": "PASS" if all(name.startswith("Neutral_") for name in material_names) and
                       contract["images"] == 0 and contract["textures"] == 0 else "FAIL",
             "detail": {"materials": material_names, "embedded_images": contract["images"],
                        "textures": contract["textures"], "logos_or_decals": 0}},
        ]
        proof_contract = {
            "published_length_envelope": ("GLB accessor AABB compared with the official Canadian 9RX 640 length with front weights and without three-point hitch/coupler; selected Category 5 drawbar remains present", ["Front_Nose_End_Plate", "Category_5_Drawbar_Two_Position"], ["public-envelope-x"]),
            "overall_width_unresolved": ("configuration unresolved-choice inspection plus published belt arithmetic", [], []),
            "overall_height_unresolved": ("configuration unresolved-choice inspection", [], []),
            "four_track_identity": ("exact semantic-root census and descendant traversal", ["Track_FL_ROOT", "Track_FR_ROOT", "Track_RL_ROOT", "Track_RR_ROOT"], ["selected-track-width", "selected-track-spacing"]),
            "track_spacing_and_belt_width": ("world-transform center spacing, belt-pad vertex AABB, and outer GLB AABB", ["Track_FL_ROOT", "Track_FR_ROOT", "Track_RL_ROOT", "Track_RR_ROOT", "Track_FL_Belt_Bottom_01"], ["selected-track-width", "selected-track-spacing"]),
            "articulation_continuity": ("direct roll-yaw-front parent chain and interface-pivot transform, compared only to a cross-market reference", ["Chassis_Roll_Pivot", "Chassis_Yaw_Pivot", "Front_Frame_ROOT", "Rear_Frame_ROOT"], []),
            "frame_oscillation_continuity": ("direct coaxial roll/yaw hierarchy and world pivot transform, compared only to a cross-market reference", ["Chassis_Roll_Pivot", "Chassis_Yaw_Pivot", "Front_Frame_ROOT"], []),
            "independent_track_pod_continuity": ("distinct pod-root role and descendant checks, compared only to a cross-market reference", ["Track_FL_ROOT", "Track_FR_ROOT", "Track_RL_ROOT", "Track_RR_ROOT"], []),
            "less_pto_less_hitch_configuration": ("case-insensitive exported-node forbidden-interface census", ["Drawbar_Pivot", "Category_5_Drawbar_Two_Position"], ["less-pto-base", "less-hitch-base", "category-five-drawbar-interface"]),
            "ground_collision": ("combined roll and per-pod pitch world-vertex minimum-Y sampling", ["Chassis_Roll_Pivot", "Track_FL_ROOT", "Track_FR_ROOT", "Track_RL_ROOT", "Track_RR_ROOT"], []),
            "self_collision": ("track-center XZ separation sampling over declared articulation extrema", ["Chassis_Yaw_Pivot", "Track_FL_ROOT", "Track_FR_ROOT", "Track_RL_ROOT", "Track_RR_ROOT"], []),
            "neutral_unbranded_material_review": ("material-name allowlist plus exported GLB image/texture census", [], []),
        }
        for gate in gates:
            method, semantic_nodes, fact_ids = proof_contract[gate["id"]]
            gate["detail"] = {
                "method": method,
                "evidence": gate["detail"],
                "semantic_nodes": semantic_nodes,
                "fact_ids": fact_ids,
            }
        return gates


def main():
    design = fleet.load_design(DESIGN_PATH)
    Deere9RX640Builder(design, DESIGN_PATH, MACHINE_DIR).run()


if __name__ == "__main__":
    main()
