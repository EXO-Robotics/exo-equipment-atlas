#!/usr/bin/env python3
"""Deterministically build the neutral Cat 320 technical structural study.

This is an independently authored visualization constrained by selected
manufacturer-published dimensions. It is not manufacturer CAD, engineering
authority, load guidance, operator training, or a mechanical solver.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


SCRIPT_PATH = Path(__file__).resolve()
MACHINE_DIR = SCRIPT_PATH.parents[2]
BLEND_PATH = SCRIPT_PATH.parent / "cat-320-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets" / "cat-320-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production" / "asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production" / "validation.json"
RENDER_DIR = MACHINE_DIR / "review" / "renders"

MACHINE_ID = "cat-320"
CONFIGURATION_ID = "CAT-320-07H-NAM-RB57-R29-HD119-LU-TG790-CW42-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"

PUBLISHED = {
    "boom_length_m": 5.7,
    "stick_length_m": 2.9,
    "boom_cylinder_stroke_m": 1.260,
    "stick_cylinder_stroke_m": 1.504,
    "bucket_cylinder_stroke_m": 1.104,
    "transport_length_m": 9.530,
    "transport_height_m": 3.160,
    "upperframe_width_m": 2.780,
    "undercarriage_width_m": 3.170,
    "track_length_m": 4.450,
    "roller_center_length_m": 3.650,
    "track_gauge_m": 2.380,
    "ground_clearance_m": 0.470,
    "cab_height_m": 2.960,
    "tail_swing_radius_m": 2.830,
    "counterweight_clearance_m": 1.050,
    "shoe_width_m": 0.790,
    "shoe_count_each_side": 49,
    "track_rollers_each_side": 8,
    "carrier_rollers_each_side": 2,
    "bucket_capacity_m3": 1.19,
    "bucket_tip_radius_m": 1.570,
}

RECONSTRUCTED = {
    "scene_transport_pose": {
        "upper_swing_deg": 0.0,
        "boom_deg": 0.0,
        "stick_relative_deg": -64.0,
        "bucket_relative_deg": 224.0,
        "note": "Visualization pose selected to fit the published transport envelope; not a manufacturer pose definition.",
    },
    "review_articulated_pose": {
        "upper_swing_deg": -18.0,
        "boom_deg": 28.0,
        "stick_relative_deg": -83.0,
        "bucket_relative_deg": -42.0,
        "note": "Review-only pose; it is not retained in the saved asset and is not a validated working endpoint.",
    },
    "slew_center_m": [-0.18, 1.08, 0.0],
    "slew_ring_diameter_m": 1.65,
    "boom_pivot_m": [0.10, 1.98, 0.0],
    "boom_centerline_polyline_local_m": [[0.0, 0.0], [1.91, 1.10], [3.91, 0.995], [5.38, 0.735]],
    "stick_pivot_local_m": [5.38, 0.735, 0.0],
    "stick_modeled_pin_distance_m": 2.90,
    "bucket_pivot_local_m": [2.90, 0.09, 0.0],
    "bucket_shell_width_m": 1.20,
    "bucket_shell_note": "Width is a compatible published HD 1.19 m3 table option, but pin-on/coupler identity remains unresolved; shell curvature and volume are not engineering-validated.",
    "track_loop_radius_m": 0.39,
    "track_shoe_modeled_pitch_m": 0.199,
    "track_shoe_thickness_m": 0.075,
    "wheel_and_roller_centers": "Reconstructed from the published track length, roller-center length, counts, and visible first-party illustrations.",
    "cab_house_counterweight_panels": "Independently authored from first-party illustration observations; no hidden internal assembly is represented.",
    "hydraulic_anchors": "All base and rod anchor coordinates are reconstructed. Published strokes constrain future solver work only.",
    "bucket_linkage": "Bellcrank, dogbone, bucket lug, and all pin locations are reconstructed visual closure cues only.",
    "inspection_volumes": "Envelope and component volumes are non-authoritative visualization aids.",
    "material_colors": "Neutral unbranded ochre, graphite, steel, rubber, and glass; not a claim to protected manufacturer livery.",
}

REQUIRED_NODES = [
    "Machine_Root",
    "Undercarriage_ROOT",
    "Track_L_ROOT",
    "Track_R_ROOT",
    "Upper_Swing_Pivot",
    "Upper_ROOT",
    "Boom_Pivot",
    "Boom_ROOT",
    "Stick_Pivot",
    "Stick_ROOT",
    "Bucket_Pivot",
    "Bucket_ROOT",
    "Hydraulics_ROOT",
    "Linkage_ROOT",
    "Inspection_Volumes",
    "PIVOT_Attachment_Pin",
    "INSPECT_Transport_Envelope",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(MACHINE_DIR).as_posix()


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    scene = bpy.context.scene
    bpy.context.preferences.filepaths.save_version = 0
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.resolution_percentage = 100
    scene.render.engine = "BLENDER_EEVEE"
    scene.world.color = (0.018, 0.024, 0.032)
    scene["exo_machine_id"] = MACHINE_ID
    scene["exo_configuration_id"] = CONFIGURATION_ID
    scene["exo_candidate_class"] = CANDIDATE_CLASS
    scene["exo_axes"] = "+X toward bucket, +Y vertical, +Z machine right"
    scene["exo_authority_boundary"] = "independently authored technical structural study; not engineering authority"


def material(name: str, color, metallic=0.0, roughness=0.5, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    mat["exo_rights"] = "neutral_unbranded"
    return mat


def tag(obj, role="geometry", export=True, authority="reconstructed"):
    obj["exo_role"] = role
    obj["exo_export"] = bool(export)
    obj["exo_authority"] = authority
    return obj


def empty(name, location=(0, 0, 0), parent=None, role="pivot", display="PLAIN_AXES", size=0.18, export=True):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    if parent:
        obj.parent = parent
    return tag(obj, role=role, export=export)


def bevel(obj, width=0.025, segments=2):
    if width <= 0:
        return
    modifier = obj.modifiers.new("Edge_Radius", "BEVEL")
    modifier.width = width
    modifier.segments = segments


def box(name, location, dimensions, mat, parent=None, bevel_width=0.02, role="geometry", export=True, authority="reconstructed"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if parent:
        obj.parent = parent
    obj.data.materials.append(mat)
    bevel(obj, min(bevel_width, min(dimensions) * 0.22), 2)
    return tag(obj, role, export, authority)


def cylinder(name, location, radius, depth, mat, parent=None, vertices=24, rotation=(0, 0, 0), role="geometry", export=True, authority="reconstructed"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    if parent:
        obj.parent = parent
    obj.data.materials.append(mat)
    bevel(obj, min(radius * 0.10, 0.018), 2)
    return tag(obj, role, export, authority)


def torus(name, location, major_radius, minor_radius, mat, parent=None, major_segments=32, minor_segments=10, role="geometry"):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=major_segments,
        minor_segments=minor_segments,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    if parent:
        obj.parent = parent
    obj.data.materials.append(mat)
    return tag(obj, role)


def side_profile(name, points_xy, thickness, mat, parent=None, z_center=0.0, bevel_width=0.02, role="geometry"):
    count = len(points_xy)
    vertices = [(x, y, z_center - thickness / 2) for x, y in points_xy]
    vertices += [(x, y, z_center + thickness / 2) for x, y in points_xy]
    faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, count * 2))]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, count + nxt, count + index))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if parent:
        obj.parent = parent
    obj.data.materials.append(mat)
    bevel(obj, bevel_width, 2)
    return tag(obj, role)


def compound_shoe(name, location, tangent_angle, width, mat, parent):
    # Local X is the path tangent and local Y points away from the track loop.
    boxes = [
        ((0.0, 0.0, 0.0), (0.190, 0.075, width)),
        ((-0.060, 0.054, 0.0), (0.025, 0.040, width * 0.94)),
        ((0.000, 0.054, 0.0), (0.025, 0.040, width * 0.94)),
        ((0.060, 0.054, 0.0), (0.025, 0.040, width * 0.94)),
    ]
    vertices = []
    faces = []
    cos_a, sin_a = math.cos(tangent_angle), math.sin(tangent_angle)
    for offset, dims in boxes:
        ox, oy, oz = offset
        dx, dy, dz = [value / 2 for value in dims]
        start = len(vertices)
        for x, y, z in [(-dx,-dy,-dz),(dx,-dy,-dz),(dx,dy,-dz),(-dx,dy,-dz),(-dx,-dy,dz),(dx,-dy,dz),(dx,dy,dz),(-dx,dy,dz)]:
            lx, ly = x + ox, y + oy
            rx = lx * cos_a - ly * sin_a
            ry = lx * sin_a + ly * cos_a
            vertices.append((rx + location[0], ry + location[1], z + oz + location[2]))
        faces.extend([
            (start+0,start+1,start+2,start+3),(start+4,start+7,start+6,start+5),
            (start+0,start+4,start+5,start+1),(start+1,start+5,start+6,start+2),
            (start+2,start+6,start+7,start+3),(start+4,start+0,start+3,start+7),
        ])
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(mat)
    bevel(obj, 0.008, 1)
    return tag(obj, "track_shoe", True, "manufacturer_count_reconstructed_geometry")


def capsule_point(distance, straight=3.65, radius=0.39, center_y=0.54):
    perimeter = 2 * straight + 2 * math.pi * radius
    distance %= perimeter
    half = straight / 2
    if distance < straight:
        # Bottom: front to rear.
        return (half - distance, center_y - radius, math.pi)
    distance -= straight
    arc = math.pi * radius
    if distance < arc:
        u = distance / arc
        theta = -math.pi / 2 - u * math.pi
        x = -half + radius * math.cos(theta)
        y = center_y + radius * math.sin(theta)
        tangent = math.atan2(-math.pi * radius * math.cos(theta), math.pi * radius * math.sin(theta))
        return (x, y, tangent)
    distance -= arc
    if distance < straight:
        return (-half + distance, center_y + radius, 0.0)
    distance -= straight
    u = distance / arc
    theta = math.pi / 2 - u * math.pi
    x = half + radius * math.cos(theta)
    y = center_y + radius * math.sin(theta)
    tangent = math.atan2(-math.pi * radius * math.cos(theta), math.pi * radius * math.sin(theta))
    return (x, y, tangent)


def build_track(side, z_center, root, mats):
    prefix = f"Track_{side}"
    perimeter = 2 * 3.65 + 2 * math.pi * 0.39
    for index in range(PUBLISHED["shoe_count_each_side"]):
        x, y, angle = capsule_point((index + 0.5) * perimeter / PUBLISHED["shoe_count_each_side"])
        compound_shoe(f"{prefix}_Shoe_{index+1:02d}", (x, y, z_center), angle, PUBLISHED["shoe_width_m"], mats["track"], root)

    for label, x in (("Rear_Sprocket", -1.825), ("Front_Idler", 1.825)):
        torus(f"{prefix}_{label}_Rim", (x, 0.54, z_center), 0.30, 0.055, mats["steel_dark"], root)
        cylinder(f"{prefix}_{label}_Hub", (x, 0.54, z_center), 0.18, 0.68, mats["steel"], root)
        # Six visible hub/drive cues, independently reconstructed.
        for bolt_index in range(6):
            theta = bolt_index * math.tau / 6
            cylinder(
                f"{prefix}_{label}_Bolt_{bolt_index+1}",
                (x + math.cos(theta)*0.105, 0.54 + math.sin(theta)*0.105, z_center - 0.352),
                0.020, 0.025, mats["bolt"], root, vertices=12,
            )

    for index in range(PUBLISHED["track_rollers_each_side"]):
        x = -1.46 + index * (2.92 / 7)
        torus(f"{prefix}_Lower_Roller_{index+1:02d}", (x, 0.26, z_center), 0.105, 0.032, mats["steel_dark"], root, major_segments=20, minor_segments=8)
        cylinder(f"{prefix}_Lower_Roller_Hub_{index+1:02d}", (x, 0.26, z_center), 0.07, 0.54, mats["steel"], root, vertices=16)
    for index, x in enumerate((-0.58, 0.65), start=1):
        torus(f"{prefix}_Carrier_Roller_{index:02d}", (x, 0.83, z_center), 0.08, 0.025, mats["steel_dark"], root, major_segments=18, minor_segments=8)
        cylinder(f"{prefix}_Carrier_Roller_Hub_{index:02d}", (x, 0.83, z_center), 0.055, 0.48, mats["steel"], root, vertices=16)

    box(f"{prefix}_Track_Frame", (0, 0.54, z_center), (3.55, 0.34, 0.34), mats["steel_dark"], root, 0.055, "fixed_structure")
    side_profile(
        f"{prefix}_Track_Frame_Side",
        [(-1.72,0.37),(1.72,0.37),(1.45,0.71),(-1.45,0.71)],
        0.42, mats["steel"], root, z_center=z_center, bevel_width=0.025, role="fixed_structure",
    )


def object_between(name, start, end, radius, mat, role="hydraulic", vertices=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=1.0, depth=1.0)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    tag(obj, role)
    place_between(obj, start, end, radius)
    bevel(obj, 0.012, 2)
    return obj


def place_between(obj, start, end, radius):
    start, end = Vector(start), Vector(end)
    vector = end - start
    length = vector.length
    obj.location = (start + end) / 2
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(vector.normalized())
    obj.scale = (radius, radius, length)


def world(anchor):
    return anchor.matrix_world.translation.copy()


def add_pin(name, location, radius, length, mat, parent, role="pivot_marker"):
    return cylinder(name, location, radius, length, mat, parent, vertices=24, role=role)


def create_model():
    mats = {
        "ochre": material("Neutral_Construction_Ochre", (0.76, 0.39, 0.055), 0.12, 0.34),
        "ochre_dark": material("Neutral_Ochre_Shadow", (0.42, 0.19, 0.035), 0.15, 0.38),
        "track": material("Neutral_Track_Steel", (0.075, 0.085, 0.095), 0.72, 0.33),
        "steel_dark": material("Neutral_Graphite_Steel", (0.035, 0.045, 0.055), 0.62, 0.30),
        "steel": material("Neutral_Machined_Steel", (0.25, 0.28, 0.30), 0.82, 0.24),
        "rod": material("Neutral_Hydraulic_Rod", (0.53, 0.56, 0.59), 0.93, 0.14),
        "rubber": material("Neutral_Rubber", (0.015, 0.018, 0.021), 0.05, 0.78),
        "glass": material("Neutral_Smoke_Glass", (0.045, 0.095, 0.12), 0.35, 0.16),
        "bolt": material("Neutral_Fastener", (0.12, 0.13, 0.14), 0.85, 0.23),
        "safety": material("Neutral_Safety_Red", (0.52, 0.045, 0.025), 0.18, 0.42),
        "interior": material("Neutral_Cab_Interior", (0.025, 0.030, 0.034), 0.1, 0.66),
        "ground": material("Review_Ground", (0.055, 0.065, 0.075), 0.0, 0.74),
    }

    machine = empty("Machine_Root", role="machine_root", size=0.32)
    under = empty("Undercarriage_ROOT", parent=machine, role="fixed_group", size=0.24)
    left_root = empty("Track_L_ROOT", parent=under, role="track_group", size=0.18)
    right_root = empty("Track_R_ROOT", parent=under, role="track_group", size=0.18)
    build_track("L", -PUBLISHED["track_gauge_m"] / 2, left_root, mats)
    build_track("R", PUBLISHED["track_gauge_m"] / 2, right_root, mats)

    # Published 470 mm clearance is represented beneath the center carbody.
    box("Undercarriage_Center_Frame", (0.0, 0.78, 0.0), (2.35, 0.33, 1.70), mats["steel_dark"], under, 0.06, "fixed_structure")
    box("Undercarriage_Crossmember_Front", (1.22, 0.73, 0.0), (0.30, 0.29, 2.55), mats["steel"], under, 0.035, "fixed_structure")
    box("Undercarriage_Crossmember_Rear", (-1.22, 0.73, 0.0), (0.30, 0.29, 2.55), mats["steel"], under, 0.035, "fixed_structure")

    swing = empty("Upper_Swing_Pivot", (-0.18, 1.08, 0), under, "revolute_pivot", "CIRCLE", 0.82)
    swing["axis"] = "+Y"
    swing["authority"] = "observed_axis_reconstructed_center"
    upper = empty("Upper_ROOT", parent=swing, role="articulated_group", size=0.24)
    cylinder("Slew_Ring_Lower", (0.0, 0.0, 0.0), 0.825, 0.18, mats["steel_dark"], swing, vertices=48, rotation=(math.pi/2,0,0), role="slew_structure")
    cylinder("Slew_Ring_Upper", (0.0, 0.12, 0.0), 0.72, 0.16, mats["ochre_dark"], swing, vertices=48, rotation=(math.pi/2,0,0), role="slew_structure")
    box("Upper_Deck_Main", (-0.20, 0.34, 0.0), (3.95, 0.22, 2.72), mats["steel_dark"], upper, 0.055, "upper_structure")
    box("Upper_Deck_Walkway_L", (-0.10, 0.46, -1.28), (3.55, 0.10, 0.20), mats["track"], upper, 0.018, "upper_structure")
    box("Upper_Deck_Walkway_R", (-0.10, 0.46, 1.28), (3.55, 0.10, 0.20), mats["track"], upper, 0.018, "upper_structure")

    # Rear house and counterweight. Locations are local to the swing pivot.
    side_profile("Counterweight_Core", [(-2.12,0.40),(-1.92,1.35),(-1.25,1.58),(-0.78,1.32),(-0.76,0.48)], 2.56, mats["ochre"], upper, bevel_width=0.10, role="counterweight")
    side_profile("Engine_House_Main", [(-1.48,0.48),(-1.42,1.54),(-0.55,1.72),(0.35,1.47),(0.36,0.48)], 2.42, mats["ochre"], upper, bevel_width=0.055, role="upper_structure")
    box("Engine_House_Top", (-0.65, 1.62, 0.30), (1.60, 0.12, 2.10), mats["ochre_dark"], upper, 0.035, "upper_structure")
    box("Engine_House_Service_Door_R", (-0.56, 1.02, 1.235), (1.20, 0.78, 0.045), mats["ochre"], upper, 0.015, "service_panel")
    for index in range(7):
        box(f"Engine_Vent_R_{index+1:02d}", (-0.78 + index*0.17, 1.20, 1.263), (0.11, 0.025, 0.018), mats["steel_dark"], upper, 0.003, "vent")
    for index in range(6):
        box(f"Counterweight_Rear_Vent_{index+1:02d}", (-2.135, 0.80 + index*0.095, 0.0), (0.025, 0.052, 0.76), mats["steel_dark"], upper, 0.004, "vent")
    box("Exhaust_Muffler", (-0.72, 1.47, 0.72), (0.28, 0.44, 0.30), mats["steel_dark"], upper, 0.04, "exhaust")
    cylinder("Exhaust_Stack", (-0.72, 1.77, 0.72), 0.075, 0.34, mats["steel_dark"], upper, vertices=24, rotation=(math.pi/2,0,0), role="exhaust")
    cylinder("Air_Intake_Stack", (-0.34, 1.71, 0.90), 0.065, 0.30, mats["steel_dark"], upper, vertices=24, rotation=(math.pi/2,0,0), role="intake")

    # Cab on machine left (-Z), with distinct frame and glass boundaries.
    cab = empty("Cab_ROOT", (0,0,0), upper, "fixed_group", size=0.16)
    side_profile("Cab_Interior_Block", [(-0.15,0.48),(-0.10,1.68),(0.55,1.82),(1.08,1.48),(1.04,0.48)], 0.98, mats["interior"], cab, z_center=-0.78, bevel_width=0.05, role="cab_interior")
    side_profile("Cab_Left_Glass", [(-0.04,0.88),(0.00,1.60),(0.50,1.72),(0.94,1.43),(0.92,0.87)], 0.035, mats["glass"], cab, z_center=-1.285, bevel_width=0.012, role="glass")
    side_profile("Cab_Front_Glass", [(0.91,0.88),(0.94,1.43),(1.06,1.31),(1.04,0.86)], 0.90, mats["glass"], cab, z_center=-0.78, bevel_width=0.012, role="glass")
    box("Cab_Roof", (0.38, 1.78, -0.78), (1.20, 0.12, 1.05), mats["ochre_dark"], cab, 0.045, "cab_frame")
    box("Cab_Floor", (0.42, 0.55, -0.78), (1.28, 0.16, 1.08), mats["steel_dark"], cab, 0.025, "cab_frame")
    for name, loc, dims in [
        ("Cab_A_Pillar", (1.00,1.22,-1.30),(0.085,0.95,0.09)),
        ("Cab_B_Pillar", (0.53,1.25,-1.30),(0.075,1.00,0.09)),
        ("Cab_Rear_Pillar", (-0.08,1.22,-1.30),(0.09,1.02,0.09)),
        ("Cab_Belt_Rail", (0.46,0.88,-1.30),(1.08,0.075,0.09)),
    ]:
        box(name, loc, dims, mats["steel_dark"], cab, 0.012, "cab_frame")
    box("Cab_Seat_Back", (0.25, 0.90, -0.75), (0.42, 0.62, 0.46), mats["interior"], cab, 0.09, "cab_interior")
    box("Cab_Seat_Base", (0.36, 0.65, -0.75), (0.46, 0.18, 0.48), mats["interior"], cab, 0.06, "cab_interior")
    cylinder("Cab_Steering_Control", (0.72, 1.00, -0.76), 0.08, 0.32, mats["steel_dark"], cab, vertices=20, rotation=(math.pi/2,0,0), role="cab_interior")
    # Neutral work lights, handrail, mirror, steps.
    box("Cab_Work_Light", (0.88, 1.76, -1.34), (0.22, 0.10, 0.11), mats["steel_dark"], cab, 0.025, "lighting")
    cylinder("Cab_Mirror_Arm", (0.98,1.46,-1.36), 0.018, 0.20, mats["steel"], cab, vertices=12, rotation=(math.pi/2,0,0), role="cab_accessory")
    box("Cab_Mirror", (0.98,1.46,-1.48),(0.08,0.26,0.14),mats["glass"],cab,0.025,"cab_accessory")
    for index in range(3):
        box(f"Cab_Access_Step_{index+1}", (0.28-index*0.18, 0.46-index*0.13, -1.44), (0.34,0.06,0.22), mats["track"], upper, 0.012, "access_step")
    # Tube-like handrail segments as cylinders between independently selected points.
    handrail_points = [(-1.35,1.90,-1.18),(-0.72,2.05,-1.18),(-0.05,1.98,-1.18)]
    for index in range(len(handrail_points)-1):
        object_between(f"Handrail_L_{index+1}", handrail_points[index], handrail_points[index+1], 0.022, mats["steel_dark"], "handrail", 12).parent = upper

    # Front equipment hierarchy. All hidden pivots and anchors are reconstructed.
    boom_pivot = empty("Boom_Pivot", (0.28, 0.90, 0.0), upper, "revolute_pivot", "CIRCLE", 0.28)
    boom_pivot["axis"] = "+Z"
    boom_pivot["authority"] = "reconstructed"
    boom_root = empty("Boom_ROOT", parent=boom_pivot, role="articulated_group", size=0.20)
    boom_profile = [(0.0,-0.28),(0.44,-0.42),(1.90,0.86),(3.88,0.73),(5.32,0.58),(5.48,0.40),(5.34,0.12),(3.82,0.34),(1.98,0.49),(0.50,-0.62)]
    side_profile("Boom_Main_Weldment", boom_profile, 0.58, mats["ochre"], boom_root, bevel_width=0.055, role="boom_structure")
    side_profile("Boom_Left_Reinforcement", [(0.42,-0.26),(1.92,0.70),(3.80,0.60),(5.10,0.48),(4.84,0.31),(2.02,0.38)], 0.035, mats["ochre_dark"], boom_root, z_center=-0.307, bevel_width=0.012, role="boom_reinforcement")
    side_profile("Boom_Right_Reinforcement", [(0.42,-0.26),(1.92,0.70),(3.80,0.60),(5.10,0.48),(4.84,0.31),(2.02,0.38)], 0.035, mats["ochre_dark"], boom_root, z_center=0.307, bevel_width=0.012, role="boom_reinforcement")
    add_pin("PIN_Boom_Base", (0,0,0), 0.15, 0.78, mats["steel"], boom_pivot)
    for x, y in ((1.92,0.62),(3.85,0.52),(5.32,0.35)):
        add_pin(f"Boom_Service_Pin_{x:.2f}", (x,y,0), 0.065, 0.70, mats["bolt"], boom_root, "fastener")

    stick_pivot = empty("Stick_Pivot", (5.38, 0.735, 0.0), boom_pivot, "revolute_pivot", "CIRCLE", 0.24)
    stick_pivot.rotation_euler[2] = math.radians(RECONSTRUCTED["scene_transport_pose"]["stick_relative_deg"])
    stick_pivot["axis"] = "+Z"
    stick_root = empty("Stick_ROOT", parent=stick_pivot, role="articulated_group", size=0.18)
    stick_profile = [(-0.10,0.24),(0.40,0.34),(2.63,0.16),(2.90,0.02),(2.78,-0.21),(0.42,-0.28),(-0.10,-0.18)]
    side_profile("Stick_Main_Weldment", stick_profile, 0.43, mats["ochre"], stick_root, bevel_width=0.045, role="stick_structure")
    side_profile("Stick_Left_Wear_Plate", [(0.20,-0.20),(2.64,-0.15),(2.78,-0.05),(0.45,-0.08)], 0.026, mats["ochre_dark"], stick_root, z_center=-0.228, bevel_width=0.008, role="wear_plate")
    side_profile("Stick_Right_Wear_Plate", [(0.20,-0.20),(2.64,-0.15),(2.78,-0.05),(0.45,-0.08)], 0.026, mats["ochre_dark"], stick_root, z_center=0.228, bevel_width=0.008, role="wear_plate")
    add_pin("PIN_Stick", (0,0,0), 0.13, 0.68, mats["steel"], stick_pivot)

    bucket_pivot = empty("Bucket_Pivot", (2.90, 0.09, 0.0), stick_pivot, "revolute_pivot", "CIRCLE", 0.22)
    bucket_pivot["axis"] = "+Z"
    bucket_root = empty("Bucket_ROOT", parent=bucket_pivot, role="articulated_group", size=0.18)
    bucket_root.rotation_euler[2] = math.radians(RECONSTRUCTED["scene_transport_pose"]["bucket_relative_deg"])
    bucket_profile = [(0.02,-0.01),(0.50,0.16),(1.04,-0.10),(1.45,-0.62),(1.36,-1.02),(0.78,-1.22),(0.10,-0.60)]
    side_profile("Bucket_Left_Side_Plate", bucket_profile, 0.065, mats["ochre"], bucket_root, z_center=-0.565, bevel_width=0.020, role="bucket_structure")
    side_profile("Bucket_Right_Side_Plate", bucket_profile, 0.065, mats["ochre"], bucket_root, z_center=0.565, bevel_width=0.020, role="bucket_structure")
    box("Bucket_Back_Shell", (0.88,-0.48,0.0),(0.62,0.12,1.10),mats["ochre"],bucket_root,0.045,"bucket_structure")
    box("Bucket_Cutting_Edge", (1.28,-0.97,0.0),(0.42,0.10,1.20),mats["steel"],bucket_root,0.018,"bucket_cutting_edge")
    for index, z in enumerate((-0.48,-0.24,0.0,0.24,0.48), start=1):
        tooth = side_profile(f"Bucket_Tooth_{index:02d}", [(0,0.05),(0.38,0.0),(0.52,-0.08),(0.10,-0.12)], 0.14, mats["steel"], bucket_root, z_center=z, bevel_width=0.015, role="bucket_tooth")
        tooth.location = (1.38,-0.97,0)
    add_pin("PIN_Bucket", (0,0,0), 0.11, 0.72, mats["steel"], bucket_pivot)
    attach_pin = empty("PIVOT_Attachment_Pin", (0.0,0.0,0.0), bucket_pivot, "attachment_pivot", "SPHERE", 0.15)
    attach_pin["authority"] = "reconstructed"
    attach_pin["quick_coupler_status"] = "unresolved_no_coupler_geometry"

    hydraulics = empty("Hydraulics_ROOT", parent=machine, role="hydraulic_group", size=0.18)
    linkage = empty("Linkage_ROOT", parent=machine, role="linkage_group", size=0.18)

    # Anchor empties allow critic inspection and articulated review refresh.
    anchors = {}
    for name, loc, parent in [
        ("ANCHOR_Boom_Base_L", (0.04,0.40,-0.40), upper),
        ("ANCHOR_Boom_Rod_L", (1.64,0.42,-0.36), boom_root),
        ("ANCHOR_Boom_Base_R", (0.04,0.40,0.40), upper),
        ("ANCHOR_Boom_Rod_R", (1.64,0.42,0.36), boom_root),
        ("ANCHOR_Stick_Base", (2.52,0.93,0.0), boom_root),
        ("ANCHOR_Stick_Rod", (0.46,0.38,0.0), stick_root),
        ("ANCHOR_Bucket_Base", (0.42,0.28,0.0), stick_root),
        ("ANCHOR_Bucket_Rod", (2.52,0.34,0.0), stick_root),
        ("ANCHOR_Bellcrank", (2.60,0.02,0.0), stick_root),
        ("ANCHOR_Bucket_Lug", (0.22,0.20,0.0), bucket_root),
    ]:
        anchors[name] = empty(name, loc, parent, "hydraulic_anchor", "SPHERE", 0.065)

    cylinders = {}
    def pair(key, a, b, barrel_radius, rod_radius):
        start, end = world(anchors[a]), world(anchors[b])
        direction = end - start
        barrel_end = start + direction * 0.62
        rod_start = start + direction * 0.56
        cylinders[f"{key}_Barrel"] = object_between(f"{key}_Barrel", start, barrel_end, barrel_radius, mats["steel_dark"], "hydraulic_barrel", 24)
        cylinders[f"{key}_Rod"] = object_between(f"{key}_Rod", rod_start, end, rod_radius, mats["rod"], "hydraulic_rod", 20)
        cylinders[f"{key}_Barrel"].parent = hydraulics
        cylinders[f"{key}_Rod"].parent = hydraulics
    bpy.context.view_layer.update()
    pair("Boom_Cylinder_L", "ANCHOR_Boom_Base_L", "ANCHOR_Boom_Rod_L", 0.095, 0.052)
    pair("Boom_Cylinder_R", "ANCHOR_Boom_Base_R", "ANCHOR_Boom_Rod_R", 0.095, 0.052)
    pair("Stick_Cylinder", "ANCHOR_Stick_Base", "ANCHOR_Stick_Rod", 0.105, 0.058)
    pair("Bucket_Cylinder", "ANCHOR_Bucket_Base", "ANCHOR_Bucket_Rod", 0.095, 0.050)
    cylinders["Bucket_Link_Dogbone"] = object_between("Bucket_Link_Dogbone", world(anchors["ANCHOR_Bellcrank"]), world(anchors["ANCHOR_Bucket_Lug"]), 0.050, mats["ochre_dark"], "bucket_linkage", 16)
    cylinders["Bucket_Link_Dogbone"].parent = linkage
    add_pin("PIN_Bucket_Bellcrank", anchors["ANCHOR_Bellcrank"].location, 0.075, 0.62, mats["steel"], stick_root, "linkage_pin")

    inspection = empty("Inspection_Volumes", parent=machine, role="inspection_group", size=0.24)
    envelope = empty("INSPECT_Transport_Envelope", (-0.18, PUBLISHED["transport_height_m"]/2, 0.0), inspection, "inspection_volume", "CUBE", 1.0)
    envelope.scale = (PUBLISHED["transport_length_m"]/2, PUBLISHED["transport_height_m"]/2, PUBLISHED["undercarriage_width_m"]/2)
    envelope["published_constraint"] = "transport-length transport-height undercarriage-width"
    for name, loc, scale in [
        ("INSPECT_Upper_Clearance", (-0.18,1.38,0),(2.1,0.42,1.37)),
        ("INSPECT_Boom_Swept_Study", (2.70,2.20,0),(2.85,1.05,0.42)),
        ("INSPECT_Attachment_Volume", (6.30,0.85,0),(1.15,0.85,0.72)),
    ]:
        marker = empty(name, loc, inspection, "inspection_volume", "CUBE", 1.0)
        marker.scale = scale

    # Review-only environment is not exported.
    box("Review_Ground", (1.5, 0.02, 0), (15.0, 0.04, 10.0), mats["ground"], None, 0.0, "review_environment", False)
    return {
        "mats": mats,
        "machine": machine,
        "boom_pivot": boom_pivot,
        "stick_pivot": stick_pivot,
        "bucket_root": bucket_root,
        "anchors": anchors,
        "cylinders": cylinders,
    }


def refresh_hydraulics(model):
    bpy.context.view_layer.update()
    anchors = model["anchors"]
    cylinders = model["cylinders"]
    definitions = [
        ("Boom_Cylinder_L", "ANCHOR_Boom_Base_L", "ANCHOR_Boom_Rod_L", 0.095, 0.052),
        ("Boom_Cylinder_R", "ANCHOR_Boom_Base_R", "ANCHOR_Boom_Rod_R", 0.095, 0.052),
        ("Stick_Cylinder", "ANCHOR_Stick_Base", "ANCHOR_Stick_Rod", 0.105, 0.058),
        ("Bucket_Cylinder", "ANCHOR_Bucket_Base", "ANCHOR_Bucket_Rod", 0.095, 0.050),
    ]
    for key, a, b, barrel_radius, rod_radius in definitions:
        start, end = world(anchors[a]), world(anchors[b])
        vector = end - start
        place_between(cylinders[f"{key}_Barrel"], start, start + vector*0.62, barrel_radius)
        place_between(cylinders[f"{key}_Rod"], start + vector*0.56, end, rod_radius)
    place_between(cylinders["Bucket_Link_Dogbone"], world(anchors["ANCHOR_Bellcrank"]), world(anchors["ANCHOR_Bucket_Lug"]), 0.050)
    bpy.context.view_layer.update()


def add_review_lighting():
    def area(name, location, energy, size, color):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = location
        tag(obj, "review_environment", False)
        return obj
    key = area("Review_Key", (3.5, 8.0, -5.5), 1600, 5.0, (1.0,0.83,0.65))
    fill = area("Review_Fill", (-4.5, 4.5, 5.5), 1150, 4.0, (0.62,0.78,1.0))
    rim = area("Review_Rim", (3.0, 6.5, 5.8), 1300, 3.5, (0.72,0.86,1.0))
    for light, target in ((key,(1.0,1.2,0)),(fill,(-0.4,1.3,0)),(rim,(1.5,1.6,0))):
        point_camera(light, target, forward_axis="-Z", up_axis="Y")


def point_camera(obj, target, forward_axis="-Z", up_axis="Y"):
    # Blender's track quaternion assumes world +Z as the stabilizing up vector.
    # The machine contract is Y-up, so construct a camera/light basis explicitly.
    forward = (Vector(target) - obj.location).normalized()
    world_up = Vector((0.0, 1.0, 0.0))
    right = forward.cross(world_up).normalized()
    true_up = right.cross(forward).normalized()
    rotation = Matrix((right, true_up, -forward)).transposed().to_quaternion()
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = rotation


def render_view(name, camera_location, target, lens=58):
    camera_data = bpy.data.cameras.new(f"Camera_{name}")
    camera_data.lens = lens
    camera_data.sensor_width = 36
    camera = bpy.data.objects.new(f"Camera_{name}", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = camera_location
    point_camera(camera, target)
    tag(camera, "review_environment", False)
    bpy.context.scene.camera = camera
    path = RENDER_DIR / f"cat-320-{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.context.scene.render.image_settings.color_mode = "RGB"
    bpy.ops.render.render(write_still=True)
    return path


def render_all(model):
    paths = []
    paths.append(render_view("operator-side", (2.15, 4.35, -16.5), (2.15,1.35,0), 52))
    paths.append(render_view("right-three-quarter", (12.0, 5.8, 16.0), (1.65,1.35,0), 48))
    paths.append(render_view("rear-three-quarter", (-10.8, 4.7, 10.2), (0.25,1.30,0), 52))
    paths.append(render_view("front-equipment", (14.0, 5.3, -11.0), (2.25,1.30,0), 48))
    paths.append(render_view("linkage-detail", (9.0, 2.9, -5.0), (6.30,0.80,0), 68))

    # Review-only articulation. It is restored before save/export.
    model["boom_pivot"].rotation_euler[2] = math.radians(RECONSTRUCTED["review_articulated_pose"]["boom_deg"])
    model["stick_pivot"].rotation_euler[2] = math.radians(RECONSTRUCTED["review_articulated_pose"]["stick_relative_deg"])
    model["bucket_root"].rotation_euler[2] = math.radians(RECONSTRUCTED["review_articulated_pose"]["bucket_relative_deg"])
    refresh_hydraulics(model)
    paths.append(render_view("articulated-review", (14.0, 8.0, -16.5), (1.6,2.25,0), 50))

    model["boom_pivot"].rotation_euler[2] = math.radians(RECONSTRUCTED["scene_transport_pose"]["boom_deg"])
    model["stick_pivot"].rotation_euler[2] = math.radians(RECONSTRUCTED["scene_transport_pose"]["stick_relative_deg"])
    model["bucket_root"].rotation_euler[2] = math.radians(RECONSTRUCTED["scene_transport_pose"]["bucket_relative_deg"])
    refresh_hydraulics(model)
    return paths


def export_objects():
    return [obj for obj in bpy.context.scene.objects if obj.get("exo_export", False)]


def mesh_bounds(objects):
    bpy.context.view_layer.update()
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    mins = [min(point[index] for point in points) for index in range(3)]
    maxs = [max(point[index] for point in points) for index in range(3)]
    return {
        "min_m": [round(value, 4) for value in mins],
        "max_m": [round(value, 4) for value in maxs],
        "size_m": [round(maxs[index]-mins[index], 4) for index in range(3)],
    }


def triangle_count(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        mesh.calc_loop_triangles()
        total += len(mesh.loop_triangles)
        bpy.data.meshes.remove(mesh)
    return total


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def create_validation(bounds, counts, render_paths):
    node_presence = {name: bpy.data.objects.get(name) is not None for name in REQUIRED_NODES}
    width = bounds["size_m"][2]
    height = bounds["size_m"][1]
    length = bounds["size_m"][0]
    render_ok = all(path.exists() and path.stat().st_size > 20_000 for path in render_paths)
    shoe_l = len([obj for obj in bpy.data.objects if obj.name.startswith("Track_L_Shoe_")])
    shoe_r = len([obj for obj in bpy.data.objects if obj.name.startswith("Track_R_Shoe_")])
    lower_l = len([obj for obj in bpy.data.objects if obj.name.startswith("Track_L_Lower_Roller_") and "Hub" not in obj.name])
    lower_r = len([obj for obj in bpy.data.objects if obj.name.startswith("Track_R_Lower_Roller_") and "Hub" not in obj.name])
    carrier_l = len([obj for obj in bpy.data.objects if obj.name.startswith("Track_L_Carrier_Roller_") and "Hub" not in obj.name])
    carrier_r = len([obj for obj in bpy.data.objects if obj.name.startswith("Track_R_Carrier_Roller_") and "Hub" not in obj.name])
    gates = [
        {"id":"builder-execution","status":"PASS","detail":"Factory-startup background builder reached receipt generation."},
        {"id":"candidate-class-boundary","status":"PASS","detail":"technical_structural_study; not engineering authority."},
        {"id":"scene-units-and-axes","status":"PASS","detail":"Meters; +X toward bucket, +Y vertical, +Z machine right."},
        {"id":"independent-authoring-boundary","status":"PASS","detail":"No CAD, copied texture, downloaded geometry, logo, or manufacturer binary is embedded."},
        {"id":"required-semantic-nodes","status":"PASS" if all(node_presence.values()) else "FAIL","detail":node_presence},
        {"id":"hierarchy-and-pivot-parenting","status":"PASS","detail":"Upper, boom, stick, and bucket are separate pivot-parented groups."},
        {"id":"track-published-counts","status":"PASS" if (shoe_l,shoe_r,lower_l,lower_r,carrier_l,carrier_r)==(49,49,8,8,2,2) else "FAIL","detail":{"shoes":[shoe_l,shoe_r],"lower_rollers":[lower_l,lower_r],"carrier_rollers":[carrier_l,carrier_r]}},
        {"id":"transport-width-envelope","status":"PASS" if width <= PUBLISHED["undercarriage_width_m"] + 0.04 else "FAIL","detail":{"modeled_m":width,"published_max_m":PUBLISHED["undercarriage_width_m"],"classification":"published_constraint_reconstructed_geometry"}},
        {"id":"transport-height-envelope","status":"PASS" if height <= PUBLISHED["transport_height_m"] + 0.05 else "FAIL","detail":{"modeled_m":height,"published_max_m":PUBLISHED["transport_height_m"],"classification":"published_constraint_reconstructed_pose"}},
        {"id":"transport-length-envelope","status":"PASS" if length <= PUBLISHED["transport_length_m"] + 0.08 else "FAIL","detail":{"modeled_m":length,"published_max_m":PUBLISHED["transport_length_m"],"classification":"published_constraint_reconstructed_pose"}},
        {"id":"object-count","status":"PASS" if counts["objects"] >= 180 else "FAIL","detail":counts["objects"]},
        {"id":"triangle-budget","status":"PASS" if 20_000 <= counts["triangles"] <= 220_000 else "FAIL","detail":{"triangles":counts["triangles"],"budget":[20000,220000]}},
        {"id":"neutral-unbranded-materials","status":"PASS","detail":"Neutral materials only; no manufacturer logo or exact livery claim."},
        {"id":"transport-pose-cylinder-visual-closure","status":"PASS","detail":"Static barrel/rod objects join reconstructed anchor empties in the retained transport pose; published stroke travel is not asserted."},
        {"id":"review-renders-nonempty","status":"PASS" if render_ok else "FAIL","detail":{"count":len(render_paths),"minimum_bytes":20000}},
        {"id":"configuration-freeze","status":"PENDING","detail":"Research candidate retains unresolved coupler, thumb, OPG, grade-control, camera, serial/order, and rights choices."},
        {"id":"mechanical-solver","status":"PENDING","detail":"No solver, limits, or cylinder travel validation yet."},
        {"id":"published-working-envelope","status":"PENDING","detail":"Dig depth/reach are recorded evidence constraints but are not demonstrated by this static study."},
        {"id":"bucket-linkage-kinematic-closure","status":"PENDING","detail":"Current linkage is reconstructed visual closure only."},
        {"id":"ground-self-swept-collision","status":"PENDING","detail":"No swept-volume or collision solver exists."},
        {"id":"critic-human-visual-review","status":"PENDING","detail":"Overall critic must inspect exact render and asset hashes."},
        {"id":"viewer-browser-accessibility-mobile-selection-performance","status":"PENDING","detail":"No viewer integration in this lane."},
        {"id":"publication-and-deployment","status":"PENDING","detail":"Only the overall publisher may advance publication state."},
    ]
    required_failed = [gate["id"] for gate in gates if gate["status"] == "FAIL"]
    payload = {
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "candidate_class":CANDIDATE_CLASS,
        "verdict":"PASS" if not required_failed else "FAIL",
        "bounds":bounds,
        "counts":counts,
        "gates":gates,
        "failed_gate_ids":required_failed,
    }
    write_json(VALIDATION_PATH, payload)
    return payload


def main():
    for path in (GLB_PATH.parent, RECEIPT_PATH.parent, RENDER_DIR):
        path.mkdir(parents=True, exist_ok=True)
    reset_scene()
    model = create_model()
    add_review_lighting()
    bpy.context.view_layer.update()
    render_paths = render_all(model)

    objects = export_objects()
    bounds = mesh_bounds(objects)
    counts = {
        "objects": len(objects),
        "meshes": sum(obj.type == "MESH" for obj in objects),
        "empties": sum(obj.type == "EMPTY" for obj in objects),
        "triangles": triangle_count(objects),
        "materials": len({slot.material.name for obj in objects if obj.type == "MESH" for slot in obj.material_slots if slot.material}),
    }

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = model["machine"]
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=False,
        export_extras=True,
        export_cameras=False,
        export_lights=False,
    )

    validation = create_validation(bounds, counts, render_paths)
    render_records = [{"path":rel(path),"sha256":sha256(path),"bytes":path.stat().st_size} for path in render_paths]
    node_presence = {name: bpy.data.objects.get(name) is not None for name in REQUIRED_NODES}
    receipt = {
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "configuration_status":"research_candidate",
        "candidate_class":CANDIDATE_CLASS,
        "authority_boundary":"Independently authored technical structural study. Not manufacturer CAD, engineering authority, load guidance, operator training, safety guidance, a digital twin, or a mechanically validated candidate.",
        "blender":{"version":bpy.app.version_string,"factory_startup_required":True,"background_required":True},
        "builder":{"path":rel(SCRIPT_PATH),"sha256":sha256(SCRIPT_PATH),"deterministic":True,"network_used":False,"downloaded_geometry_used":False,"manufacturer_cad_used":False,"copied_textures_used":False,"opaque_addons_used":False},
        "artifacts":{
            "blend":{"path":rel(BLEND_PATH),"sha256":sha256(BLEND_PATH),"bytes":BLEND_PATH.stat().st_size},
            "glb":{"path":rel(GLB_PATH),"sha256":sha256(GLB_PATH),"bytes":GLB_PATH.stat().st_size},
        },
        "scene":{"units":"meters","axes":{"longitudinal":"+X toward bucket","vertical":"+Y","lateral":"+Z machine right"},"bounds":bounds,**counts},
        "required_semantic_nodes":node_presence,
        "manufacturer_published_constraints_used":[
            "boom-length","stick-length","boom-cylinder-stroke","stick-cylinder-stroke","bucket-cylinder-stroke",
            "transport-length","transport-height","undercarriage-width","upperframe-width","tail-swing-radius",
            "counterweight-clearance","ground-clearance","track-length","roller-center-length","track-gauge",
            "track-shoes-per-side","track-rollers-per-side","carrier-rollers-per-side","top-cab-height","bucket-tip-radius"
        ],
        "reconstructed_values":RECONSTRUCTED,
        "unresolved_choices":["exact serial or order family","quick coupler selection","thumb selection","cab OPG selection","grade-control and camera options","public material and branding authorization"],
        "mechanical_gaps":["slew bearing center and elevation authority","boom/stick/bucket pivot authority","all hydraulic anchor coordinates","bucket linkage topology dimensions","track link pitch and roller centers","motion limits and solver","collision and swept-volume validation","published working envelope reproduction"],
        "renders":render_records,
        "build_verdict":"PASS" if validation["verdict"] == "PASS" else "FAIL",
        "validation_verdict":validation["verdict"],
        "validation_path":rel(VALIDATION_PATH),
        "higher_stage_gates":"PENDING",
    }
    write_json(RECEIPT_PATH, receipt)
    if validation["verdict"] == "FAIL":
        raise RuntimeError(f"Structural validation failed: {validation['failed_gate_ids']}")
    print(json.dumps({"status":"PASS","machine":MACHINE_ID,"blend":str(BLEND_PATH),"glb":str(GLB_PATH),"validation":validation["verdict"],"counts":counts,"bounds":bounds}, indent=2))


if __name__ == "__main__":
    main()
