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
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


SCRIPT_PATH = Path(__file__).resolve()
MACHINE_DIR = SCRIPT_PATH.parents[2]
REPO_ROOT = MACHINE_DIR.parents[1]
BLEND_PATH = SCRIPT_PATH.parent / "cat-320-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets" / "cat-320-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production" / "asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production" / "validation.json"
RENDER_DIR = MACHINE_DIR / "review" / "renders"
CONFIGURATION_PATH = MACHINE_DIR / "configuration.json"
FACTS_PATH = MACHINE_DIR / "evidence" / "facts.json"
SOURCE_MANIFEST_PATH = MACHINE_DIR / "evidence" / "source-manifest.json"
MECHANISM_PATH = MACHINE_DIR / "mechanism.json"
DESIGN_PATH = MACHINE_DIR / "source" / "design.json"

MACHINE_ID = "cat-320"
CONFIGURATION_ID = "CAT-320-07H-NAM-RB57-R29-HD119-LU-TG790-CW42-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"
SOURCE_ID = "CAT-320-AEXQ3758-01-NAM"
SOURCE_SHA256 = "3c8a3801febde2f7728ba13d3b9cfe59528bc08394f9cf57dfd0e618ef158a98"
SOURCE_BYTES = 2_285_842
SOURCE_PAGES = 24
SOURCE_PUBLICATION = "AEXQ3758-01"
SOURCE_BUILD_NUMBER = "07H"
SOURCE_MARKET = "North America"

ROUND_1_BASELINE = {
    "tail_swing_radius_m": 2.4167622706023075,
    "counterweight_clearance_agl_m": 1.4858722686767578,
    "engine_house_length_m": 1.8363363146781921,
    "engine_house_height_m": 1.2400001287460327,
    "unapplied_hydraulic_linkage_handrail_meshes": 11,
    "glb_scene_roots": ["Machine_Root"],
}

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
        "stick_relative_deg": -67.6,
        "bucket_relative_deg": 232.0,
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
    "boom_pivot_m": [0.10, 1.86, 0.0],
    "boom_centerline_polyline_local_m": [[0.0, 0.0], [1.15, 0.85], [2.25, 1.22], [4.05, 0.82], [5.32, 0.95]],
    "stick_pivot_local_m": [5.32, 0.95, 0.0],
    "stick_modeled_pin_distance_m": 2.90,
    "bucket_pivot_local_m": [2.90, 0.0, 0.0],
    "bucket_shell_width_m": 1.20,
    "bucket_shell_note": "Width is a compatible published HD 1.19 m3 table option, but pin-on/coupler identity remains unresolved; shell curvature and volume are not engineering-validated.",
    "track_loop_radius_m": 0.39,
    "track_shoe_modeled_pitch_m": 0.199,
    "track_shoe_thickness_m": 0.075,
    "wheel_and_roller_centers": "Reconstructed from the published track length, roller-center length, counts, and visible first-party illustrations.",
    "cab_house_counterweight_panels": "Independently authored from first-party illustration observations; no hidden internal assembly is represented.",
    "engine_house_visible_target_m": {"length_range": [2.35, 2.65], "height_range": [0.95, 1.15]},
    "drive_sprocket_teeth_each_side": 14,
    "hose_bundle_paths": "Reconstructed exterior routing cues only; no hose diameter, pressure, fitting, or service authority.",
    "hydraulic_anchors": "All base and rod anchor coordinates are reconstructed. Published strokes constrain future solver work only.",
    "bucket_linkage": "Bellcrank, dogbone, bucket lug, and all pin locations are reconstructed visual closure cues only.",
    "inspection_volumes": "Envelope and component volumes are non-authoritative visualization aids.",
    "material_colors": "Low-saturation neutral slate body, graphite trim, steel, rubber, and smoke glass; no manufacturer-identifying yellow or protected livery is represented.",
    "validated_review_pose_set": {
        "classification": "two independently measured reconstructed review poses; not a continuous manufacturer motion range",
        "poses": ["stowed_transport", "articulated_review"],
    },
}

REQUIRED_SEMANTICS = {
    "Machine_Root": {"type": "EMPTY", "parent": None, "role": "machine_root", "min_mesh_descendants": 1},
    "Undercarriage_ROOT": {"type": "EMPTY", "parent": "Machine_Root", "role": "fixed_group", "min_mesh_descendants": 1},
    "Track_L_ROOT": {"type": "EMPTY", "parent": "Undercarriage_ROOT", "role": "track_group", "min_mesh_descendants": 49},
    "Track_R_ROOT": {"type": "EMPTY", "parent": "Undercarriage_ROOT", "role": "track_group", "min_mesh_descendants": 49},
    "Upper_Swing_Pivot": {"type": "EMPTY", "parent": "Undercarriage_ROOT", "role": "revolute_pivot", "axis": "+Y", "min_mesh_descendants": 1},
    "Upper_ROOT": {"type": "EMPTY", "parent": "Upper_Swing_Pivot", "role": "articulated_group", "min_mesh_descendants": 1},
    "Boom_Pivot": {"type": "EMPTY", "parent": "Upper_ROOT", "role": "revolute_pivot", "axis": "+Z", "min_mesh_descendants": 1},
    "Boom_ROOT": {"type": "EMPTY", "parent": "Boom_Pivot", "role": "articulated_group", "min_mesh_descendants": 1},
    "Stick_Pivot": {"type": "EMPTY", "parent": "Boom_Pivot", "role": "revolute_pivot", "axis": "+Z", "min_mesh_descendants": 1},
    "Stick_ROOT": {"type": "EMPTY", "parent": "Stick_Pivot", "role": "articulated_group", "min_mesh_descendants": 1},
    "Bucket_Pivot": {"type": "EMPTY", "parent": "Stick_Pivot", "role": "revolute_pivot", "axis": "+Z", "min_mesh_descendants": 1},
    "Bucket_ROOT": {"type": "EMPTY", "parent": "Bucket_Pivot", "role": "articulated_group", "min_mesh_descendants": 1},
    "Boom_Hydraulics_ROOT": {"type": "EMPTY", "parent": "Upper_ROOT", "role": "hydraulic_owner_group", "min_mesh_descendants": 1},
    "Stick_Hydraulics_ROOT": {"type": "EMPTY", "parent": "Boom_ROOT", "role": "hydraulic_owner_group", "min_mesh_descendants": 1},
    "Bucket_Hydraulics_ROOT": {"type": "EMPTY", "parent": "Stick_ROOT", "role": "hydraulic_owner_group", "min_mesh_descendants": 1},
    "Bucket_Linkage_ROOT": {"type": "EMPTY", "parent": "Stick_ROOT", "role": "linkage_owner_group", "min_mesh_descendants": 1},
    "Bucket_Bellcrank_ROOT": {"type": "EMPTY", "parent": "Stick_ROOT", "role": "linkage_pivot", "min_mesh_descendants": 1},
    "PIVOT_Attachment_Pin": {"type": "MESH", "parent": "Bucket_Pivot", "role": "attachment_pivot"},
    "Bucket_Tip_Radius_Point_1p570m": {"type": "MESH", "parent": "Bucket_ROOT", "role": "dimension_witness"},
}
REQUIRED_NODES = list(REQUIRED_SEMANTICS)

