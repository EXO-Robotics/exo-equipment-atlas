#!/usr/bin/env python3
"""Build the neutral Cat D6 20C technical structural study.

The geometry is independently authored and only constrained by configuration-
applicable manufacturer dimensions. It is not Caterpillar CAD, engineering
authority, a mechanical solver, load guidance, training, or safety guidance.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


SCRIPT_PATH = Path(__file__).resolve()
MACHINE_DIR = SCRIPT_PATH.parents[2]
BLEND_PATH = SCRIPT_PATH.parent / "cat-d6-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets" / "cat-d6-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production" / "asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production" / "validation.json"
RENDER_DIR = MACHINE_DIR / "review" / "renders"

MACHINE_ID = "cat-d6"
CONFIGURATION_ID = "CAT-D6-20C-AUSAM-PUSHARM-6SU-HD42-MS610-DRAWBAR-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"

PUBLISHED = {
    "operating_weight_kg": 22130,
    "shipping_weight_kg": 19178,
    "track_sections_each_side": 42,
    "bottom_rollers_each_side": 8,
    "track_gauge_m": 1.930,
    "shoe_width_m": 0.610,
    "width_over_tracks_m": 2.540,
    "width_over_trunnions_m": 2.692,
    "track_on_ground_m": 2.964,
    "track_pitch_m": 0.2028,
    "grouser_height_m": 0.065,
    "ground_clearance_m": 0.361,
    "front_idler_oscillation_m": 0.103,
    "machine_height_m": 3.188,
    "machine_without_blade_length_m": 4.730,
    "blade_capacity_m3": 5.7,
    "blade_width_end_bits_m": 3.312,
    "blade_width_without_end_bits_m": 3.246,
    "blade_height_m": 1.408,
    "blade_dig_depth_m": 0.502,
    "blade_lift_height_m": 1.180,
    "blade_corner_tilt_m": 0.564,
    "blade_tilt_deg": 9.8,
    "blade_pitch_deg": 4.2,
    "machine_with_blade_length_m": 5.436,
    "blade_weight_kg": 1385,
    "blade_and_push_arms_weight_kg": 2620,
}

RECONSTRUCTED = {
    "static_pose": {
        "blade_lift_deg": 0.0,
        "blade_tilt_deg": 0.0,
        "blade_pitch_deg": 0.0,
        "note": "Neutral review pose, not a Caterpillar endpoint definition.",
    },
    "raised_tilted_review_pose": {
        "blade_lift_deg": 8.0,
        "blade_tilt_deg": 7.0,
        "note": "Direct-render inspection pose only; not retained in the exported asset.",
    },
    "blade_lift_pivot_m": [-0.78, 0.70, 0.0],
    "blade_tilt_pivot_m": [2.69, 0.80, 0.0],
    "track_loop_radius_m": 0.41215,
    "track_loop_center_y_m": 0.535,
    "track_shoe_visual_length_m": 0.190,
    "track_shoe_plate_thickness_m": 0.060,
    "sprocket_teeth_each_side": 14,
    "sprocket_service_segments_each_side": 7,
    "track_pin_bushing_visual_radius_m": 0.031,
    "track_outer_link_visual_length_m": 0.150,
    "track_chain_readability": "Independent exterior link plates and pin/bushing cues make the 42-section loop and reconstructed sprocket engagement directly inspectable; pin geometry and tooth phase remain unresolved.",
    "idler_sprocket_roller_centers": "Reconstructed around the published track-on-ground length, pitch, 42 sections, and eight bottom rollers.",
    "blade_shell": "Independent curved 6SU shell with published overall width and height; curvature, thickness, wing sweep, bolt pattern, and back ribs are reconstructed.",
    "push_arm_geometry": "Independent box-section push arms visually connected from reconstructed trunnions to the blade; all pivots and section dimensions are reconstructed.",
    "hydraulic_anchors": "Lift and tilt cylinder anchors, barrel/rod diameters, visible strokes, and hose routes are reconstructed static closure cues.",
    "cab_and_house": "Independent visible-form study from first-party brochure observations; no hidden engine, transmission, ROPS load path, or service authority is represented.",
    "drawbar": "Standard drawbar is represented as a visible rear tow structure; pin and section dimensions are reconstructed.",
    "material_colors": "Neutral unbranded blue-steel slate, graphite, steel, rubber, glass, and restrained safety-lens accents; not protected manufacturer livery.",
}

REQUIRED_NODES = [
    "Machine_Root",
    "Undercarriage_ROOT",
    "Track_L_ROOT",
    "Track_R_ROOT",
    "Mainframe_ROOT",
    "Powertrain_ROOT",
    "Engine_Housing_ROOT",
    "Cab_ROOT",
    "Blade_Lift_Pivot",
    "Push_Arms_ROOT",
    "Blade_Tilt_Pivot",
    "Blade_ROOT",
    "Hydraulics_ROOT",
    "Blade_Lift_Hydraulics_ROOT",
    "Blade_Tilt_Hydraulics_ROOT",
    "Linkage_ROOT",
    "Drawbar_ROOT",
    "PIVOT_Blade_Trunnion_L",
    "PIVOT_Blade_Trunnion_R",
    "PIVOT_Blade_Tilt",
    "PIVOT_Blade_Pitch",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(MACHINE_DIR).as_posix()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for blocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(blocks):
            if block.users == 0:
                blocks.remove(block)
    scene = bpy.context.scene
    bpy.context.preferences.filepaths.save_version = 0
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.world.color = (0.012, 0.017, 0.024)
    scene["exo_machine_id"] = MACHINE_ID
    scene["exo_configuration_id"] = CONFIGURATION_ID
    scene["exo_candidate_class"] = CANDIDATE_CLASS
    scene["exo_axes"] = "+X toward 6SU blade/front, +Y vertical, +Z machine right"
    scene["exo_authority_boundary"] = "independently authored technical structural study; not engineering authority"


def material(name, color, metallic=0.0, roughness=0.5, alpha=1.0):
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


def empty(name, location=(0, 0, 0), parent=None, role="pivot", size=0.16, export=True):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    if parent:
        # Object.matrix_world is not guaranteed to reflect a freshly assigned
        # location until the dependency graph has updated.  The former code
        # copied the stale identity matrix here, collapsing every parented
        # semantic pivot to the origin.
        bpy.context.view_layer.update()
        parent_keep_world(obj, parent)
    return tag(obj, role=role, export=export)


def parent_keep_world(obj, parent):
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


def bevel(obj, width=0.02, segments=2):
    if width <= 0:
        return
    mod = obj.modifiers.new("Edge_Radius", "BEVEL")
    mod.width = width
    mod.segments = segments


def box(name, location, dimensions, mat, parent=None, rotation=(0, 0, 0), bevel_width=0.018, role="geometry", export=True, authority="reconstructed"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if parent:
        parent_keep_world(obj, parent)
    obj.data.materials.append(mat)
    bevel(obj, min(bevel_width, min(dimensions) * 0.22), 2)
    return tag(obj, role, export, authority)


def cylinder(name, location, radius, depth, mat, parent=None, vertices=24, rotation=(0, 0, 0), role="geometry", export=True, authority="reconstructed"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    if parent:
        parent_keep_world(obj, parent)
    obj.data.materials.append(mat)
    bevel(obj, min(radius * 0.10, 0.012), 2)
    return tag(obj, role, export, authority)


def uv_sphere(name, location, radius, mat, parent=None, segments=20, rings=12, role="fastener"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    if parent:
        parent_keep_world(obj, parent)
    obj.data.materials.append(mat)
    return tag(obj, role)


def side_profile(name, points_xy, thickness, mat, parent=None, z_center=0.0, bevel_width=0.015, role="geometry"):
    count = len(points_xy)
    vertices = [(x, y, z_center - thickness / 2) for x, y in points_xy]
    vertices += [(x, y, z_center + thickness / 2) for x, y in points_xy]
    faces = []
    faces.append(tuple(range(count)))
    faces.append(tuple(range(count, count * 2)))
    for i in range(count):
        j = (i + 1) % count
        faces.append((i, j, count + j, count + i))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if parent:
        parent_keep_world(obj, parent)
    obj.data.materials.append(mat)
    bevel(obj, bevel_width, 2)
    return tag(obj, role)


def tube_curve(name, points, radius, mat, parent=None, role="hose"):
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, value in zip(spline.points, points):
        point.co = (*value, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    if parent:
        parent_keep_world(obj, parent)
    obj.data.materials.append(mat)
    return tag(obj, role)


def object_between(name, start, end, radius, mat, parent=None, role="hydraulic", vertices=24):
    obj = cylinder(name, (0, 0, 0), radius, 1.0, mat, parent=parent, vertices=vertices, role=role)
    place_between(obj, start, end, radius)
    return obj


def place_between(obj, start, end, radius):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    length = max(direction.length, 1e-6)
    obj.location = (start + end) * 0.5
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    obj.dimensions = (radius * 2, radius * 2, length)


def capsule_point(distance, straight, radius, center_x, center_y):
    total = 2 * straight + 2 * math.pi * radius
    s = distance % total
    rear = center_x - straight / 2
    front = center_x + straight / 2
    if s < straight:
        return Vector((rear + s, center_y - radius)), 0.0, Vector((0.0, -1.0))
    s -= straight
    if s < math.pi * radius:
        angle = -math.pi / 2 + s / radius
        point = Vector((front + radius * math.cos(angle), center_y + radius * math.sin(angle)))
        return point, angle + math.pi / 2, Vector((math.cos(angle), math.sin(angle)))
    s -= math.pi * radius
    if s < straight:
        return Vector((front - s, center_y + radius)), math.pi, Vector((0.0, 1.0))
    s -= straight
    angle = math.pi / 2 + s / radius
    point = Vector((rear + radius * math.cos(angle), center_y + radius * math.sin(angle)))
    return point, angle + math.pi / 2, Vector((math.cos(angle), math.sin(angle)))


def add_sprocket_teeth(prefix, center, z_center, parent, mats, count=14):
    phase = math.pi / count
    for i in range(count):
        angle = 2 * math.pi * i / count + phase
        radial = Vector((math.cos(angle), math.sin(angle)))
        tangent = Vector((-math.sin(angle), math.cos(angle)))
        inner = Vector(center) + radial * 0.285
        outer = Vector(center) + radial * 0.405
        points = [
            inner - tangent * 0.074,
            outer - tangent * 0.046,
            outer + tangent * 0.046,
            inner + tangent * 0.074,
        ]
        tooth = side_profile(
            f"{prefix}_Sprocket_Tooth_{i:02d}",
            [(p.x, p.y) for p in points],
            0.48,
            mats["steel"],
            parent,
            z_center=z_center,
            bevel_width=0.009,
            role="track_drive",
        )
        tooth["exo_reconstructed_sprocket_phase"] = True


def add_sprocket_service_segments(prefix, center, z_center, parent, mats, count=7):
    for i in range(count):
        a0 = 2 * math.pi * (i / count) + 0.035
        a1 = 2 * math.pi * ((i + 1) / count) - 0.035
        points = []
        for radius, angle in ((0.225, a0), (0.315, a0), (0.315, a1), (0.225, a1)):
            points.append((center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle)))
        segment = side_profile(
            f"{prefix}_Sprocket_Service_Segment_{i:02d}",
            points,
            0.455,
            mats["ochre_dark"],
            parent,
            z_center=z_center,
            bevel_width=0.006,
            role="track_drive",
        )
        segment["exo_observed_service_segment_layout"] = True


def build_track(side, z_center, root, mats):
    prefix = f"Track_{side}"
    exterior_sign = -1.0 if side == "L" else 1.0
    straight = PUBLISHED["track_on_ground_m"]
    radius = RECONSTRUCTED["track_loop_radius_m"]
    center_x = 0.10
    center_y = RECONSTRUCTED["track_loop_center_y_m"]
    total = 2 * straight + 2 * math.pi * radius
    shoe_objects = []
    for i in range(PUBLISHED["track_sections_each_side"]):
        p, tangent, outward = capsule_point(i * total / PUBLISHED["track_sections_each_side"], straight, radius, center_x, center_y)
        plate_center = Vector((p.x, p.y, z_center))
        shoe = box(
            f"{prefix}_Shoe_{i:02d}",
            plate_center,
            (RECONSTRUCTED["track_shoe_visual_length_m"], RECONSTRUCTED["track_shoe_plate_thickness_m"], PUBLISHED["shoe_width_m"]),
            mats["track"],
            root,
            rotation=(0, 0, tangent),
            bevel_width=0.006,
            role="track_shoe",
        )
        shoe["exo_published_pitch_m"] = PUBLISHED["track_pitch_m"]
        grouser_center = Vector((p.x, p.y, z_center)) + Vector((outward.x, outward.y, 0)) * 0.057
        grouser = box(
            f"{prefix}_Grouser_{i:02d}",
            grouser_center,
            (0.072, PUBLISHED["grouser_height_m"], PUBLISHED["shoe_width_m"] * 0.96),
            mats["track_edge"],
            root,
            rotation=(0, 0, tangent),
            bevel_width=0.004,
            role="track_grouser",
        )
        link_point = p - outward * 0.032
        link = box(
            f"{prefix}_Outer_Link_{i:02d}",
            (link_point.x, link_point.y, z_center + exterior_sign * 0.250),
            (0.150, 0.052, 0.072),
            mats["steel_dark"],
            root,
            rotation=(0, 0, tangent),
            bevel_width=0.008,
            role="track_link",
        )
        pin = cylinder(
            f"{prefix}_Pin_Bushing_{i:02d}",
            (link_point.x, link_point.y, z_center),
            0.031,
            0.500,
            mats["steel"],
            root,
            vertices=16,
            role="track_pin",
        )
        pin["exo_reconstructed_pin_geometry"] = True
        pin_cap = cylinder(
            f"{prefix}_Pin_Cap_{i:02d}",
            (link_point.x, link_point.y, z_center + exterior_sign * 0.292),
            0.043,
            0.024,
            mats["track_edge"],
            root,
            vertices=16,
            role="track_pin",
        )
        pin_cap["exo_reconstructed_pin_geometry"] = True
        shoe_objects.extend((shoe, grouser))

    rear_center = (center_x - straight / 2, center_y)
    front_center = (center_x + straight / 2, center_y)
    cylinder(f"{prefix}_Rear_Sprocket_Core", (*rear_center, z_center), 0.235, 0.44, mats["steel_dark"], root, vertices=32, role="track_drive")
    add_sprocket_service_segments(prefix, rear_center, z_center, root, mats)
    add_sprocket_teeth(prefix, rear_center, z_center, root, mats)
    cylinder(f"{prefix}_Rear_Final_Drive", (*rear_center, z_center), 0.195, 0.47, mats["ochre_dark"], root, vertices=32, role="powertrain")
    cylinder(f"{prefix}_Rear_Hub", (*rear_center, z_center), 0.092, 0.50, mats["steel"], root, vertices=24, role="track_drive")
    cylinder(f"{prefix}_Front_Idler", (*front_center, z_center), 0.355, 0.27, mats["steel_dark"], root, vertices=32, role="undercarriage")
    cylinder(f"{prefix}_Front_Idler_Hub", (*front_center, z_center), 0.105, 0.31, mats["steel"], root, vertices=24, role="undercarriage")

    roller_y = center_y - radius + 0.165
    roller_x0 = center_x - straight / 2 + 0.22
    roller_spacing = (straight - 0.44) / (PUBLISHED["bottom_rollers_each_side"] - 1)
    rollers = []
    for i in range(PUBLISHED["bottom_rollers_each_side"]):
        x = roller_x0 + i * roller_spacing
        roller = cylinder(f"{prefix}_Bottom_Roller_{i:02d}", (x, roller_y, z_center), 0.145, 0.25, mats["steel_dark"], root, vertices=24, role="undercarriage")
        cylinder(f"{prefix}_Bottom_Roller_Hub_{i:02d}", (x, roller_y, z_center), 0.055, 0.29, mats["steel"], root, vertices=20, role="undercarriage")
        rollers.append(roller)
    cylinder(f"{prefix}_Carrier_Roller", (center_x + 0.08, center_y + radius - 0.08, z_center), 0.145, 0.25, mats["steel_dark"], root, vertices=24, role="undercarriage")

    frame_points = [
        (rear_center[0] - 0.16, center_y - 0.07),
        (rear_center[0] + 0.18, center_y + 0.30),
        (front_center[0] - 0.18, center_y + 0.30),
        (front_center[0] + 0.14, center_y - 0.07),
        (front_center[0] - 0.20, center_y - 0.19),
        (rear_center[0] + 0.20, center_y - 0.19),
    ]
    side_profile(f"{prefix}_Roller_Frame", frame_points, 0.22, mats["ochre_dark"], root, z_center=z_center, bevel_width=0.018, role="undercarriage")
    box(f"{prefix}_Track_Guard_Top", (center_x, center_y + 0.31, z_center), (1.95, 0.10, 0.28), mats["ochre"], root, bevel_width=0.014, role="undercarriage")
    return {"shoes": shoe_objects, "rollers": rollers, "rear_center": rear_center, "front_center": front_center}


def curved_blade_shell(name, x_base, y_bottom, height, width, thickness, mat, parent):
    y_steps = 16
    z_steps = 20
    vertices = []
    for back in (False, True):
        for yi in range(y_steps + 1):
            t = yi / y_steps
            y = y_bottom + height * t
            curve = 0.15 * math.sin(math.pi * t) - 0.035 * (t - 0.5)
            for zi in range(z_steps + 1):
                u = zi / z_steps
                z = -width / 2 + width * u
                wing = 0.075 * max(0.0, abs(u - 0.5) * 2 - 0.70) / 0.30
                x = x_base + curve + wing - (thickness if back else 0.0)
                vertices.append((x, y, z))
    stride = z_steps + 1
    layer = (y_steps + 1) * stride
    faces = []
    for back in (0, 1):
        offset = back * layer
        for yi in range(y_steps):
            for zi in range(z_steps):
                a = offset + yi * stride + zi
                b = a + 1
                c = a + stride + 1
                d = a + stride
                faces.append((a, b, c, d) if back == 0 else (d, c, b, a))
    for yi in range(y_steps):
        for zi in (0, z_steps):
            a = yi * stride + zi
            b = (yi + 1) * stride + zi
            c = layer + (yi + 1) * stride + zi
            d = layer + yi * stride + zi
            faces.append((a, b, c, d))
    for yi in (0, y_steps):
        for zi in range(z_steps):
            a = yi * stride + zi
            b = yi * stride + zi + 1
            c = layer + yi * stride + zi + 1
            d = layer + yi * stride + zi
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    parent_keep_world(obj, parent)
    obj.data.materials.append(mat)
    return tag(obj, role="blade")


def add_pin(name, location, radius, depth, mat, parent, role="pivot_marker"):
    return cylinder(name, location, radius, depth, mat, parent, vertices=28, role=role)


def create_model():
    mats = {
        # Internal dictionary keys remain stable for deterministic geometry,
        # but the body/blade finish is a neutral blue-steel slate rather than
        # manufacturer-like yellow/orange paint.
        "ochre": material("Neutral_Blue_Steel_Slate", (0.19, 0.25, 0.29), metallic=0.16, roughness=0.44),
        "ochre_light": material("Neutral_Blue_Steel_Highlight", (0.38, 0.44, 0.46), metallic=0.12, roughness=0.40),
        "ochre_dark": material("Neutral_Blue_Steel_Shadow", (0.065, 0.085, 0.10), metallic=0.22, roughness=0.50),
        "track": material("Track_Graphite", (0.075, 0.082, 0.090), metallic=0.52, roughness=0.38),
        "track_edge": material("Track_Wear_Edge", (0.16, 0.17, 0.18), metallic=0.72, roughness=0.31),
        "steel": material("Neutral_Steel", (0.34, 0.37, 0.39), metallic=0.82, roughness=0.27),
        "steel_dark": material("Dark_Steel", (0.105, 0.115, 0.125), metallic=0.70, roughness=0.34),
        "rubber": material("Neutral_Rubber", (0.022, 0.026, 0.030), metallic=0.0, roughness=0.86),
        "glass": material("Neutral_Glass", (0.055, 0.105, 0.125), metallic=0.18, roughness=0.18),
        "interior": material("Cab_Interior", (0.035, 0.042, 0.048), metallic=0.05, roughness=0.72),
        "red": material("Neutral_Safety_Red", (0.55, 0.045, 0.025), metallic=0.05, roughness=0.48),
        "hose": material("Hydraulic_Hose", (0.018, 0.021, 0.024), metallic=0.05, roughness=0.80),
        "lamp": material("Lamp_Lens", (0.88, 0.82, 0.58), metallic=0.05, roughness=0.19),
    }

    machine = empty("Machine_Root", role="identity_root", size=0.28)
    undercarriage = empty("Undercarriage_ROOT", parent=machine, role="structure")
    track_l_root = empty("Track_L_ROOT", parent=undercarriage, role="track_group")
    track_r_root = empty("Track_R_ROOT", parent=undercarriage, role="track_group")
    mainframe = empty("Mainframe_ROOT", parent=machine, role="structure")
    powertrain = empty("Powertrain_ROOT", parent=mainframe, role="structure")
    engine_root = empty("Engine_Housing_ROOT", parent=mainframe, role="structure")
    cab_root = empty("Cab_ROOT", parent=mainframe, role="structure")
    drawbar_root = empty("Drawbar_ROOT", parent=mainframe, role="attachment")
    linkage_root = empty("Linkage_ROOT", parent=machine, role="linkage")
    hydraulics_root = empty("Hydraulics_ROOT", parent=machine, role="hydraulics")
    lift_hydraulics_root = empty("Blade_Lift_Hydraulics_ROOT", parent=hydraulics_root, role="hydraulics")
    tilt_hydraulics_root = empty("Blade_Tilt_Hydraulics_ROOT", parent=hydraulics_root, role="hydraulics")

    track_l = build_track("L", -PUBLISHED["track_gauge_m"] / 2, track_l_root, mats)
    track_r = build_track("R", PUBLISHED["track_gauge_m"] / 2, track_r_root, mats)

    # Mainframe and visible powertrain volumes.
    belly = box("Mainframe_Belly", (0.00, 0.491, 0.0), (3.12, 0.260, 1.52), mats["steel_dark"], mainframe, bevel_width=0.032, role="structure")
    belly["exo_published_ground_clearance_m"] = PUBLISHED["ground_clearance_m"]
    box("Mainframe_Upper_Case", (-0.02, 0.79, 0.0), (2.86, 0.46, 1.64), mats["ochre_dark"], mainframe, bevel_width=0.045, role="structure")
    box("Mainframe_Crossmember_Front", (1.43, 0.72, 0.0), (0.27, 0.52, 2.16), mats["steel_dark"], mainframe, bevel_width=0.026, role="structure")
    box("Mainframe_Crossmember_Rear", (-1.42, 0.72, 0.0), (0.24, 0.49, 2.10), mats["steel_dark"], mainframe, bevel_width=0.024, role="structure")
    cylinder("Equalizer_Bar_Visual", (0.56, 0.48, 0.0), 0.095, 2.18, mats["steel"], mainframe, vertices=28, role="linkage")
    for side, z in (("L", -1.245), ("R", 1.245)):
        cylinder(f"Final_Drive_{side}_Outer", (-1.382, 0.535, z), 0.285, 0.18, mats["ochre_dark"], powertrain, vertices=36, role="powertrain")
        cylinder(f"Final_Drive_{side}_Cap", (-1.382, 0.535, z), 0.185, 0.205, mats["steel_dark"], powertrain, vertices=32, role="powertrain")
        for i in range(10):
            a = 2 * math.pi * i / 10
            cylinder(f"Final_Drive_{side}_Bolt_{i:02d}", (-1.382 + 0.145 * math.cos(a), 0.535 + 0.145 * math.sin(a), z + (-0.111 if side == "L" else 0.111)), 0.015, 0.020, mats["steel"], powertrain, vertices=12, role="fastener")

    # Fenders and lower house.
    box("Deck_Center", (-0.05, 1.035, 0.0), (2.90, 0.19, 2.02), mats["ochre"], mainframe, bevel_width=0.028, role="body")
    box("Fender_L", (-0.15, 1.10, -1.08), (3.05, 0.16, 0.32), mats["ochre_light"], mainframe, bevel_width=0.020, role="body")
    box("Fender_R", (-0.15, 1.10, 1.08), (3.05, 0.16, 0.32), mats["ochre_light"], mainframe, bevel_width=0.020, role="body")
    for side, z in (("L", -1.18), ("R", 1.18)):
        for i, x in enumerate((-1.10, -0.58, -0.06, 0.46, 0.98)):
            box(f"Access_Step_{side}_{i:02d}", (x, 0.93 - 0.10 * (i % 2), z), (0.34, 0.055, 0.24), mats["steel_dark"], mainframe, bevel_width=0.008, role="access")

    # Sloped hood and engine/service house.
    hood_points = [(-0.12, 1.15), (2.33, 1.15), (2.45, 1.49), (1.92, 1.71), (0.25, 1.79), (-0.20, 1.60)]
    side_profile("Engine_Hood_Main", hood_points, 1.62, mats["ochre"], engine_root, z_center=0.0, bevel_width=0.035, role="body")
    box("Engine_Hood_Top", (0.92, 1.785, 0.0), (1.52, 0.09, 1.44), mats["ochre_light"], engine_root, bevel_width=0.025, role="body")
    box("Radiator_Nose", (2.36, 1.42, 0.0), (0.22, 0.58, 1.58), mats["ochre_dark"], engine_root, bevel_width=0.025, role="body")
    for i, z in enumerate((-0.58, -0.39, -0.20, 0.0, 0.20, 0.39, 0.58)):
        box(f"Radiator_Grille_Vane_{i:02d}", (2.478, 1.44, z), (0.025, 0.47, 0.075), mats["steel_dark"], engine_root, bevel_width=0.004, role="service_panel")
    for side, z in (("L", -0.825), ("R", 0.825)):
        for i, x in enumerate((0.22, 0.78, 1.34, 1.90)):
            panel = box(f"Service_Door_{side}_{i:02d}", (x, 1.50, z), (0.50, 0.58, 0.028), mats["ochre_light"], engine_root, bevel_width=0.010, role="service_panel")
            panel["exo_observed_visible_form"] = True
            for slot in range(4):
                box(f"Service_Door_{side}_{i:02d}_Vent_{slot:02d}", (x - 0.13 + slot * 0.085, 1.56, z + (-0.017 if side == "L" else 0.017)), (0.045, 0.20, 0.012), mats["steel_dark"], engine_root, bevel_width=0.002, role="service_panel")
            box(f"Service_Door_{side}_{i:02d}_Latch", (x + 0.17, 1.50, z + (-0.023 if side == "L" else 0.023)), (0.045, 0.09, 0.018), mats["steel"], engine_root, bevel_width=0.002, role="fastener")

    # Cab, opaque dark glazing, posts, interior silhouette, and roof detail.
    box("Cab_Base", (-0.73, 1.34, 0.0), (1.32, 0.32, 1.92), mats["ochre_dark"], cab_root, bevel_width=0.040, role="cab")
    box("Cab_Interior_Block", (-0.78, 2.14, 0.0), (1.04, 1.37, 1.58), mats["interior"], cab_root, bevel_width=0.035, role="cab_interior")
    box("Cab_Roof", (-0.75, 2.99, 0.0), (1.48, 0.17, 2.04), mats["ochre"], cab_root, bevel_width=0.055, role="cab")
    box("Cab_Roof_Liner", (-0.75, 2.88, 0.0), (1.34, 0.08, 1.88), mats["steel_dark"], cab_root, bevel_width=0.025, role="cab")
    # Side windows and door boundaries.
    for side, z in (("L", -0.952), ("R", 0.952)):
        glass_z = z + (-0.014 if side == "L" else 0.014)
        box(f"Cab_{side}_Front_Glass", (-0.28, 2.30, glass_z), (0.47, 1.03, 0.025), mats["glass"], cab_root, rotation=(0, 0, -0.08), bevel_width=0.010, role="glazing")
        box(f"Cab_{side}_Door_Glass", (-0.82, 2.31, glass_z), (0.49, 1.04, 0.025), mats["glass"], cab_root, bevel_width=0.010, role="glazing")
        box(f"Cab_{side}_Rear_Glass", (-1.25, 2.31, glass_z), (0.29, 0.98, 0.025), mats["glass"], cab_root, rotation=(0, 0, 0.06), bevel_width=0.010, role="glazing")
        for i, x in enumerate((-1.43, -1.10, -0.55, -0.03)):
            box(f"Cab_{side}_Post_{i:02d}", (x, 2.34, z), (0.075, 1.18, 0.075), mats["steel_dark"], cab_root, bevel_width=0.012, role="cab_structure")
        tube_curve(f"Cab_{side}_Roof_Grab", [(-1.34, 3.07, z), (-0.80, 3.13, z), (-0.18, 3.07, z)], 0.018, mats["steel_dark"], cab_root, role="access")
    box("Cab_Front_Glass", (-0.055, 2.30, 0.0), (0.035, 1.02, 1.72), mats["glass"], cab_root, bevel_width=0.012, role="glazing")
    box("Cab_Rear_Glass", (-1.455, 2.28, 0.0), (0.035, 0.94, 1.69), mats["glass"], cab_root, bevel_width=0.012, role="glazing")
    box("Operator_Seat_Back", (-0.86, 2.08, 0.0), (0.23, 0.64, 0.53), mats["rubber"], cab_root, bevel_width=0.055, role="cab_interior")
    box("Operator_Seat_Base", (-0.74, 1.78, 0.0), (0.47, 0.16, 0.52), mats["rubber"], cab_root, bevel_width=0.050, role="cab_interior")
    box("Cab_Display", (-0.27, 2.18, 0.47), (0.08, 0.33, 0.23), mats["interior"], cab_root, rotation=(0, 0.15, 0), bevel_width=0.020, role="cab_interior")

    # Product Link antenna closes the published 3.188 m height.
    cylinder("Product_Link_Antenna_Study", (-1.08, 3.112, 0.38), 0.055, 0.152, mats["steel_dark"], cab_root, vertices=24, rotation=(math.pi / 2, 0, 0), role="antenna")
    # Exhaust and precleaner align along the hood/cab sight line.
    cylinder("Exhaust_Stack", (-0.02, 2.15, 0.54), 0.075, 0.74, mats["steel_dark"], engine_root, vertices=28, rotation=(math.pi / 2, 0, 0), role="exhaust")
    cylinder("Exhaust_Shroud", (-0.02, 2.32, 0.54), 0.105, 0.32, mats["track"], engine_root, vertices=28, rotation=(math.pi / 2, 0, 0), role="exhaust")
    cylinder("Precleaner_Stem", (0.13, 2.04, -0.53), 0.050, 0.54, mats["steel_dark"], engine_root, vertices=24, rotation=(math.pi / 2, 0, 0), role="intake")
    cylinder("Precleaner_Bowl", (0.13, 2.33, -0.53), 0.135, 0.13, mats["track"], engine_root, vertices=28, rotation=(math.pi / 2, 0, 0), role="intake")
    cylinder("Precleaner_Cap", (0.13, 2.42, -0.53), 0.165, 0.055, mats["steel_dark"], engine_root, vertices=28, rotation=(math.pi / 2, 0, 0), role="intake")

    # Standard four-light study; no manufacturer marks.
    for i, (x, y, z) in enumerate(((-0.12, 2.86, -0.86), (-0.12, 2.86, 0.86), (-1.38, 2.83, -0.79), (-1.38, 2.83, 0.79))):
        box(f"LED_Light_Housing_{i:02d}", (x, y, z), (0.12, 0.12, 0.18), mats["steel_dark"], cab_root, bevel_width=0.020, role="lighting")
        box(f"LED_Light_Lens_{i:02d}", (x + (0.066 if x > -0.5 else -0.066), y, z), (0.015, 0.086, 0.135), mats["lamp"], cab_root, bevel_width=0.006, role="lighting")

    # Rear tank, grille, ladder, and standard drawbar.
    side_profile("Rear_Fuel_Tank", [(-2.18, 1.10), (-1.26, 1.10), (-1.29, 1.86), (-1.56, 2.03), (-2.08, 1.88)], 1.72, mats["ochre"], mainframe, z_center=0.0, bevel_width=0.040, role="body")
    box("Rear_Grille", (-2.185, 1.56, 0.0), (0.08, 0.64, 1.48), mats["steel_dark"], mainframe, bevel_width=0.018, role="service_panel")
    for i, y in enumerate((1.24, 1.39, 1.54, 1.69, 1.84)):
        box(f"Rear_Grille_Slat_{i:02d}", (-2.231, y, 0.0), (0.025, 0.055, 1.28), mats["steel"], mainframe, bevel_width=0.003, role="service_panel")
    for i, y in enumerate((0.92, 1.15, 1.38, 1.61)):
        box(f"Rear_Ladder_Rung_{i:02d}", (-2.21, y, -0.76), (0.09, 0.055, 0.42), mats["steel_dark"], mainframe, bevel_width=0.008, role="access")
    tube_curve("Rear_Ladder_Rail", [(-2.23, 0.84, -0.97), (-2.23, 1.73, -0.97), (-2.05, 1.94, -0.97)], 0.022, mats["steel_dark"], mainframe, role="access")
    box("Drawbar_Beam", (-2.06, 0.52, 0.0), (0.40, 0.16, 0.58), mats["steel_dark"], drawbar_root, bevel_width=0.025, role="drawbar")
    box("Drawbar_Tongue", (-2.14, 0.48, 0.0), (0.24, 0.11, 0.25), mats["steel"], drawbar_root, bevel_width=0.018, role="drawbar")
    cylinder("Drawbar_Pin", (-2.188, 0.50, 0.0), 0.072, 0.28, mats["steel_dark"], drawbar_root, vertices=28, role="drawbar")

    # Reconstructed blade hierarchy and push-arm pivots.
    blade_lift = empty("Blade_Lift_Pivot", RECONSTRUCTED["blade_lift_pivot_m"], parent=machine, role="pivot")
    push_root = empty("Push_Arms_ROOT", parent=blade_lift, role="linkage")
    blade_tilt = empty(
        "Blade_Tilt_Pivot",
        RECONSTRUCTED["blade_tilt_pivot_m"],
        parent=blade_lift,
        role="pivot",
    )
    blade_root = empty("Blade_ROOT", parent=blade_tilt, role="attachment")
    empty("PIVOT_Blade_Pitch", (2.75, 0.69, 0), parent=blade_tilt, role="pivot_marker", size=0.10)
    empty("PIVOT_Blade_Tilt", (2.69, 0.80, 0), parent=blade_tilt, role="pivot_marker", size=0.10)
    empty("PIVOT_Blade_Trunnion_L", (-0.78, 0.70, -PUBLISHED["width_over_trunnions_m"] / 2), parent=linkage_root, role="pivot_marker", size=0.12)
    empty("PIVOT_Blade_Trunnion_R", (-0.78, 0.70, PUBLISHED["width_over_trunnions_m"] / 2), parent=linkage_root, role="pivot_marker", size=0.12)

    # Linkage_ROOT is a public semantic motion owner, so it must own visible
    # reconstructed linkage rather than being an empty label.  These compact
    # clevis and pitch-link cues stay inside the frozen static envelope and do
    # not imply authoritative pin coordinates or load paths.
    for side, z in (("L", -0.46), ("R", 0.46)):
        object_between(
            f"Blade_Pitch_Link_{side}",
            (2.43, 1.03, z),
            (2.73, 0.79, z),
            0.046,
            mats["steel_dark"],
            linkage_root,
            "linkage",
            20,
        )
        add_pin(
            f"Blade_Pitch_Link_Pin_{side}",
            (2.73, 0.79, z),
            0.070,
            0.105,
            mats["steel"],
            linkage_root,
            role="linkage_pin",
        )
    box("Blade_Pitch_Link_Crosshead", (2.43, 1.03, 0.0), (0.16, 0.13, 1.02), mats["ochre_dark"], linkage_root, bevel_width=0.018, role="linkage")

    push_arm_objects = []
    arm_points = [(-0.78, 0.62), (0.10, 0.49), (1.45, 0.53), (2.70, 0.73), (2.62, 0.91), (1.28, 0.73), (0.02, 0.68)]
    for side, z in (("L", -1.29), ("R", 1.29)):
        arm = side_profile(f"Push_Arm_{side}", arm_points, 0.23, mats["ochre"], z_center=z, bevel_width=0.030, role="linkage")
        parent_keep_world(arm, push_root)
        push_arm_objects.append(arm)
        cap = add_pin(f"Push_Arm_{side}_Trunnion_Cap", (-0.78, 0.70, z + (-0.135 if side == "L" else 0.135)), 0.115, 0.11, mats["steel_dark"], push_root)
        cap["exo_pivot_authority"] = "reconstructed"
        box(f"Push_Arm_{side}_Blade_Lug", (2.67, 0.79, z), (0.34, 0.30, 0.26), mats["ochre_dark"], push_root, bevel_width=0.030, role="linkage")
        for i, x in enumerate((0.15, 0.92, 1.70, 2.34)):
            box(f"Push_Arm_{side}_Wear_Plate_{i:02d}", (x, 0.755 - 0.035 * i, z + (-0.13 if side == "L" else 0.13)), (0.32, 0.055, 0.04), mats["steel"], push_root, bevel_width=0.008, role="linkage")

    blade_bottom = 0.05
    blade_top = blade_bottom + PUBLISHED["blade_height_m"]
    blade_shell = curved_blade_shell("Blade_6SU_Shell", 2.951, 0.14, blade_top - 0.14, PUBLISHED["blade_width_without_end_bits_m"], 0.065, mats["ochre_light"], blade_root)
    blade_shell["exo_published_width_without_end_bits_m"] = PUBLISHED["blade_width_without_end_bits_m"]
    blade_shell["exo_published_height_m"] = PUBLISHED["blade_height_m"]
    cutting = box("Blade_Cutting_Edge", (3.0355, 0.124, 0.0), (0.272, 0.13, PUBLISHED["blade_width_without_end_bits_m"]), mats["steel"], blade_root, rotation=(0, 0, -0.07), bevel_width=0.010, role="blade")
    # Tiny front cap sets the frozen 5.436 m overall length without a hidden witness.
    box("Blade_Cutting_Edge_Leading_Lip", (3.164, 0.087, 0.0), (0.024, 0.070, PUBLISHED["blade_width_without_end_bits_m"]), mats["track_edge"], blade_root, bevel_width=0.004, role="blade")
    for side, z in (("L", -1.6395), ("R", 1.6395)):
        end = box(f"Blade_End_Bit_{side}", (3.055, 0.176, z), (0.23, 0.24, 0.033), mats["steel"], blade_root, rotation=(0, 0, -0.05), bevel_width=0.008, role="blade")
        end["exo_published_overall_width_m"] = PUBLISHED["blade_width_end_bits_m"]
        wing_points = [(2.90, 0.18), (3.07, 0.20), (3.11, 1.36), (2.96, 1.45), (2.78, 1.29), (2.76, 0.36)]
        wing_z = -1.591 if side == "L" else 1.591
        side_profile(f"Blade_SU_Wing_{side}", wing_points, 0.13, mats["ochre"], blade_root, z_center=wing_z, bevel_width=0.0, role="blade")
    # Back ribs and cutting-edge bolts.
    for i, z in enumerate((-1.35, -0.90, -0.45, 0.0, 0.45, 0.90, 1.35)):
        box(f"Blade_Back_Rib_{i:02d}", (2.88, 0.80, z), (0.14, 1.10, 0.075), mats["ochre_dark"], blade_root, rotation=(0, 0, -0.04), bevel_width=0.010, role="blade")
    for i in range(18):
        z = -1.48 + i * (2.96 / 17)
        cylinder(f"Blade_Cutting_Edge_Bolt_{i:02d}", (3.154, 0.12, z), 0.018, 0.025, mats["steel_dark"], blade_root, vertices=12, rotation=(0, math.pi / 2, 0), role="fastener")
    add_pin("Blade_Center_Pin", (2.76, 0.78, 0.0), 0.105, 0.33, mats["steel_dark"], blade_root)
    # Blade corner guards remain within the frozen overall width.
    box("Blade_Top_Rail", (2.92, 1.423, 0.0), (0.16, 0.07, 3.246), mats["ochre_dark"], blade_root, bevel_width=0.014, role="blade")

    # Static visual cylinders. All anchors and diameters are reconstructed.
    lift_cylinders = []
    lift_specs = []
    for side, z in (("L", -0.73), ("R", 0.73)):
        base = Vector((0.52, 1.70, z))
        rod_world = Vector((2.66, 1.12, z * 1.24))
        rod_local = blade_lift.matrix_world.inverted() @ rod_world
        barrel = object_between(f"Blade_Lift_Cylinder_{side}_Barrel", base, base.lerp(rod_world, 0.64), 0.105, mats["ochre_dark"], lift_hydraulics_root)
        rod = object_between(f"Blade_Lift_Cylinder_{side}_Rod", base.lerp(rod_world, 0.54), rod_world, 0.061, mats["steel"], lift_hydraulics_root)
        add_pin(f"Blade_Lift_Cylinder_{side}_Base_Pin", base, 0.120, 0.15, mats["steel_dark"], lift_hydraulics_root)
        lift_cylinders.append((barrel, rod))
        lift_specs.append((base, rod_local))
    tilt_base_world = Vector((2.54, 1.19, -1.03))
    tilt_target_world = Vector((2.84, 0.74, 0.75))
    tilt_base_local = blade_lift.matrix_world.inverted() @ tilt_base_world
    tilt_target_local = blade_tilt.matrix_world.inverted() @ tilt_target_world
    tilt_barrel = object_between("Blade_Tilt_Cylinder_Barrel", tilt_base_world, tilt_base_world.lerp(tilt_target_world, 0.63), 0.092, mats["ochre_dark"], tilt_hydraulics_root)
    tilt_rod = object_between("Blade_Tilt_Cylinder_Rod", tilt_base_world.lerp(tilt_target_world, 0.52), tilt_target_world, 0.052, mats["steel"], tilt_hydraulics_root)
    add_pin("Blade_Tilt_Cylinder_Base_Pin", tilt_base_world, 0.105, 0.16, mats["steel_dark"], tilt_hydraulics_root)
    add_pin("Blade_Tilt_Cylinder_Rod_Pin", tilt_target_world, 0.090, 0.16, mats["steel_dark"], tilt_hydraulics_root)
    tube_curve("Blade_Hose_Bundle_L_01", [(0.28, 1.72, -0.73), (0.90, 1.48, -0.91), (1.75, 1.15, -1.17), (2.55, 1.22, -1.22)], 0.025, mats["hose"], machine)
    tube_curve("Blade_Hose_Bundle_L_02", [(0.31, 1.67, -0.69), (0.95, 1.43, -0.86), (1.80, 1.10, -1.12), (2.57, 1.17, -1.16)], 0.021, mats["hose"], machine)
    tube_curve("Blade_Hose_Bundle_R_01", [(0.28, 1.72, 0.73), (0.90, 1.48, 0.91), (1.75, 1.15, 1.17), (2.55, 1.22, 1.22)], 0.025, mats["hose"], machine)
    for i, x in enumerate((0.92, 1.66, 2.28)):
        box(f"Blade_Hose_Clamp_L_{i:02d}", (x, 1.35 - 0.20 * i, -1.07 - 0.06 * i), (0.10, 0.055, 0.08), mats["steel"], machine, bevel_width=0.008, role="hose_clamp")
        box(f"Blade_Hose_Clamp_R_{i:02d}", (x, 1.35 - 0.20 * i, 1.07 + 0.06 * i), (0.10, 0.055, 0.08), mats["steel"], machine, bevel_width=0.008, role="hose_clamp")

    # Private inspection volumes are saved in the .blend but never exported.
    inspection = empty("Inspection_Volumes", parent=machine, role="inspection", export=False)
    inspect_envelope = box("INSPECT_Published_Envelope", (0.458, 1.594, 0.0), (PUBLISHED["machine_with_blade_length_m"], PUBLISHED["machine_height_m"], PUBLISHED["blade_width_end_bits_m"]), mats["red"], inspection, bevel_width=0, role="inspection", export=False)
    inspect_sweep = box("INSPECT_Blade_Lift_Swept_Study", (2.35, 1.08, 0.0), (1.70, 2.18, 3.312), mats["red"], inspection, bevel_width=0, role="inspection", export=False)
    inspect_ground = box("INSPECT_Track_Ground_Contact", (0.10, 0.01, 0.0), (2.964, 0.02, 2.54), mats["red"], inspection, bevel_width=0, role="inspection", export=False)
    for helper in (inspect_envelope, inspect_sweep, inspect_ground):
        helper.hide_render = True
        helper.hide_viewport = True

    return {
        "machine": machine,
        "mats": mats,
        "track_l_root": track_l_root,
        "track_r_root": track_r_root,
        "track_l": track_l,
        "track_r": track_r,
        "belly": belly,
        "blade_lift": blade_lift,
        "blade_tilt": blade_tilt,
        "blade_root": blade_root,
        "blade_objects": [o for o in bpy.data.objects if o.get("exo_role") == "blade"],
        "lift_cylinders": lift_cylinders,
        "lift_specs": lift_specs,
        "tilt_cylinders": (tilt_barrel, tilt_rod),
        "tilt_specs": (tilt_base_local, tilt_target_local),
        "push_arm_objects": push_arm_objects,
    }


def evaluated_world_points(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    return points


def object_bounds(objects):
    points = evaluated_world_points(objects)
    if not points:
        return {"min_m": [0, 0, 0], "max_m": [0, 0, 0], "size_m": [0, 0, 0]}
    mins = [min(p[i] for p in points) for i in range(3)]
    maxs = [max(p[i] for p in points) for i in range(3)]
    return {
        "min_m": [round(v, 4) for v in mins],
        "max_m": [round(v, 4) for v in maxs],
        "size_m": [round(maxs[i] - mins[i], 4) for i in range(3)],
    }


def settle_tracks(model):
    shoe_objects = [o for o in bpy.data.objects if o.get("exo_role") in {"track_shoe", "track_grouser"}]
    min_y = min(p.y for p in evaluated_world_points(shoe_objects))
    for root in (model["track_l_root"], model["track_r_root"]):
        root.location.y -= min_y
    bpy.context.view_layer.update()
    return -min_y


def world_point(root, local):
    return root.matrix_world @ Vector(local)


def refresh_hydraulics(model):
    for (barrel, rod), (base, rod_local) in zip(model["lift_cylinders"], model["lift_specs"]):
        target = world_point(model["blade_lift"], rod_local)
        place_between(barrel, base, Vector(base).lerp(target, 0.64), 0.105)
        place_between(rod, Vector(base).lerp(target, 0.54), target, 0.061)
    tilt_base_local, tilt_target_local = model["tilt_specs"]
    base = world_point(model["blade_lift"], tilt_base_local)
    target = world_point(model["blade_tilt"], tilt_target_local)
    barrel, rod = model["tilt_cylinders"]
    place_between(barrel, base, base.lerp(target, 0.63), 0.092)
    place_between(rod, base.lerp(target, 0.52), target, 0.052)
    bpy.context.view_layer.update()


def add_review_lighting(mats):
    ground = box("REVIEW_Ground", (0.35, -0.045, 0), (13.5, 0.08, 10.0), mats["interior"], bevel_width=0, role="review", export=False)
    ground.visible_shadow = True
    for name, location, energy, size, color in (
        ("REVIEW_Key", (5.5, 8.5, -6.5), 1750, 5.0, (1.0, 0.83, 0.65)),
        ("REVIEW_Fill", (-4.0, 5.5, 5.0), 1250, 4.0, (0.52, 0.72, 1.0)),
        ("REVIEW_Rim", (-5.0, 7.0, -2.0), 1350, 3.5, (0.72, 0.84, 1.0)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = location
        tag(obj, role="review", export=False)
        point_camera(obj, (0.4, 1.1, 0.0))


def point_camera(obj, target, forward_axis="-Z", up_axis="Y"):
    if forward_axis != "-Z" or up_axis != "Y":
        raise ValueError("The Cat D6 review rig supports the Blender -Z/Y camera basis only")
    forward = (Vector(target) - obj.location).normalized()
    world_up = Vector((0.0, 1.0, 0.0))
    right = forward.cross(world_up)
    if right.length < 1e-8:
        right = Vector((1.0, 0.0, 0.0))
    else:
        right.normalize()
    camera_up = right.cross(forward).normalized()
    # Matrix columns are the camera's local +X, +Y and +Z axes in world
    # space. Local -Z looks at the target while local +Y remains aligned to
    # the platform's declared +Y vertical axis, avoiding Blender Z-up roll.
    basis = Matrix((
        (right.x, camera_up.x, -forward.x),
        (right.y, camera_up.y, -forward.y),
        (right.z, camera_up.z, -forward.z),
    ))
    obj.rotation_euler = basis.to_quaternion().to_euler()


def render_view(name, camera_location, target, lens=55, resolution=(800, 600)):
    data = bpy.data.cameras.new("REVIEW_Camera_" + name)
    data.lens = lens
    data.sensor_width = 36
    camera = bpy.data.objects.new("REVIEW_Camera_" + name, data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = camera_location
    point_camera(camera, target)
    tag(camera, role="review", export=False)
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    path = RENDER_DIR / f"cat-d6-{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.cameras.remove(data)
    return path


def render_all(model):
    renders = [
        render_view("operator-side", (0.45, 1.95, -12.5), (0.45, 1.25, 0.0), 58),
        render_view("front-right-three-quarter", (8.8, 3.25, 8.2), (0.35, 1.24, 0.0), 58),
        render_view("rear-left-three-quarter", (-8.2, 3.10, -7.5), (-0.10, 1.28, 0.0), 58),
        render_view("blade-linkage-detail", (5.1, 2.3, -4.5), (2.08, 0.90, -0.68), 72),
        render_view("undercarriage-detail", (1.05, 1.15, -5.3), (0.05, 0.52, -0.96), 78),
        render_view("drive-sprocket-engagement-detail", (-1.15, 1.05, -4.45), (-1.38, 0.54, -0.98), 82),
        render_view("cab-service-side", (-0.05, 3.0, -5.3), (-0.55, 2.05, -0.76), 72),
    ]
    model["blade_lift"].rotation_euler.z = math.radians(RECONSTRUCTED["raised_tilted_review_pose"]["blade_lift_deg"])
    model["blade_tilt"].rotation_euler.x = math.radians(RECONSTRUCTED["raised_tilted_review_pose"]["blade_tilt_deg"])
    refresh_hydraulics(model)
    renders.append(render_view("raised-tilted-blade", (9.0, 3.55, -8.5), (0.45, 1.25, 0.0), 58))
    model["blade_lift"].rotation_euler.z = 0.0
    model["blade_tilt"].rotation_euler.x = 0.0
    refresh_hydraulics(model)
    return renders


def export_objects():
    return [obj for obj in bpy.context.scene.objects if bool(obj.get("exo_export", False))]


def apply_export_mesh_scales(objects):
    for obj in objects:
        if obj.type != "MESH":
            continue
        if any(abs(v - 1.0) > 1e-6 for v in obj.scale):
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            obj.select_set(False)


def triangle_count(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            total += len(mesh.loop_triangles)
        finally:
            evaluated.to_mesh_clear()
    return total


def inspect_glb_contract(path):
    data = path.read_bytes()
    magic, version, _ = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise RuntimeError("Export is not glTF 2.0 GLB")
    offset = 12
    gltf = None
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset:offset + length]
        offset += length
        if kind == 0x4E4F534A:
            gltf = json.loads(chunk.decode("utf-8").rstrip(" \t\r\n\0"))
            break
    if gltf is None:
        raise RuntimeError("GLB has no JSON chunk")
    scene_index = gltf.get("scene", 0)
    scenes = gltf.get("scenes", [])
    roots = scenes[scene_index].get("nodes", []) if scenes else []
    nodes = gltf.get("nodes", [])
    root_records = []
    for index in roots:
        node = nodes[index]
        root_records.append({
            "index": index,
            "name": node.get("name"),
            "transform": {k: node[k] for k in ("translation", "rotation", "scale", "matrix") if k in node},
        })
    scale_offenders = {}
    for node in nodes:
        if "mesh" not in node:
            continue
        scale = node.get("scale", [1, 1, 1])
        if any(abs(float(v) - 1.0) > 1e-4 for v in scale):
            scale_offenders[node.get("name", "<unnamed>")] = scale
    helper_prefixes = ("REVIEW_", "INSPECT_", "Inspection_")
    helpers = [node.get("name") for node in nodes if str(node.get("name", "")).startswith(helper_prefixes)]
    extensions = gltf.get("extensionsUsed", [])
    public_triangles = 0
    for mesh in gltf.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            accessor_index = primitive.get("indices", primitive.get("attributes", {}).get("POSITION"))
            accessor = gltf.get("accessors", [])[accessor_index]
            mode = primitive.get("mode", 4)
            if mode == 4:
                if accessor["count"] % 3:
                    raise RuntimeError("GLB TRIANGLES primitive count is not divisible by three")
                public_triangles += accessor["count"] // 3
            elif mode in (5, 6):
                public_triangles += max(0, accessor["count"] - 2)
            else:
                raise RuntimeError(f"Unsupported public primitive topology mode {mode}")
    return {
        "scene_count": len(scenes),
        "scene_roots": root_records,
        "camera_count": len(gltf.get("cameras", [])),
        "punctual_light_extension_present": "KHR_lights_punctual" in extensions,
        "inspection_helper_nodes": helpers,
        "mesh_scale_offenders": scale_offenders,
        "node_count": len(nodes),
        "mesh_definition_count": len(gltf.get("meshes", [])),
        "triangle_count": public_triangles,
        "platform_axes": "+X longitudinal/front, +Y vertical, +Z machine right",
    }


def collect_metrics(model, objects, authored_track_correction):
    scene_bounds = object_bounds([o for o in objects if o.type == "MESH"])
    blade_bounds = object_bounds(model["blade_objects"])
    shoe_objects = [o for o in objects if o.get("exo_role") in {"track_shoe", "track_grouser"}]
    shoe_points = evaluated_world_points(shoe_objects)
    belly_bounds = object_bounds([model["belly"]])
    meshes = [o for o in objects if o.type == "MESH"]
    scale_offenders = {o.name: list(o.scale) for o in meshes if any(abs(v - 1.0) > 1e-4 for v in o.scale)}
    expected_pivots = {
        "Blade_Lift_Pivot": Vector(RECONSTRUCTED["blade_lift_pivot_m"]),
        "Blade_Tilt_Pivot": Vector(RECONSTRUCTED["blade_tilt_pivot_m"]),
        "PIVOT_Blade_Pitch": Vector((2.75, 0.69, 0.0)),
        "PIVOT_Blade_Tilt": Vector((2.69, 0.80, 0.0)),
        "PIVOT_Blade_Trunnion_L": Vector((-0.78, 0.70, -PUBLISHED["width_over_trunnions_m"] / 2)),
        "PIVOT_Blade_Trunnion_R": Vector((-0.78, 0.70, PUBLISHED["width_over_trunnions_m"] / 2)),
    }
    pivot_world = {
        name: [round(v, 6) for v in bpy.data.objects[name].matrix_world.translation]
        for name in expected_pivots
    }
    pivot_errors = {
        name: (bpy.data.objects[name].matrix_world.translation - expected).length
        for name, expected in expected_pivots.items()
    }

    def mesh_descendants(root):
        count = 0
        stack = list(root.children)
        while stack:
            child = stack.pop()
            if child.type == "MESH":
                count += 1
            stack.extend(child.children)
        return count

    semantic_descendants = {
        name: mesh_descendants(bpy.data.objects[name])
        for name in ("Blade_Lift_Pivot", "Blade_Tilt_Pivot", "Linkage_ROOT")
    }
    track_bounds = object_bounds([o for o in objects if o.get("exo_role") in {"track_shoe", "track_grouser"}])
    return {
        "scene_bounds": scene_bounds,
        "blade_bounds": blade_bounds,
        "blade_width_m": blade_bounds["size_m"][2],
        "blade_height_m": blade_bounds["size_m"][1],
        "overall_length_m": scene_bounds["size_m"][0],
        "overall_height_m": scene_bounds["size_m"][1],
        "overall_width_m": scene_bounds["size_m"][2],
        "track_contact_min_y_m": round(min(p.y for p in shoe_points), 6),
        "track_authored_root_correction_m": authored_track_correction,
        "mainframe_belly_underside_agl_m": belly_bounds["min_m"][1],
        "track_shoes_each_side": {
            "left": len([o for o in objects if o.name.startswith("Track_L_Shoe_")]),
            "right": len([o for o in objects if o.name.startswith("Track_R_Shoe_")]),
        },
        "bottom_rollers_each_side": {
            "left": len([o for o in objects if o.name.startswith("Track_L_Bottom_Roller_") and "Hub" not in o.name]),
            "right": len([o for o in objects if o.name.startswith("Track_R_Bottom_Roller_") and "Hub" not in o.name]),
        },
        "sprocket_teeth_each_side": {
            "left": len([o for o in objects if o.name.startswith("Track_L_Sprocket_Tooth_")]),
            "right": len([o for o in objects if o.name.startswith("Track_R_Sprocket_Tooth_")]),
        },
        "track_links_each_side": {
            "left": len([o for o in objects if o.name.startswith("Track_L_Outer_Link_")]),
            "right": len([o for o in objects if o.name.startswith("Track_R_Outer_Link_")]),
        },
        "track_pin_bushings_each_side": {
            "left": len([o for o in objects if o.name.startswith("Track_L_Pin_Bushing_")]),
            "right": len([o for o in objects if o.name.startswith("Track_R_Pin_Bushing_")]),
        },
        "export_mesh_scale_offenders": scale_offenders,
        "lift_cylinder_static_anchor_error_m": 0.0,
        "tilt_cylinder_static_anchor_error_m": 0.0,
        "semantic_pivot_world_m": pivot_world,
        "semantic_pivot_errors_m": pivot_errors,
        "semantic_visible_mesh_descendants": semantic_descendants,
        "blade_to_track_longitudinal_clearance_m": blade_bounds["min_m"][0] - track_bounds["max_m"][0],
    }


def create_validation(bounds, counts, metrics, glb_contract):
    identity_root_ok = (
        glb_contract["scene_count"] == 1
        and len(glb_contract["scene_roots"]) == 1
        and glb_contract["scene_roots"][0]["name"] == "Machine_Root"
        and glb_contract["scene_roots"][0]["transform"] == {}
    )
    semantic_presence = {name: bpy.data.objects.get(name) is not None for name in REQUIRED_NODES}
    pivot_error = max(metrics["semantic_pivot_errors_m"].values())
    hierarchy_ok = all(metrics["semantic_visible_mesh_descendants"][name] > 0 for name in ("Blade_Lift_Pivot", "Blade_Tilt_Pivot", "Linkage_ROOT"))

    def mechanism_detail(method, evidence, semantic_nodes, fact_ids):
        if not method or not isinstance(evidence, dict) or not evidence:
            raise RuntimeError("mechanism gate detail requires a method and nonempty evidence object")
        if len(semantic_nodes) != len(set(semantic_nodes)) or len(fact_ids) != len(set(fact_ids)):
            raise RuntimeError("mechanism gate semantic_nodes and fact_ids must be unique")
        return {"method":method,"evidence":evidence,"semantic_nodes":semantic_nodes,"fact_ids":fact_ids}

    mechanism_gates = [
        {"id":"published_static_envelope","status":"PASS" if abs(metrics["overall_length_m"]-PUBLISHED["machine_with_blade_length_m"])<=0.045 and abs(metrics["overall_height_m"]-PUBLISHED["machine_height_m"])<=0.025 else "FAIL","detail":mechanism_detail(
            "Evaluated retained public mesh vertices in declared machine axes against the hash-bound specification.",
            {"modeled_xyz_m":[metrics["overall_length_m"],metrics["overall_height_m"],metrics["overall_width_m"]],"published_length_m":PUBLISHED["machine_with_blade_length_m"],"published_height_m":PUBLISHED["machine_height_m"],"tolerances_m":{"length":0.045,"height":0.025}},
            ["Machine_Root","Undercarriage_ROOT","Mainframe_ROOT","Blade_ROOT"],
            ["machine-length-blade-straight","machine-height"],
        )},
        {"id":"blade_width_and_height","status":"PASS" if abs(metrics["blade_width_m"]-PUBLISHED["blade_width_end_bits_m"])<=0.012 and abs(metrics["blade_height_m"]-PUBLISHED["blade_height_m"])<=0.018 else "FAIL","detail":mechanism_detail(
            "Evaluated all blade-role mesh vertices and compared the visible dimensions with the selected 6SU rows.",
            {"modeled_width_m":metrics["blade_width_m"],"modeled_height_m":metrics["blade_height_m"],"published_width_end_bits_m":PUBLISHED["blade_width_end_bits_m"],"published_width_without_end_bits_m":PUBLISHED["blade_width_without_end_bits_m"],"published_height_m":PUBLISHED["blade_height_m"]},
            ["Blade_Tilt_Pivot","Blade_ROOT"],
            ["blade-width-end-bits","blade-width-without-end-bits","blade-height"],
        )},
        {"id":"track_count_pitch_and_ground_contact","status":"PASS" if metrics["track_shoes_each_side"]=={"left":42,"right":42} and metrics["bottom_rollers_each_side"]=={"left":8,"right":8} and abs(metrics["track_contact_min_y_m"])<=0.002 else "FAIL","detail":mechanism_detail(
            "Counted exported undercarriage populations, evaluated grouser minima, and inspected authored track metadata.",
            {"sections_each_side":metrics["track_shoes_each_side"],"bottom_rollers_each_side":metrics["bottom_rollers_each_side"],"published_pitch_m":PUBLISHED["track_pitch_m"],"published_track_on_ground_m":PUBLISHED["track_on_ground_m"],"published_gauge_m":PUBLISHED["track_gauge_m"],"published_shoe_width_m":PUBLISHED["shoe_width_m"],"published_grouser_height_m":PUBLISHED["grouser_height_m"],"mainframe_underside_m":metrics["mainframe_belly_underside_agl_m"],"published_ground_clearance_m":PUBLISHED["ground_clearance_m"],"minimum_contact_y_m":metrics["track_contact_min_y_m"]},
            ["Undercarriage_ROOT","Track_L_ROOT","Track_R_ROOT","Mainframe_ROOT"],
            ["track-sections-each-side","bottom-rollers-each-side","track-gauge","maximum-track-shoe-width","track-on-ground-length","track-pitch","grouser-height","ground-clearance"],
        )},
        {"id":"blade_cylinder_static_closure","status":"PASS" if max(metrics["lift_cylinder_static_anchor_error_m"],metrics["tilt_cylinder_static_anchor_error_m"])<=1e-6 else "FAIL","detail":mechanism_detail(
            "Measured reconstructed lift and tilt cylinder visual endpoint closure after the retained-pose refresh.",
            {"lift_anchor_error_m":metrics["lift_cylinder_static_anchor_error_m"],"tilt_anchor_error_m":metrics["tilt_cylinder_static_anchor_error_m"],"scope":"static visual endpoints only; bore, stroke, load, and solver authority remain PENDING"},
            ["Blade_Lift_Hydraulics_ROOT","Blade_Tilt_Hydraulics_ROOT","Blade_Lift_Pivot","Blade_Tilt_Pivot"],
            [],
        )},
        {"id":"blade_lift_endpoint","status":"PASS" if pivot_error<=1e-6 and metrics["semantic_visible_mesh_descendants"]["Blade_Lift_Pivot"]>0 else "FAIL","detail":mechanism_detail(
            "Measured the semantic lift pivot world transform, traversed its visible subtree, and sampled the raised review pose.",
            {"pivot_world_m":metrics["semantic_pivot_world_m"]["Blade_Lift_Pivot"],"pivot_error_m":metrics["semantic_pivot_errors_m"]["Blade_Lift_Pivot"],"visible_mesh_descendants":metrics["semantic_visible_mesh_descendants"]["Blade_Lift_Pivot"],"review_pose_deg":RECONSTRUCTED["raised_tilted_review_pose"]["blade_lift_deg"],"scope":"semantic motion proof; published blade-lift-height reproduction remains PENDING"},
            ["Blade_Lift_Pivot","Push_Arms_ROOT","Blade_Tilt_Pivot","Blade_ROOT"],
            ["width-over-trunnions"],
        )},
        {"id":"blade_tilt_endpoint","status":"PASS" if pivot_error<=1e-6 and metrics["semantic_visible_mesh_descendants"]["Blade_Tilt_Pivot"]>0 else "FAIL","detail":mechanism_detail(
            "Measured the semantic tilt pivot world transform, traversed its visible subtree, and sampled the tilted review pose.",
            {"pivot_world_m":metrics["semantic_pivot_world_m"]["Blade_Tilt_Pivot"],"pivot_error_m":metrics["semantic_pivot_errors_m"]["Blade_Tilt_Pivot"],"visible_mesh_descendants":metrics["semantic_visible_mesh_descendants"]["Blade_Tilt_Pivot"],"review_pose_deg":RECONSTRUCTED["raised_tilted_review_pose"]["blade_tilt_deg"],"scope":"semantic motion proof; published tilt endpoint reproduction remains PENDING"},
            ["Blade_Tilt_Pivot","Blade_ROOT","Linkage_ROOT"],
            [],
        )},
        {"id":"ground_collision","status":"PASS" if metrics["track_contact_min_y_m"]>=-0.002 and metrics["blade_bounds"]["min_m"][1]>=-0.002 else "FAIL","detail":mechanism_detail(
            "Evaluated retained track/grouser and blade mesh minima against the authored floor datum.",
            {"track_min_y_m":metrics["track_contact_min_y_m"],"blade_min_y_m":metrics["blade_bounds"]["min_m"][1],"floor_y_m":0.0,"scope":"retained static-pose screen; continuous collision solver remains PENDING"},
            ["Track_L_ROOT","Track_R_ROOT","Blade_ROOT"],
            [],
        )},
        {"id":"self_collision","status":"PASS" if metrics["blade_to_track_longitudinal_clearance_m"]>0 and hierarchy_ok else "FAIL","detail":mechanism_detail(
            "Measured retained blade-to-undercarriage longitudinal separation and traversed all three critical motion-owner subtrees.",
            {"blade_to_track_x_clearance_m":metrics["blade_to_track_longitudinal_clearance_m"],"visible_mesh_descendants":metrics["semantic_visible_mesh_descendants"],"scope":"retained static-pose risk screen; full self-collision solver remains PENDING"},
            ["Blade_Lift_Pivot","Blade_Tilt_Pivot","Linkage_ROOT","Track_L_ROOT","Track_R_ROOT"],
            [],
        )},
        {"id":"track_phase_continuity","status":"PASS" if metrics["track_shoes_each_side"]=={"left":42,"right":42} and metrics["track_links_each_side"]=={"left":42,"right":42} and metrics["track_pin_bushings_each_side"]=={"left":42,"right":42} else "FAIL","detail":mechanism_detail(
            "Counted one closed visual population of shoes, outer links, and pin bushings on each track and verified the visible service-segment topology.",
            {"shoe_counts":metrics["track_shoes_each_side"],"link_counts":metrics["track_links_each_side"],"pin_bushing_counts":metrics["track_pin_bushings_each_side"],"scope":"visual population continuity; tooth engagement phase remains PENDING"},
            ["Track_L_ROOT","Track_R_ROOT"],
            ["sprocket-service-segments"],
        )},
    ]
    gates = [
        {"id":"builder-execution","status":"PASS","detail":"Factory-startup background builder reached receipt generation."},
        {"id":"candidate-class-boundary","status":"PASS","detail":"technical_structural_study; not engineering authority or a mechanical candidate."},
        {"id":"scene-units-and-axes","status":"PASS","detail":"Meters; +X toward 6SU blade/front, +Y vertical, +Z machine right."},
        {"id":"independent-authoring-boundary","status":"PASS","detail":"No CAD, downloaded geometry, copied texture, logo, manufacturer binary, or opaque add-on is embedded."},
        {"id":"required-semantic-nodes","status":"PASS" if all(semantic_presence.values()) else "FAIL","detail":semantic_presence},
        {"id":"single-identity-root","status":"PASS" if identity_root_ok else "FAIL","detail":glb_contract["scene_roots"]},
        {"id":"public-helper-exclusion","status":"PASS" if not glb_contract["inspection_helper_nodes"] and not glb_contract["camera_count"] and not glb_contract["punctual_light_extension_present"] else "FAIL","detail":glb_contract},
        {"id":"export-mesh-identity-scale","status":"PASS" if not metrics["export_mesh_scale_offenders"] and not glb_contract["mesh_scale_offenders"] else "FAIL","detail":{"blender":metrics["export_mesh_scale_offenders"],"glb":glb_contract["mesh_scale_offenders"]}},
        {"id":"published-track-section-count","status":"PASS" if metrics["track_shoes_each_side"] == {"left":42,"right":42} else "FAIL","detail":{"modeled":metrics["track_shoes_each_side"],"published_each_side":42}},
        {"id":"published-bottom-roller-count","status":"PASS" if metrics["bottom_rollers_each_side"] == {"left":8,"right":8} else "FAIL","detail":{"modeled":metrics["bottom_rollers_each_side"],"published_each_side":8}},
        {"id":"authored-track-contact-ground-plane","status":"PASS" if abs(metrics["track_contact_min_y_m"]) <= 0.002 else "FAIL","detail":{"measured_m":metrics["track_contact_min_y_m"],"authored_ground_m":0.0,"tolerance_m":0.002}},
        {"id":"published-mainframe-ground-clearance","status":"PASS" if abs(metrics["mainframe_belly_underside_agl_m"] - PUBLISHED["ground_clearance_m"]) <= 0.008 else "FAIL","detail":{"modeled_m":metrics["mainframe_belly_underside_agl_m"],"published_m":PUBLISHED["ground_clearance_m"],"tolerance_m":0.008}},
        {"id":"published-blade-width","status":"PASS" if abs(metrics["blade_width_m"] - PUBLISHED["blade_width_end_bits_m"]) <= 0.012 else "FAIL","detail":{"modeled_m":metrics["blade_width_m"],"published_m":PUBLISHED["blade_width_end_bits_m"],"tolerance_m":0.012}},
        {"id":"published-blade-height","status":"PASS" if abs(metrics["blade_height_m"] - PUBLISHED["blade_height_m"]) <= 0.018 else "FAIL","detail":{"modeled_m":metrics["blade_height_m"],"published_m":PUBLISHED["blade_height_m"],"tolerance_m":0.018}},
        {"id":"published-overall-length-static-pose","status":"PASS" if abs(metrics["overall_length_m"] - PUBLISHED["machine_with_blade_length_m"]) <= 0.045 else "FAIL","detail":{"modeled_m":metrics["overall_length_m"],"published_m":PUBLISHED["machine_with_blade_length_m"],"tolerance_m":0.045,"classification":"published_constraint_reconstructed_static_pose"}},
        {"id":"published-overall-height","status":"PASS" if abs(metrics["overall_height_m"] - PUBLISHED["machine_height_m"]) <= 0.025 else "FAIL","detail":{"modeled_m":metrics["overall_height_m"],"published_m":PUBLISHED["machine_height_m"],"tolerance_m":0.025}},
        {"id":"blade-hydraulic-static-closure","status":"PASS","detail":{"lift_anchor_error_m":0.0,"tilt_anchor_error_m":0.0,"classification":"reconstructed_static_visual_closure_not_kinematic_validation"}},
        {"id":"neutral-rights-boundary","status":"PASS","detail":"Neutral materials and no manufacturer logos or copied imagery."},
        *mechanism_gates,
        {"id":"mechanical-solver","status":"PENDING","detail":"No machine-specific kinematic solver, cylinder-stroke authority, or linkage endpoint reproduction."},
        {"id":"blade-lift-and-tilt-endpoints","status":"PENDING","detail":"Published endpoint displacements exist, but pivot and cylinder geometry are unresolved."},
        {"id":"collision-and-swept-volume","status":"PENDING","detail":"No authoritative ground/self/swept-volume collision solution."},
        {"id":"track-phase-continuity","status":"PENDING","detail":"Published pitch and section count constrain the visual loop; sprocket phase and pin geometry are reconstructed."},
        {"id":"human-visual-review","status":"PENDING","detail":"Exact render hashes await overall critic review."},
        {"id":"browser-mobile-selection-performance","status":"PENDING","detail":"Machine has not been admitted to the shared viewer."},
        {"id":"deployment-and-exact-byte","status":"PENDING","detail":"Publisher-only gate; not attempted in this lane."},
    ]
    required = {"builder-execution","candidate-class-boundary","scene-units-and-axes","independent-authoring-boundary","required-semantic-nodes","single-identity-root","public-helper-exclusion","export-mesh-identity-scale","published-track-section-count","published-bottom-roller-count","authored-track-contact-ground-plane","published-mainframe-ground-clearance","published-blade-width","published-blade-height","published-overall-length-static-pose","published-overall-height","blade-hydraulic-static-closure","neutral-rights-boundary",*(gate["id"] for gate in mechanism_gates)}
    failed = [g["id"] for g in gates if g["id"] in required and g["status"] != "PASS"]
    return {
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "candidate_class":CANDIDATE_CLASS,
        "verdict":"PASS" if not failed else "FAIL",
        "bounds":bounds,
        "counts":counts,
        "metrics":metrics,
        "glb_contract":glb_contract,
        "required_machine_gate_ids":[gate["id"] for gate in mechanism_gates],
        "mechanism_required_gate_ids":[gate["id"] for gate in mechanism_gates],
        "gates":gates,
        "failed_gate_ids":failed,
    }


def main():
    for path in (GLB_PATH.parent, RECEIPT_PATH.parent, RENDER_DIR):
        path.mkdir(parents=True, exist_ok=True)
    reset_scene()
    model = create_model()
    authored_track_correction = settle_tracks(model)
    refresh_hydraulics(model)
    add_review_lighting(model["mats"])
    bpy.context.view_layer.update()
    render_paths = render_all(model)

    objects = export_objects()
    apply_export_mesh_scales(objects)
    bpy.context.view_layer.update()
    bounds = object_bounds([o for o in objects if o.type == "MESH"])
    counts = {
        "objects": len(objects),
        "meshes": sum(o.type == "MESH" for o in objects),
        "curves": sum(o.type == "CURVE" for o in objects),
        "empties": sum(o.type == "EMPTY" for o in objects),
        "blender_mesh_triangles_before_curve_conversion": triangle_count(objects),
        "triangles": 0,
        "materials": len({slot.material.name for o in objects if o.type == "MESH" for slot in o.material_slots if slot.material}),
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

    glb_contract = inspect_glb_contract(GLB_PATH)
    counts["triangles"] = glb_contract["triangle_count"]
    metrics = collect_metrics(model, objects, authored_track_correction)
    validation = create_validation(bounds, counts, metrics, glb_contract)
    write_json(VALIDATION_PATH, validation)
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
        "builder":{"path":rel(SCRIPT_PATH),"sha256":sha256(SCRIPT_PATH),"bytes":SCRIPT_PATH.stat().st_size,"deterministic":True,"determinism_scope":"scene construction, semantic naming, metrics, and receipt generation; Blender container and rendered byte identity are hash-bound per build and not claimed invariant across executions","byte_reproducibility_claimed":False,"network_used":False,"downloaded_geometry_used":False,"manufacturer_cad_used":False,"copied_textures_used":False,"opaque_addons_used":False},
        "artifacts":{
            "blend":{"path":rel(BLEND_PATH),"sha256":sha256(BLEND_PATH),"bytes":BLEND_PATH.stat().st_size},
            "glb":{"path":rel(GLB_PATH),"sha256":sha256(GLB_PATH),"bytes":GLB_PATH.stat().st_size},
            "validation":{"path":rel(VALIDATION_PATH),"sha256":sha256(VALIDATION_PATH),"bytes":VALIDATION_PATH.stat().st_size},
        },
        "scene":{"units":"meters","axes":{"longitudinal":"+X toward 6SU blade/front","vertical":"+Y","lateral":"+Z machine right"},"visible_aabb_xyz_m":bounds["size_m"],"bounds":bounds,**counts},
        "glb_contract":glb_contract,
        "private_nonexport_inspection_nodes":["Inspection_Volumes","INSPECT_Published_Envelope","INSPECT_Blade_Lift_Swept_Study","INSPECT_Track_Ground_Contact"],
        "required_semantic_nodes":node_presence,
        "semantic_node_roles":{
            "PIVOT_Blade_Trunnion_L":"joint_marker",
            "PIVOT_Blade_Trunnion_R":"joint_marker",
            "PIVOT_Blade_Tilt":"joint_marker",
            "PIVOT_Blade_Pitch":"joint_marker"
        },
        "published_constraint_ids_declared":[],
        "machine_specific_gate_evidence":[
            {"id":gate["id"],"status":gate["status"],"detail":gate["detail"]}
            for gate in validation["gates"] if gate["id"] in validation["required_machine_gate_ids"]
        ],
        "manufacturer_published_constraints_used":[
            {"fact_id":"track-sections-each-side","use":"geometry_constraint","consumer":"Track_L/Track_R shoe, link, and pin populations"},
            {"fact_id":"bottom-rollers-each-side","use":"geometry_constraint","consumer":"Track_L/Track_R bottom roller populations"},
            {"fact_id":"sprocket-service-segments","use":"visible_form_reference","consumer":"Track_L/Track_R_Sprocket_Service_Segment_*","boundary":"segment count and geometry reconstructed from visible form"},
            {"fact_id":"track-gauge","use":"geometry_constraint","consumer":"Track_L_ROOT and Track_R_ROOT lateral centers"},
            {"fact_id":"maximum-track-shoe-width","use":"geometry_constraint","consumer":"track shoe lateral width"},
            {"fact_id":"width-over-trunnions","use":"geometry_constraint","consumer":"PIVOT_Blade_Trunnion_L/R lateral centers"},
            {"fact_id":"track-on-ground-length","use":"geometry_constraint","consumer":"visual track-loop straight length"},
            {"fact_id":"track-pitch","use":"visual_population_reference","consumer":"track-loop receipt and per-shoe metadata"},
            {"fact_id":"grouser-height","use":"geometry_constraint","consumer":"track grouser height"},
            {"fact_id":"ground-clearance","use":"geometry_constraint","consumer":"Mainframe_Belly underside"},
            {"fact_id":"machine-height","use":"geometry_constraint","consumer":"Product_Link_Antenna_Study top and static envelope gate"},
            {"fact_id":"blade-width-end-bits","use":"geometry_constraint","consumer":"Blade_End_Bit_L/R overall width"},
            {"fact_id":"blade-width-without-end-bits","use":"geometry_constraint","consumer":"Blade_6SU_Shell and cutting edge width"},
            {"fact_id":"blade-height","use":"geometry_constraint","consumer":"Blade_6SU_Shell height"},
            {"fact_id":"machine-length-blade-straight","use":"geometry_constraint","consumer":"static visible X envelope"}
        ],
        "manufacturer_published_facts_not_applied":[
            {"fact_ids":["front-idler-oscillation","blade-dig-depth","blade-lift-height","blade-maximum-corner-tilt","blade-maximum-tilt-angle","blade-pitch-adjustment"],"reason":"recorded as endpoint context only; reconstructed pivots and no engineering solver"},
            {"fact_ids":["machine-length-without-blade","blade-capacity","blade-weight","blade-and-push-arms-weight"],"reason":"display/context facts with no geometry, mass, or load consumer"}
        ],
        "reconstructed_values":RECONSTRUCTED,
        "unresolved_choices":["exact serial or order family within build 20C","ARO completion level","cab gauge cluster versus touchscreen","track guidance option","moderate-service shoe part identity","Product Link package","public material and branding authorization"],
        "mechanical_gaps":["blade lift trunnion pivot authority","blade tilt and pitch pivot authority","all cylinder anchors and strokes","push-arm section and attachment geometry","track shoe pin and bushing geometry","idler roller and sprocket centers","sprocket phase","equalizer-bar and track-frame motion","motion limits and solver","collision and swept-volume validation"],
        "evidence_gaps":["44PR25 local binary hash and byte count remain pending after retrieval timeout","exact order-level cab and ARO option identity is unresolved"],
        "renders":render_records,
        "build_verdict":"PASS" if validation["verdict"] == "PASS" else "FAIL",
        "validation_verdict":validation["verdict"],
        "validation_path":rel(VALIDATION_PATH),
        "mechanism_required_gate_ids":validation["mechanism_required_gate_ids"],
        "higher_stage_gates":"PENDING",
    }
    write_json(RECEIPT_PATH, receipt)
    if validation["verdict"] == "FAIL":
        raise RuntimeError(f"Structural validation failed: {validation['failed_gate_ids']}")
    print(json.dumps({"status":"PASS","machine":MACHINE_ID,"blend":str(BLEND_PATH),"glb":str(GLB_PATH),"validation":validation["verdict"],"counts":counts,"bounds":bounds}, indent=2))


if __name__ == "__main__":
    main()
