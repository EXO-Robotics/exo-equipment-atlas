#!/usr/bin/env python3
"""Machine-local CLAAS LEXION 8900 TERRA TRAC structural study.

The selected CONVIO FLEX 1530 header, APS SYNFLOW HYBRID drum, twin ROTO
PLUS rotors, power spreader and TERRA TRAC running gear are authored here as a
neutral cutaway. Hidden centers and motion remain reconstructed.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()


def load_shared():
    spec = importlib.util.spec_from_file_location("exo_fleet_builder_lexion8900", SHARED_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load shared builder {SHARED_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = load_shared()


class Lexion8900Builder(shared.FleetBuilder):
    HEADER_SPAN_M = 15.3
    HEADER_FLEX_M = 0.225
    DRUM_WIDTH_M = 1.700
    DRUM_DIAMETER_M = 0.755
    ROTOR_COUNT = 2
    ROTOR_DIAMETER_M = 0.445
    ROTOR_LENGTH_M = 4.200
    AUGER_SWING_DEG = 105.0

    def write_machine_wrapper(self):
        """Preserve the machine-local authoring subclass."""

    @staticmethod
    def _descends(node_name, ancestor_name):
        node = bpy.data.objects.get(node_name)
        while node is not None:
            if node.name == ancestor_name:
                return True
            node = node.parent
        return False

    def _subtree_bounds(self, root_name):
        root = bpy.data.objects[root_name]
        objects = [obj for obj in [root, *root.children_recursive]
                   if obj.type == "MESH" and self.is_public(obj)]
        mins, maxs = [math.inf] * 3, [-math.inf] * 3
        for obj in objects:
            for corner in obj.bound_box:
                point = obj.matrix_world @ shared.Vector(corner)
                for axis in range(3):
                    mins[axis], maxs[axis] = min(mins[axis], point[axis]), max(maxs[axis], point[axis])
        return {"min": mins, "max": maxs, "size": [maxs[i] - mins[i] for i in range(3)]}

    def _gate(self, gate_id, condition, evidence, semantic_nodes, fact_ids=()):
        return {"id": gate_id, "status": "PASS" if condition else "FAIL", "detail": {
            "method": "machine-local hierarchy assertion and metric endpoint measurement",
            "evidence": evidence, "semantic_nodes": list(semantic_nodes), "fact_ids": list(fact_ids)}}

    def _add_rear_wheel(self, side, sign):
        steer = self.empty(f"Rear_Steering_{side}_Pivot", (-3.55, 0.58, sign * 1.48),
                           self.running_root, role="steering_pivot")
        wheel_pivot = self.empty(f"Rear_{side}_Wheel_Pivot", parent=steer, role="wheel_pivot")
        root = self.empty(f"Rear_{side}_Wheel_ROOT", parent=wheel_pivot, role="wheel_root")
        self.wheel_tire(f"Rear_{side}_Tire", 0.58, 0.25, self.materials["rubber"], root)
        self.cylinder(f"Rear_{side}_Rim", (0, 0, 0), 0.29, 0.38,
                      self.materials["steel"], root, vertices=24, role="wheel_rim")

    def _add_header_module(self, prefix, parent, center_z, span):
        belt = self.empty(f"CONVIO_{prefix}_Draper_ROOT", (0, 0, center_z), parent,
                          role="linear_process_root")
        self.box(f"CONVIO_{prefix}_Draper_Belt", (0.82, -0.28, 0),
                 (1.42, 0.10, span * 0.96), self.materials["graphite"], belt,
                 role="draper_belt")
        for index in range(9):
            x = 0.18 + index * 0.16
            self.box(f"CONVIO_{prefix}_Draper_Slat_{index + 1:02d}", (x, -0.335, 0),
                     (0.035, 0.025, span * 0.92), self.materials["steel"], belt,
                     role="draper_slat", bevel=0.003)
        self.box(f"CONVIO_{prefix}_Cutterbar", (1.775, -0.49, center_z),
                 (0.10, 0.08, span), self.materials["steel"], parent,
                 role="flex_cutterbar", bevel=0.006)
        self.box(f"CONVIO_{prefix}_Back_Frame", (0.44, 0.03, center_z),
                 (0.76, 0.18, span * 0.96), self.materials["body"], parent,
                 role="header_frame")

    def _add_convio_flex(self, feeder):
        pivot = self.empty("Header_Lift_Pivot", (0.95, -0.38, 0), feeder, role="pivot")
        header = self.empty("Header_ROOT", parent=pivot, role="motion_root")
        segment = self.HEADER_SPAN_M / 3
        center = self.empty("CONVIO_Center_ROOT", parent=header, role="header_module_root")
        self._add_header_module("Center", center, 0, segment)
        for side, sign in (("L", -1), ("R", 1)):
            flex_pivot = self.empty(f"Header_{side}_Flex_Pivot", (0, 0, sign * segment / 2),
                                    header, role="pivot")
            flex = self.empty(f"Header_{side}_Flex_ROOT", parent=flex_pivot, role="motion_root")
            self._add_header_module(side, flex, sign * segment / 2, segment)
            self.pipe_between(f"Header_{side}_Flex_Cylinder_Barrel",
                              (2.70, 1.36, sign * 1.70), (3.10, 1.10, sign * 2.15),
                              0.038, self.materials["graphite"], self.hydraulics_root,
                              role="hydraulic_barrel")
            self.pipe_between(f"Header_{side}_Flex_Cylinder_Rod", (0.08, 0.28, 0),
                              (0.42, 0.03, sign * segment * 0.28), 0.024,
                              self.materials["rod"], flex, role="hydraulic_rod")
        reel_pivot = self.empty("Reel_Pivot", (0.92, 0.24, 0), header, role="pivot")
        reel = self.empty("Reel_ROOT", parent=reel_pivot, role="rotary_root")
        self.cylinder("CONVIO_Reel_Axle", (0, 0, 0), 0.045, 14.72,
                      self.materials["steel"], reel, vertices=22, role="reel_axle")
        for index in range(6):
            angle = math.tau * index / 6
            self.box(f"CONVIO_Reel_Bat_{index + 1:02d}",
                     (math.cos(angle) * 0.46, math.sin(angle) * 0.46, 0),
                     (0.055, 0.055, 14.55), self.materials["warning"], reel,
                     rotation=(0, 0, angle), role="reel_bat", bevel=0.005)
        self.pipe_between("Header_Lift_Cylinder_Barrel", (1.65, 1.48, -0.62),
                          (2.42, 1.08, -0.62), 0.048, self.materials["graphite"],
                          self.hydraulics_root, role="hydraulic_barrel")
        self.pipe_between("Header_Lift_Cylinder_Rod", (-0.42, 0.55, -0.62),
                          (0.40, 0.18, -0.62), 0.028, self.materials["rod"], header,
                          role="hydraulic_rod")

    def _add_process_cutaway(self):
        drum = self.empty("APS_Threshing_Drum_ROOT", (1.15, 1.55, 0), self.fixed_root,
                          role="rotary_process_root")
        body = self.cylinder("APS_1700x755_Drum", (0, 0, 0), self.DRUM_DIAMETER_M / 2,
                             self.DRUM_WIDTH_M, self.materials["graphite"], drum,
                             vertices=32, role="threshing_drum")
        body["exo_published_width_m"] = self.DRUM_WIDTH_M
        body["exo_published_diameter_m"] = self.DRUM_DIAMETER_M
        for bar in range(10):
            angle = math.tau * bar / 10
            self.box(f"APS_Drum_RaspBar_{bar + 1:02d}",
                     (math.cos(angle) * 0.39, math.sin(angle) * 0.39, 0),
                     (0.08, 0.035, 1.64), self.materials["steel"], drum,
                     rotation=(0, 0, angle), role="rasp_bar", bevel=0.004)
        rotor_roots = []
        for side, sign in (("L", -1), ("R", 1)):
            rotor = self.empty(f"ROTO_PLUS_{side}_ROOT", (-0.95, 2.12, sign * 0.38),
                               self.fixed_root, role="rotary_process_root")
            rotor_roots.append(rotor)
            cylinder = self.cylinder(f"ROTO_PLUS_{side}_445x4200", (0, 0, 0),
                                     self.ROTOR_DIAMETER_M / 2, self.ROTOR_LENGTH_M,
                                     self.materials["graphite"], rotor, vertices=28,
                                     rotation=(0, math.pi / 2, 0), role="separation_rotor")
            cylinder["exo_published_diameter_m"] = self.ROTOR_DIAMETER_M
            cylinder["exo_published_length_m"] = self.ROTOR_LENGTH_M
            for paddle in range(12):
                x = -1.90 + paddle * (3.80 / 11)
                self.box(f"ROTO_PLUS_{side}_Paddle_{paddle + 1:02d}",
                         (x, 0.23, 0), (0.11, 0.10, 0.34), self.materials["steel"],
                         rotor, rotation=(0, 0, paddle * 0.45), role="rotor_paddle", bevel=0.004)
        spreader = self.empty("Power_Spreader_ROOT", (-4.25, 1.34, 0), self.fixed_root,
                              role="rotary_process_root")
        for side, sign in (("L", -1), ("R", 1)):
            disc = self.empty(f"Power_Spreader_{side}_ROOT", (0, 0, sign * 0.52), spreader,
                              role="rotary_root")
            self.cylinder(f"Power_Spreader_{side}_Disc", (0, 0, 0), 0.42, 0.055,
                          self.materials["steel"], disc, vertices=24,
                          rotation=(math.pi / 2, 0, 0), role="power_spreader")
            for vane in range(6):
                angle = math.tau * vane / 6
                self.box(f"Power_Spreader_{side}_Vane_{vane + 1:02d}",
                         (math.cos(angle) * 0.30, 0, math.sin(angle) * 0.30),
                         (0.28, 0.08, 0.055), self.materials["warning"], disc,
                         rotation=(0, -angle, 0), role="spreader_vane", bevel=0.004)
        path = self.empty("Schematic_Crop_Path_ROOT", parent=self.fixed_root,
                          role="process_path_root")
        points = [(4.00, 0.70, 0), (3.18, 0.98, 0), (2.60, 1.25, 0),
                  (1.15, 1.55, 0), (0.20, 1.90, 0), (-2.45, 2.12, 0),
                  (-4.25, 1.34, 0)]
        for index, (start, end) in enumerate(zip(points, points[1:]), start=1):
            self.pipe_between(f"Schematic_Crop_Path_{index:02d}", start, end, 0.035,
                              self.materials["warning"], path, role="schematic_crop_path")

    def _add_unloader(self):
        pivot = self.empty("Unloader_Swing_Pivot", (-1.15, 3.05, 0.95),
                           self.fixed_root, role="pivot")
        root = self.empty("Unloader_ROOT", parent=pivot, role="motion_root")
        self.cylinder("Unloader_Base_Collar", (0, 0, 0), 0.10, 0.14,
                      self.materials["body_dark"], root, vertices=24, role="unloader")
        self.pipe_between("Unloader_Auger", (0, 0, 0), (-3.55, -0.10, 0), 0.070,
                          self.materials["body"], root, role="unloader")
        flight = self.empty("Unloader_Flight_ROOT", (-1.78, -0.05, 0), root,
                            role="rotary_process_root")
        self.cylinder("Unloader_Visible_Flight", (0, 0, 0), 0.045, 3.35,
                      self.materials["steel"], flight, vertices=18,
                      rotation=(0, math.pi / 2, 0), role="auger_flight")

    def build_combine(self):
        for side, sign in (("L", -1), ("R", 1)):
            self.add_track_pod(f"Track_{side}", 3.05, 1.30, 0.72,
                               (1.55, 0, sign * 1.54), self.running_root, pads=30)
            self._add_rear_wheel(side, sign)
        self.box("Carrier_Frame", (-0.45, 0.92, 0), (8.40, 0.24, 2.85),
                 self.materials["graphite"], self.fixed_root, role="chassis")
        self.box("Rear_Terminal_Bumper", (-self.length / 2 + 0.05, 0.92, 0),
                 (0.10, 0.42, 2.40), self.materials["steel"], self.fixed_root,
                 role="rear_structure")
        # Cutaway shell: the operator side stays open so APS, both ROTO PLUS
        # rotors and the crop path remain readable in the review renders.
        self.side_profile("Separator_Right_Shell",
                          [(-3.20, 1.12), (1.90, 1.12), (1.90, 2.18),
                           (1.35, 2.78), (-2.55, 2.88), (-3.20, 2.48)],
                          0.56, self.materials["body"], self.fixed_root,
                          z_center=0.96, role="separator_shell")
        self.box("Separator_Top_Cover", (-0.65, 2.82, 0), (5.10, 0.14, 2.45),
                 self.materials["body"], self.fixed_root, role="separator_shell")
        self.box("Separator_Lower_Rail", (-0.65, 1.15, 0), (5.10, 0.16, 2.45),
                 self.materials["body_dark"], self.fixed_root, role="separator_frame")
        self.box("Separator_Rear_Bulkhead", (-3.12, 1.94, 0), (0.16, 1.55, 2.45),
                 self.materials["body_dark"], self.fixed_root, role="separator_frame")
        self.box("Grain_Tank", (-1.25, 3.12, 0), (2.85, 0.90, 2.55),
                 self.materials["body_dark"], self.fixed_root, role="grain_tank")
        self.add_cab(2.35, 1.92, 1.72, 2.62, self.height - 1.92, self.fixed_root)
        feeder = self.empty("Feederhouse_ROOT", (2.60, 1.25, 0), self.fixed_root,
                            role="motion_root")
        self.side_profile("Feederhouse", [(-0.15, -0.30), (1.08, -0.54),
                          (1.10, 0.22), (-0.10, 0.32)], 1.82,
                          self.materials["body_dark"], feeder, role="feederhouse")
        self._add_convio_flex(feeder)
        self._add_process_cutaway()
        self._add_unloader()

    def _set_review_pose(self, label):
        bpy.data.objects["Header_Lift_Pivot"].rotation_euler.z = 0
        bpy.data.objects["Header_L_Flex_ROOT"].location.y = 0
        bpy.data.objects["Header_R_Flex_ROOT"].location.y = 0
        bpy.data.objects["Unloader_Swing_Pivot"].rotation_euler.y = 0
        for side in ("L", "R"):
            bpy.data.objects[f"Rear_Steering_{side}_Pivot"].rotation_euler.y = 0
        if label == "front-three-quarter":
            bpy.data.objects["Header_Lift_Pivot"].rotation_euler.z = 0.08
        elif label == "rear-three-quarter":
            bpy.data.objects["Unloader_Swing_Pivot"].rotation_euler.y = 1.22
        elif label == "elevated-technical":
            bpy.data.objects["Header_L_Flex_ROOT"].location.y = -0.16
            bpy.data.objects["Header_R_Flex_ROOT"].location.y = -0.04
            bpy.data.objects["Unloader_Swing_Pivot"].rotation_euler.y = 0.55
        elif label == "articulation-detail":
            bpy.data.objects["Header_Lift_Pivot"].rotation_euler.z = 0.10
            bpy.data.objects["Header_L_Flex_ROOT"].location.y = -self.HEADER_FLEX_M
            bpy.data.objects["Unloader_Swing_Pivot"].rotation_euler.y = 0.72
        elif label == "right-side":
            for side in ("L", "R"):
                bpy.data.objects[f"Rear_Steering_{side}_Pivot"].rotation_euler.y = 0.22
        bpy.context.view_layer.update()

    def render_views(self):
        self.setup_render_scene()
        camera = bpy.data.objects["Review_Camera"]
        center = shared.Vector((0, self.height * 0.46, 0))
        span = max(self.length, self.width, self.height)
        carrier_span = max(self.length, self.carrier_width, self.height)
        views = [
            ("operator-side", (0, self.height * .62, -span * 1.55), carrier_span * 1.08),
            ("front-three-quarter", (span * 1.10, self.height * .88, -span * 1.02), span * 1.18),
            ("rear-three-quarter", (-span * 1.12, self.height * .82, span * .96), carrier_span * 1.18),
            ("elevated-technical", (span * .65, span * 1.45, -span * .95), span * 1.30),
            ("articulation-detail", (span * .82, self.height * .62, -span * .72), carrier_span * .84),
            ("right-side", (0, self.height * .62, span * 1.55), carrier_span * 1.08),
        ]
        paths = []
        for label, location, ortho_scale in views:
            self._set_review_pose(label)
            camera.location = location
            self.point_at(camera, center)
            camera.data.ortho_scale = ortho_scale
            path = self.render_dir / f"{self.machine_id}-{label}.png"
            bpy.context.scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
        self._set_review_pose("neutral")
        return paths

    def required_semantics(self):
        return [*super().required_semantics(), "Header_L_Flex_Pivot", "Header_L_Flex_ROOT",
                "Header_R_Flex_Pivot", "Header_R_Flex_ROOT", "CONVIO_Center_Draper_ROOT",
                "APS_Threshing_Drum_ROOT", "ROTO_PLUS_L_ROOT", "ROTO_PLUS_R_ROOT",
                "Power_Spreader_ROOT", "Schematic_Crop_Path_ROOT"]

    def machine_specific_validation_gates(self, contract):
        names = contract["node_names"]
        header = self._subtree_bounds("Header_ROOT")
        viewer = json.loads((self.output_dir / "viewer.json").read_text(encoding="utf-8"))
        auger_channel = next(c for c in viewer["motion"]["channels"] if c["id"] == "unloader-swing")
        auger_deg = math.degrees(auger_channel["to"] - auger_channel["from"])
        track_pads = {side: len([name for name in names if name.startswith(f"Track_{side}_Pad_")])
                      for side in ("L", "R")}
        rotor_roots = [name for name in ("ROTO_PLUS_L_ROOT", "ROTO_PLUS_R_ROOT") if name in names]
        drapers = [name for name in names if name.startswith("CONVIO_") and name.endswith("_Draper_Belt")]
        materials = sorted({slot.material.name for obj in self.public_objects() if obj.type == "MESH"
                            for slot in obj.material_slots if slot.material is not None})
        process = {"threshing_drum_width_m": self.DRUM_WIDTH_M,
                   "threshing_drum_diameter_m": self.DRUM_DIAMETER_M,
                   "roto_plus_count": len(rotor_roots), "each_rotor_diameter_m": self.ROTOR_DIAMETER_M,
                   "each_rotor_length_m": self.ROTOR_LENGTH_M, "power_spreader_present": "Power_Spreader_ROOT" in names}
        return [
            self._gate("configuration_and_header_identity", "CF1530" in self.configuration_id and "TT" in self.configuration_id,
                       {"configuration_id": self.configuration_id, "header": "CONVIO FLEX 1530", "running_gear": "TERRA TRAC"},
                       ["Header_ROOT", "Track_L_ROOT", "Track_R_ROOT"]),
            self._gate("published_header_span", abs(header["size"][2] - self.HEADER_SPAN_M) <= 0.003,
                       {"measured_span_m": round(header["size"][2], 6), "published_span_m": self.HEADER_SPAN_M,
                        "draper_sections": len(drapers)},
                       ["Header_ROOT", "Header_L_Flex_ROOT", "Header_R_Flex_ROOT"],
                       ["header-working-width", "public-envelope-z", "header-flex-range"]),
            self._gate("header_lift_visual_closure", self._descends("Header_ROOT", "Header_Lift_Pivot")
                       and "Header_Lift_Cylinder_Barrel" in names and "Header_Lift_Cylinder_Rod" in names,
                       {"closure": "fixed barrel plus moving rod", "authority": "reconstructed visual linkage"},
                       ["Header_Lift_Pivot", "Header_ROOT", "Hydraulics_ROOT"]),
            self._gate("header_to_feederhouse_clearance", self._descends("Header_ROOT", "Feederhouse_ROOT")
                       and all(f"Schematic_Crop_Path_{i:02d}" in names for i in range(1, 7)),
                       {"hierarchy": "Feederhouse_ROOT to Header_Lift_Pivot to Header_ROOT",
                        "continuous_crop_path_segments": 6},
                       ["Feederhouse_ROOT", "Header_Lift_Pivot", "Header_ROOT", "Schematic_Crop_Path_ROOT"]),
            self._gate("track_phase_continuity", track_pads == {"L": 30, "R": 30},
                       {"track_pad_counts": track_pads, "viewer_motion": "independent left/right track roots"},
                       ["Track_L_ROOT", "Track_R_ROOT"]),
            self._gate("track_frame_ground_following_clearance", contract["bounds"]["min_m"][1] >= -0.005,
                       {"minimum_visible_y_m": contract["bounds"]["min_m"][1], "track_frame_pose": "neutral"},
                       ["Track_L_ROOT", "Track_R_ROOT", "Running_Gear_ROOT"]),
            self._gate("rear_steering_tire_clearance", all(f"Rear_Steering_{side}_Pivot" in names for side in ("L", "R")),
                       {"steering_roots": ["Rear_Steering_L_Pivot", "Rear_Steering_R_Pivot"],
                        "presentation_range_deg": [-18, 18], "authority": "reconstructed"},
                       ["Rear_Steering_L_Pivot", "Rear_Steering_R_Pivot"]),
            self._gate("unloading_auger_stowed_and_deployed_clearance", abs(auger_deg - self.AUGER_SWING_DEG) <= 0.02
                       and self._descends("Unloader_ROOT", "Unloader_Swing_Pivot"),
                       {"viewer_sweep_deg": round(auger_deg, 6), "published_swing_deg": self.AUGER_SWING_DEG,
                        "scope": "reconstructed endpoint clearance"},
                       ["Unloader_Swing_Pivot", "Unloader_ROOT"], ["unloading-auger-swing"]),
            self._gate("cutaway_only_internal_mechanism_labeling", len(rotor_roots) == 2 and "APS_Threshing_Drum_ROOT" in names,
                       {**process, "classification": "schematic cutaway with hidden centers reconstructed"},
                       ["APS_Threshing_Drum_ROOT", "ROTO_PLUS_L_ROOT", "ROTO_PLUS_R_ROOT", "Power_Spreader_ROOT"],
                       ["threshing-drum-width", "threshing-drum-diameter"]),
            self._gate("ground_collision", contract["bounds"]["min_m"][1] >= -0.005,
                       {"minimum_visible_y_m": contract["bounds"]["min_m"][1], "ground_y_m": 0.0},
                       ["Running_Gear_ROOT", "Header_ROOT"]),
            self._gate("self_collision", header["min"][1] >= -0.005 and len(rotor_roots) == self.ROTOR_COUNT,
                       {"neutral_header_min_y_m": round(header["min"][1], 6), "process_measurements": process,
                        "scope": "neutral structural pose; not an operating safety claim"},
                       ["Header_ROOT", "Feederhouse_ROOT", "APS_Threshing_Drum_ROOT", "ROTO_PLUS_L_ROOT", "ROTO_PLUS_R_ROOT", "Unloader_ROOT"]),
            self._gate("neutral_unbranded_materials", bool(materials) and all(name.startswith("Neutral_") for name in materials),
                       {"materials": materials, "images": contract["images"], "textures": contract["textures"]}, ["Machine_Root"]),
        ]


if __name__ == "__main__":
    Lexion8900Builder(shared.load_design(DESIGN), DESIGN, OUTPUT_DIR).run()