# Only constraints that materially shape or bound this model belong here.
# Published cylinder strokes and nominal boom length remain sourced future
# mechanism inputs; they are deliberately not claimed as used by this static
# geometry because there is no travel solver or authoritative hidden pin span.
DESIGN_FACT_IDS = [
    "stick-length",
    "transport-length",
    "transport-height",
    "undercarriage-width",
    "upperframe-width",
    "tail-swing-radius",
    "counterweight-clearance",
    "ground-clearance",
    "track-length",
    "roller-center-length",
    "track-gauge",
    "track-shoes-per-side",
    "track-rollers-per-side",
    "carrier-rollers-per-side",
    "top-cab-height",
    "bucket-tip-radius",
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


def parent_keep_world(obj, parent):
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


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
        if label == "Rear_Sprocket":
            # Reconstructed visible tooth cues. Count/shape are not manufacturer authority.
            for tooth_index in range(RECONSTRUCTED["drive_sprocket_teeth_each_side"]):
                theta = tooth_index * math.tau / RECONSTRUCTED["drive_sprocket_teeth_each_side"]
                tooth = box(
                    f"{prefix}_Drive_Sprocket_Tooth_{tooth_index+1:02d}",
                    (x + math.cos(theta)*0.310, 0.54 + math.sin(theta)*0.310, z_center),
                    (0.135, 0.070, 0.56), mats["steel"], root, 0.012, "drive_sprocket_tooth",
                )
                tooth.rotation_euler[2] = theta

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

    # The source defines overall track length independently from roller-center
    # length. Normalize only the reconstructed shoe loop to the 4.450 m visible
    # subtree length, preserving the published +/-1.825 m roller centers.
    bpy.context.view_layer.update()
    shoes = sorted(
        [obj for obj in bpy.data.objects if obj.name.startswith(f"{prefix}_Shoe_")],
        key=lambda obj: obj.name,
    )
    for _ in range(3):
        points = evaluated_world_points(shoes)
        minimum = min(point.x for point in points)
        maximum = max(point.x for point in points)
        measured = maximum - minimum
        center = (minimum + maximum) / 2
        factor = PUBLISHED["track_length_m"] / measured
        for obj in shoes:
            for vertex in obj.data.vertices:
                vertex.co.x = (vertex.co.x - center) * factor
        bpy.context.view_layer.update()
    final_points = evaluated_world_points(shoes)
    root["published_track_length_m"] = PUBLISHED["track_length_m"]
    root["measured_shoe_loop_length_m"] = max(point.x for point in final_points) - min(point.x for point in final_points)
    root["roller_center_length_m"] = PUBLISHED["roller_center_length_m"]


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
    rotation = Vector((0, 0, 1)).rotation_difference(vector.normalized())
    obj.matrix_world = Matrix.LocRotScale((start + end) / 2, rotation, (radius, radius, length))


def apply_export_mesh_scales(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.select_set(False)


def evaluated_world_points(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
    return points


def object_descendants(obj):
    descendants = []
    pending = list(obj.children)
    while pending:
        child = pending.pop()
        descendants.append(child)
        pending.extend(child.children)
    return descendants


def semantic_contract_records():
    records = {}
    for name, expected in REQUIRED_SEMANTICS.items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            records[name] = {"pass": False, "expected": expected, "observed": None}
            continue
        descendants = object_descendants(obj)
        observed = {
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "role": obj.get("exo_role"),
            "axis": obj.get("axis"),
            "mesh_descendants": len([
                child for child in descendants
                if child.type == "MESH" and child.get("exo_export", False)
            ]),
        }
        passed = all(
            observed.get(key) == value
            for key, value in expected.items()
            if key not in {"min_mesh_descendants"}
        )
        if "min_mesh_descendants" in expected:
            passed = passed and observed["mesh_descendants"] >= expected["min_mesh_descendants"]
        records[name] = {"pass": passed, "expected": expected, "observed": observed}
    return records


def calibrate_planar_radius(objects, parent, target_radius_m):
    """Scale authored XY geometry until its evaluated maximum radius is exact."""
    for _ in range(4):
        inverse_parent = parent.matrix_world.inverted()
        evaluated = [
            (inverse_parent @ point, obj.name)
            for obj in objects
            for point in evaluated_world_points([obj])
        ]
        tip, _ = max(evaluated, key=lambda item: math.hypot(item[0].x, item[0].y))
        measured = math.hypot(tip.x, tip.y)
        factor = target_radius_m / measured
        for obj in objects:
            object_to_parent = inverse_parent @ obj.matrix_world
            parent_to_object = object_to_parent.inverted()
            for vertex in obj.data.vertices:
                point = object_to_parent @ vertex.co
                point.x *= factor
                point.y *= factor
                vertex.co = parent_to_object @ point
        bpy.context.view_layer.update()
    inverse_parent = parent.matrix_world.inverted()
    evaluated = [
        (inverse_parent @ point, obj.name)
        for obj in objects
        for point in evaluated_world_points([obj])
    ]
    tip, object_name = max(evaluated, key=lambda item: math.hypot(item[0].x, item[0].y))
    return tip, object_name, math.hypot(tip.x, tip.y)


def tip_witness(name, tip, mat, parent):
    radial = Vector((tip.x, tip.y, 0.0)).normalized()
    lateral = Vector((-radial.y, radial.x, 0.0))
    # Keep the witness apex on the exact farthest tooth vertex in all three
    # coordinates. The published radius is planar XY, but the semantic witness
    # must also make physical 3D contact rather than floating at Z=0.
    tip_point = Vector((tip.x, tip.y, tip.z))
    base = tip_point - radial * 0.045
    vertices = [
        tuple(tip_point),
        tuple(base + lateral * 0.014 + Vector((0, 0, -0.014))),
        tuple(base - lateral * 0.014 + Vector((0, 0, -0.014))),
        tuple(base + Vector((0, 0, 0.014))),
    ]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], [(0,1,2),(0,3,1),(0,2,3),(1,3,2)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(mat)
    tag(obj, "dimension_witness", True, "manufacturer_published_constraint")
    obj["source_id"] = SOURCE_ID
    obj["source_locator"] = "PDF page 4, Dimensions table, Bucket Type HD row, Bucket Tip Radius"
    obj["published_radius_m"] = PUBLISHED["bucket_tip_radius_m"]
    obj["measurement"] = "planar XY radius from Bucket_Pivot/Bucket_ROOT origin to witness apex"
    return obj


def evaluated_bounds(objects):
    points = evaluated_world_points(objects)
    return {
        "min": [min(point[index] for point in points) for index in range(3)],
        "max": [max(point[index] for point in points) for index in range(3)],
    }


def bounds_gap(a, b):
    gaps = [max(a["min"][axis] - b["max"][axis], b["min"][axis] - a["max"][axis], 0.0) for axis in range(3)]
    return math.sqrt(sum(gap * gap for gap in gaps)), gaps


def object_center_world(obj):
    bounds = evaluated_bounds([obj])
    return Vector(tuple((bounds["min"][axis] + bounds["max"][axis]) / 2 for axis in range(3)))


def inspect_render_files(paths):
    records = []
    for path in paths:
        signature_ok = path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        image = bpy.data.images.load(str(path), check_existing=False)
        width, height = image.size
        luminance = []
        for y in range(0, height, max(1, height // 24)):
            for x in range(0, width, max(1, width // 32)):
                index = 4 * (y * width + x)
                red, green, blue = image.pixels[index:index+3]
                luminance.append(0.2126 * red + 0.7152 * green + 0.0722 * blue)
        record = {
            "path": rel(path),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "width_px": width,
            "height_px": height,
            "png_signature": signature_ok,
            "sampled_luminance_min": min(luminance),
            "sampled_luminance_max": max(luminance),
            "sampled_luminance_span": max(luminance) - min(luminance),
        }
        record["pass"] = (
            signature_ok and width == 720 and height == 540
            and record["bytes"] > 20_000 and record["sampled_luminance_span"] > 0.08
        )
        records.append(record)
        bpy.data.images.remove(image)
    return records


def verify_source_configuration_contract():
    configuration = json.loads(CONFIGURATION_PATH.read_text(encoding="utf-8"))
    facts_payload = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    mechanism = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    source = next((entry for entry in manifest["sources"] if entry["id"] == SOURCE_ID), None)
    source_path = REPO_ROOT / source["local_path"] if source else None
    expected_facts = {
        "boom-length": PUBLISHED["boom_length_m"],
        "stick-length": PUBLISHED["stick_length_m"],
        "boom-cylinder-stroke": PUBLISHED["boom_cylinder_stroke_m"],
        "stick-cylinder-stroke": PUBLISHED["stick_cylinder_stroke_m"],
        "bucket-cylinder-stroke": PUBLISHED["bucket_cylinder_stroke_m"],
        "transport-length": PUBLISHED["transport_length_m"],
        "transport-height": PUBLISHED["transport_height_m"],
        "undercarriage-width": PUBLISHED["undercarriage_width_m"],
        "maximum-digging-depth": 6.73,
        "maximum-ground-reach": 9.87,
        "top-cab-height": PUBLISHED["cab_height_m"],
        "upperframe-width": PUBLISHED["upperframe_width_m"],
        "tail-swing-radius": PUBLISHED["tail_swing_radius_m"],
        "counterweight-clearance": PUBLISHED["counterweight_clearance_m"],
        "ground-clearance": PUBLISHED["ground_clearance_m"],
        "track-length": PUBLISHED["track_length_m"],
        "roller-center-length": PUBLISHED["roller_center_length_m"],
        "track-gauge": PUBLISHED["track_gauge_m"],
        "bucket-tip-radius": PUBLISHED["bucket_tip_radius_m"],
        "track-shoes-per-side": PUBLISHED["shoe_count_each_side"],
        "track-rollers-per-side": PUBLISHED["track_rollers_each_side"],
        "carrier-rollers-per-side": PUBLISHED["carrier_rollers_each_side"],
    }
    published_facts = {
        fact["id"]: fact for fact in facts_payload["facts"]
        if fact["authority"] == "manufacturer_published"
    }
    fact_records = {}
    for fact_id, expected_value in expected_facts.items():
        fact = published_facts.get(fact_id)
        fact_records[fact_id] = {
            "pass": bool(
                fact and fact.get("source_id") == SOURCE_ID
                and fact.get("value") == expected_value
                and isinstance(fact.get("source_page"), int)
                and isinstance(fact.get("source_section"), str) and fact["source_section"]
                and isinstance(fact.get("source_row"), str) and fact["source_row"]
            ),
            "source_page": fact.get("source_page") if fact else None,
            "source_section": fact.get("source_section") if fact else None,
            "source_row": fact.get("source_row") if fact else None,
            "value": fact.get("value") if fact else None,
        }
    choices = configuration.get("choices", {})
    traces = configuration.get("choice_trace", {})
    choice_records = {
        key: {
            "pass": key in traces and traces[key].get("source_id") == SOURCE_ID
            and isinstance(traces[key].get("source_page"), int)
            and bool(traces[key].get("source_section")) and bool(traces[key].get("source_row")),
            "value": value,
            "trace": traces.get(key),
        }
        for key, value in choices.items()
    }
    source_record = {
        "path": source["local_path"] if source else None,
        "actual_sha256": sha256(source_path) if source_path and source_path.exists() else None,
        "actual_bytes": source_path.stat().st_size if source_path and source_path.exists() else None,
        "manifest_sha256": source.get("sha256") if source else None,
        "manifest_bytes": source.get("bytes") if source else None,
        "manifest_pages": source.get("pages") if source else None,
        "publication": source.get("publication") if source else None,
        "market": source.get("market") if source else None,
        "document_identity": source.get("document_identity") if source else None,
    }
    source_record["pass"] = bool(
        source and source.get("admission") == "primary"
        and source_record["actual_sha256"] == source_record["manifest_sha256"] == SOURCE_SHA256
        and source_record["actual_bytes"] == source_record["manifest_bytes"] == SOURCE_BYTES
        and source_record["manifest_pages"] == SOURCE_PAGES
        and source_record["publication"] == SOURCE_PUBLICATION
        and source_record["market"] == SOURCE_MARKET
        and source.get("document_identity", {}).get("build_number") == SOURCE_BUILD_NUMBER
    )
    identity_ok = (
        configuration.get("machine_id") == MACHINE_ID
        and configuration.get("configuration_id") == CONFIGURATION_ID
        and configuration.get("identity", {}).get("publication_family") == SOURCE_BUILD_NUMBER
        and configuration.get("identity", {}).get("market") == SOURCE_MARKET
        and facts_payload.get("configuration_id") == CONFIGURATION_ID
        and manifest.get("configuration_id") == CONFIGURATION_ID
        and mechanism.get("configuration_id") == CONFIGURATION_ID
        and design.get("machine_id") == MACHINE_ID
        and design.get("configuration_id") == CONFIGURATION_ID
    )
    design_ok = design.get("published_constraints_used") == DESIGN_FACT_IDS
    return {
        "pass": source_record["pass"] and identity_ok and design_ok
        and all(record["pass"] for record in fact_records.values())
        and all(record["pass"] for record in choice_records.values()),
        "identity_pass": identity_ok,
        "design_pass": design_ok,
        "design_published_constraints_used": design.get("published_constraints_used"),
        "source": source_record,
        "facts": fact_records,
        "choices": choice_records,
        "mechanism_required_gates": mechanism.get("required_gates", []),
    }


def endpoint_error(obj, anchors):
    local_z = [corner[2] for corner in obj.bound_box]
    endpoints = [obj.matrix_world @ Vector((0, 0, min(local_z))), obj.matrix_world @ Vector((0, 0, max(local_z)))]
    targets = [world(anchor) for anchor in anchors]
    return max(min((endpoint-target).length for endpoint in endpoints) for target in targets)


def inspect_glb_contract(path):
    data = path.read_bytes()
    offset = 12
    json_chunk = None
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset:offset+length]
        offset += length
        if kind == 0x4E4F534A:
            json_chunk = chunk
            break
    if json_chunk is None:
        raise RuntimeError("GLB JSON chunk missing")
    document = json.loads(json_chunk.decode("utf-8").rstrip("\x00 "))
    materials = document.get("materials", [])
    material_usage_counts = {index: 0 for index in range(len(materials))}
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            material_index = primitive.get("material")
            if material_index in material_usage_counts:
                material_usage_counts[material_index] += 1
    scene = document["scenes"][document.get("scene", 0)]
    root_indices = scene.get("nodes", [])
    roots = []
    for index in root_indices:
        node = document["nodes"][index]
        transform = {key: node[key] for key in ("translation", "rotation", "scale", "matrix") if key in node}
        roots.append({"index": index, "name": node.get("name"), "transform": transform})
    return {
        "scene_count": len(document.get("scenes", [])),
        "scene_roots": roots,
        "camera_count": len(document.get("cameras", [])),
        "punctual_light_extension_present": "KHR_lights_punctual" in document.get("extensions", {}),
        "inspection_helper_nodes": sorted(
            node.get("name", "")
            for node in document.get("nodes", [])
            if node.get("name", "").startswith("INSPECT_") or node.get("name") == "Inspection_Volumes"
        ),
        "node_names": sorted(node.get("name", "") for node in document.get("nodes", [])),
        "material_names": sorted(material.get("name", "") for material in materials),
        "materials": [
            {
                "name": material.get("name", ""),
                "base_color_rgba": material.get("pbrMetallicRoughness", {}).get("baseColorFactor"),
                "metallic_factor": material.get("pbrMetallicRoughness", {}).get("metallicFactor"),
                "roughness_factor": material.get("pbrMetallicRoughness", {}).get("roughnessFactor"),
                "primitive_usage_count": material_usage_counts[index],
            }
            for index, material in enumerate(materials)
        ],
        "image_count": len(document.get("images", [])),
        "texture_count": len(document.get("textures", [])),
        "animation_count": len(document.get("animations", [])),
        "skin_count": len(document.get("skins", [])),
        "external_uri_count": sum(
            1 for collection in ("buffers", "images")
            for item in document.get(collection, []) if item.get("uri")
        ),
        "platform_axes": "+X longitudinal, +Y vertical, +Z machine right",
    }


def world(anchor):
    return anchor.matrix_world.translation.copy()


def add_pin(name, location, radius, length, mat, parent, role="pivot_marker"):
    return cylinder(name, location, radius, length, mat, parent, vertices=24, role=role)


def create_model():
    mats = {
        "ochre": material("Neutral_Slate_Body", (0.24, 0.29, 0.31), 0.14, 0.48),
        "ochre_dark": material("Neutral_Graphite_Trim", (0.065, 0.080, 0.090), 0.32, 0.46),
        "track": material("Neutral_Track_Steel", (0.075, 0.085, 0.095), 0.72, 0.33),
        "steel_dark": material("Neutral_Graphite_Steel", (0.035, 0.045, 0.055), 0.62, 0.30),
        "steel": material("Neutral_Machined_Steel", (0.25, 0.28, 0.30), 0.82, 0.24),
        "rod": material("Neutral_Hydraulic_Rod", (0.53, 0.56, 0.59), 0.93, 0.14),
        "rubber": material("Neutral_Rubber", (0.015, 0.018, 0.021), 0.05, 0.78),
        "glass": material("Neutral_Smoke_Glass", (0.045, 0.095, 0.12), 0.35, 0.16),
        "bolt": material("Neutral_Fastener", (0.12, 0.13, 0.14), 0.85, 0.23),
        "safety": material("Neutral_Muted_Copper_Accent", (0.28, 0.18, 0.12), 0.18, 0.52),
        "interior": material("Neutral_Cab_Interior", (0.025, 0.030, 0.034), 0.1, 0.66),
        "ground": material("Review_Ground", (0.055, 0.065, 0.075), 0.0, 0.74),
    }

    machine = empty("Machine_Root", role="machine_root", size=0.32)
    under = empty("Undercarriage_ROOT", parent=machine, role="fixed_group", size=0.24)
    left_root = empty("Track_L_ROOT", parent=under, role="track_group", size=0.18)
    right_root = empty("Track_R_ROOT", parent=under, role="track_group", size=0.18)
    build_track("L", -PUBLISHED["track_gauge_m"] / 2, left_root, mats)
    build_track("R", PUBLISHED["track_gauge_m"] / 2, right_root, mats)
    # Author the visible track contact surface at Y=0. This correction is
    # derived from the evaluated reconstructed shoe meshes, not from an empty
    # witness or a viewer-side offset.
    bpy.context.view_layer.update()
    track_shoes = [obj for obj in bpy.data.objects if obj.get("exo_role") == "track_shoe"]
    contact_before = min(point.y for point in evaluated_world_points(track_shoes))
    left_root.location.y -= contact_before
    right_root.location.y -= contact_before
    machine["track_contact_correction_m"] = -contact_before

    # Published 470 mm clearance is represented beneath the center carbody.
    box("Undercarriage_Center_Frame", (0.0, 0.635, 0.0), (2.35, 0.33, 1.70), mats["steel_dark"], under, 0.06, "fixed_structure")
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
    side_profile("Counterweight_Core", [(-2.578,-0.036),(-2.548,0.76),(-2.24,1.28),(-1.42,1.50),(-0.78,1.28),(-0.76,-0.036)], 2.50, mats["ochre"], upper, bevel_width=0.08, role="counterweight")
    side_profile("Engine_House_Lower_Body", [(-2.20,0.48),(-2.18,1.08),(-1.94,1.20),(0.30,1.20),(0.38,1.05),(0.38,0.48)], 2.36, mats["ochre"], upper, bevel_width=0.055, role="engine_house")
    side_profile("Engine_House_Upper_Hood", [(-2.08,1.06),(-1.92,1.34),(-1.54,1.45),(-0.52,1.48),(0.24,1.31),(0.30,1.06)], 2.18, mats["ochre"], upper, bevel_width=0.045, role="engine_house")
    box("Engine_Hood_Crown", (-0.86, 1.455, 0.16), (2.24, 0.09, 1.72), mats["ochre_dark"], upper, 0.025, "engine_house")
    box("Engine_Hood_Center_Access", (-0.86, 1.505, 0.16), (1.12, 0.035, 0.86), mats["ochre"], upper, 0.012, "hood_access_panel")
    box("Engine_House_Service_Door_R", (-0.78, 0.92, 1.205), (1.72, 0.70, 0.045), mats["ochre"], upper, 0.015, "engine_house")
    box("Engine_House_Service_Door_L", (-0.78, 0.92, -1.205), (1.72, 0.70, 0.045), mats["ochre"], upper, 0.015, "engine_house")
    for seam_index, seam_x in enumerate((-1.57, -0.78, 0.02), start=1):
        box(f"Engine_House_Panel_Seam_R_{seam_index}", (seam_x,0.92,1.232),(0.018,0.68,0.012),mats["ochre_dark"],upper,0.002,"service_panel_seam")
        box(f"Engine_House_Panel_Seam_L_{seam_index}", (seam_x,0.92,-1.232),(0.018,0.68,0.012),mats["ochre_dark"],upper,0.002,"service_panel_seam")
    for side, z in (("L",-1.238),("R",1.238)):
        box(f"Engine_House_Door_Handle_{side}", (-0.08,1.02,z),(0.18,0.035,0.018),mats["steel_dark"],upper,0.003,"service_panel_latch")
    box("Counterweight_Left_Cheek", (-1.82,0.92,-1.272),(1.28,0.74,0.065),mats["ochre_dark"],upper,0.018,"counterweight_panel")
    box("Counterweight_Right_Cheek", (-1.82,0.92,1.272),(1.28,0.74,0.065),mats["ochre_dark"],upper,0.018,"counterweight_panel")
    for index in range(7):
        box(f"Engine_Vent_R_{index+1:02d}", (-1.54 + index*0.18, 1.16, 1.236), (0.12, 0.025, 0.018), mats["steel_dark"], upper, 0.003, "vent")
    for index in range(6):
        box(f"Counterweight_Rear_Vent_{index+1:02d}", (-2.583, 0.70 + index*0.090, 0.0), (0.025, 0.048, 0.72), mats["steel_dark"], upper, 0.004, "vent")
    box("Exhaust_Muffler", (-0.88, 1.31, 0.68), (0.28, 0.38, 0.30), mats["steel_dark"], upper, 0.04, "exhaust")
    cylinder("Exhaust_Stack", (-0.88, 1.58, 0.68), 0.075, 0.30, mats["steel_dark"], upper, vertices=24, rotation=(math.pi/2,0,0), role="exhaust")
    cylinder("Air_Intake_Stack", (-0.48, 1.54, 0.88), 0.065, 0.27, mats["steel_dark"], upper, vertices=24, rotation=(math.pi/2,0,0), role="intake")

    # Cab on machine left (-Z), with distinct frame and glass boundaries.
    cab = empty("Cab_ROOT", (0,0,0), upper, "fixed_group", size=0.16)
    side_profile("Cab_Interior_Block", [(-0.15,0.48),(-0.10,1.68),(0.55,1.82),(1.08,1.48),(1.04,0.48)], 0.98, mats["interior"], cab, z_center=-0.78, bevel_width=0.05, role="cab_interior")
    side_profile("Cab_Left_Glass", [(-0.04,0.88),(0.00,1.60),(0.50,1.72),(0.94,1.43),(0.92,0.87)], 0.035, mats["glass"], cab, z_center=-1.285, bevel_width=0.012, role="glass")
    side_profile("Cab_Right_Glass", [(-0.02,0.90),(0.02,1.57),(0.48,1.68),(0.90,1.41),(0.88,0.90)], 0.030, mats["glass"], cab, z_center=-0.275, bevel_width=0.010, role="glass")
    side_profile("Cab_Front_Glass", [(0.91,0.88),(0.94,1.43),(1.06,1.31),(1.04,0.86)], 0.90, mats["glass"], cab, z_center=-0.78, bevel_width=0.012, role="glass")
    side_profile("Cab_Lower_Front_Glass", [(0.91,0.58),(0.92,0.84),(1.04,0.82),(1.03,0.58)], 0.88, mats["glass"], cab, z_center=-0.78, bevel_width=0.010, role="glass")
    box("Cab_Rear_Glass", (-0.095,1.25,-0.78),(0.035,0.58,0.86),mats["glass"],cab,0.010,"glass")
    box("Cab_Roof", (0.38, 1.82, -0.78), (1.20, 0.12, 1.05), mats["ochre_dark"], cab, 0.045, "cab_frame")
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
    handrail_points = [(-1.82,1.44,-1.16),(-1.08,1.58,-1.16),(-0.30,1.54,-1.16)]
    bpy.context.view_layer.update()
    handrail_world = [upper.matrix_world @ Vector(point) for point in handrail_points]
    for index in range(len(handrail_points)-1):
        rail = object_between(f"Handrail_L_{index+1}", handrail_world[index], handrail_world[index+1], 0.022, mats["steel_dark"], "handrail", 12)
        parent_keep_world(rail, upper)

    # Front equipment hierarchy. All hidden pivots and anchors are reconstructed.
    boom_pivot = empty("Boom_Pivot", (0.28, 0.78, 0.0), upper, "revolute_pivot", "CIRCLE", 0.28)
    boom_pivot["axis"] = "+Z"
    boom_pivot["authority"] = "reconstructed"
    boom_root = empty("Boom_ROOT", parent=boom_pivot, role="articulated_group", size=0.20)
    # Three overlapping tapered box-section volumes make the foot, crown, and
    # head transitions readable without claiming hidden weldment authority.
    side_profile("Boom_Foot_Box", [(0.0,-0.28),(0.46,-0.36),(1.12,0.70),(1.55,0.92),(1.48,0.59),(1.12,0.50),(0.48,-0.56)], 0.68, mats["ochre"], boom_root, bevel_width=0.050, role="boom_structure")
    side_profile("Boom_Crown_Box", [(1.10,0.50),(1.50,0.92),(2.24,1.30),(3.18,1.17),(3.20,0.84),(2.20,0.98),(1.46,0.70)], 0.56, mats["ochre"], boom_root, bevel_width=0.045, role="boom_structure")
    side_profile("Boom_Head_Box", [(3.08,0.84),(3.16,1.17),(4.05,0.96),(5.32,1.09),(5.46,0.92),(5.31,0.66),(4.00,0.66)], 0.44, mats["ochre"], boom_root, bevel_width=0.040, role="boom_structure")
    side_profile("Boom_Left_Reinforcement", [(0.48,-0.18),(1.18,0.62),(2.28,1.14),(4.02,0.82),(5.10,0.94),(4.86,0.73),(2.22,0.87),(1.18,0.43)], 0.030, mats["ochre_dark"], boom_root, z_center=-0.352, bevel_width=0.010, role="boom_reinforcement")
    side_profile("Boom_Right_Reinforcement", [(0.48,-0.18),(1.18,0.62),(2.28,1.14),(4.02,0.82),(5.10,0.94),(4.86,0.73),(2.22,0.87),(1.18,0.43)], 0.030, mats["ochre_dark"], boom_root, z_center=0.352, bevel_width=0.010, role="boom_reinforcement")
    box("Boom_Foot_Transition_Cap", (0.58,0.02,0.0),(0.20,0.72,0.74),mats["ochre_dark"],boom_root,0.040,"boom_transition")
    box("Boom_Head_Clevis", (5.25,0.86,0.0),(0.42,0.38,0.52),mats["ochre_dark"],boom_root,0.035,"boom_transition")
    add_pin("PIN_Boom_Base", (0,0,0), 0.15, 0.78, mats["steel"], boom_pivot)
    for x, y in ((1.18,0.61),(2.26,1.02),(4.05,0.79),(5.27,0.86)):
        add_pin(f"Boom_Service_Pin_{x:.2f}", (x,y,0), 0.065, 0.70, mats["bolt"], boom_root, "fastener")

    stick_pivot = empty("Stick_Pivot", (5.32, 0.95, 0.0), boom_pivot, "revolute_pivot", "CIRCLE", 0.24)
    stick_pivot.rotation_euler[2] = math.radians(RECONSTRUCTED["scene_transport_pose"]["stick_relative_deg"])
    stick_pivot["axis"] = "+Z"
    stick_root = empty("Stick_ROOT", parent=stick_pivot, role="articulated_group", size=0.18)
    stick_profile = [(-0.10,0.24),(0.40,0.34),(2.63,0.16),(2.90,0.02),(2.78,-0.21),(0.42,-0.28),(-0.10,-0.18)]
    side_profile("Stick_Main_Weldment", stick_profile, 0.43, mats["ochre"], stick_root, bevel_width=0.045, role="stick_structure")
    side_profile("Stick_Left_Wear_Plate", [(0.20,-0.20),(2.64,-0.15),(2.78,-0.05),(0.45,-0.08)], 0.026, mats["ochre_dark"], stick_root, z_center=-0.228, bevel_width=0.008, role="wear_plate")
    side_profile("Stick_Right_Wear_Plate", [(0.20,-0.20),(2.64,-0.15),(2.78,-0.05),(0.45,-0.08)], 0.026, mats["ochre_dark"], stick_root, z_center=0.228, bevel_width=0.008, role="wear_plate")
    add_pin("PIN_Stick", (0,0,0), 0.13, 0.68, mats["steel"], stick_pivot)

    bucket_pivot = empty("Bucket_Pivot", (2.90, 0.0, 0.0), stick_pivot, "revolute_pivot", "CIRCLE", 0.22)
    bucket_pivot["axis"] = "+Z"
    bucket_root = empty("Bucket_ROOT", parent=bucket_pivot, role="articulated_group", size=0.18)
    bucket_root.rotation_euler[2] = math.radians(RECONSTRUCTED["scene_transport_pose"]["bucket_relative_deg"])
    bucket_profile = [(0.02,-0.01),(0.50,0.16),(1.04,-0.10),(1.45,-0.62),(1.36,-1.02),(0.78,-1.22),(0.10,-0.60)]
    bucket_body_objects = []
    bucket_body_objects.append(side_profile("Bucket_Left_Side_Plate", bucket_profile, 0.065, mats["ochre"], bucket_root, z_center=-0.565, bevel_width=0.020, role="bucket_structure"))
    bucket_body_objects.append(side_profile("Bucket_Right_Side_Plate", bucket_profile, 0.065, mats["ochre"], bucket_root, z_center=0.565, bevel_width=0.020, role="bucket_structure"))
    bucket_body_objects.append(box("Bucket_Back_Shell", (0.88,-0.48,0.0),(0.62,0.12,1.10),mats["ochre"],bucket_root,0.045,"bucket_structure"))
    bucket_body_objects.append(box("Bucket_Cutting_Edge", (1.28,-0.97,0.0),(0.42,0.10,1.20),mats["steel"],bucket_root,0.018,"bucket_cutting_edge"))
    for index, z in enumerate((-0.48,-0.24,0.0,0.24,0.48), start=1):
        tooth = side_profile(f"Bucket_Tooth_{index:02d}", [(0,0.05),(0.38,0.0),(0.52,-0.08),(0.10,-0.12)], 0.14, mats["steel"], bucket_root, z_center=z, bevel_width=0.015, role="bucket_tooth")
        tooth.location = (1.38,-0.97,0)
        bucket_body_objects.append(tooth)
    bpy.context.view_layer.update()
    bucket_tip, bucket_tip_mesh, bucket_tip_radius = calibrate_planar_radius(
        bucket_body_objects, bucket_root, PUBLISHED["bucket_tip_radius_m"]
    )
    bucket_tip_marker = tip_witness("Bucket_Tip_Radius_Point_1p570m", bucket_tip, mats["steel"], bucket_root)
    bucket_tip_marker["contact_mesh"] = bucket_tip_mesh
    bucket_tip_marker["measured_radius_m"] = bucket_tip_radius
    attach_pin = add_pin("PIVOT_Attachment_Pin", (0.0,0.0,0.0), 0.12, 0.76, mats["steel"], bucket_pivot, "attachment_pivot")
    attach_pin["authority"] = "reconstructed"
    attach_pin["quick_coupler_status"] = "unresolved_no_coupler_geometry"

    # Exterior hose bundles are reconstructed visual routing cues only.
    hose_objects = []
    def hose_bundle(prefix, parent, points, lateral_offsets):
        bpy.context.view_layer.update()
        for bundle_index, lateral in enumerate(lateral_offsets, start=1):
            local_points = [Vector((point[0], point[1], lateral)) for point in points]
            world_points = [parent.matrix_world @ point for point in local_points]
            for segment_index in range(len(world_points)-1):
                hose = object_between(
                    f"{prefix}_{bundle_index:02d}_Segment_{segment_index+1:02d}",
                    world_points[segment_index], world_points[segment_index+1],
                    0.022 if bundle_index in (2,3) else 0.026,
                    mats["rubber"], "reconstructed_hose", 12,
                )
                parent_keep_world(hose, parent)
                hose_objects.append(hose)
    hose_bundle("Boom_Hose", boom_root, [(0.38,0.10),(1.20,0.67),(2.30,1.10),(3.90,0.80),(5.02,0.88)], (-0.38,-0.33,0.33,0.38))
    hose_bundle("Stick_Hose", stick_root, [(0.16,0.22),(1.26,0.22),(2.66,0.08)], (-0.29,-0.25,0.25,0.29))

    boom_hydraulics = empty("Boom_Hydraulics_ROOT", parent=upper, role="hydraulic_owner_group", size=0.15)
    stick_hydraulics = empty("Stick_Hydraulics_ROOT", parent=boom_root, role="hydraulic_owner_group", size=0.15)
    bucket_hydraulics = empty("Bucket_Hydraulics_ROOT", parent=stick_root, role="hydraulic_owner_group", size=0.15)
    bucket_linkage = empty("Bucket_Linkage_ROOT", parent=stick_root, role="linkage_owner_group", size=0.15)
    bellcrank_root = empty("Bucket_Bellcrank_ROOT", (2.44,0.08,0.0), stick_root, "linkage_pivot", "CIRCLE", 0.13)
    side_profile("Bucket_Bellcrank_Left", [(-0.18,0.26),(0.32,0.02),(0.18,-0.19),(-0.10,-0.06)], 0.035, mats["ochre_dark"], bellcrank_root, z_center=-0.245, bevel_width=0.010, role="bucket_bellcrank")
    side_profile("Bucket_Bellcrank_Right", [(-0.18,0.26),(0.32,0.02),(0.18,-0.19),(-0.10,-0.06)], 0.035, mats["ochre_dark"], bellcrank_root, z_center=0.245, bevel_width=0.010, role="bucket_bellcrank")
    add_pin("PIN_Bucket_Bellcrank_Pivot", (0,0,0), 0.075, 0.60, mats["steel"], bellcrank_root, "linkage_pin")

    # Anchor empties allow critic inspection and articulated review refresh.
    anchors = {}
    for name, loc, parent in [
        ("ANCHOR_Boom_Base_L", (0.04,0.40,-0.40), upper),
        ("ANCHOR_Boom_Rod_L", (1.64,0.42,-0.36), boom_root),
        ("ANCHOR_Boom_Base_R", (0.04,0.40,0.40), upper),
        ("ANCHOR_Boom_Rod_R", (1.64,0.42,0.36), boom_root),
        ("ANCHOR_Stick_Base", (2.52,0.93,0.0), boom_root),
        ("ANCHOR_Stick_Rod", (0.46,0.38,0.0), stick_root),
        ("ANCHOR_Bucket_Base", (0.42,0.30,0.0), stick_root),
        ("ANCHOR_Bellcrank_Rod", (-0.10,0.23,0.0), bellcrank_root),
        ("ANCHOR_Bellcrank_Dogbone", (0.29,-0.02,0.0), bellcrank_root),
        ("ANCHOR_Bucket_Lug", (0.10,-0.15,0.0), bucket_root),
    ]:
        anchors[name] = empty(name, loc, parent, "hydraulic_anchor", "SPHERE", 0.065)

    # Every static cylinder endpoint is represented by visible physical mount
    # geometry, not merely an empty marker. Structural ears/pins inherit the
    # moving component; hydraulic eyes inherit the assembly owner below.
    mount_records = {}
    def physical_mount(key, anchor_name, structure_parent, pin_radius=0.062, pin_length=0.34):
        anchor = anchors[anchor_name]
        x, y, z = anchor.location
        ear_offset = max(0.055, pin_length * 0.25)
        ears = []
        for side, offset in (("L", -ear_offset), ("R", ear_offset)):
            ears.append(box(
                f"{key}_Mount_Ear_{side}", (x, y, z + offset),
                (0.25, 0.22, 0.060), mats["ochre_dark"], structure_parent,
                0.018, "hydraulic_mount_ear",
            ))
        pin = add_pin(f"PIN_{key}", (x, y, z), pin_radius, pin_length, mats["steel"], structure_parent, "hydraulic_mount_pin")
        mount_records[anchor_name] = {"ears": [ear.name for ear in ears], "pin": pin.name, "parent": structure_parent.name}

    physical_mount("Boom_Base_L", "ANCHOR_Boom_Base_L", upper, pin_length=0.30)
    physical_mount("Boom_Rod_L", "ANCHOR_Boom_Rod_L", boom_root, pin_length=0.30)
    physical_mount("Boom_Base_R", "ANCHOR_Boom_Base_R", upper, pin_length=0.30)
    physical_mount("Boom_Rod_R", "ANCHOR_Boom_Rod_R", boom_root, pin_length=0.30)
    physical_mount("Stick_Base", "ANCHOR_Stick_Base", boom_root, pin_length=0.40)
    physical_mount("Stick_Rod", "ANCHOR_Stick_Rod", stick_root, pin_length=0.40)
    physical_mount("Bucket_Base", "ANCHOR_Bucket_Base", stick_root, pin_length=0.40)

    lug_anchor = anchors["ANCHOR_Bucket_Lug"]
    lug_x, lug_y, lug_z = lug_anchor.location
    lug_ears = []
    for side, z_center in (("L", -0.105), ("R", 0.105)):
        lug_ears.append(side_profile(
            f"Bucket_Lug_{side}_Ear",
            [(lug_x-0.13,lug_y-0.11),(lug_x+0.14,lug_y-0.09),(lug_x+0.17,lug_y+0.12),(lug_x-0.10,lug_y+0.15)],
            0.060, mats["ochre_dark"], bucket_root, z_center=z_center,
            bevel_width=0.012, role="bucket_lug_ear",
        ))
    bucket_lug_pin = add_pin("PIN_Bucket_Lug", (lug_x,lug_y,lug_z), 0.060, 0.32, mats["steel"], bucket_root, "bucket_lug_pin")
    mount_records["ANCHOR_Bucket_Lug"] = {"ears": [ear.name for ear in lug_ears], "pin": bucket_lug_pin.name, "parent": bucket_root.name}

    cylinders = {}
    def pair(key, a, b, barrel_radius, rod_radius, owner):
        start, end = world(anchors[a]), world(anchors[b])
        direction = end - start
        barrel_end = start + direction * 0.62
        rod_start = start + direction * 0.56
        cylinders[f"{key}_Barrel"] = object_between(f"{key}_Barrel", start, barrel_end, barrel_radius, mats["steel_dark"], "hydraulic_barrel", 24)
        cylinders[f"{key}_Rod"] = object_between(f"{key}_Rod", rod_start, end, rod_radius, mats["rod"], "hydraulic_rod", 20)
        parent_keep_world(cylinders[f"{key}_Barrel"], owner)
        parent_keep_world(cylinders[f"{key}_Rod"], owner)
    bpy.context.view_layer.update()
    pair("Boom_Cylinder_L", "ANCHOR_Boom_Base_L", "ANCHOR_Boom_Rod_L", 0.095, 0.052, boom_hydraulics)
    pair("Boom_Cylinder_R", "ANCHOR_Boom_Base_R", "ANCHOR_Boom_Rod_R", 0.095, 0.052, boom_hydraulics)
    pair("Stick_Cylinder", "ANCHOR_Stick_Base", "ANCHOR_Stick_Rod", 0.105, 0.058, stick_hydraulics)
    pair("Bucket_Cylinder", "ANCHOR_Bucket_Base", "ANCHOR_Bellcrank_Rod", 0.095, 0.050, bucket_hydraulics)
    cylinders["Bucket_Link_Dogbone"] = object_between("Bucket_Link_Dogbone", world(anchors["ANCHOR_Bellcrank_Dogbone"]), world(anchors["ANCHOR_Bucket_Lug"]), 0.050, mats["ochre_dark"], "bucket_linkage", 16)
    parent_keep_world(cylinders["Bucket_Link_Dogbone"], bucket_linkage)
    add_pin("PIN_Bellcrank_Rod", anchors["ANCHOR_Bellcrank_Rod"].location, 0.050, 0.54, mats["steel"], bellcrank_root, "linkage_pin")
    add_pin("PIN_Bellcrank_Dogbone", anchors["ANCHOR_Bellcrank_Dogbone"].location, 0.048, 0.54, mats["steel"], bellcrank_root, "linkage_pin")

    hydraulic_eyes = {}
    eye_definitions = [
        ("Boom_Cylinder_L_Base_Eye", "ANCHOR_Boom_Base_L", boom_hydraulics, 0.112, mats["steel_dark"]),
        ("Boom_Cylinder_L_Rod_Eye", "ANCHOR_Boom_Rod_L", boom_hydraulics, 0.086, mats["rod"]),
        ("Boom_Cylinder_R_Base_Eye", "ANCHOR_Boom_Base_R", boom_hydraulics, 0.112, mats["steel_dark"]),
        ("Boom_Cylinder_R_Rod_Eye", "ANCHOR_Boom_Rod_R", boom_hydraulics, 0.086, mats["rod"]),
        ("Stick_Cylinder_Base_Eye", "ANCHOR_Stick_Base", stick_hydraulics, 0.122, mats["steel_dark"]),
        ("Stick_Cylinder_Rod_Eye", "ANCHOR_Stick_Rod", stick_hydraulics, 0.092, mats["rod"]),
        ("Bucket_Cylinder_Base_Eye", "ANCHOR_Bucket_Base", bucket_hydraulics, 0.112, mats["steel_dark"]),
        ("Bucket_Cylinder_Rod_Eye", "ANCHOR_Bellcrank_Rod", bucket_hydraulics, 0.082, mats["rod"]),
        ("Bucket_Dogbone_Bellcrank_Eye", "ANCHOR_Bellcrank_Dogbone", bucket_linkage, 0.078, mats["ochre_dark"]),
        ("Bucket_Dogbone_Lug_Eye", "ANCHOR_Bucket_Lug", bucket_linkage, 0.078, mats["ochre_dark"]),
    ]
    for name, anchor_name, owner, radius, eye_mat in eye_definitions:
        eye = cylinder(name, world(anchors[anchor_name]), radius, 0.095, eye_mat, vertices=24, role="physical_joint_eye")
        parent_keep_world(eye, owner)
        eye["anchor"] = anchor_name
        hydraulic_eyes[name] = eye

    inspection = empty("Inspection_Volumes", parent=machine, role="inspection_group", size=0.24, export=False)
    envelope = empty("INSPECT_Transport_Envelope", (-0.18, PUBLISHED["transport_height_m"]/2, 0.0), inspection, "inspection_volume", "CUBE", 1.0, export=False)
    envelope.scale = (PUBLISHED["transport_length_m"]/2, PUBLISHED["transport_height_m"]/2, PUBLISHED["undercarriage_width_m"]/2)
    envelope["published_constraint"] = "transport-length transport-height undercarriage-width"
    for name, loc, scale in [
        ("INSPECT_Upper_Clearance", (-0.18,1.38,0),(2.1,0.42,1.37)),
        ("INSPECT_Boom_Swept_Study", (2.70,2.20,0),(2.85,1.05,0.42)),
        ("INSPECT_Attachment_Volume", (6.30,0.85,0),(1.15,0.85,0.72)),
    ]:
        marker = empty(name, loc, inspection, "inspection_volume", "CUBE", 1.0, export=False)
        marker.scale = scale

    # Review-only environment is not exported.
    box("Review_Ground", (1.5, 0.02, 0), (15.0, 0.04, 10.0), mats["ground"], None, 0.0, "review_environment", False)
    return {
        "mats": mats,
        "machine": machine,
        "swing": swing,
        "boom_pivot": boom_pivot,
        "stick_pivot": stick_pivot,
        "bucket_root": bucket_root,
        "bucket_tip_marker": bucket_tip_marker,
        "bucket_body_objects": bucket_body_objects,
        "anchors": anchors,
        "cylinders": cylinders,
        "hydraulic_eyes": hydraulic_eyes,
        "mount_records": mount_records,
        "hose_objects": hose_objects,
        "counterweight": bpy.data.objects["Counterweight_Core"],
        "engine_house_objects": [obj for obj in bpy.data.objects if obj.get("exo_role") == "engine_house"],
    }


def refresh_hydraulics(model):
    bpy.context.view_layer.update()
    anchors = model["anchors"]
    cylinders = model["cylinders"]
    definitions = [
        ("Boom_Cylinder_L", "ANCHOR_Boom_Base_L", "ANCHOR_Boom_Rod_L", 0.095, 0.052),
        ("Boom_Cylinder_R", "ANCHOR_Boom_Base_R", "ANCHOR_Boom_Rod_R", 0.095, 0.052),
        ("Stick_Cylinder", "ANCHOR_Stick_Base", "ANCHOR_Stick_Rod", 0.105, 0.058),
        ("Bucket_Cylinder", "ANCHOR_Bucket_Base", "ANCHOR_Bellcrank_Rod", 0.095, 0.050),
    ]
    for key, a, b, barrel_radius, rod_radius in definitions:
        start, end = world(anchors[a]), world(anchors[b])
        vector = end - start
        place_between(cylinders[f"{key}_Barrel"], start, start + vector*0.62, barrel_radius)
        place_between(cylinders[f"{key}_Rod"], start + vector*0.56, end, rod_radius)
    place_between(cylinders["Bucket_Link_Dogbone"], world(anchors["ANCHOR_Bellcrank_Dogbone"]), world(anchors["ANCHOR_Bucket_Lug"]), 0.050)
    for eye in model["hydraulic_eyes"].values():
        matrix = eye.matrix_world.copy()
        matrix.translation = world(anchors[eye["anchor"]])
        eye.matrix_world = matrix
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
    pose_metrics = {"stowed_transport": measure_pose_geometry(model, "stowed_transport")}
    paths.append(render_view("operator-side", (2.15, 4.35, -16.5), (2.15,1.35,0), 52))
    paths.append(render_view("right-three-quarter", (12.0, 5.8, 16.0), (1.65,1.35,0), 48))
    paths.append(render_view("rear-three-quarter", (-10.8, 4.7, 10.2), (0.25,1.30,0), 52))
    paths.append(render_view("front-equipment", (14.0, 5.3, -11.0), (2.25,1.30,0), 48))
    paths.append(render_view("linkage-detail", (8.2, 4.5, -3.2), (6.30,0.72,0), 68))
    paths.append(render_view("drive-sprocket-detail", (-3.25, 1.35, -3.10), (-2.00,0.54,-1.19), 72))
    paths.append(render_view("hydraulic-routing-detail", (5.5, 4.15, -5.2), (3.25,2.38,-0.22), 68))

    # Review-only articulation. It is restored before save/export.
    model["swing"].rotation_euler[1] = math.radians(RECONSTRUCTED["review_articulated_pose"]["upper_swing_deg"])
    model["boom_pivot"].rotation_euler[2] = math.radians(RECONSTRUCTED["review_articulated_pose"]["boom_deg"])
    model["stick_pivot"].rotation_euler[2] = math.radians(RECONSTRUCTED["review_articulated_pose"]["stick_relative_deg"])
    model["bucket_root"].rotation_euler[2] = math.radians(RECONSTRUCTED["review_articulated_pose"]["bucket_relative_deg"])
    refresh_hydraulics(model)
    pose_metrics["articulated_review"] = measure_pose_geometry(model, "articulated_review")
    paths.append(render_view("articulated-review", (14.0, 8.0, -16.5), (1.6,2.25,0), 50))

    model["swing"].rotation_euler[1] = math.radians(RECONSTRUCTED["scene_transport_pose"]["upper_swing_deg"])
    model["boom_pivot"].rotation_euler[2] = math.radians(RECONSTRUCTED["scene_transport_pose"]["boom_deg"])
    model["stick_pivot"].rotation_euler[2] = math.radians(RECONSTRUCTED["scene_transport_pose"]["stick_relative_deg"])
    model["bucket_root"].rotation_euler[2] = math.radians(RECONSTRUCTED["scene_transport_pose"]["bucket_relative_deg"])
    refresh_hydraulics(model)
    return paths, pose_metrics


def export_objects():
    return [obj for obj in bpy.context.scene.objects if obj.get("exo_export", False)]


def mesh_bounds(objects):
    bpy.context.view_layer.update()
    points = evaluated_world_points([obj for obj in objects if obj.type == "MESH"])
    mins = [min(point[index] for point in points) for index in range(3)]
    maxs = [max(point[index] for point in points) for index in range(3)]
    return {
        "min_m": [round(value, 4) for value in mins],
        "max_m": [round(value, 4) for value in maxs],
        "size_m": [round(maxs[index]-mins[index], 4) for index in range(3)],
    }


def object_evaluated_bounds(objects):
    points = evaluated_world_points(objects)
    mins = [min(point[index] for point in points) for index in range(3)]
    maxs = [max(point[index] for point in points) for index in range(3)]
    return {
        "min_m": mins,
        "max_m": maxs,
        "size_m": [maxs[index] - mins[index] for index in range(3)],
    }


def anchor_endpoint_min_error(obj, anchor):
    local_z = [corner[2] for corner in obj.bound_box]
    endpoints = [
        obj.matrix_world @ Vector((0, 0, min(local_z))),
        obj.matrix_world @ Vector((0, 0, max(local_z))),
    ]
    target = world(anchor)
    return min((endpoint - target).length for endpoint in endpoints)


def segment_endpoints(obj):
    local_z = [corner[2] for corner in obj.bound_box]
    return [
        obj.matrix_world @ Vector((0, 0, min(local_z))),
        obj.matrix_world @ Vector((0, 0, max(local_z))),
    ]


def segment_axial_overlap(barrel, rod, base_anchor, rod_anchor):
    base = world(base_anchor)
    axis = (world(rod_anchor) - base).normalized()
    barrel_span = sorted((point - base).dot(axis) for point in segment_endpoints(barrel))
    rod_span = sorted((point - base).dot(axis) for point in segment_endpoints(rod))
    return min(barrel_span[1], rod_span[1]) - max(barrel_span[0], rod_span[0])


def is_descendant_of(obj, root):
    current = obj.parent
    while current:
        if current == root:
            return True
        current = current.parent
    return False


def mesh_descendants(root):
    return [
        obj for obj in object_descendants(root)
        if obj.type == "MESH" and obj.get("exo_export", False)
    ]


def planar_radius_points(objects, parent):
    inverse = parent.matrix_world.inverted()
    points = [inverse @ point for obj in objects for point in evaluated_world_points([obj])]
    return max(math.hypot(point.x, point.y) for point in points)


def track_phase_metrics(root, side):
    meshes = mesh_descendants(root)
    bounds = evaluated_bounds(meshes)
    shoes = sorted(
        [obj for obj in meshes if obj.name.startswith(f"Track_{side}_Shoe_")],
        key=lambda obj: obj.name,
    )
    centers = []
    for shoe in shoes:
        points = evaluated_world_points([shoe])
        centers.append(Vector(tuple(sum(point[index] for point in points) / len(points) for index in range(3))))
    gaps = [(centers[(index+1) % len(centers)] - centers[index]).length for index in range(len(centers))]
    ordered = sorted(gaps)
    median = ordered[len(ordered)//2]
    sprocket = object_center_world(bpy.data.objects[f"Track_{side}_Rear_Sprocket_Hub"])
    idler = object_center_world(bpy.data.objects[f"Track_{side}_Front_Idler_Hub"])
    return {
        "subtree_length_m": bounds["max"][0] - bounds["min"][0],
        "subtree_min_x_m": bounds["min"][0],
        "subtree_max_x_m": bounds["max"][0],
        "shoe_count": len(shoes),
        "ordered_center_gap_min_m": min(gaps),
        "ordered_center_gap_max_m": max(gaps),
        "ordered_center_gap_median_m": median,
        "max_gap_to_median_ratio": max(gaps) / median,
        "closure_gap_m": gaps[-1],
        "roller_center_length_m": abs(idler.x - sprocket.x),
        "centers": [[center.x, center.y, center.z] for center in centers],
    }


def measure_pose_geometry(model, pose_name):
    export_meshes = [obj for obj in export_objects() if obj.type == "MESH"]
    under_root = bpy.data.objects["Undercarriage_ROOT"]
    swing_root = bpy.data.objects["Upper_Swing_Pivot"]
    upper_root = bpy.data.objects["Upper_ROOT"]
    boom_pivot = bpy.data.objects["Boom_Pivot"]
    bucket_root = bpy.data.objects["Bucket_ROOT"]
    stick_root = bpy.data.objects["Stick_ROOT"]
    boom_root = bpy.data.objects["Boom_ROOT"]
    under_meshes = [
        obj for obj in export_meshes
        if is_descendant_of(obj, under_root) and not is_descendant_of(obj, swing_root)
    ]
    upper_house_meshes = [
        obj for obj in export_meshes
        if is_descendant_of(obj, upper_root) and not is_descendant_of(obj, boom_pivot)
        and obj.get("exo_role") not in {"hydraulic_barrel", "hydraulic_rod", "physical_joint_eye"}
    ]
    boom_meshes = mesh_descendants(boom_root)
    stick_meshes = mesh_descendants(stick_root)
    bucket_meshes = mesh_descendants(bucket_root)
    front_meshes = list({obj.name: obj for obj in boom_meshes + stick_meshes + bucket_meshes + list(model["cylinders"].values()) + list(model["hydraulic_eyes"].values())}.values())
    pair_groups = {
        "bucket_to_undercarriage": (bucket_meshes, under_meshes),
        "bucket_to_upper_house": (bucket_meshes, upper_house_meshes),
        "stick_to_undercarriage": (stick_meshes, under_meshes),
        "boom_to_undercarriage": (boom_meshes, under_meshes),
    }
    separations = {}
    for name, (first, second) in pair_groups.items():
        gap, axes = bounds_gap(evaluated_bounds(first), evaluated_bounds(second))
        separations[name] = {"aabb_gap_m": gap, "axis_gaps_m": axes}
    under_bounds = evaluated_bounds(under_meshes)
    upper_bounds = evaluated_bounds(upper_house_meshes)
    return {
        "pose": pose_name,
        "front_equipment_min_y_m": min(point.y for point in evaluated_world_points(front_meshes)),
        "all_visible_min_y_m": min(point.y for point in evaluated_world_points(export_meshes)),
        "upper_house_min_y_m": upper_bounds["min"][1],
        "undercarriage_max_y_m": under_bounds["max"][1],
        "upper_to_undercarriage_vertical_gap_m": upper_bounds["min"][1] - under_bounds["max"][1],
        "critical_group_aabb_separations": separations,
    }


def collect_geometry_metrics(model, objects):
    bpy.context.view_layer.update()
    swing_center = world(bpy.data.objects["Upper_Swing_Pivot"])
    counterweight_points = evaluated_world_points([model["counterweight"]])
    counterweight_bounds = object_evaluated_bounds([model["counterweight"]])
    house_bounds = object_evaluated_bounds(model["engine_house_objects"])
    anchors = model["anchors"]
    cylinders = model["cylinders"]
    export_meshes = [obj for obj in objects if obj.type == "MESH"]
    track_shoes = [obj for obj in export_meshes if obj.get("exo_role") == "track_shoe"]
    track_bounds = object_evaluated_bounds(track_shoes)
    center_frame_bounds = object_evaluated_bounds([bpy.data.objects["Undercarriage_Center_Frame"]])
    cab_roof_bounds = object_evaluated_bounds([bpy.data.objects["Cab_Roof"]])
    visible_minima = []
    for obj in export_meshes:
        points = evaluated_world_points([obj])
        visible_minima.append((min(point.y for point in points), obj.name))
    visible_min = min(value for value, _ in visible_minima)
    lowest_visible_objects = sorted(
        name for value, name in visible_minima if value <= visible_min + 0.001
    )
    scale_offenders = {
        obj.name: [round(value, 8) for value in obj.scale]
        for obj in objects
        if obj.type == "MESH" and any(abs(value - 1.0) > 1e-7 for value in obj.scale)
    }
    owner_names = {
        name: (obj.parent.name if obj.parent else None)
        for name, obj in cylinders.items()
    }
    semantic_records = semantic_contract_records()
    track_left = track_phase_metrics(bpy.data.objects["Track_L_ROOT"], "L")
    track_right = track_phase_metrics(bpy.data.objects["Track_R_ROOT"], "R")
    paired_phase_error = max(
        math.hypot(left[0]-right[0], left[1]-right[1])
        for left, right in zip(track_left["centers"], track_right["centers"])
    )
    bucket_root = bpy.data.objects["Bucket_ROOT"]
    bucket_teeth = [obj for obj in export_meshes if obj.get("exo_role") == "bucket_tooth"]
    bucket_tip_radius = planar_radius_points(bucket_teeth, bucket_root)
    inverse_bucket = bucket_root.matrix_world.inverted()
    tooth_points = [inverse_bucket @ point for obj in bucket_teeth for point in evaluated_world_points([obj])]
    witness_points = [inverse_bucket @ point for point in evaluated_world_points([model["bucket_tip_marker"]])]
    tooth_tip = max(tooth_points, key=lambda point: math.hypot(point.x, point.y))
    witness_tip = max(witness_points, key=lambda point: math.hypot(point.x, point.y))
    bucket_tip_planar_contact_error = math.hypot(tooth_tip.x-witness_tip.x, tooth_tip.y-witness_tip.y)
    bucket_tip_3d_contact_error = (tooth_tip-witness_tip).length
    hydraulic_definitions = {
        "Boom_Cylinder_L": {
            "base_anchor": "ANCHOR_Boom_Base_L", "rod_anchor": "ANCHOR_Boom_Rod_L",
            "base_eye": "Boom_Cylinder_L_Base_Eye", "rod_eye": "Boom_Cylinder_L_Rod_Eye",
            "base_pin": "PIN_Boom_Base_L", "rod_pin": "PIN_Boom_Rod_L",
        },
        "Boom_Cylinder_R": {
            "base_anchor": "ANCHOR_Boom_Base_R", "rod_anchor": "ANCHOR_Boom_Rod_R",
            "base_eye": "Boom_Cylinder_R_Base_Eye", "rod_eye": "Boom_Cylinder_R_Rod_Eye",
            "base_pin": "PIN_Boom_Base_R", "rod_pin": "PIN_Boom_Rod_R",
        },
        "Stick_Cylinder": {
            "base_anchor": "ANCHOR_Stick_Base", "rod_anchor": "ANCHOR_Stick_Rod",
            "base_eye": "Stick_Cylinder_Base_Eye", "rod_eye": "Stick_Cylinder_Rod_Eye",
            "base_pin": "PIN_Stick_Base", "rod_pin": "PIN_Stick_Rod",
        },
        "Bucket_Cylinder": {
            "base_anchor": "ANCHOR_Bucket_Base", "rod_anchor": "ANCHOR_Bellcrank_Rod",
            "base_eye": "Bucket_Cylinder_Base_Eye", "rod_eye": "Bucket_Cylinder_Rod_Eye",
            "base_pin": "PIN_Bucket_Base", "rod_pin": "PIN_Bellcrank_Rod",
        },
    }
    hydraulic_continuity = {}
    for key, definition in hydraulic_definitions.items():
        base_anchor = anchors[definition["base_anchor"]]
        rod_anchor = anchors[definition["rod_anchor"]]
        barrel = cylinders[f"{key}_Barrel"]
        rod = cylinders[f"{key}_Rod"]
        base_eye = model["hydraulic_eyes"][definition["base_eye"]]
        rod_eye = model["hydraulic_eyes"][definition["rod_eye"]]
        base_pin = bpy.data.objects[definition["base_pin"]]
        rod_pin = bpy.data.objects[definition["rod_pin"]]
        record = {
            "barrel_base_endpoint_error_m": anchor_endpoint_min_error(barrel, base_anchor),
            "rod_endpoint_error_m": anchor_endpoint_min_error(rod, rod_anchor),
            "barrel_rod_axial_overlap_m": segment_axial_overlap(barrel, rod, base_anchor, rod_anchor),
            "base_eye_center_error_m": (object_center_world(base_eye)-world(base_anchor)).length,
            "rod_eye_center_error_m": (object_center_world(rod_eye)-world(rod_anchor)).length,
            "base_pin_center_error_m": (object_center_world(base_pin)-world(base_anchor)).length,
            "rod_pin_center_error_m": (object_center_world(rod_pin)-world(rod_anchor)).length,
            "physical_nodes": [barrel.name, rod.name, base_eye.name, rod_eye.name, base_pin.name, rod_pin.name],
        }
        record["pass"] = (
            max(record[name] for name in (
                "barrel_base_endpoint_error_m", "rod_endpoint_error_m",
                "base_eye_center_error_m", "rod_eye_center_error_m",
                "base_pin_center_error_m", "rod_pin_center_error_m",
            )) <= 1e-5
            and record["barrel_rod_axial_overlap_m"] >= 0.05
            and all(bpy.data.objects.get(name) is not None and bpy.data.objects[name].type == "MESH" for name in record["physical_nodes"])
        )
        hydraulic_continuity[key] = record

    dogbone = cylinders["Bucket_Link_Dogbone"]
    dogbone_bell_eye = model["hydraulic_eyes"]["Bucket_Dogbone_Bellcrank_Eye"]
    dogbone_lug_eye = model["hydraulic_eyes"]["Bucket_Dogbone_Lug_Eye"]
    dogbone_closure = {
        "bellcrank_endpoint_error_m": anchor_endpoint_min_error(dogbone, anchors["ANCHOR_Bellcrank_Dogbone"]),
        "bucket_lug_endpoint_error_m": anchor_endpoint_min_error(dogbone, anchors["ANCHOR_Bucket_Lug"]),
        "bellcrank_eye_center_error_m": (object_center_world(dogbone_bell_eye)-world(anchors["ANCHOR_Bellcrank_Dogbone"])).length,
        "bucket_lug_eye_center_error_m": (object_center_world(dogbone_lug_eye)-world(anchors["ANCHOR_Bucket_Lug"])).length,
        "bellcrank_pin_center_error_m": (object_center_world(bpy.data.objects["PIN_Bellcrank_Dogbone"])-world(anchors["ANCHOR_Bellcrank_Dogbone"])).length,
        "bucket_lug_pin_center_error_m": (object_center_world(bpy.data.objects["PIN_Bucket_Lug"])-world(anchors["ANCHOR_Bucket_Lug"])).length,
        "bucket_lug_ear_parents": {
            name: bpy.data.objects[name].parent.name
            for name in model["mount_records"]["ANCHOR_Bucket_Lug"]["ears"]
        },
        "bucket_lug_pin_parent": bpy.data.objects["PIN_Bucket_Lug"].parent.name,
        "dogbone_parent": dogbone.parent.name,
    }
    dogbone_closure["pass"] = (
        max(value for key, value in dogbone_closure.items() if key.endswith("_error_m")) <= 1e-5
        and set(dogbone_closure["bucket_lug_ear_parents"].values()) == {"Bucket_ROOT"}
        and dogbone_closure["bucket_lug_pin_parent"] == "Bucket_ROOT"
        and dogbone_closure["dogbone_parent"] == "Bucket_Linkage_ROOT"
    )
    swing = bpy.data.objects["Upper_Swing_Pivot"]
    boom_pivot = bpy.data.objects["Boom_Pivot"]
    stick_pivot = bpy.data.objects["Stick_Pivot"]
    bucket_pivot = bpy.data.objects["Bucket_Pivot"]
    modeled_chain = stick_pivot.location.length + bucket_pivot.location.length + bucket_tip_radius
    boom_pivot_world = world(boom_pivot)
    swing_world = world(swing)
    ground_reach_capability = abs(boom_pivot_world.x-swing_world.x) + math.sqrt(
        max(0.0, modeled_chain**2 - boom_pivot_world.y**2)
    )
    working_envelope = {
        "measured_boom_pivot_to_stick_pivot_m": stick_pivot.location.length,
        "measured_stick_pivot_to_bucket_pivot_m": bucket_pivot.location.length,
        "measured_bucket_tip_radius_m": bucket_tip_radius,
        "measured_full_extension_chain_m": modeled_chain,
        "calculated_ground_reach_capability_from_slew_center_m": ground_reach_capability,
        "published_maximum_ground_reach_m": 9.87,
        "calculated_digging_depth_capability_below_ground_m": modeled_chain - boom_pivot_world.y,
        "published_maximum_digging_depth_m": 6.73,
        "classification": "geometric reachability check from measured model nodes; not a manufacturer limit or continuous solver",
    }
    working_envelope["pass"] = (
        working_envelope["calculated_ground_reach_capability_from_slew_center_m"] >= working_envelope["published_maximum_ground_reach_m"]
        and working_envelope["calculated_digging_depth_capability_below_ground_m"] >= working_envelope["published_maximum_digging_depth_m"]
    )
    upperframe_width = object_evaluated_bounds([bpy.data.objects["Upper_Deck_Main"]])["size_m"][2]
    track_gauge = abs(
        object_center_world(bpy.data.objects["Track_R_Rear_Sprocket_Hub"]).z
        - object_center_world(bpy.data.objects["Track_L_Rear_Sprocket_Hub"]).z
    )
    return {
        "tail_swing_radius_m": max(
            math.hypot(point.x - swing_center.x, point.z - swing_center.z)
            for point in counterweight_points
        ),
        "counterweight_clearance_agl_m": min(point.y for point in counterweight_points),
        "counterweight_evaluated_bounds_m": counterweight_bounds,
        "engine_house_length_m": house_bounds["size_m"][0],
        "engine_house_height_m": house_bounds["size_m"][1],
        "engine_house_evaluated_bounds_m": house_bounds,
        "drive_sprocket_teeth_left": len([
            obj for obj in objects if obj.name.startswith("Track_L_Drive_Sprocket_Tooth_")
        ]),
        "drive_sprocket_teeth_right": len([
            obj for obj in objects if obj.name.startswith("Track_R_Drive_Sprocket_Tooth_")
        ]),
        "reconstructed_hose_meshes": len(model["hose_objects"]),
        "track_contact_min_y_m": track_bounds["min_m"][1],
        "track_contact_authored_root_correction_m": bpy.data.objects["Machine_Root"]["track_contact_correction_m"],
        "undercarriage_center_frame_underside_agl_m": center_frame_bounds["min_m"][1],
        "cab_roof_top_agl_m": cab_roof_bounds["max_m"][1],
        "lowest_visible_geometry_y_m": visible_min,
        "lowest_visible_objects": lowest_visible_objects,
        "export_mesh_scale_offenders": scale_offenders,
        "hydraulic_linkage_owner_parents": owner_names,
        "semantic_contract": semantic_records,
        "track_phase": {"left": track_left, "right": track_right, "paired_xy_phase_error_m": paired_phase_error},
        "bucket_tip_radius_m": bucket_tip_radius,
        "bucket_tip_witness_radius_m": math.hypot(witness_tip.x, witness_tip.y),
        "bucket_tip_planar_contact_error_m": bucket_tip_planar_contact_error,
        "bucket_tip_3d_contact_error_m": bucket_tip_3d_contact_error,
        "bucket_tip_source_id": model["bucket_tip_marker"]["source_id"],
        "stick_modeled_pin_distance_m": bucket_pivot.location.length,
        "hydraulic_continuity": hydraulic_continuity,
        "bucket_linkage_physical_closure": dogbone_closure,
        "working_envelope_geometric_reachability": working_envelope,
        "upperframe_visible_width_m": upperframe_width,
        "track_gauge_m": track_gauge,
        "bucket_rod_to_bellcrank_error_m": anchor_endpoint_min_error(
            cylinders["Bucket_Cylinder_Rod"], anchors["ANCHOR_Bellcrank_Rod"]
        ),
        "dogbone_to_bellcrank_error_m": anchor_endpoint_min_error(
            cylinders["Bucket_Link_Dogbone"], anchors["ANCHOR_Bellcrank_Dogbone"]
        ),
        "dogbone_to_bucket_lug_error_m": anchor_endpoint_min_error(
            cylinders["Bucket_Link_Dogbone"], anchors["ANCHOR_Bucket_Lug"]
        ),
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


def create_validation(bounds, counts, render_paths, metrics, glb_contract, pose_metrics, source_trace, render_evidence):
    width, height, length = bounds["size_m"][2], bounds["size_m"][1], bounds["size_m"][0]
    semantic_ok = all(record["pass"] for record in metrics["semantic_contract"].values())
    render_ok = len(render_evidence) == 8 and all(record["pass"] for record in render_evidence)
    root_records = glb_contract["scene_roots"]
    glb_contract_ok = (
        glb_contract["scene_count"] == 1 and len(root_records) == 1
        and root_records[0]["name"] == "Machine_Root" and root_records[0]["transform"] == {}
        and glb_contract["camera_count"] == 0 and not glb_contract["punctual_light_extension_present"]
        and not glb_contract["inspection_helper_nodes"] and glb_contract["external_uri_count"] == 0
    )
    material_records = {record["name"]: record for record in glb_contract["materials"]}
    body_material = material_records.get("Neutral_Slate_Body")
    trim_material = material_records.get("Neutral_Graphite_Trim")

    def low_saturation_slate(record, minimum_uses):
        rgba = record.get("base_color_rgba") if record else None
        if not isinstance(rgba, list) or len(rgba) < 3:
            return False
        rgb = rgba[:3]
        return (
            all(isinstance(value, (int, float)) and math.isfinite(value) for value in rgb)
            and rgb[0] <= rgb[1] <= rgb[2]
            and max(rgb) - min(rgb) <= 0.10
            and record.get("primitive_usage_count", 0) >= minimum_uses
        )

    body_palette_ok = (
        low_saturation_slate(body_material, 10)
        and low_saturation_slate(trim_material, 10)
        and not any(
            token in name.lower()
            for name in glb_contract["material_names"]
            for token in ("caterpillar", "cat_yellow", "yellow", "ochre")
        )
    )
    neutral_materials_ok = (
        bool(glb_contract["material_names"])
        and all(name.startswith("Neutral_") for name in glb_contract["material_names"])
        and glb_contract["image_count"] == 0 and glb_contract["texture_count"] == 0
        and body_palette_ok
    )
    track = metrics["track_phase"]
    track_ok = (
        abs(track["left"]["subtree_length_m"] - PUBLISHED["track_length_m"]) <= 1e-4
        and abs(track["right"]["subtree_length_m"] - PUBLISHED["track_length_m"]) <= 1e-4
        and track["left"]["shoe_count"] == track["right"]["shoe_count"] == PUBLISHED["shoe_count_each_side"]
        and track["left"]["max_gap_to_median_ratio"] <= 1.25
        and track["right"]["max_gap_to_median_ratio"] <= 1.25
        and track["paired_xy_phase_error_m"] <= 1e-5
        and abs(track["left"]["roller_center_length_m"] - PUBLISHED["roller_center_length_m"]) <= 1e-5
        and abs(track["right"]["roller_center_length_m"] - PUBLISHED["roller_center_length_m"]) <= 1e-5
    )
    stowed_ok = (
        abs(width-PUBLISHED["undercarriage_width_m"]) <= 0.04
        and abs(height-PUBLISHED["transport_height_m"]) <= 0.05
        and abs(length-PUBLISHED["transport_length_m"]) <= 0.08
        and abs(metrics["cab_roof_top_agl_m"]-PUBLISHED["cab_height_m"]) <= 0.025
        and abs(metrics["upperframe_visible_width_m"]-PUBLISHED["upperframe_width_m"]) <= 0.08
        and abs(metrics["tail_swing_radius_m"]-PUBLISHED["tail_swing_radius_m"]) <= 0.015
        and abs(metrics["counterweight_clearance_agl_m"]-PUBLISHED["counterweight_clearance_m"]) <= 0.015
        and abs(metrics["undercarriage_center_frame_underside_agl_m"]-PUBLISHED["ground_clearance_m"]) <= 0.005
        and abs(metrics["track_gauge_m"]-PUBLISHED["track_gauge_m"]) <= 1e-5
        and abs(metrics["bucket_tip_radius_m"]-PUBLISHED["bucket_tip_radius_m"]) <= 1e-5
        and abs(metrics["bucket_tip_witness_radius_m"]-PUBLISHED["bucket_tip_radius_m"]) <= 1e-5
        and metrics["bucket_tip_planar_contact_error_m"] <= 1e-5
        and metrics["bucket_tip_3d_contact_error_m"] <= 1e-5
        and abs(metrics["stick_modeled_pin_distance_m"]-PUBLISHED["stick_length_m"]) <= 1e-5
        and track_ok
    )
    hydraulic_ok = all(record["pass"] for record in metrics["hydraulic_continuity"].values())
    linkage_ok = metrics["bucket_linkage_physical_closure"]["pass"]
    upper_clearance_ok = all(
        record["upper_to_undercarriage_vertical_gap_m"] > 0.005
        for record in pose_metrics.values()
    )
    ground_ok = all(
        record["front_equipment_min_y_m"] >= -0.001 and record["all_visible_min_y_m"] >= -0.001
        for record in pose_metrics.values()
    )
    self_collision_ok = all(
        separation["aabb_gap_m"] > 0.005
        for record in pose_metrics.values()
        for separation in record["critical_group_aabb_separations"].values()
    )

    def required_gate(gate_id, passed, method, evidence, semantic_nodes, fact_ids, rendered_evidence):
        assert method and isinstance(method, str)
        assert isinstance(evidence, dict) and evidence
        assert len(semantic_nodes) == len(set(semantic_nodes))
        assert len(fact_ids) == len(set(fact_ids))
        return {
            "id": gate_id,
            "status": "PASS" if passed else "FAIL",
            "detail": {
                "method": method,
                "evidence": evidence,
                "semantic_nodes": semantic_nodes,
                "fact_ids": fact_ids,
                "rendered_evidence": rendered_evidence,
            },
        }

    required_gates = [
        required_gate(
            "stowed_transport_envelope", stowed_ok,
            "Evaluate exported visible meshes in the saved stowed pose; compare AABB and named component measurements to SHA-bound source facts.",
            {
                "visible_aabb_xyz_m": [length, height, width],
                "published_transport_lhw_m": [PUBLISHED["transport_length_m"], PUBLISHED["transport_height_m"], PUBLISHED["undercarriage_width_m"]],
                "bucket_tip_radius_m": metrics["bucket_tip_radius_m"],
                "bucket_tip_witness_radius_m": metrics["bucket_tip_witness_radius_m"],
                "bucket_tip_contact_error_m": metrics["bucket_tip_planar_contact_error_m"],
                "bucket_tip_3d_contact_error_m": metrics["bucket_tip_3d_contact_error_m"],
                "track_subtree_lengths_m": [track["left"]["subtree_length_m"], track["right"]["subtree_length_m"]],
                "track_gauge_m": metrics["track_gauge_m"],
                "stick_pin_distance_m": metrics["stick_modeled_pin_distance_m"],
                "cab_roof_m": metrics["cab_roof_top_agl_m"],
                "upperframe_visible_width_m": metrics["upperframe_visible_width_m"],
                "tail_radius_m": metrics["tail_swing_radius_m"],
                "counterweight_clearance_m": metrics["counterweight_clearance_agl_m"],
                "center_frame_clearance_m": metrics["undercarriage_center_frame_underside_agl_m"],
            },
            ["Machine_Root", "Track_L_ROOT", "Track_R_ROOT", "Upper_ROOT", "Stick_Pivot", "Bucket_Pivot", "Bucket_ROOT", "Bucket_Tip_Radius_Point_1p570m"],
            ["transport-length", "transport-height", "undercarriage-width", "upperframe-width", "tail-swing-radius", "counterweight-clearance", "ground-clearance", "track-gauge", "top-cab-height", "bucket-tip-radius", "stick-length"],
            ["review/renders/cat-320-operator-side.png", "review/renders/cat-320-right-three-quarter.png"],
        ),
        required_gate(
            "published_working_envelope", metrics["working_envelope_geometric_reachability"]["pass"] and source_trace["pass"],
            "Use actual exported pivot transforms and semantic bucket-tip witness to test geometric reachability of the two published envelope extrema; this is compatibility evidence, not a limit solver.",
            {"reachability": metrics["working_envelope_geometric_reachability"], "source_fact_records": {key: source_trace["facts"][key] for key in ("maximum-digging-depth", "maximum-ground-reach")}},
            ["Upper_Swing_Pivot", "Boom_Pivot", "Stick_Pivot", "Bucket_Pivot", "Bucket_Tip_Radius_Point_1p570m"],
            ["maximum-digging-depth", "maximum-ground-reach", "stick-length", "bucket-tip-radius"],
            ["review/renders/cat-320-articulated-review.png", "review/renders/cat-320-front-equipment.png"],
        ),
        required_gate(
            "cylinder_length_continuity", hydraulic_ok,
            "Measure both segment endpoints, barrel-to-rod axial overlap, eye centers, and structural pin centers for all four hydraulic assemblies in the exported stowed pose.",
            {"assemblies": metrics["hydraulic_continuity"], "endpoint_tolerance_m": 1e-5, "minimum_internal_overlap_m": 0.05, "published_stroke_travel_asserted": False},
            ["Boom_Hydraulics_ROOT", "Stick_Hydraulics_ROOT", "Bucket_Hydraulics_ROOT", "Boom_ROOT", "Stick_ROOT", "Bucket_Bellcrank_ROOT"],
            [],
            ["review/renders/cat-320-hydraulic-routing-detail.png", "review/renders/cat-320-front-equipment.png"],
        ),
        required_gate(
            "bucket_linkage_closure", linkage_ok,
            "Measure dogbone endpoints and physical eye/pin centers against the reconstructed bellcrank and bucket-lug anchors, then verify lug ears and pin inherit Bucket_ROOT.",
            {"closure": metrics["bucket_linkage_physical_closure"], "tolerance_m": 1e-5},
            ["Bucket_Linkage_ROOT", "Bucket_Bellcrank_ROOT", "Bucket_ROOT", "PIN_Bellcrank_Dogbone", "Bucket_Dogbone_Lug_Eye", "Bucket_Lug_L_Ear", "Bucket_Lug_R_Ear", "PIN_Bucket_Lug"],
            [],
            ["review/renders/cat-320-linkage-detail.png", "review/renders/cat-320-articulated-review.png"],
        ),
        required_gate(
            "upper_to_undercarriage_clearance", upper_clearance_ok,
            "Compare evaluated upper-house minimum Y to fixed-undercarriage maximum Y in both declared review poses, excluding the intentional slew interface.",
            {"poses": {name: {"upper_house_min_y_m": record["upper_house_min_y_m"], "undercarriage_max_y_m": record["undercarriage_max_y_m"], "vertical_gap_m": record["upper_to_undercarriage_vertical_gap_m"]} for name, record in pose_metrics.items()}, "minimum_gap_m": 0.005},
            ["Undercarriage_ROOT", "Upper_Swing_Pivot", "Upper_ROOT"],
            [],
            ["review/renders/cat-320-rear-three-quarter.png", "review/renders/cat-320-right-three-quarter.png"],
        ),
        required_gate(
            "ground_collision", ground_ok,
            "Evaluate all exported mesh vertices and front-equipment vertices against authored Y=0 ground in both declared review poses.",
            {"poses": {name: {"front_equipment_min_y_m": record["front_equipment_min_y_m"], "all_visible_min_y_m": record["all_visible_min_y_m"]} for name, record in pose_metrics.items()}, "penetration_tolerance_m": 0.001},
            ["Machine_Root", "Track_L_ROOT", "Track_R_ROOT", "Boom_ROOT", "Stick_ROOT", "Bucket_ROOT"],
            ["ground-clearance"],
            ["review/renders/cat-320-operator-side.png", "review/renders/cat-320-articulated-review.png"],
        ),
        required_gate(
            "self_collision", self_collision_ok,
            "Require positive evaluated AABB separation for four nonadjacent critical group pairs in each declared review pose; adjacent designed joints are excluded.",
            {"poses": {name: record["critical_group_aabb_separations"] for name, record in pose_metrics.items()}, "minimum_aabb_gap_m": 0.005, "scope": "two declared reconstructed review poses; not a continuous swept-volume solver"},
            ["Undercarriage_ROOT", "Upper_ROOT", "Boom_ROOT", "Stick_ROOT", "Bucket_ROOT"],
            [],
            ["review/renders/cat-320-operator-side.png", "review/renders/cat-320-articulated-review.png"],
        ),
        required_gate(
            "track_phase_continuity", track_ok,
            "Measure ordered shoe-mesh centroids including the closing link, bilateral XY phase agreement, exact subtree length, and sprocket-to-idler centers.",
            {"left": {key: value for key, value in track["left"].items() if key != "centers"}, "right": {key: value for key, value in track["right"].items() if key != "centers"}, "paired_xy_phase_error_m": track["paired_xy_phase_error_m"], "maximum_gap_to_median_ratio": 1.25},
            ["Track_L_ROOT", "Track_R_ROOT", "Track_L_Rear_Sprocket_Hub", "Track_L_Front_Idler_Hub", "Track_R_Rear_Sprocket_Hub", "Track_R_Front_Idler_Hub"],
            ["track-length", "roller-center-length", "track-gauge", "track-shoes-per-side", "track-rollers-per-side", "carrier-rollers-per-side"],
            ["review/renders/cat-320-drive-sprocket-detail.png", "review/renders/cat-320-rear-three-quarter.png"],
        ),
    ]
    mechanism_required = source_trace["mechanism_required_gates"]
    required_ids = [gate["id"] for gate in required_gates]
    required_id_reconciliation_ok = (
        required_ids == mechanism_required and len(required_ids) == len(set(required_ids))
    )
    covered_fact_ids = sorted({fact_id for gate in required_gates if gate["status"] == "PASS" for fact_id in gate["detail"]["fact_ids"]})
    fact_coverage_ok = set(DESIGN_FACT_IDS).issubset(covered_fact_ids)
    house_target = RECONSTRUCTED["engine_house_visible_target_m"]
    independent_boundary_ok = (
        glb_contract["image_count"] == 0 and glb_contract["texture_count"] == 0
        and glb_contract["external_uri_count"] == 0 and source_trace["source"]["actual_sha256"] not in str(glb_contract)
    )
    gates = required_gates + [
        {"id":"builder-execution","status":"PASS","detail":{"method":"Background Blender reached post-export measurement and receipt generation.","evidence":{"blender_version":bpy.app.version_string}}},
        {"id":"candidate-class-boundary","status":"PASS","detail":{"candidate_class":CANDIDATE_CLASS,"configuration_status":"research_candidate"}},
        {"id":"source-configuration-traceability","status":"PASS" if source_trace["pass"] else "FAIL","detail":source_trace},
        {"id":"required-gate-id-reconciliation","status":"PASS" if required_id_reconciliation_ok else "FAIL","detail":{"mechanism_required_gates":mechanism_required,"validation_required_gates":required_ids}},
        {"id":"required-gate-fact-coverage","status":"PASS" if fact_coverage_ok else "FAIL","detail":{"design_published_constraints_used":DESIGN_FACT_IDS,"pass_gate_fact_id_union":covered_fact_ids}},
        {"id":"required-semantic-contract","status":"PASS" if semantic_ok else "FAIL","detail":metrics["semantic_contract"]},
        {"id":"hierarchy-and-pivot-parenting","status":"PASS" if semantic_ok else "FAIL","detail":{"method":"Compare actual type, parent, role, axis, and exported mesh descendants with REQUIRED_SEMANTICS.","records":metrics["semantic_contract"]}},
        {"id":"authored-track-contact-ground-plane","status":"PASS" if abs(metrics["track_contact_min_y_m"]) <= 0.001 else "FAIL","detail":{"measured_shoe_bottom_y_m":metrics["track_contact_min_y_m"],"authored_ground_y_m":0.0,"absolute_tolerance_m":0.001}},
        {"id":"engine-house-reconstructed-proportion","status":"PASS" if house_target["length_range"][0] <= metrics["engine_house_length_m"] <= house_target["length_range"][1] and house_target["height_range"][0] <= metrics["engine_house_height_m"] <= house_target["height_range"][1] else "FAIL","detail":{"modeled_m":{"length":metrics["engine_house_length_m"],"height":metrics["engine_house_height_m"]},"reconstructed_target_m":house_target}},
        {"id":"hydraulic-linkage-owner-hierarchy","status":"PASS" if hydraulic_ok and linkage_ok else "FAIL","detail":{"owners":metrics["hydraulic_linkage_owner_parents"],"physical_assemblies":metrics["hydraulic_continuity"],"linkage":metrics["bucket_linkage_physical_closure"]}},
        {"id":"export-mesh-scales-applied","status":"PASS" if not metrics["export_mesh_scale_offenders"] else "FAIL","detail":{"offenders":metrics["export_mesh_scale_offenders"]}},
        {"id":"glb-platform-contract","status":"PASS" if glb_contract_ok else "FAIL","detail":glb_contract},
        {"id":"neutral-unbranded-materials","status":"PASS" if neutral_materials_ok else "FAIL","detail":{"method":"Inspect exported GLB material names, decoded base colors, primitive usage, images, textures, and external URIs; require the dominant body and trim to be low-saturation slate/graphite and reject yellow/ochre or manufacturer-identifying names.","palette_contract":{"pass":body_palette_ok,"body":body_material,"trim":trim_material,"minimum_primitive_uses_each":10,"maximum_rgb_channel_spread":0.10,"required_channel_order":"R <= G <= B","prohibited_name_tokens":["caterpillar","cat_yellow","yellow","ochre"]},"material_names":glb_contract["material_names"],"image_count":glb_contract["image_count"],"texture_count":glb_contract["texture_count"],"external_uri_count":glb_contract["external_uri_count"]}},
        {"id":"independent-authoring-boundary","status":"PASS" if independent_boundary_ok else "FAIL","detail":{"method":"Inspect GLB for embedded/external images, textures, or external buffers and bind the independently authored builder hash in the receipt.","image_count":glb_contract["image_count"],"texture_count":glb_contract["texture_count"],"external_uri_count":glb_contract["external_uri_count"]}},
        {"id":"object-count","status":"PASS" if counts["objects"] >= 180 else "FAIL","detail":{"objects":counts["objects"],"minimum":180}},
        {"id":"triangle-budget","status":"PASS" if 20_000 <= counts["triangles"] <= 220_000 else "FAIL","detail":{"triangles":counts["triangles"],"budget":[20000,220000]}},
        {"id":"review-renders-measured","status":"PASS" if render_ok else "FAIL","detail":{"method":"Decode every generated PNG and measure exact dimensions, bytes, signature, SHA-256, and sampled luminance span.","renders":render_evidence}},
        {"id":"configuration-freeze","status":"PENDING","detail":"Research candidate retains unresolved serial/order, coupler, thumb, OPG, grade/camera, and rights choices."},
        {"id":"continuous-mechanical-limit-solver","status":"PENDING","detail":"Required PASS gates cover the two declared reconstructed review poses and geometric reachability only; no continuous manufacturer limit solver is claimed."},
        {"id":"continuous-swept-collision-engineering","status":"PENDING","detail":"Required collision PASS gates cover measured declared poses, not a continuous swept-volume engineering analysis."},
        {"id":"critic-human-visual-review","status":"PENDING","detail":"Overall critic must inspect the exact render and asset hashes."},
        {"id":"viewer-browser-accessibility-mobile-selection-performance","status":"PENDING","detail":"No viewer integration in this lane."},
        {"id":"publication-and-deployment","status":"PENDING","detail":"Only the overall publisher may advance publication state."},
    ]
    failed = [gate["id"] for gate in gates if gate["status"] == "FAIL"]
    payload = {
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "candidate_class":CANDIDATE_CLASS,
        "release_status":"PENDING",
        "verdict":"PASS" if not failed else "FAIL",
        "bounds":bounds,
        "counts":counts,
        "design":{"published_constraints_used":DESIGN_FACT_IDS},
        "required_machine_gate_ids":mechanism_required,
        "source_configuration_traceability":source_trace,
        "geometry_metrics":metrics,
        "pose_metrics":pose_metrics,
        "render_evidence":render_evidence,
        "glb_contract":glb_contract,
        "gates":gates,
        "failed_gate_ids":failed,
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
    render_paths, pose_metrics = render_all(model)

    objects = export_objects()
    apply_export_mesh_scales(objects)
    bpy.context.view_layer.update()
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

    glb_contract = inspect_glb_contract(GLB_PATH)
    metrics = collect_geometry_metrics(model, objects)
    render_records = inspect_render_files(render_paths)
    source_trace = verify_source_configuration_contract()
    validation = create_validation(
        bounds, counts, render_paths, metrics, glb_contract,
        pose_metrics, source_trace, render_records,
    )
    semantic_records = metrics["semantic_contract"]
    receipt = {
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "configuration_status":"research_candidate",
        "candidate_class":CANDIDATE_CLASS,
        "release_status":"PENDING",
        "authority_boundary":"Independently authored technical structural study. Not manufacturer CAD, engineering authority, load guidance, operator training, safety guidance, a digital twin, or a mechanically validated candidate.",
        "blender":{"version":bpy.app.version_string,"factory_startup_required":True,"background_required":True},
        "builder":{"path":rel(SCRIPT_PATH),"sha256":sha256(SCRIPT_PATH),"bytes":SCRIPT_PATH.stat().st_size,"deterministic":True,"network_used":False,"downloaded_geometry_used":False,"manufacturer_cad_used":False,"copied_textures_used":False,"opaque_addons_used":False},
        "design":{"path":rel(DESIGN_PATH),"sha256":sha256(DESIGN_PATH),"bytes":DESIGN_PATH.stat().st_size},
        "artifacts":{
            "validation":{"path":rel(VALIDATION_PATH),"sha256":sha256(VALIDATION_PATH),"bytes":VALIDATION_PATH.stat().st_size},
            "blend":{"path":rel(BLEND_PATH),"sha256":sha256(BLEND_PATH),"bytes":BLEND_PATH.stat().st_size},
            "glb":{"path":rel(GLB_PATH),"sha256":sha256(GLB_PATH),"bytes":GLB_PATH.stat().st_size},
        },
        "scene":{"units":"meters","axes":{"longitudinal":"+X toward bucket","vertical":"+Y","lateral":"+Z machine right"},"visible_aabb_xyz_m":bounds["size_m"],"bounds":bounds,**counts},
        "glb_contract":glb_contract,
        "repair_round_3":{
            "finding_ids":["CAT320-R3-BUCKET-TIP","CAT320-R3-PHYSICAL-JOINTS","CAT320-R3-TRACK-LENGTH","CAT320-R3-FAIL-CLOSED-GATES","CAT320-R3-SOURCE-TRACE"],
            "measured":{
                "bucket_tip_radius_m":metrics["bucket_tip_radius_m"],
                "bucket_tip_witness_radius_m":metrics["bucket_tip_witness_radius_m"],
                "bucket_tip_contact_error_m":metrics["bucket_tip_planar_contact_error_m"],
                "bucket_tip_3d_contact_error_m":metrics["bucket_tip_3d_contact_error_m"],
                "track_subtree_length_left_m":metrics["track_phase"]["left"]["subtree_length_m"],
                "track_subtree_length_right_m":metrics["track_phase"]["right"]["subtree_length_m"],
                "stick_modeled_pin_distance_m":metrics["stick_modeled_pin_distance_m"],
                "hydraulic_continuity":metrics["hydraulic_continuity"],
                "bucket_linkage_physical_closure":metrics["bucket_linkage_physical_closure"],
                "pose_metrics":pose_metrics,
            },
            "visual_repairs":["visible boom-cylinder base and rod clevis ears, eyes, and pins","visible stick and bucket cylinder endpoint eyes and pins","bucket-root lug ears and pin with dogbone endpoint eye","published-radius bucket tip witness","exact-length bilateral track shoe loops"],
        },
        "repair_round_4":{
            "finding_ids":["CAT320-R4-NEUTRAL-UNBRANDED-PALETTE"],
            "resolution":"Replaced the dominant yellow/ochre-like body treatment with low-saturation neutral slate and graphite while preserving geometry, hierarchy, poses, and cameras.",
            "viewer_accent":"#71838a",
            "material_evidence":next(gate["detail"] for gate in validation["gates"] if gate["id"] == "neutral-unbranded-materials"),
        },
        "private_nonexport_inspection_nodes":["Inspection_Volumes","INSPECT_Transport_Envelope","INSPECT_Upper_Clearance","INSPECT_Boom_Swept_Study","INSPECT_Attachment_Volume"],
        "required_semantic_nodes":{name:True for name in REQUIRED_NODES},
        "required_semantic_contract":semantic_records,
        "manufacturer_published_constraints_used":DESIGN_FACT_IDS,
        "published_constraint_ids_declared":DESIGN_FACT_IDS,
        "source_configuration_traceability":source_trace,
        "machine_specific_gate_evidence":[
            {"id":gate["id"],"status":gate["status"],"detail":gate["detail"]}
            for required_id in source_trace["mechanism_required_gates"]
            for gate in validation["gates"] if gate["id"] == required_id
        ],
        "required_gate_evidence":[gate for gate in validation["gates"] if gate["id"] in source_trace["mechanism_required_gates"]],
        "reconstructed_values":RECONSTRUCTED,
        "unresolved_choices":["exact serial or order family","quick coupler selection","thumb selection","cab OPG selection","grade-control and camera options","public material and branding authorization"],
        "mechanical_gaps":["slew bearing center and elevation authority","boom/stick/bucket pivot authority","all hydraulic anchor coordinates","bucket linkage topology dimensions","track link pitch and individual roller-center authority","continuous manufacturer motion limits and stroke solver","continuous swept-volume collision engineering","published working-envelope limit reproduction beyond geometric reachability"],
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
