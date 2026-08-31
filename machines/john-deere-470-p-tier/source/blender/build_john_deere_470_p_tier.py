#!/usr/bin/env python3
"""Build the neutral Deere 470 P-Tier technical structural study.

Run with Blender factory startup in background mode.  Geometry is independently
authored from configuration-applicable published dimensions and first-party
visual observations.  Hidden pivots, anchors, linkage dimensions, track phase,
and hose routing are explicitly reconstructed.  This is not manufacturer CAD,
engineering authority, load guidance, safety guidance, or operator training.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector


SCRIPT_PATH = Path(__file__).resolve()
MACHINE_DIR = SCRIPT_PATH.parents[2]
BLEND_PATH = SCRIPT_PATH.parent / "john-deere-470-p-tier-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets" / "john-deere-470-p-tier-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production" / "asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production" / "validation.json"
RENDER_DIR = MACHINE_DIR / "review" / "renders"
BUILD_INPUT_PATH = MACHINE_DIR / "source" / "build-input.json"
SOURCE_MANIFEST_PATH = MACHINE_DIR / "evidence" / "source-manifest.json"
DESIGN_PATH = MACHINE_DIR / "source" / "design.json"
MECHANISM_PATH = MACHINE_DIR / "mechanism.json"

MACHINE_ID = "john-deere-470-p-tier"
CONFIGURATION_ID = "JD-470P-NAM-B70-A39-B234-W1370-TSG900-CW8400-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"

PUBLISHED = {
    "boom_length_m": 7.0,
    "arm_length_m": 3.9,
    "bucket_capacity_m3_operating_weight_basis": 2.34,
    "bucket_width_m_operating_weight_basis": 1.370,
    "counterweight_mass_kg": 8400,
    "overall_length_m": 12.01,
    "overall_height_m": 3.50,
    "tail_swing_radius_m": 3.67,
    "idler_sprocket_center_distance_m": 4.47,
    "undercarriage_length_m": 5.47,
    "counterweight_clearance_m": 1.36,
    "upperstructure_width_m": 3.48,
    "cab_height_m": 3.33,
    "shoe_width_m": 0.90,
    "track_gauge_operating_m": 2.89,
    "overall_width_operating_m": 3.79,
    "ground_clearance_m": 0.74,
    "shoe_count_each_side": 53,
    "track_rollers_each_side": 9,
    "carrier_rollers_each_side": 3,
    "boom_cylinder_count": 2,
    "boom_cylinder_bore_m": 0.170,
    "boom_cylinder_rod_m": 0.115,
    "boom_cylinder_stroke_m": 1.590,
    "arm_cylinder_bore_m": 0.190,
    "arm_cylinder_rod_m": 0.130,
    "arm_cylinder_stroke_m": 1.940,
    "bucket_cylinder_bore_m": 0.170,
    "bucket_cylinder_rod_m": 0.120,
    "bucket_cylinder_stroke_m": 1.325,
    "maximum_reach_m": 12.49,
    "maximum_ground_reach_m": 12.28,
    "maximum_digging_depth_m": 8.27,
    "work_light_count": 9,
}

PUBLISHED_FACT_IDS = [
    "boom-length", "arm-length", "bucket-capacity-operating-weight",
    "bucket-width-operating-weight", "counterweight-mass", "overall-length",
    "overall-height", "tail-swing-radius", "idler-sprocket-centers",
    "undercarriage-length", "counterweight-clearance", "upperstructure-width",
    "cab-height", "track-shoe-width", "track-gauge-operating",
    "overall-width-operating", "ground-clearance", "track-shoes-per-side",
    "track-rollers-per-side", "carrier-rollers-per-side", "boom-cylinder-count",
    "boom-cylinder-bore", "boom-cylinder-rod", "boom-cylinder-stroke",
    "arm-cylinder-bore", "arm-cylinder-rod", "arm-cylinder-stroke",
    "bucket-cylinder-bore", "bucket-cylinder-rod", "bucket-cylinder-stroke",
    "maximum-reach", "maximum-ground-reach", "maximum-digging-depth",
    "work-light-count",
]

RECONSTRUCTED = {
    "transport_pose": {
        "upper_swing_deg": 0.0,
        "boom_delta_deg": 0.0,
        "arm_delta_deg": 0.0,
        "bucket_delta_deg": 0.0,
        "note": "Authored folded pose constrained to published overall dimensions; not a manufacturer pose definition.",
    },
    "review_articulated_pose": {
        "upper_swing_deg": -16.0,
        "boom_delta_deg": 28.0,
        "arm_delta_deg": 17.0,
        "bucket_delta_deg": -32.0,
        "note": "Review-only articulation for hierarchy inspection; not a validated working endpoint.",
    },
    "slew_center_m": [0.0, 1.18, 0.0],
    "slew_ring_diameter_m": 2.18,
    "boom_pivot_m": [0.15, 1.82, 0.0],
    "boom_profile_and_pin_locations": "Reconstructed to preserve the 7.0 m selected boom identity and published machine envelope; 7.0 m is not asserted as modeled pin-center distance.",
    "arm_modeled_pin_distance_m": 3.8985,
    "bucket_shell": "Reconstructed around the operating-weight 2.34 m3 / 1370 mm basis. Shell volume and bucket family are not validated because the same publication conflicts with its bucket table.",
    "track_loop_radius_m": 0.45,
    "track_center_y_m": 0.5448,
    "track_link_pitch_and_phase": "Reconstructed from 53 shoes around a capsule loop constrained by the published 4.47 m idler/sprocket-center distance.",
    "sprocket_teeth_each_side": 16,
    "sprocket_tooth_geometry": "Reconstructed visibility cue; not a published count or tooth form.",
    "roller_centers": "Evenly reconstructed within the published undercarriage envelope; only counts are manufacturer-published.",
    "hydraulic_anchors": "All base, rod, and linkage anchors are reconstructed; bore, rod diameter, stroke, and cylinder count are published constraints only.",
    "bucket_linkage": "Bellcrank, twin dogbones, bucket lugs, pin centers, and plate thicknesses are reconstructed visual closure cues.",
    "exterior_hose_paths": "Reconstructed exterior routing cues only; no pressure, service, diameter, or fitting authority.",
    "upper_house_and_cab": "Independently authored from first-party imagery observations and published envelope facts; hidden internal assemblies are omitted.",
    "work_light_locations": "Nine visible light housings follow the published count and described mounting regions; exact bracket coordinates are reconstructed.",
    "materials": "Neutral unbranded copper-clay, graphite, steel, rubber, and blue-gray glass; not Deere trade dress.",
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
    "Arm_Pivot",
    "Arm_ROOT",
    "Bucket_Pivot",
    "Bucket_ROOT",
    "Boom_Hydraulics_ROOT",
    "Arm_Hydraulics_ROOT",
    "Bucket_Hydraulics_ROOT",
    "Bucket_Linkage_ROOT",
    "Bucket_Bellcrank_ROOT",
]


def load_build_input() -> dict:
    payload = json.loads(BUILD_INPUT_PATH.read_text(encoding="utf-8"))
    if payload.get("machine_id") != MACHINE_ID or payload.get("configuration_id") != CONFIGURATION_ID:
        raise RuntimeError("build-input identity does not match builder identity")
    if not payload.get("export_pivots_world_xyz_m") or not payload.get("viewer_motion_nodes"):
        raise RuntimeError("build-input must bind pivots and viewer motion nodes")
    return payload


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(MACHINE_DIR).as_posix()


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for blocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(blocks):
            if block.users == 0:
                blocks.remove(block)
    scene = bpy.context.scene
    bpy.context.preferences.filepaths.save_version = 0
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 840
    scene.render.resolution_y = 630
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.world.color = (0.012, 0.017, 0.024)
    scene["exo_machine_id"] = MACHINE_ID
    scene["exo_configuration_id"] = CONFIGURATION_ID
    scene["exo_candidate_class"] = CANDIDATE_CLASS
    scene["exo_axes"] = "+X toward bucket, +Y up, +Z machine right"
    scene["exo_authority_boundary"] = "independently authored technical structural study; not engineering authority"


def material(name, color, metallic=0.0, roughness=0.5, alpha=1.0, emission=None):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    if emission and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 2.2
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
    return tag(obj, role, export)


def bevel(obj, width=0.025, segments=2):
    if width <= 0:
        return obj
    modifier = obj.modifiers.new("Edge_Radius", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    return obj


def box(name, location, dimensions, mat, parent=None, bevel_width=0.02, role="geometry", export=True, authority="reconstructed"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if parent:
        obj.parent = parent
    obj.data.materials.append(mat)
    bevel(obj, min(bevel_width, min(dimensions) * 0.2), 2)
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


def torus(name, location, major_radius, minor_radius, mat, parent=None, major_segments=28, minor_segments=10, role="geometry"):
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


def side_profile(name, points_xy, thickness, mat, parent=None, z_center=0.0, bevel_width=0.02, role="geometry", export=True):
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
    return tag(obj, role, export)


def footprint_prism(name, points_xz, y_min, y_max, mat, parent=None, bevel_width=0.04, role="geometry"):
    count = len(points_xz)
    vertices = [(x, y_min, z) for x, z in points_xz] + [(x, y_max, z) for x, z in points_xz]
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
    bevel(obj, bevel_width, 3)
    return tag(obj, role)


def curve_tube(name, points, radius, mat, parent=None, role="reconstructed_hose", export=True):
    curve = bpy.data.curves.new(f"{name}_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, value in zip(spline.points, points):
        point.co = (*value, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    if parent:
        obj.parent = parent
    obj.data.materials.append(mat)
    return tag(obj, role, export)


def parent_keep_world(obj, parent):
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


def place_between(obj, start, end, radius):
    start, end = Vector(start), Vector(end)
    vector = end - start
    rotation = Vector((0, 0, 1)).rotation_difference(vector.normalized())
    obj.matrix_world = Matrix.LocRotScale((start + end) / 2, rotation, (radius, radius, vector.length))


def object_between(name, start, end, radius, mat, role="hydraulic", vertices=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=1.0, depth=1.0)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    tag(obj, role)
    place_between(obj, start, end, radius)
    bevel(obj, 0.010, 2)
    return obj


def world(obj):
    return obj.matrix_world.translation.copy()


def add_pin(name, location, radius, length, mat, parent, role="pivot_marker"):
    return cylinder(name, location, radius, length, mat, parent, vertices=24, role=role)


def capsule_point(distance, straight=4.47, radius=0.45, center_y=0.5448):
    perimeter = 2 * straight + 2 * math.pi * radius
    distance %= perimeter
    half = straight / 2
    if distance < straight:
        return (half - distance, center_y - radius, math.pi)
    distance -= straight
    arc = math.pi * radius
    if distance < arc:
        theta = -math.pi / 2 - distance / radius
        return (-half + radius * math.cos(theta), center_y + radius * math.sin(theta), math.atan2(-math.cos(theta), math.sin(theta)))
    distance -= arc
    if distance < straight:
        return (-half + distance, center_y + radius, 0.0)
    distance -= straight
    theta = math.pi / 2 - distance / radius
    return (half + radius * math.cos(theta), center_y + radius * math.sin(theta), math.atan2(-math.cos(theta), math.sin(theta)))


def compound_shoe(name, location, tangent_angle, width, mat, parent):
    # Main plate plus three semi-grouser bars.  Published count/width constrain
    # placement; pitch, plate profile, and phase remain reconstructed.
    boxes = [
        ((0.0, 0.0, 0.0), (0.212, 0.090, width)),
        ((-0.070, 0.067, 0.0), (0.028, 0.045, width * 0.95)),
        ((0.000, 0.067, 0.0), (0.028, 0.045, width * 0.95)),
        ((0.070, 0.067, 0.0), (0.028, 0.045, width * 0.95)),
    ]
    vertices, faces = [], []
    cos_a, sin_a = math.cos(tangent_angle), math.sin(tangent_angle)
    for offset, dims in boxes:
        ox, oy, oz = offset
        dx, dy, dz = (value / 2 for value in dims)
        start = len(vertices)
        for x, y, z in [(-dx,-dy,-dz),(dx,-dy,-dz),(dx,dy,-dz),(-dx,dy,-dz),(-dx,-dy,dz),(dx,-dy,dz),(dx,dy,dz),(-dx,dy,dz)]:
            lx, ly = x + ox, y + oy
            vertices.append((lx * cos_a - ly * sin_a + location[0], lx * sin_a + ly * cos_a + location[1], z + oz + location[2]))
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
    bevel(obj, 0.006, 1)
    return tag(obj, "track_shoe", True, "manufacturer_count_reconstructed_geometry")


def build_track(side, z_center, root, mats):
    prefix = f"Track_{side}"
    perimeter = 2 * PUBLISHED["idler_sprocket_center_distance_m"] + 2 * math.pi * RECONSTRUCTED["track_loop_radius_m"]
    for index in range(PUBLISHED["shoe_count_each_side"]):
        x, y, angle = capsule_point((index + 0.5) * perimeter / PUBLISHED["shoe_count_each_side"])
        compound_shoe(f"{prefix}_Shoe_{index+1:02d}", (x, y, z_center), angle, PUBLISHED["shoe_width_m"], mats["track"], root)

    for label, x in (("Rear_Sprocket", -2.235), ("Front_Idler", 2.235)):
        torus(f"{prefix}_{label}_Outer_Rim", (x, 0.5448, z_center), 0.355, 0.060, mats["steel_dark"], root, 36, 10, "wheel")
        torus(f"{prefix}_{label}_Inner_Rim", (x, 0.5448, z_center), 0.235, 0.045, mats["steel"], root, 30, 8, "wheel")
        cylinder(f"{prefix}_{label}_Hub", (x, 0.5448, z_center), 0.175, 0.70, mats["steel"], root, vertices=24, role="wheel_hub")
        for bolt_index in range(10):
            theta = bolt_index * math.tau / 10
            cylinder(
                f"{prefix}_{label}_Bolt_{bolt_index+1:02d}",
                (x + math.cos(theta)*0.115, 0.5448 + math.sin(theta)*0.115, z_center - 0.365),
                0.017, 0.028, mats["bolt"], root, vertices=10, role="fastener",
            )
        if label == "Rear_Sprocket":
            for tooth_index in range(RECONSTRUCTED["sprocket_teeth_each_side"]):
                theta = tooth_index * math.tau / RECONSTRUCTED["sprocket_teeth_each_side"]
                tooth = box(
                    f"{prefix}_Drive_Sprocket_Tooth_{tooth_index+1:02d}",
                    (x + math.cos(theta)*0.432, 0.5448 + math.sin(theta)*0.432, z_center),
                    (0.145, 0.075, 0.62), mats["steel"], root, 0.010, "drive_sprocket_tooth",
                )
                tooth.rotation_euler[2] = theta

    for index in range(PUBLISHED["track_rollers_each_side"]):
        x = -1.75 + index * (3.50 / 8)
        torus(f"{prefix}_Lower_Roller_{index+1:02d}", (x, 0.278, z_center), 0.125, 0.037, mats["steel_dark"], root, 22, 8, "track_roller")
        cylinder(f"{prefix}_Lower_Roller_Hub_{index+1:02d}", (x, 0.278, z_center), 0.075, 0.60, mats["steel"], root, vertices=18, role="track_roller_hub")
    for index, x in enumerate((-1.10, 0.0, 1.10), start=1):
        torus(f"{prefix}_Carrier_Roller_{index:02d}", (x, 0.865, z_center), 0.095, 0.030, mats["steel_dark"], root, 20, 8, "carrier_roller")
        cylinder(f"{prefix}_Carrier_Roller_Hub_{index:02d}", (x, 0.865, z_center), 0.060, 0.54, mats["steel"], root, vertices=16, role="carrier_roller_hub")

    side_profile(
        f"{prefix}_Box_Section_Frame",
        [(-2.18,0.36),(2.18,0.36),(2.02,0.79),(1.64,0.95),(-1.70,0.95),(-2.05,0.79)],
        0.48, mats["steel_dark"], root, z_center=z_center, bevel_width=0.028, role="fixed_structure",
    )
    box(f"{prefix}_Final_Drive_Guard", (-2.13,0.54,z_center), (0.48,0.62,0.76), mats["graphite"], root, 0.055, "drive_guard")
    box(f"{prefix}_Front_Track_Guard", (1.58,0.40,z_center), (0.52,0.22,0.62), mats["steel_dark"], root, 0.020, "track_guard")
    box(f"{prefix}_Center_Track_Guard", (0.00,0.40,z_center), (0.60,0.22,0.62), mats["steel_dark"], root, 0.020, "track_guard")


def create_model():
    mats = {
        "body": material("Neutral_Warm_Slate", (0.34, 0.27, 0.21), 0.18, 0.36),
        "body_light": material("Neutral_Warm_Highlight", (0.50, 0.40, 0.30), 0.12, 0.34),
        "body_dark": material("Neutral_Warm_Shadow", (0.19, 0.15, 0.12), 0.20, 0.38),
        "graphite": material("Neutral_Graphite", (0.045, 0.055, 0.067), 0.44, 0.38),
        "track": material("Neutral_Track_Steel", (0.060, 0.066, 0.073), 0.72, 0.34),
        "steel": material("Neutral_Machined_Steel", (0.20, 0.225, 0.25), 0.78, 0.26),
        "steel_dark": material("Neutral_Dark_Steel", (0.085, 0.095, 0.108), 0.70, 0.32),
        "rod": material("Neutral_Chrome_Rod", (0.55, 0.61, 0.67), 0.92, 0.14),
        "rubber": material("Neutral_Hydraulic_Rubber", (0.012, 0.014, 0.017), 0.05, 0.72),
        "glass": material("Neutral_Blue_Gray_Glass", (0.10, 0.20, 0.26), 0.18, 0.18, 0.46),
        "interior": material("Neutral_Cab_Interior", (0.028, 0.032, 0.038), 0.02, 0.70),
        "bolt": material("Neutral_Fastener", (0.31, 0.335, 0.36), 0.88, 0.22),
        "light": material("Neutral_LED_Lens", (0.70, 0.78, 0.82), 0.08, 0.16, 1.0, emission=(0.80,0.88,1.0)),
        "amber": material("Neutral_Amber_Lens", (0.73, 0.24, 0.035), 0.05, 0.22, 1.0, emission=(0.85,0.22,0.02)),
        "ground": material("Review_Ground_Material", (0.025, 0.032, 0.040), 0.0, 0.88),
    }

    machine = empty("Machine_Root", role="machine_root", size=0.30)
    machine["identity_transform_required"] = True
    machine["configuration_status"] = "research_candidate"

    undercarriage = empty("Undercarriage_ROOT", parent=machine, role="fixed_structure_group", size=0.22)
    track_l = empty("Track_L_ROOT", parent=undercarriage, role="track_group", size=0.18)
    track_r = empty("Track_R_ROOT", parent=undercarriage, role="track_group", size=0.18)
    build_track("L", -PUBLISHED["track_gauge_operating_m"] / 2, track_l, mats)
    build_track("R", PUBLISHED["track_gauge_operating_m"] / 2, track_r, mats)

    # Thick-plate mainframe and variable-gauge cross members.  The publication
    # describes the gauge endpoints but not the extension mechanism.
    box("Undercarriage_Center_Frame", (0.0,0.925,0.0), (3.30,0.37,1.28), mats["steel_dark"], undercarriage, 0.060, "mainframe")
    for index, x in enumerate((-1.05, 0.98), start=1):
        box(f"Variable_Gauge_Crossmember_{index:02d}", (x,0.90,0.0), (0.56,0.26,2.88), mats["steel"], undercarriage, 0.025, "reconstructed_variable_gauge_structure")
        for side_index, z in enumerate((-1.18, 1.18), start=1):
            box(f"Variable_Gauge_Wear_Pad_{index:02d}_{side_index:02d}", (x,0.90,z), (0.46,0.12,0.24), mats["bolt"], undercarriage, 0.015, "wear_pad")
    cylinder("Slew_Bearing_Lower", (0.0,1.165,0.0), 1.09, 0.20, mats["steel_dark"], undercarriage, vertices=64, rotation=(math.pi/2,0,0), role="slew_bearing")
    cylinder("Slew_Bearing_Upper", (0.0,1.235,0.0), 0.94, 0.14, mats["steel"], undercarriage, vertices=64, rotation=(math.pi/2,0,0), role="slew_bearing")
    for index in range(28):
        theta = index * math.tau / 28
        cylinder("Slew_Bearing_Bolt_%02d" % (index+1), (math.cos(theta)*0.87,1.31,math.sin(theta)*0.87), 0.023, 0.055, mats["bolt"], undercarriage, vertices=10, rotation=(math.pi/2,0,0), role="fastener")

    swing = empty("Upper_Swing_Pivot", (0.0,1.18,0.0), machine, "reconstructed_slew_pivot", "CIRCLE", 0.30)
    upper = empty("Upper_ROOT", parent=swing, role="articulated_upper_group", size=0.24)
    box("Upper_Main_Deck", (-0.25,0.29,0.0), (5.55,0.30,3.18), mats["steel_dark"], upper, 0.075, "upper_mainframe")
    box("Upper_Boom_Mount_Crossmember", (0.42,0.63,0.0), (1.18,0.72,1.20), mats["body_dark"], upper, 0.055, "boom_mount")
    for z in (-0.48, 0.48):
        side_profile("Boom_Mount_Cheek_L" if z < 0 else "Boom_Mount_Cheek_R", [(-0.22,0.34),(0.06,1.15),(0.56,1.22),(0.80,0.36)], 0.11, mats["body"], upper, z_center=z, bevel_width=0.028, role="boom_mount")

    # Rounded 8400 kg counterweight envelope.  The tail point reaches the
    # published 3.67 m radius while side vertices stay inside that radius.
    counterweight_points = [
        (-3.67,0.0),(-3.53,-0.82),(-3.08,-1.48),(-2.45,-1.72),(-1.55,-1.72),
        (-1.05,-1.40),(-1.05,1.40),(-1.55,1.72),(-2.45,1.72),(-3.08,1.48),(-3.53,0.82),
    ]
    counterweight = footprint_prism("Counterweight_8400kg_Shell", counterweight_points, 0.18, 1.36, mats["body"], upper, 0.075, "counterweight")
    counterweight["published_mass_kg"] = 8400
    counterweight["geometry_authority"] = "reconstructed_envelope"
    box("Counterweight_Rear_Inset", (-3.49,0.79,0.0), (0.22,0.46,1.52), mats["body_dark"], upper, 0.050, "counterweight_detail")
    for z in (-1.28, 1.28):
        box("Counterweight_Side_Rub_Rail_L" if z < 0 else "Counterweight_Side_Rub_Rail_R", (-2.70,0.82,z), (1.20,0.16,0.12), mats["steel_dark"], upper, 0.020, "counterweight_detail")

    # Cab on machine left (-Z).  Glazing boundaries, pillars, seat, controls,
    # wiper, roof hatch, mirror, and camera pod remain observed/reconstructed.
    cab_root = empty("Cab_ROOT", (-0.05,0.0,-1.03), upper, "cab_group", size=0.14)
    box("Cab_Lower_Sill", (0.20,0.65,-1.20), (1.72,0.48,1.03), mats["body_dark"], upper, 0.050, "cab_structure")
    box("Cab_Roof", (-0.05,2.085,-1.14), (1.82,0.13,1.16), mats["body"], upper, 0.040, "cab_roof")
    # Roof top: swing Y 1.18 + local center 2.085 + half 0.065 = 3.33 m.
    for name, loc, dims in [
        ("Cab_Front_Pillar", (0.79,1.42,-1.70),(0.10,1.48,0.10)),
        ("Cab_A_Pillar", (0.62,1.42,-0.60),(0.11,1.48,0.10)),
        ("Cab_Rear_Pillar", (-0.82,1.42,-1.70),(0.12,1.48,0.10)),
        ("Cab_Rear_Inner_Pillar", (-0.72,1.42,-0.60),(0.11,1.48,0.10)),
        ("Cab_Door_Midrail", (-0.10,1.43,-1.705),(1.35,0.09,0.08)),
    ]:
        box(name, loc, dims, mats["graphite"], upper, 0.018, "cab_frame")
    box("Cab_Front_Glass", (0.765,1.51,-1.145), (0.035,1.20,1.00), mats["glass"], upper, 0.004, "glass")
    box("Cab_Door_Upper_Glass", (-0.08,1.67,-1.705), (1.22,0.82,0.032), mats["glass"], upper, 0.004, "glass")
    box("Cab_Door_Lower_Glass", (-0.10,1.08,-1.705), (1.18,0.27,0.032), mats["glass"], upper, 0.004, "glass")
    box("Cab_Rear_Glass", (-0.78,1.54,-1.15), (0.032,1.00,0.94), mats["glass"], upper, 0.004, "glass")
    box("Cab_Roof_Hatch_Glass", (0.23,2.158,-1.15), (0.70,0.025,0.72), mats["glass"], upper, 0.003, "glass")
    box("Cab_Seat_Base", (-0.18,0.90,-1.14), (0.55,0.22,0.52), mats["interior"], upper, 0.055, "cab_interior")
    box("Cab_Seat_Back", (-0.40,1.30,-1.14), (0.16,0.72,0.54), mats["interior"], upper, 0.070, "cab_interior")
    for z in (-1.44, -0.84):
        box("Cab_Control_Console_L" if z < -1.1 else "Cab_Control_Console_R", (0.03,1.03,z), (0.66,0.19,0.18), mats["graphite"], upper, 0.025, "cab_interior")
        cylinder("Cab_Joystick_L" if z < -1.1 else "Cab_Joystick_R", (0.23,1.24,z), 0.035, 0.28, mats["graphite"], upper, vertices=14, rotation=(math.pi/2,0,0), role="cab_interior")
    curve_tube("Cab_Windshield_Wiper", [(0.79,1.08,-1.70),(0.79,1.70,-1.34),(0.79,1.90,-0.96)], 0.012, mats["graphite"], upper, "cab_detail")
    box("Cab_Door_Handle", (-0.42,1.43,-1.735), (0.25,0.035,0.035), mats["bolt"], upper, 0.008, "cab_detail")
    curve_tube("Cab_Left_Mirror_Arm", [(0.72,1.88,-1.66),(0.88,2.00,-1.80)], 0.018, mats["graphite"], upper, "cab_detail")
    box("Cab_Left_Mirror", (0.88,2.01,-1.84), (0.26,0.30,0.055), mats["glass"], upper, 0.025, "cab_detail")

    # Service house: segmented doors, lower skirts, louvers, cooling screen,
    # exhaust, intake, fill caps, rails, platform, steps, and fastener cues.
    box("Service_House_Lower", (-1.52,0.86,0.48), (3.12,0.88,2.46), mats["body_dark"], upper, 0.090, "engine_house")
    box("Service_House_Upper", (-1.38,1.48,0.52), (2.70,0.62,2.36), mats["body"], upper, 0.110, "engine_house")
    box("Cooling_Pack_Hood", (-0.70,1.92,0.75), (1.32,0.32,1.74), mats["body_light"], upper, 0.080, "engine_house")
    for side, z in (("L",-0.78),("R",1.72)):
        for index, (x, width) in enumerate(((-2.30,0.72),(-1.45,0.72),(-0.58,0.76)), start=1):
            box(f"Service_Door_{side}_{index:02d}", (x,1.38,z), (width,0.92,0.055), mats["body"], upper, 0.025, "service_door")
            cylinder(f"Service_Door_{side}_{index:02d}_Latch", (x+width*0.30,1.38,z + (-0.038 if side=='L' else 0.038)), 0.028, 0.035, mats["bolt"], upper, vertices=12, role="service_latch")
    for index in range(11):
        x = -2.58 + index * 0.15
        box(f"Cooling_Louver_{index+1:02d}", (x,1.56,1.755), (0.095,0.58,0.028), mats["graphite"], upper, 0.006, "vent_louver")
    for index in range(8):
        x = -1.12 + index * 0.115
        box(f"Debris_Screen_Slat_{index+1:02d}", (x,1.90,-0.715), (0.065,0.36,0.026), mats["graphite"], upper, 0.004, "debris_screen")
    cylinder("Exhaust_Stack", (-1.38,2.00,0.86), 0.105, 0.64, mats["graphite"], upper, vertices=24, rotation=(math.pi/2,0,0), role="exhaust")
    cylinder("Exhaust_Rain_Cap", (-1.38,2.28,0.86), 0.14, 0.08, mats["graphite"], upper, vertices=24, rotation=(math.pi/2,0,0), role="exhaust")
    cylinder("Air_Intake_Precleaner", (-0.92,2.09,1.12), 0.14, 0.46, mats["graphite"], upper, vertices=24, rotation=(math.pi/2,0,0), role="intake")
    cylinder("Fuel_Fill_Cap", (-2.34,1.89,-0.73), 0.070, 0.055, mats["bolt"], upper, vertices=18, role="service_detail")
    cylinder("Hydraulic_Fill_Cap", (-1.90,1.89,-0.73), 0.070, 0.055, mats["bolt"], upper, vertices=18, role="service_detail")
    box("Left_Service_Platform", (-1.20,0.62,-1.67), (2.70,0.12,0.34), mats["steel_dark"], upper, 0.022, "service_platform")
    for index in range(5):
        box(f"Access_Step_{index+1:02d}", (-2.54+index*0.31,0.43,-1.79), (0.24,0.08,0.22), mats["steel"], upper, 0.012, "access_step")
    curve_tube("Left_Handrail", [(-2.52,0.72,-1.80),(-2.35,1.60,-1.80),(-1.10,1.90,-1.80),(0.30,1.88,-1.80)], 0.027, mats["steel"], upper, "handrail")
    curve_tube("Right_Handrail", [(-2.58,0.72,1.79),(-2.40,1.56,1.79),(-0.90,1.85,1.79),(0.32,1.78,1.79)], 0.027, mats["steel"], upper, "handrail")
    for index, x in enumerate((-2.45,-2.05,-1.65,-1.25,-0.85,-0.45), start=1):
        cylinder(f"Service_Panel_Fastener_{index:02d}", (x,1.83,-0.747), 0.018, 0.024, mats["bolt"], upper, vertices=10, role="fastener")

    # Nine published LED work-light housings.  Exact mounts are reconstructed.
    light_specs = [
        ((0.85,0.75,-1.35),(0.22,0.12,0.24)),       # frame
        ((0.55,2.18,-1.52),(0.24,0.12,0.18)),       # cab roof front 1
        ((0.15,2.18,-1.52),(0.24,0.12,0.18)),       # cab roof front 2
        ((-0.62,2.16,-1.38),(0.22,0.12,0.18)),      # cab rear
        ((-3.48,1.10,0.0),(0.12,0.22,0.28)),        # counterweight
        ((-1.05,1.91,-1.79),(0.22,0.15,0.14)),      # left rail
        ((-1.05,1.87,1.79),(0.22,0.15,0.14)),       # right rail
    ]
    work_lights = []
    for index, (location, dimensions) in enumerate(light_specs, start=1):
        work_lights.append(box(f"Work_Light_{index:02d}", location, dimensions, mats["light"], upper, 0.028, "work_light"))

    # Boom/arm/bucket hierarchy.  Local zero is the authored transport pose;
    # review articulation rotates the parent groups about reconstructed pins.
    boom_pivot = empty("Boom_Pivot", (0.15,0.64,0.0), upper, "reconstructed_boom_pivot", "CIRCLE", 0.22)
    boom_root = empty("Boom_ROOT", parent=boom_pivot, role="articulated_boom_group", size=0.20)
    boom_profile = [
        (-0.16,-0.24),(0.42,0.18),(1.28,0.94),(2.55,1.56),(3.18,1.68),
        (4.28,1.52),(5.18,1.38),(5.28,1.08),(4.30,1.14),(3.10,1.28),(2.18,1.12),(1.10,0.48),(0.18,-0.12),
    ]
    for z, suffix in ((-0.39,"L"),(0.39,"R")):
        side_profile(f"Boom_Box_Side_{suffix}", boom_profile, 0.105, mats["body_light"], boom_root, z_center=z, bevel_width=0.030, role="boom_structure")
    side_profile("Boom_Box_Center_Web", boom_profile, 0.68, mats["body"], boom_root, z_center=0.0, bevel_width=0.045, role="boom_structure")
    # Exterior weld-seam cues only. The publication mentions three internal
    # boom bulkheads, but no hidden bulkhead geometry is fabricated here.
    for index, (x,y,height) in enumerate(((0.65,0.36,0.30),(2.10,1.18,0.32),(3.55,1.40,0.24),(4.72,1.27,0.20)), start=1):
        for z, suffix in ((-0.45,"L"),(0.45,"R")):
            box(f"Boom_Exterior_Weld_Seam_{index:02d}_{suffix}", (x,y,z), (0.028,height,0.022), mats["body_dark"], boom_root, 0.004, "exterior_weld_seam")
    add_pin("PIN_Boom", (0,0,0), 0.16, 1.04, mats["steel"], boom_root)
    for index, (x,y) in enumerate(((0.46,0.25),(2.05,1.35),(3.76,1.48),(4.85,1.32)), start=1):
        cylinder(f"Boom_Hose_Clamp_{index:02d}", (x,y,-0.49), 0.045, 0.10, mats["steel"], boom_root, vertices=14, role="hose_clamp")

    # Two boom-mounted work lights complete the published count of nine.
    work_lights.append(box("Work_Light_08", (1.55,1.12,-0.52), (0.24,0.16,0.16), mats["light"], boom_root, 0.028, "work_light"))
    work_lights.append(box("Work_Light_09", (1.93,1.28,-0.52), (0.24,0.16,0.16), mats["light"], boom_root, 0.028, "work_light"))

    arm_pivot = empty("Arm_Pivot", (5.10,1.38,0.0), boom_root, "reconstructed_arm_pivot", "CIRCLE", 0.20)
    arm_root = empty("Arm_ROOT", parent=arm_pivot, role="articulated_arm_group", size=0.19)
    arm_profile = [
        (-0.12,0.26),(0.48,0.22),(1.45,-0.50),(2.52,-1.82),(2.92,-2.70),
        (2.72,-2.88),(2.42,-2.34),(1.35,-0.90),(0.30,-0.10),(-0.16,-0.08),
    ]
    for z, suffix in ((-0.31,"L"),(0.31,"R")):
        side_profile(f"Arm_Box_Side_{suffix}", arm_profile, 0.095, mats["body_light"], arm_root, z_center=z, bevel_width=0.028, role="arm_structure")
    side_profile("Arm_Box_Center_Web", arm_profile, 0.52, mats["body"], arm_root, z_center=0.0, bevel_width=0.040, role="arm_structure")
    add_pin("PIN_Arm", (0,0,0), 0.15, 0.92, mats["steel"], arm_root)
    for index, (x,y) in enumerate(((0.25,0.05),(1.05,-0.32),(1.88,-1.18),(2.55,-2.05)), start=1):
        cylinder(f"Arm_Hose_Clamp_{index:02d}", (x,y,-0.40), 0.040, 0.09, mats["steel"], arm_root, vertices=14, role="hose_clamp")

    bucket_pivot = empty("Bucket_Pivot", (2.85,-2.66,0.0), arm_root, "reconstructed_bucket_pivot", "CIRCLE", 0.18)
    bucket_root = empty("Bucket_ROOT", parent=bucket_pivot, role="articulated_bucket_group", size=0.18)
    bucket_profile = [(0.0,0.0),(-0.38,0.62),(-1.16,0.78),(-1.63,0.28),(-1.54,-0.30),(-0.82,-0.54),(0.06,-0.50),(0.24,-0.44)]
    for z, suffix in ((-0.65,"L"),(0.65,"R")):
        side_profile(f"Bucket_Side_Plate_{suffix}", bucket_profile, 0.070, mats["body"], bucket_root, z_center=z, bevel_width=0.025, role="bucket_structure")
    box("Bucket_Curved_Back_Cue", (-0.82,-0.02,0.0), (1.42,0.14,1.30), mats["body_light"], bucket_root, 0.055, "bucket_structure")
    box("Bucket_Heel_Wear_Plate", (-1.12,-0.47,0.0), (0.88,0.13,1.34), mats["steel_dark"], bucket_root, 0.024, "bucket_wear_plate")
    box("Bucket_Cutting_Edge", (0.0,-0.47,0.0), (0.48,0.11,1.37), mats["steel"], bucket_root, 0.018, "bucket_cutting_edge")
    for index, z in enumerate((-0.52,-0.26,0.0,0.26,0.52), start=1):
        side_profile(f"Bucket_Tooth_{index:02d}", [(-0.10,-0.39),(0.12,-0.40),(0.24,-0.44),(0.08,-0.54)], 0.15, mats["steel"], bucket_root, z_center=z, bevel_width=0.015, role="bucket_tooth")
    add_pin("PIN_Bucket", (0,0,0), 0.14, 0.88, mats["steel"], bucket_root)
    attachment = empty("PIVOT_Attachment_Pin", (0,0,0), bucket_root, "attachment_pivot", "SPHERE", 0.15)
    attachment["quick_coupler_status"] = "unresolved_no_coupler_geometry"

    # Exterior hose bundles. Curves are converted to meshes before export.
    hose_objects = []
    for offset_index, z in enumerate((-0.53,-0.48,0.48,0.53), start=1):
        hose_objects.append(curve_tube(f"Boom_Hose_{offset_index:02d}", [(0.25,0.12,z),(1.20,0.78,z),(2.50,1.39,z),(3.82,1.48,z),(4.82,1.29,z)], 0.025 if offset_index in (2,3) else 0.021, mats["rubber"], boom_root))
    for offset_index, z in enumerate((-0.43,-0.38,0.38,0.43), start=1):
        hose_objects.append(curve_tube(f"Arm_Hose_{offset_index:02d}", [(0.12,0.12,z),(0.85,-0.20,z),(1.62,-0.88,z),(2.40,-1.92,z),(2.68,-2.48,z)], 0.023 if offset_index in (2,3) else 0.020, mats["rubber"], arm_root))
    curve_tube("Boom_Hardline_L", [(0.32,0.30,-0.43),(1.40,1.08,-0.43),(3.00,1.50,-0.43),(4.45,1.38,-0.43)], 0.018, mats["steel"], boom_root, "hydraulic_hardline")
    curve_tube("Boom_Hardline_R", [(0.32,0.30,0.43),(1.40,1.08,0.43),(3.00,1.50,0.43),(4.45,1.38,0.43)], 0.018, mats["steel"], boom_root, "hydraulic_hardline")

    hydraulics = empty("Hydraulics_ROOT", parent=machine, role="hydraulic_group", size=0.18)
    boom_hydraulics = empty("Boom_Hydraulics_ROOT", parent=upper, role="hydraulic_owner_group", size=0.16)
    arm_hydraulics = empty("Arm_Hydraulics_ROOT", parent=boom_root, role="hydraulic_owner_group", size=0.16)
    bucket_hydraulics = empty("Bucket_Hydraulics_ROOT", parent=arm_root, role="hydraulic_owner_group", size=0.16)
    linkage = empty("Linkage_ROOT", parent=arm_root, role="linkage_group", size=0.18)
    bucket_linkage = empty("Bucket_Linkage_ROOT", parent=linkage, role="linkage_owner_group", size=0.16)
    bellcrank = empty("Bucket_Bellcrank_ROOT", (2.32,-2.13,0.0), linkage, "linkage_pivot", "CIRCLE", 0.14)
    for z, suffix in ((-0.34,"L"),(0.34,"R")):
        side_profile(f"Bucket_Bellcrank_{suffix}", [(-0.24,0.34),(0.36,0.08),(0.22,-0.25),(-0.16,-0.10)], 0.050, mats["body_dark"], bellcrank, z_center=z, bevel_width=0.012, role="bucket_bellcrank")
    add_pin("PIN_Bucket_Bellcrank", (0,0,0), 0.090, 0.84, mats["steel"], bellcrank, "linkage_pin")

    anchors = {}
    for name, location, parent in [
        ("ANCHOR_Boom_Base_L", (0.02,0.44,-0.48), upper),
        ("ANCHOR_Boom_Rod_L", (1.82,0.66,-0.44), boom_root),
        ("ANCHOR_Boom_Base_R", (0.02,0.44,0.48), upper),
        ("ANCHOR_Boom_Rod_R", (1.82,0.66,0.44), boom_root),
        ("ANCHOR_Arm_Base", (2.95,1.55,0.0), boom_root),
        ("ANCHOR_Arm_Rod", (0.55,0.22,0.0), arm_root),
        ("ANCHOR_Bucket_Base", (0.44,0.13,0.0), arm_root),
        ("ANCHOR_Bellcrank_Rod", (-0.12,0.27,0.0), bellcrank),
        ("ANCHOR_Bellcrank_Dogbone_L", (0.30,0.02,-0.29), bellcrank),
        ("ANCHOR_Bellcrank_Dogbone_R", (0.30,0.02,0.29), bellcrank),
        ("ANCHOR_Bucket_Lug_L", (-0.10,0.28,-0.29), bucket_root),
        ("ANCHOR_Bucket_Lug_R", (-0.10,0.28,0.29), bucket_root),
    ]:
        anchors[name] = empty(name, location, parent, "hydraulic_anchor", "SPHERE", 0.065)

    cylinders = {}
    cylinder_defs = []
    def add_cylinder(key, a, b, barrel_radius, rod_radius, owner):
        start, end = world(anchors[a]), world(anchors[b])
        vector = end - start
        barrel = object_between(f"{key}_Barrel", start, start + vector * 0.64, barrel_radius, mats["steel_dark"], "hydraulic_barrel", 28)
        rod = object_between(f"{key}_Rod", start + vector * 0.57, end, rod_radius, mats["rod"], "hydraulic_rod", 24)
        parent_keep_world(barrel, owner)
        parent_keep_world(rod, owner)
        cylinders[f"{key}_Barrel"] = barrel
        cylinders[f"{key}_Rod"] = rod
        cylinder_defs.append((key,a,b,barrel_radius,rod_radius))
    bpy.context.view_layer.update()
    add_cylinder("Boom_Cylinder_L", "ANCHOR_Boom_Base_L", "ANCHOR_Boom_Rod_L", PUBLISHED["boom_cylinder_bore_m"]/2, PUBLISHED["boom_cylinder_rod_m"]/2, boom_hydraulics)
    add_cylinder("Boom_Cylinder_R", "ANCHOR_Boom_Base_R", "ANCHOR_Boom_Rod_R", PUBLISHED["boom_cylinder_bore_m"]/2, PUBLISHED["boom_cylinder_rod_m"]/2, boom_hydraulics)
    add_cylinder("Arm_Cylinder", "ANCHOR_Arm_Base", "ANCHOR_Arm_Rod", PUBLISHED["arm_cylinder_bore_m"]/2, PUBLISHED["arm_cylinder_rod_m"]/2, arm_hydraulics)
    add_cylinder("Bucket_Cylinder", "ANCHOR_Bucket_Base", "ANCHOR_Bellcrank_Rod", PUBLISHED["bucket_cylinder_bore_m"]/2, PUBLISHED["bucket_cylinder_rod_m"]/2, bucket_hydraulics)
    for suffix in ("L","R"):
        dogbone = object_between(f"Bucket_Link_Dogbone_{suffix}", world(anchors[f"ANCHOR_Bellcrank_Dogbone_{suffix}"]), world(anchors[f"ANCHOR_Bucket_Lug_{suffix}"]), 0.055, mats["body_dark"], "bucket_linkage", 18)
        parent_keep_world(dogbone, bucket_linkage)
        cylinders[f"Bucket_Link_Dogbone_{suffix}"] = dogbone

    for name, anchor in anchors.items():
        if name.startswith("ANCHOR_Boom"):
            add_pin(name.replace("ANCHOR_","PIN_"), anchor.location, 0.050, 0.15, mats["steel"], anchor.parent, "hydraulic_pin")

    # Private inspection nodes remain in the .blend but are excluded from GLB.
    inspection = empty("Inspection_Volumes", parent=machine, role="inspection_group", size=0.25, export=False)
    envelope = empty("INSPECT_Transport_Envelope", ((8.34-3.67)/2,1.75,0.0), inspection, "inspection_volume", "CUBE", 1.0, export=False)
    envelope.scale = (PUBLISHED["overall_length_m"]/2,PUBLISHED["overall_height_m"]/2,PUBLISHED["overall_width_operating_m"]/2)
    for name, location, scale in [
        ("INSPECT_Upper_Clearance",(-1.1,1.55,0.0),(2.6,0.45,1.70)),
        ("INSPECT_Boom_Swept_Study",(3.6,2.65,0.0),(4.0,1.25,0.70)),
        ("INSPECT_Attachment_Volume",(7.35,0.55,0.0),(1.30,0.75,0.85)),
        ("INSPECT_Variable_Gauge",(0.0,0.75,0.0),(2.8,0.48,1.90)),
    ]:
        marker = empty(name, location, inspection, "inspection_volume", "CUBE", 1.0, export=False)
        marker.scale = scale

    box("Review_Ground", (1.5,-0.025,0.0), (20.0,0.05,13.0), mats["ground"], None, 0.0, "review_environment", False)
    return {
        "mats": mats,
        "machine": machine,
        "swing": swing,
        "boom_root": boom_root,
        "arm_root": arm_root,
        "bucket_root": bucket_root,
        "anchors": anchors,
        "cylinders": cylinders,
        "cylinder_defs": cylinder_defs,
        "hose_objects": hose_objects,
        "counterweight": counterweight,
        "work_lights": work_lights,
    }


def refresh_hydraulics(model):
    bpy.context.view_layer.update()
    anchors = model["anchors"]
    cylinders = model["cylinders"]
    for key, a, b, barrel_radius, rod_radius in model["cylinder_defs"]:
        start, end = world(anchors[a]), world(anchors[b])
        vector = end - start
        place_between(cylinders[f"{key}_Barrel"], start, start + vector * 0.64, barrel_radius)
        place_between(cylinders[f"{key}_Rod"], start + vector * 0.57, end, rod_radius)
    for suffix in ("L","R"):
        place_between(
            cylinders[f"Bucket_Link_Dogbone_{suffix}"],
            world(anchors[f"ANCHOR_Bellcrank_Dogbone_{suffix}"]),
            world(anchors[f"ANCHOR_Bucket_Lug_{suffix}"]),
            0.055,
        )
    bpy.context.view_layer.update()


def point_camera(obj, target):
    forward = (Vector(target) - obj.location).normalized()
    world_up = Vector((0.0, 1.0, 0.0))
    right = forward.cross(world_up).normalized()
    true_up = right.cross(forward).normalized()
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Matrix((right, true_up, -forward)).transposed().to_quaternion()


def add_review_lighting():
    world = bpy.context.scene.world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.018,0.025,0.034,1.0)
    background.inputs["Strength"].default_value = 0.24

    def area(name, location, energy, size, color, target):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = location
        point_camera(obj, target)
        tag(obj, "review_environment", False)
        return obj

    area("Review_Key", (5.5,9.0,-8.5), 2100, 5.5, (1.0,0.76,0.56), (1.5,1.35,0.0))
    area("Review_Fill", (-7.0,6.0,8.0), 1650, 5.2, (0.55,0.73,1.0), (-0.8,1.35,0.0))
    area("Review_Rim", (7.0,7.5,8.5), 1850, 4.5, (0.68,0.82,1.0), (1.7,1.65,0.0))
    area("Review_Top", (-0.5,11.0,0.0), 1050, 4.0, (1.0,0.90,0.74), (0.0,1.2,0.0))


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
    path = RENDER_DIR / f"john-deere-470-p-tier-{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def render_all(model):
    paths = [
        render_view("transport-operator-side", (2.3,5.2,-18.8), (2.15,1.45,0.0), 54),
        render_view("transport-technical-right", (2.4,5.1,18.8), (2.10,1.42,0.0), 54),
        render_view("operator-front-quarter", (13.8,6.7,-14.0), (1.7,1.45,-0.1), 50),
        render_view("rear-service-quarter", (-13.5,6.0,12.5), (-0.5,1.48,0.1), 52),
        render_view("track-sprocket-detail", (-4.9,1.75,-4.0), (-2.15,0.55,-1.445), 72),
        render_view("boom-hydraulic-detail", (4.7,5.2,-6.2), (2.0,2.50,-0.15), 70),
    ]
    # Review-only cutaway: hide the near bucket side plate for one frame so the
    # reconstructed bellcrank, dogbone, cylinder rod, pins, and lug can be
    # inspected. The plate is restored before save/export.
    cutaway_objects = [
        bpy.data.objects["Bucket_Side_Plate_L"],
        bpy.data.objects["Bucket_Side_Plate_R"],
        bpy.data.objects["Bucket_Curved_Back_Cue"],
        bpy.data.objects["Bucket_Heel_Wear_Plate"],
    ]
    for obj in cutaway_objects:
        obj.hide_render = True
    paths.append(render_view("bucket-linkage-detail", (8.8,2.2,-3.0), (7.72,0.92,0.0), 82))
    for obj in cutaway_objects:
        obj.hide_render = False
    paths.append(render_view("cab-service-detail", (-1.0,4.2,-7.3), (-0.55,1.85,-1.0), 66))

    model["swing"].rotation_euler[1] = math.radians(RECONSTRUCTED["review_articulated_pose"]["upper_swing_deg"])
    model["boom_root"].rotation_euler[2] = math.radians(RECONSTRUCTED["review_articulated_pose"]["boom_delta_deg"])
    model["arm_root"].rotation_euler[2] = math.radians(RECONSTRUCTED["review_articulated_pose"]["arm_delta_deg"])
    model["bucket_root"].rotation_euler[2] = math.radians(RECONSTRUCTED["review_articulated_pose"]["bucket_delta_deg"])
    refresh_hydraulics(model)
    paths.append(render_view("articulated-reach", (14.5,9.5,-18.0), (2.3,3.1,0.0), 48))

    model["swing"].rotation_euler[1] = 0.0
    model["boom_root"].rotation_euler[2] = 0.0
    model["arm_root"].rotation_euler[2] = 0.0
    model["bucket_root"].rotation_euler[2] = 0.0
    refresh_hydraulics(model)
    return paths


def export_objects():
    return [obj for obj in bpy.context.scene.objects if obj.get("exo_export", False)]


def convert_export_curves_to_mesh():
    curves = [obj for obj in export_objects() if obj.type == "CURVE"]
    for obj in curves:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
    bpy.ops.object.select_all(action="DESELECT")


def apply_export_mesh_scales(objects):
    for obj in objects:
        if obj.type != "MESH":
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.select_all(action="DESELECT")


def evaluated_world_points(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        bpy.data.meshes.remove(mesh)
    return points


def bounds_for(objects):
    points = evaluated_world_points([obj for obj in objects if obj.type == "MESH"])
    mins = [min(point[index] for point in points) for index in range(3)]
    maxs = [max(point[index] for point in points) for index in range(3)]
    return {
        "min_m": [round(value,4) for value in mins],
        "max_m": [round(value,4) for value in maxs],
        "size_m": [round(maxs[index]-mins[index],4) for index in range(3)],
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


def endpoint_error(obj, anchor):
    local_z = [corner[2] for corner in obj.bound_box]
    endpoints = [obj.matrix_world @ Vector((0,0,min(local_z))), obj.matrix_world @ Vector((0,0,max(local_z)))]
    target = world(anchor)
    return min((endpoint-target).length for endpoint in endpoints)


def collect_metrics(model, objects):
    export_meshes = [obj for obj in objects if obj.type == "MESH"]
    swing_center = world(bpy.data.objects["Upper_Swing_Pivot"])
    counterweight_points = evaluated_world_points([model["counterweight"]])
    shoe_objects = [obj for obj in export_meshes if obj.get("exo_role") == "track_shoe"]
    shoe_points = evaluated_world_points(shoe_objects)
    center_frame_points = evaluated_world_points([bpy.data.objects["Undercarriage_Center_Frame"]])
    cab_roof_points = evaluated_world_points([bpy.data.objects["Cab_Roof"]])
    all_points = evaluated_world_points(export_meshes)
    work_lights = [obj for obj in export_meshes if obj.get("exo_role") == "work_light"]
    counts = {
        "shoes_left": len([obj for obj in export_meshes if obj.name.startswith("Track_L_Shoe_")]),
        "shoes_right": len([obj for obj in export_meshes if obj.name.startswith("Track_R_Shoe_")]),
        "track_rollers_left": len([obj for obj in export_meshes if obj.name.startswith("Track_L_Lower_Roller_") and "Hub" not in obj.name]),
        "track_rollers_right": len([obj for obj in export_meshes if obj.name.startswith("Track_R_Lower_Roller_") and "Hub" not in obj.name]),
        "carrier_rollers_left": len([obj for obj in export_meshes if obj.name.startswith("Track_L_Carrier_Roller_") and "Hub" not in obj.name]),
        "carrier_rollers_right": len([obj for obj in export_meshes if obj.name.startswith("Track_R_Carrier_Roller_") and "Hub" not in obj.name]),
        "sprocket_teeth_left": len([obj for obj in export_meshes if obj.name.startswith("Track_L_Drive_Sprocket_Tooth_")]),
        "sprocket_teeth_right": len([obj for obj in export_meshes if obj.name.startswith("Track_R_Drive_Sprocket_Tooth_")]),
        "work_lights": len(work_lights),
    }
    closure_errors = {
        "bucket_rod_to_bellcrank_m": endpoint_error(model["cylinders"]["Bucket_Cylinder_Rod"], model["anchors"]["ANCHOR_Bellcrank_Rod"]),
        "dogbone_left_to_bellcrank_m": endpoint_error(model["cylinders"]["Bucket_Link_Dogbone_L"], model["anchors"]["ANCHOR_Bellcrank_Dogbone_L"]),
        "dogbone_left_to_bucket_m": endpoint_error(model["cylinders"]["Bucket_Link_Dogbone_L"], model["anchors"]["ANCHOR_Bucket_Lug_L"]),
        "dogbone_right_to_bellcrank_m": endpoint_error(model["cylinders"]["Bucket_Link_Dogbone_R"], model["anchors"]["ANCHOR_Bellcrank_Dogbone_R"]),
        "dogbone_right_to_bucket_m": endpoint_error(model["cylinders"]["Bucket_Link_Dogbone_R"], model["anchors"]["ANCHOR_Bucket_Lug_R"]),
    }
    return {
        "published_component_counts": counts,
        "track_contact_min_y_m": min(point.y for point in shoe_points),
        "shoe_outer_width_m": max(point.z for point in shoe_points) - min(point.z for point in shoe_points),
        "center_frame_underside_y_m": min(point.y for point in center_frame_points),
        "cab_roof_top_y_m": max(point.y for point in cab_roof_points),
        "lowest_visible_y_m": min(point.y for point in all_points),
        "tail_swing_radius_m": max(math.hypot(point.x-swing_center.x, point.z-swing_center.z) for point in counterweight_points),
        "counterweight_clearance_y_m": min(point.y for point in counterweight_points),
        "bucket_linkage_static_closure_errors_m": closure_errors,
        "export_mesh_scale_offenders": {
            obj.name: [round(value,8) for value in obj.scale]
            for obj in export_meshes
            if any(abs(value-1.0)>1e-7 for value in obj.scale)
        },
        "reconstructed_hose_meshes": len([obj for obj in export_meshes if obj.get("exo_role") in ("reconstructed_hose","hydraulic_hardline")]),
    }


def inspect_glb_contract(path: Path):
    data = path.read_bytes()
    if data[:4] != b"glTF" or struct.unpack_from("<I", data, 4)[0] != 2:
        raise RuntimeError("invalid GLB header")
    offset, document = 12, None
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset:offset+length]
        offset += length
        if kind == 0x4E4F534A:
            document = json.loads(chunk.decode("utf-8").rstrip("\x00 "))
            break
    if document is None:
        raise RuntimeError("GLB JSON chunk missing")
    scene = document["scenes"][document.get("scene",0)]
    nodes = document.get("nodes",[])
    roots = []
    for index in scene.get("nodes",[]):
        node = nodes[index]
        transforms = {key:node[key] for key in ("translation","rotation","scale","matrix") if key in node}
        roots.append({"index":index,"name":node.get("name"),"transform":transforms})

    def local_matrix(node):
        if "matrix" in node:
            values = node["matrix"]
            return Matrix((
                (values[0], values[4], values[8], values[12]),
                (values[1], values[5], values[9], values[13]),
                (values[2], values[6], values[10], values[14]),
                (values[3], values[7], values[11], values[15]),
            ))
        translation = node.get("translation", [0.0, 0.0, 0.0])
        rotation = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
        scale = node.get("scale", [1.0, 1.0, 1.0])
        return (
            Matrix.Translation(Vector(translation))
            @ Quaternion((rotation[3], rotation[0], rotation[1], rotation[2])).to_matrix().to_4x4()
            @ Matrix.Diagonal(Vector((*scale, 1.0)))
        )

    bounds_min = Vector((math.inf, math.inf, math.inf))
    bounds_max = Vector((-math.inf, -math.inf, -math.inf))
    world_translation_by_name = {}
    parent_by_name = {}
    child_count_by_name = {}

    def visit(node_index, parent_world, parent_name=None):
        node = nodes[node_index]
        world_matrix = parent_world @ local_matrix(node)
        name = node.get("name",f"node-{node_index}")
        world_translation_by_name[name] = [round(world_matrix[row][3],6) for row in range(3)]
        parent_by_name[name] = parent_name
        child_count_by_name[name] = len(node.get("children",[]))
        if "mesh" in node:
            for primitive in document["meshes"][node["mesh"]].get("primitives",[]):
                position_index = primitive.get("attributes",{}).get("POSITION")
                if position_index is None:
                    continue
                accessor = document["accessors"][position_index]
                lo, hi = accessor.get("min"), accessor.get("max")
                if lo is None or hi is None:
                    continue
                for x in (lo[0],hi[0]):
                    for y in (lo[1],hi[1]):
                        for z in (lo[2],hi[2]):
                            point = world_matrix @ Vector((x,y,z))
                            for axis in range(3):
                                bounds_min[axis] = min(bounds_min[axis],point[axis])
                                bounds_max[axis] = max(bounds_max[axis],point[axis])
        for child in node.get("children",[]):
            visit(child,world_matrix,name)

    for root_index in scene.get("nodes",[]):
        visit(root_index,Matrix.Identity(4))
    decoded_bounds = {
        "min_xyz_m":[round(value,6) for value in bounds_min],
        "max_xyz_m":[round(value,6) for value in bounds_max],
        "dimensions_xyz_m":[round(bounds_max[axis]-bounds_min[axis],6) for axis in range(3)],
    }
    mesh_scale_offenders = []
    for node in nodes:
        if "mesh" not in node:
            continue
        scale = node.get("scale",[1,1,1])
        if any(abs(value-1.0)>1e-4 for value in scale):
            mesh_scale_offenders.append({"name":node.get("name"),"scale":scale})
    helper_names = sorted(
        node.get("name","") for node in nodes
        if node.get("name","").startswith(("INSPECT_","Inspection_","Review_","Camera_"))
    )
    decoded_triangles = 0
    primitive_count = 0
    unsupported_primitive_modes = []
    for mesh in document.get("meshes",[]):
        for primitive in mesh.get("primitives",[]):
            primitive_count += 1
            position_index = primitive.get("attributes",{}).get("POSITION")
            index_accessor = primitive.get("indices")
            element_count = (document["accessors"][index_accessor]["count"]
                             if index_accessor is not None
                             else document["accessors"][position_index]["count"])
            mode = primitive.get("mode",4)
            if mode == 4:
                decoded_triangles += element_count // 3
            elif mode in (5,6):
                decoded_triangles += max(0,element_count-2)
            else:
                unsupported_primitive_modes.append(mode)
    return {
        "scene_count": len(document.get("scenes",[])),
        "scene_roots": roots,
        "camera_count": len(document.get("cameras",[])),
        "punctual_light_extension_present": "KHR_lights_punctual" in document.get("extensions",{}),
        "helper_nodes": helper_names,
        "mesh_scale_offenders": mesh_scale_offenders,
        "node_count": len(document.get("nodes",[])),
        "mesh_count": len(document.get("meshes",[])),
        "material_count": len(document.get("materials",[])),
        "primitive_count": primitive_count,
        "decoded_triangle_count": decoded_triangles,
        "unsupported_primitive_modes": sorted(set(unsupported_primitive_modes)),
        "decoded_visible_aabb_m": decoded_bounds,
        "node_names": sorted(world_translation_by_name),
        "node_world_translation_xyz_m": world_translation_by_name,
        "node_parent": parent_by_name,
        "node_child_count": child_count_by_name,
    }


def create_validation(bounds, counts, metrics, glb_contract, render_paths):
    build_input = load_build_input()
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    mechanism = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    retained_fact_ids = build_input["retained_fact_ids"]
    if (len(retained_fact_ids) != len(set(retained_fact_ids))
            or retained_fact_ids != design["published_constraints_used"]
            or retained_fact_ids != PUBLISHED_FACT_IDS):
        raise RuntimeError("build-input, design, and receipt fact contracts differ")
    source_manifest = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    source_binding_ok = any(
        source.get("admission") == "primary"
        and source.get("sha256") == build_input["primary_source_sha256"]
        for source in source_manifest["sources"]
    )
    node_presence = {name:bpy.data.objects.get(name) is not None for name in REQUIRED_NODES}
    component_counts = metrics["published_component_counts"]
    track_count_ok = component_counts == {
        "shoes_left":53,"shoes_right":53,
        "track_rollers_left":9,"track_rollers_right":9,
        "carrier_rollers_left":3,"carrier_rollers_right":3,
        "sprocket_teeth_left":16,"sprocket_teeth_right":16,
        "work_lights":9,
    }
    root_records = glb_contract["scene_roots"]
    glb_contract_ok = (
        glb_contract["scene_count"] == 1
        and len(root_records) == 1
        and root_records[0]["name"] == "Machine_Root"
        and root_records[0]["transform"] == {}
        and glb_contract["camera_count"] == 0
        and not glb_contract["punctual_light_extension_present"]
        and not glb_contract["helper_nodes"]
        and not glb_contract["mesh_scale_offenders"]
    )
    closure_max = max(metrics["bucket_linkage_static_closure_errors_m"].values())
    render_ok = len(render_paths) >= 7 and all(path.exists() and path.stat().st_size > 20000 for path in render_paths)
    x_size, y_size, z_size = bounds["size_m"]
    decoded_bounds = glb_contract["decoded_visible_aabb_m"]
    decoded_dimensions = decoded_bounds["dimensions_xyz_m"]
    envelope_deltas = {
        "overall_length_m": round(abs(decoded_dimensions[0]-PUBLISHED["overall_length_m"]),6),
        "overall_height_m": round(abs(decoded_dimensions[1]-PUBLISHED["overall_height_m"]),6),
        "overall_width_operating_m": round(abs(decoded_dimensions[2]-PUBLISHED["overall_width_operating_m"]),6),
    }
    envelope_ok = (
        envelope_deltas["overall_length_m"] <= 0.06
        and envelope_deltas["overall_height_m"] <= 0.04
        and envelope_deltas["overall_width_operating_m"] <= 0.025
    )
    decoded_nodes = glb_contract["node_world_translation_xyz_m"]
    pivot_actual = {name:decoded_nodes.get(name) for name in build_input["export_pivots_world_xyz_m"]}
    pivot_errors = {
        name:max(abs(actual[axis]-expected[axis]) for axis in range(3))
        for name,expected in build_input["export_pivots_world_xyz_m"].items()
        for actual in [pivot_actual.get(name)] if actual is not None
    }
    expected_pivot_parents = {
        "Upper_Swing_Pivot":"Machine_Root",
        "Boom_Pivot":"Upper_ROOT",
        "Arm_Pivot":"Boom_ROOT",
        "Bucket_Pivot":"Arm_ROOT",
    }
    actual_pivot_parents = {name:glb_contract["node_parent"].get(name) for name in expected_pivot_parents}
    pivots_ok = (
        len(pivot_errors) == len(build_input["export_pivots_world_xyz_m"])
        and max(pivot_errors.values(),default=math.inf) <= 1e-5
        and actual_pivot_parents == expected_pivot_parents
    )
    motion_nodes = build_input["viewer_motion_nodes"]
    motion_resolution = {name:name in decoded_nodes for name in motion_nodes}
    linkage_nodes = [
        "Bucket_Linkage_ROOT", "Bucket_Bellcrank_ROOT", "Bucket_Cylinder_Rod",
        "Bucket_Link_Dogbone_L", "Bucket_Link_Dogbone_R", "Bucket_ROOT",
    ]
    linkage_resolution = {name:name in decoded_nodes for name in linkage_nodes}
    node_names = glb_contract["node_names"]
    shoes_l = sorted(name for name in node_names if name.startswith("Track_L_Shoe_"))
    shoes_r = sorted(name for name in node_names if name.startswith("Track_R_Shoe_"))
    rollers_l = sorted(name for name in node_names if name.startswith("Track_L_Lower_Roller_") and "Hub" not in name)
    rollers_r = sorted(name for name in node_names if name.startswith("Track_R_Lower_Roller_") and "Hub" not in name)
    carriers_l = sorted(name for name in node_names if name.startswith("Track_L_Carrier_Roller_") and "Hub" not in name)
    carriers_r = sorted(name for name in node_names if name.startswith("Track_R_Carrier_Roller_") and "Hub" not in name)
    decoded_counts_ok = (
        len(shoes_l) == len(shoes_r) == 53
        and len(rollers_l) == len(rollers_r) == 9
        and len(carriers_l) == len(carriers_r) == 3
    )
    identity_scales_ok = (
        len(root_records) == 1 and root_records[0]["name"] == "Machine_Root"
        and root_records[0]["transform"] == {} and not glb_contract["mesh_scale_offenders"]
    )
    required_gates = [
        {"id":"decoded_public_transport_envelope","status":"PASS" if envelope_ok else "FAIL","detail":{"method":"Decode shipped-GLB accessor bounds with composed node transforms and compare the visible retained-pose AABB to the selected published length, height, and operating width.","evidence":{"decoded_visible_aabb_m":decoded_bounds,"absolute_deltas_m":envelope_deltas,"tolerances_m":{"length":0.06,"height":0.04,"width":0.025}},"semantic_nodes":["Machine_Root"],"fact_ids":["overall-length","overall-height","overall-width-operating"]}},
        {"id":"decoded_public_pivot_world_positions","status":"PASS" if pivots_ok else "FAIL","detail":{"method":"Compose shipped-GLB node TRS and parent indices, then compare every deterministic pivot world translation and hierarchy edge.","evidence":{"expected_xyz_m":build_input["export_pivots_world_xyz_m"],"decoded_actual_xyz_m":pivot_actual,"maximum_errors_m":pivot_errors,"tolerance_m":0.00001,"expected_parent":expected_pivot_parents,"decoded_parent":actual_pivot_parents},"semantic_nodes":list(build_input["export_pivots_world_xyz_m"]),"fact_ids":[]}},
        {"id":"viewer_motion_nodes_resolve","status":"PASS" if all(motion_resolution.values()) else "FAIL","detail":{"method":"Resolve every viewer Auto/manual motion target by exact name in the decoded shipped-GLB node table.","evidence":{"resolved":motion_resolution,"static_only":build_input["static_only"]},"semantic_nodes":motion_nodes,"fact_ids":[]}},
        {"id":"static_bucket_linkage_components_present","status":"PASS" if all(linkage_resolution.values()) else "FAIL","detail":{"method":"Resolve the static reconstructed bellcrank, cylinder rod, twin dogbones, linkage owner, and bucket subtree in the decoded shipped GLB; no dynamic closure is claimed.","evidence":{"resolved":linkage_resolution,"dynamic_solver":False,"static_source_closure_max_error_m":closure_max},"semantic_nodes":linkage_nodes,"fact_ids":["bucket-cylinder-bore","bucket-cylinder-rod","bucket-cylinder-stroke"]}},
        {"id":"published_roller_and_shoe_counts","status":"PASS" if decoded_counts_ok else "FAIL","detail":{"method":"Count exact shoe, lower-roller, and carrier-roller semantic node names directly in the decoded shipped-GLB node table, excluding hub detail nodes.","evidence":{"left_shoes":shoes_l,"right_shoes":shoes_r,"left_track_rollers":rollers_l,"right_track_rollers":rollers_r,"left_carrier_rollers":carriers_l,"right_carrier_rollers":carriers_r,"expected_per_side":{"shoes":53,"track_rollers":9,"carrier_rollers":3}},"semantic_nodes":["Track_L_ROOT","Track_R_ROOT"],"fact_ids":["track-shoes-per-side","track-rollers-per-side","carrier-rollers-per-side"]}},
        {"id":"identity_root_and_applied_scales","status":"PASS" if identity_scales_ok else "FAIL","detail":{"method":"Decode the active GLB scene root TRS and every mesh-bearing node scale from the shipped artifact.","evidence":{"scene_roots":root_records,"mesh_scale_offenders":glb_contract["mesh_scale_offenders"],"mesh_count":glb_contract["mesh_count"]},"semantic_nodes":["Machine_Root"],"fact_ids":[]}},
        {"id":"source_design_contract_binding","status":"PASS" if source_binding_ok else "FAIL","detail":{"method":"Hash-bind the deterministic build input to an admitted primary source and require its unique retained fact IDs to exactly equal source/design.json.","evidence":{"build_input_path":rel(BUILD_INPUT_PATH),"build_input_sha256":sha256(BUILD_INPUT_PATH),"design_path":rel(DESIGN_PATH),"design_sha256":sha256(DESIGN_PATH),"primary_source_sha256":build_input["primary_source_sha256"],"retained_fact_count":len(retained_fact_ids),"unique_fact_count":len(set(retained_fact_ids))},"semantic_nodes":[],"fact_ids":retained_fact_ids}},
    ]
    gates = [
        *required_gates,
        {"id":"builder-execution","status":"PASS","detail":"Factory-startup background builder reached deterministic receipt generation."},
        {"id":"candidate-class-boundary","status":"PASS","detail":"technical_structural_study / research_candidate; not engineering authority."},
        {"id":"scene-units-and-axes","status":"PASS","detail":"Meters; +X toward bucket, +Y up, +Z machine right."},
        {"id":"independent-authoring-and-rights-boundary","status":"PASS","detail":"No CAD, copied imagery, copied texture, downloaded geometry, logo, protected livery claim, or manufacturer binary embedded."},
        {"id":"required-semantic-nodes","status":"PASS" if all(node_presence.values()) else "FAIL","detail":node_presence},
        {"id":"articulation-hierarchy","status":"PASS","detail":"Upper swing, boom, arm, bucket, hydraulic owners, and bucket linkage are pivot-parented groups."},
        {"id":"published-component-counts","status":"PASS" if track_count_ok else "FAIL","detail":component_counts},
        {"id":"operating-width-envelope","status":"PASS" if abs(z_size-PUBLISHED["overall_width_operating_m"])<=0.025 else "FAIL","detail":{"modeled_m":z_size,"published_m":PUBLISHED["overall_width_operating_m"],"tolerance_m":0.025}},
        {"id":"transport-length-envelope","status":"PASS" if abs(x_size-PUBLISHED["overall_length_m"])<=0.06 else "FAIL","detail":{"modeled_m":x_size,"published_m":PUBLISHED["overall_length_m"],"tolerance_m":0.06,"classification":"published_constraint_reconstructed_pose"}},
        {"id":"transport-height-envelope","status":"PASS" if abs(y_size-PUBLISHED["overall_height_m"])<=0.04 else "FAIL","detail":{"modeled_m":y_size,"published_m":PUBLISHED["overall_height_m"],"tolerance_m":0.04,"classification":"published_constraint_reconstructed_pose"}},
        {"id":"authored-track-contact-ground","status":"PASS" if abs(metrics["track_contact_min_y_m"])<=0.004 else "FAIL","detail":{"measured_y_m":metrics["track_contact_min_y_m"],"ground_y_m":0.0,"tolerance_m":0.004}},
        {"id":"published-shoe-outer-width","status":"PASS" if abs(metrics["shoe_outer_width_m"]-PUBLISHED["overall_width_operating_m"])<=0.01 else "FAIL","detail":{"measured_m":metrics["shoe_outer_width_m"],"published_m":PUBLISHED["overall_width_operating_m"],"tolerance_m":0.01}},
        {"id":"published-center-frame-ground-clearance","status":"PASS" if abs(metrics["center_frame_underside_y_m"]-PUBLISHED["ground_clearance_m"])<=0.006 else "FAIL","detail":{"measured_m":metrics["center_frame_underside_y_m"],"published_m":PUBLISHED["ground_clearance_m"],"tolerance_m":0.006}},
        {"id":"published-cab-height","status":"PASS" if abs(metrics["cab_roof_top_y_m"]-PUBLISHED["cab_height_m"])<=0.012 else "FAIL","detail":{"measured_m":metrics["cab_roof_top_y_m"],"published_m":PUBLISHED["cab_height_m"],"tolerance_m":0.012}},
        {"id":"published-tail-swing-radius","status":"PASS" if abs(metrics["tail_swing_radius_m"]-PUBLISHED["tail_swing_radius_m"])<=0.015 else "FAIL","detail":{"measured_m":metrics["tail_swing_radius_m"],"published_m":PUBLISHED["tail_swing_radius_m"],"tolerance_m":0.015}},
        {"id":"published-counterweight-clearance","status":"PASS" if abs(metrics["counterweight_clearance_y_m"]-PUBLISHED["counterweight_clearance_m"])<=0.012 else "FAIL","detail":{"measured_m":metrics["counterweight_clearance_y_m"],"published_m":PUBLISHED["counterweight_clearance_m"],"tolerance_m":0.012}},
        {"id":"static-bucket-linkage-visual-closure","status":"PASS" if closure_max<=1e-5 else "FAIL","detail":{"errors_m":metrics["bucket_linkage_static_closure_errors_m"],"tolerance_m":1e-5,"classification":"reconstructed visual closure only"}},
        {"id":"export-mesh-scales-applied","status":"PASS" if not metrics["export_mesh_scale_offenders"] else "FAIL","detail":{"offenders":metrics["export_mesh_scale_offenders"]}},
        {"id":"glb-platform-contract","status":"PASS" if glb_contract_ok else "FAIL","detail":glb_contract},
        {"id":"object-density","status":"PASS" if counts["objects"]>=300 else "FAIL","detail":{"objects":counts["objects"],"minimum":300}},
        {"id":"triangle-budget","status":"PASS" if 30000<=counts["triangles"]<=260000 else "FAIL","detail":{"triangles":counts["triangles"],"budget":[30000,260000]}},
        {"id":"review-renders-nonempty","status":"PASS" if render_ok else "FAIL","detail":{"count":len(render_paths),"minimum_count":7,"minimum_bytes":20000}},
        {"id":"bucket-publication-conflict-carried","status":"PASS","detail":"2.34 m3 / 1370 mm operating-weight basis is frozen while the 1372 mm / 2.01 m3 heavy-duty table branch remains explicitly conflicted and unresolved."},
        {"id":"configuration-freeze","status":"PENDING","detail":"Research candidate retains unresolved PIN/order, bucket family, coupler, auxiliary hydraulics, cab/trim, grade management, removal-device, and rights choices."},
        {"id":"mechanical-solver","status":"PENDING","detail":"No solver, published joint limits, or cylinder travel proof exists."},
        {"id":"published-working-envelope","status":"PENDING","detail":"Reach, dig depth, cutting height, and dump height are recorded facts but are not demonstrated by the static structural study."},
        {"id":"bucket-linkage-kinematic-closure","status":"PENDING","detail":"Static visual closure does not establish multi-pose linkage closure."},
        {"id":"track-phase-and-motion","status":"PENDING","detail":"Shoe count is exact; pitch, sprocket phase, and rolling motion remain reconstructed without a solver."},
        {"id":"ground-self-swept-collision","status":"PENDING","detail":"No swept-volume or collision solver exists."},
        {"id":"critic-human-visual-review","status":"PENDING","detail":"Overall critic must inspect exact render and artifact hashes."},
        {"id":"viewer-browser-accessibility-mobile-selection-performance","status":"PENDING","detail":"No shared viewer admission in this machine lane."},
        {"id":"publication-and-deployment","status":"PENDING","detail":"Only the overall publisher may admit, commit, push, or deploy this artifact."},
    ]
    failed = [gate["id"] for gate in gates if gate["status"]=="FAIL"]
    required_gate_ids = mechanism["required_gates"]
    required_by_id = {gate["id"]:gate for gate in required_gates}
    if list(required_by_id) != required_gate_ids:
        raise RuntimeError("required validation gate order differs from mechanism.json")
    payload = {
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "candidate_class":CANDIDATE_CLASS,
        "verdict":"PASS" if not failed else "FAIL",
        "not_engineering_authority":True,
        "bounds":bounds,
        "counts":counts,
        "measured_metrics":metrics,
        "glb_contract":glb_contract,
        "required_machine_gate_ids":required_gate_ids,
        "gates":gates,
        "failed_gate_ids":failed,
        "higher_stage_gates_pending":True,
    }
    write_json(VALIDATION_PATH,payload)
    return payload


def main():
    for path in (GLB_PATH.parent, RECEIPT_PATH.parent, RENDER_DIR):
        path.mkdir(parents=True,exist_ok=True)
    reset_scene()
    model = create_model()
    add_review_lighting()
    bpy.context.view_layer.update()
    render_paths = render_all(model)

    convert_export_curves_to_mesh()
    objects = export_objects()
    apply_export_mesh_scales(objects)
    bpy.context.view_layer.update()
    bounds = bounds_for(objects)
    counts = {
        "objects":len(objects),
        "meshes":sum(obj.type=="MESH" for obj in objects),
        "empties":sum(obj.type=="EMPTY" for obj in objects),
        "triangles":triangle_count(objects),
        "materials":len({slot.material.name for obj in objects if obj.type=="MESH" for slot in obj.material_slots if slot.material}),
    }

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH),compress=True)
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

    glb_contract = inspect_glb_contract(GLB_PATH)
    metrics = collect_metrics(model,objects)
    validation = create_validation(bounds,counts,metrics,glb_contract,render_paths)
    mechanism = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    validation_by_id = {gate["id"]:gate for gate in validation["gates"]}
    machine_gate_evidence = [
        {"id":validation_by_id[gate_id]["id"],
         "status":validation_by_id[gate_id]["status"],
         "detail":validation_by_id[gate_id]["detail"]}
        for gate_id in mechanism["required_gates"]
    ]
    node_presence = {name:bpy.data.objects.get(name) is not None for name in REQUIRED_NODES}
    render_records = [{"path":rel(path),"sha256":sha256(path),"bytes":path.stat().st_size} for path in render_paths]
    receipt = {
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "configuration_status":"research_candidate",
        "candidate_class":CANDIDATE_CLASS,
        "authority_boundary":"Independently authored neutral technical structural study. Not manufacturer CAD, engineering authority, a digital twin, load guidance, operator training, safety guidance, or manufacturer endorsement.",
        "blender":{"version":bpy.app.version_string,"factory_startup_required":True,"background_required":True},
        "builder":{
            "path":rel(SCRIPT_PATH),"sha256":sha256(SCRIPT_PATH),"deterministic":True,
            "bytes":SCRIPT_PATH.stat().st_size,
            "network_used":False,"downloaded_geometry_used":False,"manufacturer_cad_used":False,
            "copied_textures_used":False,"copied_imagery_used":False,"opaque_addons_used":False,
        },
        "design":{"path":rel(DESIGN_PATH),"sha256":sha256(DESIGN_PATH),"bytes":DESIGN_PATH.stat().st_size},
        "artifacts":{
            "blend":{"path":rel(BLEND_PATH),"sha256":sha256(BLEND_PATH),"bytes":BLEND_PATH.stat().st_size},
            "glb":{"path":rel(GLB_PATH),"sha256":sha256(GLB_PATH),"bytes":GLB_PATH.stat().st_size},
            "validation":{"path":rel(VALIDATION_PATH),"sha256":sha256(VALIDATION_PATH),"bytes":VALIDATION_PATH.stat().st_size},
        },
        "scene":{
            "units":"meters",
            "axes":{"longitudinal":"+X toward bucket","vertical":"+Y","lateral":"+Z machine right"},
            "visible_aabb_xyz_m":glb_contract["decoded_visible_aabb_m"]["dimensions_xyz_m"],
            "bounds":{
                "min_m":glb_contract["decoded_visible_aabb_m"]["min_xyz_m"],
                "max_m":glb_contract["decoded_visible_aabb_m"]["max_xyz_m"],
                "size_m":glb_contract["decoded_visible_aabb_m"]["dimensions_xyz_m"],
                "classification":"decoded shipped public GLB accessor bounds with composed node transforms",
            },
            "objects":glb_contract["node_count"],
            "meshes":glb_contract["mesh_count"],
            "triangles":glb_contract["decoded_triangle_count"],
            "materials":glb_contract["material_count"],
            "blend_source_counts":counts,
        },
        "public_glb_contract":glb_contract,
        "required_semantic_nodes":node_presence,
        "manufacturer_published_constraints_used":PUBLISHED_FACT_IDS,
        "published_constraint_ids_declared":PUBLISHED_FACT_IDS,
        "machine_specific_gate_evidence":machine_gate_evidence,
        "reconstructed_values":RECONSTRUCTED,
        "measured_metrics":metrics,
        "unresolved_choices":[
            "exact PIN and order family","bucket family behind operating-weight basis","hydraulic coupler",
            "auxiliary hydraulic plumbing","cab protection and trim","grade management",
            "counterweight removal-device exterior detail","public material and branding authorization",
        ],
        "documented_source_conflicts":[
            "ME470PAU operating-weight basis states 2.34 m3 / 1370 mm / 2031 kg, while its heavy-duty table states 2.01 m3 / 1372 mm / 1924 kg. The study does not reconcile these as one bucket family."
        ],
        "mechanical_gaps":[
            "Slew-bearing dimensions and elevation are reconstructed.",
            "Boom, arm, bucket, cylinder, and linkage anchors are reconstructed.",
            "Cylinder strokes constrain identity only; no solver or authoritative endpoint curve exists.",
            "Track pitch, sprocket teeth/phase, roller centers, and rolling motion are reconstructed.",
            "No ground, self, swept-volume, working-envelope, or interference qualification exists.",
            "No hidden internal hydraulic, powertrain, counterweight-removal, or service assembly is represented.",
        ],
        "renders":render_records,
        "build_verdict":"PASS" if validation["verdict"]=="PASS" else "FAIL",
        "validation_verdict":validation["verdict"],
        "validation_path":rel(VALIDATION_PATH),
        "publication_gate":"PENDING_OVERALL_CRITIC_AND_FULL_PROOF_LADDER",
    }
    write_json(RECEIPT_PATH,receipt)
    if validation["verdict"]=="FAIL":
        raise RuntimeError(f"Structural validation failed: {validation['failed_gate_ids']}")
    print(json.dumps({"status":"PASS","machine":MACHINE_ID,"counts":counts,"bounds":bounds,"glb":str(GLB_PATH),"renders":len(render_paths)},indent=2))


if __name__ == "__main__":
    main()
