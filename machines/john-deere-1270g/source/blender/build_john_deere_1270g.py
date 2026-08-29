#!/usr/bin/env python3
"""Deterministic, independently authored John Deere 1270G 8W structural study.

Run only with Blender factory startup in background mode. Manufacturer CAD,
textures, logos and photography are not inputs. Published facts bind the
configuration and selected envelopes; every hidden pivot, anchor, section,
mesh dimension and interpolated pose is reconstructed and non-authoritative.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector


MACHINE_ID = "john-deere-1270g"
CONFIGURATION_ID = "JD-1270G-8W-CH7-R86-H480C-600-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"
MACHINE_DIR = Path(__file__).resolve().parents[2]
BUILDER_PATH = Path(__file__).resolve()
BLEND_PATH = MACHINE_DIR / "source/blender/john-deere-1270g-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets/john-deere-1270g-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production/asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production/validation.json"
RENDER_DIR = MACHINE_DIR / "review/renders"


def mv(x: float, y: float, z: float) -> Vector:
    """Machine +X/+Y/+Z to Blender +X/+Z/+Y storage."""
    return Vector((x, z, y))


PUBLISHED = {
    "base-carrier-length": 7.927,
    "front-axle-middle-joint": 2.150,
    "rear-axle-middle-joint": 2.280,
    "wheelbase": 4.430,
    "minimum-width-600": 2.746,
    "transport-height": 3.881,
    "transport-length": 12.560,
    "ground-clearance": 0.717,
    "selected-maximum-reach": 8.600,
    "turning-angle": 44.0,
    "boom-slewing-angle": 220.0,
    "cab-rotation": 160.0,
    "cab-sideways-tilt": 17.0,
    "cab-fore-aft-tilt": 9.0,
}

# Modeling inputs, not Deere dimensions.
RECONSTRUCTED = {
    "carrier_rear_x_m": -4.150,
    "carrier_front_x_m": 3.777,
    "frame_joint_xyz_m": [0.0, 1.08, 0.0],
    "front_bogie_center_xyz_m": [2.150, 0.83, 0.0],
    "rear_rigid_axle_center_xyz_m": [-2.280, 0.83, 0.0],
    "tandem_half_spacing_m": 0.730,
    "tire_outer_radius_m": 0.730,
    "tire_visual_width_m": 0.580,
    "tire_center_abs_z_m": 1.083,
    "tire_tread_blocks_per_wheel": 18,
    "crane_base_xyz_m": [1.650, 2.05, 0.0],
    "selected_max_reach_head_reference_local_x_m": 0.40,
    "head_visual_height_m": 1.65,
    "head_visual_width_m": 1.02,
    "head_visual_depth_m": 0.92,
    "boom_hose_visual_diameter_m": 0.032,
    "frame_review_articulation_deg": 24.0,
    "front_bogie_review_tilt_deg": 8.0,
    "retained_pose": "working",
    "structural_triangle_budget": 180000,
}

UNRESOLVED = [
    "exact tire make, tread, inflation, offset and sidewall geometry",
    "individual front and rear axle centers beyond published joint-distance references",
    "rear eight-wheel suspension articulation and housing geometry",
    "frame joint pivot, yokes, stops, steering-cylinder anchors and clearances",
    "rotating/leveling cab pivots, actuators, option package and control law",
    "CH7 8.6 m segment lengths, telescope stroke, pivots, cylinders and IBC interpolation",
    "boom tilt and slew datum conventions",
    "H480C exact revision, envelope, mass, internal structure and attachment interface",
    "feed-roller profiles, knife linkages, saw bar/chain/guard and hydraulic routing",
    "transport-pose retention, measured transport envelope and collision clearance",
    "regional power-unit, emissions, guarding, lighting and service-panel options",
    "manufacturer material, livery, logo and trade-dress authorization",
]

COLLECTIONS: dict[str, bpy.types.Collection] = {}
MATERIALS: dict[str, bpy.types.Material] = {}
ART: dict[str, bpy.types.Object] = {}
RENDER_PATHS: list[Path] = []


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_dirs() -> None:
    for directory in (BLEND_PATH.parent, GLB_PATH.parent, RECEIPT_PATH.parent, RENDER_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            datablocks.remove(datablock)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    if hasattr(scene.render, "dither_intensity"):
        scene.render.dither_intensity = 0.0
    for prop in (
        "use_stamp_camera", "use_stamp_date", "use_stamp_filename", "use_stamp_frame",
        "use_stamp_frame_range", "use_stamp_hostname", "use_stamp_labels", "use_stamp_lens",
        "use_stamp_marker", "use_stamp_memory", "use_stamp_note", "use_stamp_render_time",
        "use_stamp_scene", "use_stamp_sequencer_strip", "use_stamp_time",
    ):
        if hasattr(scene.render, prop):
            setattr(scene.render, prop, False)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.018, 0.022, 0.028)


def make_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    COLLECTIONS[name] = collection
    return collection


def move_to_collection(obj: bpy.types.Object, name: str) -> None:
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    COLLECTIONS[name].objects.link(obj)


def set_parent(obj: bpy.types.Object, parent: bpy.types.Object, preserve_world=True) -> None:
    world = obj.matrix_world.copy()
    obj.parent = parent
    if preserve_world:
        obj.matrix_world = world


def material(name: str, color: tuple[float, float, float, float], metallic=0.0,
             roughness=0.45, transmission=0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Alpha"].default_value = color[3]
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if color[3] < 1.0:
        mat.surface_render_method = "DITHERED"
    MATERIALS[name] = mat
    return mat


def apply_material(obj: bpy.types.Object, name: str) -> None:
    if obj.type == "MESH":
        obj.data.materials.append(MATERIALS[name])


def add_empty(name: str, xyz=(0.0, 0.0, 0.0), collection="Fixed_Structure",
              size=0.16, parent=None, public=True) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    obj.location = mv(*xyz)
    obj["public_export"] = public
    COLLECTIONS[collection].objects.link(obj)
    if parent:
        set_parent(obj, parent)
    return obj


def add_box(name: str, center: tuple[float, float, float],
            size: tuple[float, float, float], mat_name: str, collection: str,
            bevel=0.025, parent=None, local=False, public=True) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = (size[0], size[2], size[1])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
        mod.width = min(bevel, min(size) * 0.22)
        mod.segments = 2
    apply_material(obj, mat_name)
    obj["public_export"] = public
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent, preserve_world=not local)
    return obj


def add_cylinder(name: str, center: tuple[float, float, float], radius: float,
                 depth: float, axis: str, mat_name: str, collection: str,
                 vertices=32, parent=None, local=False, public=True) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    if axis == "z":
        obj.rotation_euler[0] = math.radians(90)
    elif axis == "x":
        obj.rotation_euler[1] = math.radians(90)
    elif axis != "y":
        raise ValueError(axis)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
    mod.width = min(0.014, radius * 0.10)
    mod.segments = 2
    apply_material(obj, mat_name)
    obj["public_export"] = public
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent, preserve_world=not local)
    return obj


def add_torus(name: str, center: tuple[float, float, float], major: float, minor: float,
              width_scale: float, mat_name: str, collection: str,
              parent=None, public=True) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                    major_segments=40, minor_segments=12,
                                    location=mv(*center), rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.scale.y = width_scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_material(obj, mat_name)
    obj["public_export"] = public
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def add_uv_sphere(name: str, center: tuple[float, float, float],
                  radius: float, mat_name: str, collection: str,
                  parent=None, local=False, public=True) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12,
                                        radius=radius, location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    apply_material(obj, mat_name)
    obj["public_export"] = public
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent, preserve_world=not local)
    return obj


def add_unit_beam(name: str, mat_name: str, collection: str,
                  parent=None, bevel=0.025) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=2.0)
    obj = bpy.context.object
    obj.name = name
    mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
    mod.width = bevel
    mod.segments = 2
    apply_material(obj, mat_name)
    obj["public_export"] = True
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def place_beam(obj: bpy.types.Object, a: tuple[float, float, float],
               b: tuple[float, float, float], width: float, depth: float) -> None:
    pa, pb = mv(*a), mv(*b)
    direction = pb - pa
    rotation = direction.to_track_quat("X", "Z").to_matrix().to_4x4()
    scale = Matrix.Diagonal(Vector((direction.length * 0.5, width * 0.5,
                                    depth * 0.5, 1.0)))
    obj.matrix_world = Matrix.Translation((pa + pb) * 0.5) @ rotation @ scale


def add_unit_cylinder(name: str, mat_name: str, collection: str,
                      parent=None, vertices=24) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=1.0, depth=2.0)
    obj = bpy.context.object
    obj.name = name
    apply_material(obj, mat_name)
    obj["public_export"] = True
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def place_cylinder(obj: bpy.types.Object, a: tuple[float, float, float],
                   b: tuple[float, float, float], radius: float) -> None:
    pa, pb = mv(*a), mv(*b)
    direction = pb - pa
    rotation = direction.to_track_quat("Z", "Y").to_matrix().to_4x4()
    scale = Matrix.Diagonal(Vector((radius, radius, direction.length * 0.5, 1.0)))
    obj.matrix_world = Matrix.Translation((pa + pb) * 0.5) @ rotation @ scale


def add_prism_xy(name: str, polygon: list[tuple[float, float]], z_center: float,
                 width: float, mat_name: str, collection: str,
                 parent=None, local=False, public=True) -> bpy.types.Object:
    half = width * 0.5
    verts = []
    for z in (-half, half):
        for x, y in polygon:
            verts.append((x, z, y)) if local else verts.append(tuple(mv(x, y, z + z_center)))
    count = len(polygon)
    faces = [tuple(range(count))[::-1], tuple(range(count, 2 * count))]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, count + nxt, count + index))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTIONS[collection].objects.link(obj)
    apply_material(obj, mat_name)
    mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
    mod.width = 0.018
    mod.segments = 2
    obj["public_export"] = public
    if parent:
        set_parent(obj, parent, preserve_world=not local)
    return obj


def add_polyline_tube(name: str, points: list[tuple[float, float, float]],
                      diameter: float, mat_name: str, collection: str,
                      parent=None, cyclic=False, public=True) -> bpy.types.Object:
    curve = bpy.data.curves.new(f"{name}_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = diameter * 0.5
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        p = mv(*xyz)
        point.co = (p.x, p.y, p.z, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    COLLECTIONS[collection].objects.link(obj)
    obj.data.materials.append(MATERIALS[mat_name])
    obj["public_export"] = public
    if parent:
        set_parent(obj, parent)
    return obj


def set_polyline(obj: bpy.types.Object, points: list[tuple[float, float, float]]) -> None:
    spline = obj.data.splines[0]
    if len(spline.points) != len(points):
        raise ValueError(f"{obj.name}: hose point count changed")
    for point, xyz in zip(spline.points, points):
        p = mv(*xyz)
        point.co = (p.x, p.y, p.z, 1.0)


def build_materials() -> None:
    # Deliberately neutral, unbranded industrial palette.
    material("Graphite", (0.055, 0.065, 0.078, 1), metallic=0.62, roughness=0.28)
    material("DarkPanel", (0.105, 0.120, 0.135, 1), metallic=0.42, roughness=0.38)
    material("NeutralPanel", (0.31, 0.335, 0.35, 1), metallic=0.48, roughness=0.34)
    material("WarmMetal", (0.42, 0.39, 0.34, 1), metallic=0.58, roughness=0.30)
    material("Steel", (0.49, 0.53, 0.57, 1), metallic=0.90, roughness=0.17)
    material("Rubber", (0.013, 0.016, 0.020, 1), roughness=0.88)
    material("Glass", (0.055, 0.13, 0.16, 0.27), metallic=0.03, roughness=0.12, transmission=0.46)
    material("Interior", (0.028, 0.035, 0.043, 1), roughness=0.78)
    material("Hose", (0.018, 0.022, 0.027, 1), roughness=0.72)
    material("Lamp", (0.72, 0.76, 0.78, 1), metallic=0.10, roughness=0.20)
    material("Marker", (0.84, 0.25, 0.08, 1), roughness=0.32)
    material("Collision", (0.95, 0.10, 0.06, 0.0), roughness=0.5)
    material("Inspection", (0.10, 0.55, 0.95, 0.0), roughness=0.5)
    material("Ground", (0.045, 0.052, 0.060, 1), roughness=0.94)


def build_root_and_frames() -> bpy.types.Object:
    root = add_empty("JD1270G_Root", (0, 0, 0), size=0.28)
    root["candidate_class"] = CANDIDATE_CLASS
    root["configuration_id"] = CONFIGURATION_ID
    root["engineering_authority"] = False

    rear = add_empty("RearFrame_Root", (0, 0, 0), parent=root)
    steer = add_empty("FrameSteer_Pivot_Reconstructed", tuple(RECONSTRUCTED["frame_joint_xyz_m"]),
                      collection="Articulation", parent=root)
    steer["authority"] = "published_range_reconstructed_pivot"
    front = add_empty("FrontFrame_Root", (0, 0, 0), collection="Articulation", parent=steer)
    ART.update(root=root, rear=rear, steer=steer, front=front)

    # Fixed machine-space evidence witnesses are excluded from the public GLB.
    witnesses = {
        "Reference_Carrier_Rear": (-4.150, 1.0, 0.0),
        "Reference_Carrier_Front": (3.777, 1.0, 0.0),
        "Reference_FrontAxle": (2.150, 0.83, 0.0),
        "Reference_RearAxle": (-2.280, 0.83, 0.0),
        "Reference_Width_Left": (0.0, 0.83, -1.373),
        "Reference_Width_Right": (0.0, 0.83, 1.373),
        "Reference_GroundClearance": (0.0, 0.717, 0.0),
        "Reference_TransportHeight": (0.8, 3.881, 0.0),
        "Reference_TransportLength_Front": (8.410, 1.0, 0.0),
    }
    for name, xyz in witnesses.items():
        witness = add_empty(name, xyz, "Markers", 0.09, root, public=False)
        witness["authority"] = "manufacturer_published_constraint_reference"

    # Rear carrier and power-frame rails. End caps retain the 7.927 m A datum
    # without claiming that the publication drawing is a scale profile.
    add_box("RearFrame_MainRail", (-2.00, 0.91, 0.0), (4.20, 0.38, 1.16),
            "Graphite", "Fixed_Structure", 0.055, rear)
    add_box("RearFrame_BellyPan", (-2.00, 0.767, 0.0), (4.15, 0.10, 1.10),
            "DarkPanel", "Fixed_Structure", 0.015, rear)
    add_box("CarrierRearDatumCap", (-4.10, 1.02, 0.0), (0.10, 0.52, 1.26),
            "Graphite", "Fixed_Structure", 0.025, rear)
    add_box("FrontFrame_MainRail", (1.95, 0.91, 0.0), (3.65, 0.38, 1.14),
            "Graphite", "Fixed_Structure", 0.055, front)
    add_box("FrontFrame_BellyPan", (1.92, 0.767, 0.0), (3.58, 0.10, 1.08),
            "DarkPanel", "Fixed_Structure", 0.015, front)
    add_box("CarrierFrontDatumCap", (3.727, 1.02, 0.0), (0.10, 0.52, 1.22),
            "Graphite", "Fixed_Structure", 0.025, front)

    # Articulation yokes, vertical kingpin and two readable steering cylinders.
    add_box("RearArticulationYoke", (-0.20, 1.09, 0.0), (0.46, 0.68, 0.86),
            "Graphite", "Articulation", 0.055, rear)
    add_box("FrontArticulationYoke", (0.19, 1.09, 0.0), (0.44, 0.60, 0.68),
            "NeutralPanel", "Articulation", 0.05, front)
    add_cylinder("FrameSteer_Kingpin", (0.0, 1.09, 0.0), 0.17, 0.78, "y",
                 "Steel", "Articulation", 36, root)
    for side in (-1, 1):
        suffix = "L" if side < 0 else "R"
        barrel = add_unit_cylinder(f"FrameSteerCylinder_{suffix}", "DarkPanel", "Hydraulics", rear)
        rod = add_unit_cylinder(f"FrameSteerRod_{suffix}", "Steel", "Hydraulics", rear)
        place_cylinder(barrel, (-0.55, 1.20, side * 0.43), (0.15, 1.20, side * 0.32), 0.075)
        place_cylinder(rod, (0.10, 1.20, side * 0.32), (0.62, 1.16, side * 0.43), 0.045)
    return root


def build_wheel(name: str, center: tuple[float, float, float],
                parent: bpy.types.Object) -> None:
    wheel_root = add_empty(f"{name}_Root", center, "Running_Gear", 0.13, parent)
    add_torus(f"{name}_Tire", center, 0.47, 0.26, 1.12, "Rubber", "Running_Gear", wheel_root)
    add_cylinder(f"{name}_RimOuter", center, 0.29, 0.50, "z", "WarmMetal",
                 "Running_Gear", 40, wheel_root)
    add_cylinder(f"{name}_Hub", center, 0.12, 0.55, "z", "Steel",
                 "Running_Gear", 32, wheel_root)
    side = -1 if center[2] < 0 else 1
    outer_face_z = center[2] + side * 0.285
    for index in range(8):
        angle = math.tau * index / 8
        add_cylinder(f"{name}_Lug_{index + 1:02d}",
                     (center[0] + 0.18 * math.cos(angle),
                      center[1] + 0.18 * math.sin(angle), outer_face_z),
                     0.025, 0.025, "z", "Graphite", "Running_Gear", 16, wheel_root)
    count = RECONSTRUCTED["tire_tread_blocks_per_wheel"]
    for index in range(count):
        angle = math.tau * index / count
        tread = add_box(f"{name}_Tread_{index + 1:02d}",
                        (center[0] + 0.73 * math.cos(angle),
                         center[1] + 0.73 * math.sin(angle), center[2]),
                        (0.20, 0.075, 0.61), "Rubber", "Running_Gear", 0.012, wheel_root)
        tread.rotation_euler[1] = -angle


def build_running_gear(root: bpy.types.Object) -> None:
    front = ART["front"]
    rear = ART["rear"]
    bogie = add_empty("FrontBalancedBogie_Pivot_Reconstructed", (2.15, 0.83, 0.0),
                      "Running_Gear", 0.22, front)
    bogie["authority"] = "observed_balanced_bogie_reconstructed_pivot"
    ART["front_bogie"] = bogie
    for side in (-1, 1):
        suffix = "L" if side < 0 else "R"
        z = side * 1.083
        beam = add_unit_beam(f"FrontBogieBeam_{suffix}", "Graphite", "Running_Gear", bogie, 0.04)
        place_beam(beam, (1.34, 0.83, z), (2.96, 0.83, z), 0.34, 0.24)
        add_cylinder(f"FrontBogieHub_{suffix}", (2.15, 0.83, z), 0.23, 0.42,
                     "z", "NeutralPanel", "Running_Gear", 36, bogie)
        for x, label in ((1.42, "Rear"), (2.88, "Front")):
            add_cylinder(f"FrontBogieAxle_{suffix}_{label}", (x, 0.83, z), 0.13,
                         0.44, "z", "Steel", "Running_Gear", 28, bogie)
            build_wheel(f"Front_{label}_{suffix}", (x, 0.83, z), bogie)

    # Four rear wheels are represented on two rigidly mounted axle tubes. The
    # source does not admit a rear bogie pivot for this exact 8W package.
    for x, label in ((-1.55, "Front"), (-3.01, "Rear")):
        add_cylinder(f"RearRigidAxle_{label}", (x, 0.83, 0.0), 0.18, 2.16, "z",
                     "Graphite", "Running_Gear", 32, rear)
        for side in (-1, 1):
            suffix = "L" if side < 0 else "R"
            build_wheel(f"Rear_{label}_{suffix}", (x, 0.83, side * 1.083), rear)


def build_power_unit() -> None:
    rear = ART["rear"]
    # Sloped neutral power hood and individually readable service zones.
    add_prism_xy("PowerUnit_Core", [(-4.03, 1.02), (-3.92, 2.42), (-3.42, 2.82),
                                    (-0.66, 2.53), (-0.48, 1.03)],
                 0.0, 2.18, "DarkPanel", "Power_Unit", rear)
    for side in (-1, 1):
        suffix = "L" if side < 0 else "R"
        z = side * 1.105
        add_prism_xy(f"PowerServicePanel_{suffix}",
                     [(-3.83, 1.20), (-3.72, 2.28), (-3.32, 2.58),
                      (-0.78, 2.34), (-0.66, 1.18)], z, 0.045,
                     "NeutralPanel", "Power_Unit", rear)
        # Three panel breaks plus cooling grille.
        for x in (-3.12, -2.30, -1.46):
            add_box(f"ServicePanelBreak_{suffix}_{x:+.2f}", (x, 1.78, z + side * 0.025),
                    (0.022, 1.02, 0.025), "Graphite", "Power_Unit", 0.004, rear)
        for idx, y in enumerate((1.45, 1.61, 1.77, 1.93, 2.09, 2.25)):
            add_box(f"CoolingGrille_{suffix}_{idx + 1:02d}", (-3.34, y, z + side * 0.035),
                    (0.66, 0.055, 0.026), "Graphite", "Power_Unit", 0.007, rear)
        for idx, x in enumerate((-3.72, -2.92, -2.10, -1.28, -0.79)):
            add_cylinder(f"PanelFastener_{suffix}_{idx + 1:02d}",
                         (x, 1.28 + 0.12 * (idx % 2), z + side * 0.05),
                         0.025, 0.018, "z", "Steel", "Power_Unit", 16, rear)
    add_box("PowerUnit_TopDeck", (-2.24, 2.53, 0.0), (2.75, 0.12, 2.05),
            "Graphite", "Power_Unit", 0.045, rear)
    add_cylinder("ExhaustStack", (-3.58, 2.88, 0.62), 0.09, 0.78, "y",
                 "Graphite", "Power_Unit", 28, rear)
    add_cylinder("ExhaustTip", (-3.54, 3.27, 0.62), 0.105, 0.18, "x",
                 "Graphite", "Power_Unit", 28, rear)
    # Service steps and handhold cues on operator side.
    for idx, x in enumerate((-0.92, -0.58, -0.25)):
        add_box(f"ServiceStep_{idx + 1:02d}", (x, 0.92 + idx * 0.18, -1.24),
                (0.32, 0.08, 0.34), "Steel", "Power_Unit", 0.018, rear)
    add_polyline_tube("PowerUnit_Handrail",
                      [(-1.18, 1.05, -1.25), (-1.18, 2.15, -1.25),
                       (-0.45, 2.35, -1.25), (-0.22, 1.45, -1.25)],
                      0.045, "Steel", "Power_Unit", rear)


def build_cab() -> None:
    front = ART["front"]
    cab_turntable = add_empty("CabRotation_Root_Reconstructed", (0.72, 1.20, 0.0),
                              "Cab", 0.20, front)
    cab_level = add_empty("CabLeveling_Root_Reconstructed", (0.72, 1.36, 0.0),
                          "Cab", 0.18, cab_turntable)
    cab_turntable["published_rotation_deg"] = PUBLISHED["cab-rotation"]
    cab_level["published_side_tilt_deg"] = PUBLISHED["cab-sideways-tilt"]
    cab_level["published_fore_aft_tilt_deg"] = PUBLISHED["cab-fore-aft-tilt"]
    ART.update(cab_turntable=cab_turntable, cab_level=cab_level)

    add_cylinder("CabRotation_BearingLower", (0.72, 1.20, 0.0), 0.72, 0.16, "y",
                 "Graphite", "Cab", 48, cab_turntable)
    add_cylinder("CabRotation_BearingUpper", (0.72, 1.34, 0.0), 0.60, 0.15, "y",
                 "Steel", "Cab", 48, cab_level)
    for side in (-1, 1):
        suffix = "L" if side < 0 else "R"
        cyl = add_unit_cylinder(f"CabLevelCylinder_{suffix}", "DarkPanel", "Hydraulics", front)
        rod = add_unit_cylinder(f"CabLevelRod_{suffix}", "Steel", "Hydraulics", front)
        place_cylinder(cyl, (0.40, 1.20, side * 0.52), (0.48, 1.54, side * 0.48), 0.065)
        place_cylinder(rod, (0.48, 1.51, side * 0.48), (0.60, 1.78, side * 0.43), 0.038)

    # ROPS/cab cage. World geometry is parented into the leveling root so the
    # compound hierarchy remains inspectable without claiming actual pivots.
    for side in (-1, 1):
        suffix = "L" if side < 0 else "R"
        z = side * 0.66
        rear_pillar = add_unit_beam(f"CabRearPillar_{suffix}", "Graphite", "Cab", cab_level, 0.028)
        place_beam(rear_pillar, (-0.05, 1.55, z), (0.02, 3.58, z), 0.10, 0.11)
        front_pillar = add_unit_beam(f"CabFrontPillar_{suffix}", "Graphite", "Cab", cab_level, 0.028)
        place_beam(front_pillar, (1.58, 1.55, z), (1.42, 3.58, z), 0.10, 0.11)
        add_box(f"CabLowerSill_{suffix}", (0.76, 1.62, z), (1.62, 0.14, 0.10),
                "Graphite", "Cab", 0.025, cab_level)
        add_box(f"CabRoofRail_{suffix}", (0.73, 3.57, z), (1.48, 0.13, 0.11),
                "Graphite", "Cab", 0.025, cab_level)
        add_box(f"CabSideGlass_{suffix}", (0.75, 2.57, side * 0.645),
                (1.28, 1.70, 0.035), "Glass", "Cab", 0.008, cab_level)
        add_box(f"CabDoorLower_{suffix}", (0.74, 1.78, side * 0.675),
                (1.18, 0.32, 0.05), "DarkPanel", "Cab", 0.025, cab_level)
        for idx, x in enumerate((0.15, 1.28)):
            add_cylinder(f"CabDoorHinge_{suffix}_{idx + 1}",
                         (x, 2.00, side * 0.71), 0.025, 0.12, "y",
                         "Steel", "Cab", 16, cab_level)
    add_box("CabRoof", (0.72, 3.65, 0.0), (1.62, 0.16, 1.48),
            "NeutralPanel", "Cab", 0.05, cab_level)
    add_box("CabFrontGlass", (1.48, 2.58, 0.0), (0.045, 1.72, 1.16),
            "Glass", "Cab", 0.009, cab_level)
    add_box("CabRearGlass", (-0.02, 2.56, 0.0), (0.038, 1.62, 1.10),
            "Glass", "Cab", 0.008, cab_level)
    add_box("CabFrontHeader", (1.43, 3.52, 0.0), (0.15, 0.18, 1.38),
            "Graphite", "Cab", 0.03, cab_level)
    add_box("CabRearHeader", (0.00, 3.52, 0.0), (0.14, 0.18, 1.34),
            "Graphite", "Cab", 0.03, cab_level)
    # Interior readability through the glazing.
    add_box("OperatorSeat_Base", (0.58, 1.75, 0.0), (0.52, 0.18, 0.56),
            "Interior", "Cab", 0.07, cab_level)
    add_box("OperatorSeat_Back", (0.35, 2.22, 0.0), (0.18, 0.82, 0.54),
            "Interior", "Cab", 0.08, cab_level)
    add_box("OperatorHeadrest", (0.34, 2.73, 0.0), (0.18, 0.26, 0.38),
            "Interior", "Cab", 0.07, cab_level)
    for side in (-1, 1):
        suffix = "L" if side < 0 else "R"
        add_box(f"OperatorConsole_{suffix}", (0.78, 1.92, side * 0.42),
                (0.70, 0.20, 0.18), "DarkPanel", "Cab", 0.035, cab_level)
        add_cylinder(f"OperatorJoystick_{suffix}", (0.98, 2.12, side * 0.42),
                     0.035, 0.28, "y", "Rubber", "Cab", 20, cab_level)
    add_box("OperatorDisplay", (1.20, 2.34, -0.38), (0.10, 0.46, 0.38),
            "Interior", "Cab", 0.025, cab_level)
    # Neutral work lamps establish the published transport-height witness.
    for idx, z in enumerate((-0.50, -0.17, 0.17, 0.50)):
        add_box(f"CabRoofLamp_{idx + 1:02d}", (1.25, 3.831, z),
                (0.16, 0.10, 0.16), "Lamp", "Cab", 0.025, cab_level)


def build_crane_and_boom() -> None:
    front = ART["front"]
    base_xyz = tuple(RECONSTRUCTED["crane_base_xyz_m"])
    slew = add_empty("CH7_Slew_Root_Reconstructed", base_xyz, "Boom", 0.24, front)
    ART["slew"] = slew
    add_cylinder("CH7_SlewBearing_Lower", (base_xyz[0], 1.41, 0.0), 0.63, 0.28,
                 "y", "Graphite", "Boom", 48, front)
    add_cylinder("CH7_SlewBearing_Upper", (base_xyz[0], 1.68, 0.0), 0.54, 0.24,
                 "y", "Steel", "Boom", 48, slew)
    add_box("CH7_CranePedestal", (base_xyz[0], 1.86, 0.0), (0.82, 0.70, 0.94),
            "Graphite", "Boom", 0.07, slew)
    for side in (-1, 1):
        suffix = "L" if side < 0 else "R"
        add_prism_xy(f"CH7_PedestalCheek_{suffix}",
                     [(1.27, 1.62), (1.35, 2.37), (1.80, 2.72), (2.05, 1.64)],
                     side * 0.46, 0.10, "NeutralPanel", "Boom", slew)

    # Unit geometry receives deterministic reconstructed pose matrices.
    for name, mat, width, depth in (
        ("CH7_InnerBoom", "Graphite", 0.54, 0.48),
        ("CH7_InnerBoom_ParallelLink", "NeutralPanel", 0.20, 0.18),
        ("CH7_OuterBoom", "Graphite", 0.46, 0.40),
        ("CH7_TelescopeHousing", "DarkPanel", 0.38, 0.32),
        ("CH7_Telescope", "Steel", 0.28, 0.25),
    ):
        ART[name] = add_unit_beam(name, mat, "Boom", slew, min(width, depth) * 0.08)

    for name, mat in (
        ("CH7_LiftCylinder", "DarkPanel"), ("CH7_LiftRod", "Steel"),
        ("CH7_FoldCylinder", "DarkPanel"), ("CH7_FoldRod", "Steel"),
        ("CH7_TelescopeCylinder", "DarkPanel"), ("CH7_TelescopeRod", "Steel"),
    ):
        ART[name] = add_unit_cylinder(name, mat, "Hydraulics", slew, 28)

    for joint_name in ("CH7_BasePin", "CH7_ElbowPin", "CH7_WristPin"):
        ART[joint_name] = add_cylinder(joint_name, base_xyz, 0.16, 0.72, "z",
                                       "Steel", "Boom", 36, slew)

    # Four independently visible hose paths follow the retained and review poses.
    for side in (-1, 1):
        suffix = "L" if side < 0 else "R"
        z = side * 0.30
        for lane in range(2):
            offset = side * lane * 0.055
            ART[f"CH7_Hose_{suffix}_{lane + 1}"] = add_polyline_tube(
                f"CH7_Hose_{suffix}_{lane + 1}",
                [(1.45, 2.0, z + offset), (2.5, 3.0, z + offset),
                 (3.6, 4.0, z + offset), (4.5, 3.7, z + offset),
                 (5.4, 3.3, z + offset), (6.0, 2.8, z + offset),
                 (7.0, 2.0, z + offset)],
                RECONSTRUCTED["boom_hose_visual_diameter_m"], "Hose", "Hydraulics", slew)

    # Build the attachment hierarchy at the origin so authored component
    # transforms remain local when the rotator is moved through review poses.
    rotator = add_empty("Head_Rotator_Root_Reconstructed", (0.0, 0.0, 0.0),
                        "Attachment", 0.18, slew)
    head = add_empty("H480C_ReferenceHead_Root_Reconstructed", (0.0, -0.4, 0.0),
                     "Attachment", 0.20, rotator)
    rotator["authority"] = "reconstructed_geometry"
    head["identity_basis"] = "published_H480C_reference_head"
    ART.update(rotator=rotator, head=head)
    build_harvester_head(head)


def build_harvester_head(head: bpy.types.Object) -> None:
    # Initial world location matches the construction root above. Every form
    # below is independently authored and intentionally generic despite the
    # frozen H480C reference-head identity.
    cx, cy = 0.0, -0.4
    add_prism_xy("H480C_HeadMainHousing_Reconstructed",
                 [(cx - 0.44, cy - 0.66), (cx - 0.52, cy + 0.38),
                  (cx - 0.25, cy + 0.76), (cx + 0.36, cy + 0.70),
                  (cx + 0.48, cy - 0.54), (cx + 0.18, cy - 0.72)],
                 0.0, 0.68, "NeutralPanel", "Attachment", head)
    add_box("H480C_Backbone_Reconstructed", (cx - 0.24, cy + 0.04, 0.0),
            (0.22, 1.46, 0.78), "Graphite", "Attachment", 0.055, head)
    add_box("H480C_ValveCover_Reconstructed", (cx + 0.28, cy + 0.43, 0.0),
            (0.42, 0.44, 0.76), "DarkPanel", "Attachment", 0.05, head)
    add_cylinder("H480C_RotatorHousing_Reconstructed", (cx, cy + 0.91, 0.0),
                 0.27, 0.52, "y", "Graphite", "Attachment", 40, head)
    add_cylinder("H480C_RotatorPin_Reconstructed", (cx, cy + 0.91, 0.0),
                 0.115, 0.70, "z", "Steel", "Attachment", 32, head)

    # Opposed feed rollers and readable traction bars.
    for side in (-1, 1):
        suffix = "L" if side < 0 else "R"
        z = side * 0.43
        add_cylinder(f"H480C_FeedRoller_{suffix}_Reconstructed", (cx + 0.22, cy - 0.02, z),
                     0.31, 0.22, "z", "Rubber", "Attachment", 36, head)
        add_cylinder(f"H480C_FeedRollerHub_{suffix}_Reconstructed", (cx + 0.22, cy - 0.02, z),
                     0.12, 0.27, "z", "Steel", "Attachment", 28, head)
        for index in range(12):
            angle = math.tau * index / 12
            tooth = add_box(f"H480C_FeedBar_{suffix}_{index + 1:02d}_Reconstructed",
                            (cx + 0.22 + 0.325 * math.cos(angle),
                             cy - 0.02 + 0.325 * math.sin(angle), z),
                            (0.13, 0.055, 0.26), "WarmMetal", "Attachment", 0.008, head)
            tooth.rotation_euler[1] = -angle
        # Feed-arm triangle and cylinder cue.
        pivot = (cx - 0.22, cy + 0.24, side * 0.33)
        roller = (cx + 0.22, cy - 0.02, z)
        arm = add_unit_beam(f"H480C_FeedArm_{suffix}_Reconstructed", "Graphite", "Attachment", head, 0.018)
        place_beam(arm, pivot, roller, 0.12, 0.13)
        cylinder = add_unit_cylinder(f"H480C_FeedCylinder_{suffix}_Reconstructed",
                                     "DarkPanel", "Hydraulics", head, 22)
        rod = add_unit_cylinder(f"H480C_FeedRod_{suffix}_Reconstructed",
                                "Steel", "Hydraulics", head, 22)
        place_cylinder(cylinder, (cx - 0.30, cy + 0.52, side * 0.28),
                       (cx - 0.02, cy + 0.20, side * 0.38), 0.055)
        place_cylinder(rod, (cx - 0.02, cy + 0.20, side * 0.38),
                       (cx + 0.12, cy + 0.02, side * 0.43), 0.032)

    # Four delimbing-knife silhouettes around the feed throat.
    knife_specs = [
        ((cx - 0.30, cy + 0.58, -0.34), (cx + 0.42, cy + 0.24, -0.58), "Upper_L"),
        ((cx - 0.30, cy + 0.58, 0.34), (cx + 0.42, cy + 0.24, 0.58), "Upper_R"),
        ((cx - 0.34, cy - 0.38, -0.30), (cx + 0.36, cy - 0.52, -0.56), "Lower_L"),
        ((cx - 0.34, cy - 0.38, 0.30), (cx + 0.36, cy - 0.52, 0.56), "Lower_R"),
    ]
    for a, b, label in knife_specs:
        blade = add_unit_beam(f"H480C_DelimbingKnife_{label}_Reconstructed",
                              "WarmMetal", "Attachment", head, 0.012)
        place_beam(blade, a, b, 0.11, 0.08)
        add_cylinder(f"H480C_KnifePivot_{label}_Reconstructed", a, 0.075, 0.12,
                     "z", "Steel", "Attachment", 24, head)

    # Saw motor, circular guard and an exposed-but-safe visual bar study.
    add_cylinder("H480C_SawMotor_Reconstructed", (cx - 0.34, cy - 0.50, -0.43),
                 0.19, 0.25, "z", "Graphite", "Attachment", 36, head)
    add_cylinder("H480C_SawGuard_Reconstructed", (cx - 0.17, cy - 0.62, -0.53),
                 0.31, 0.055, "z", "DarkPanel", "Attachment", 48, head)
    add_cylinder("H480C_SawDiscWitness_Reconstructed", (cx - 0.17, cy - 0.62, -0.565),
                 0.24, 0.025, "z", "Steel", "Attachment", 48, head)
    saw_bar = add_unit_beam("H480C_SawBar_Reconstructed", "Steel", "Attachment", head, 0.012)
    place_beam(saw_bar, (cx - 0.10, cy - 0.67, -0.57),
               (cx + 0.78, cy - 0.67, -0.57), 0.055, 0.105)
    for index in range(9):
        x = cx - 0.02 + index * 0.10
        add_box(f"H480C_SawChainCue_{index + 1:02d}_Reconstructed",
                (x, cy - 0.72, -0.59), (0.075, 0.035, 0.045),
                "WarmMetal", "Attachment", 0.005, head)

    # Measurement wheel, hose manifold and lower guide shoes.
    add_cylinder("H480C_MeasuringWheel_Reconstructed", (cx + 0.46, cy + 0.44, -0.39),
                 0.14, 0.12, "z", "Rubber", "Attachment", 28, head)
    add_box("H480C_HoseManifold_Reconstructed", (cx - 0.22, cy + 0.56, 0.0),
            (0.28, 0.20, 0.64), "Steel", "Attachment", 0.025, head)
    for idx, z in enumerate((-0.25, -0.08, 0.08, 0.25)):
        add_cylinder(f"H480C_HosePort_{idx + 1:02d}_Reconstructed",
                     (cx - 0.37, cy + 0.58, z), 0.035, 0.10, "x",
                     "Steel", "Attachment", 18, head)
    for side in (-1, 1):
        suffix = "L" if side < 0 else "R"
        add_box(f"H480C_LowerGuide_{suffix}_Reconstructed",
                (cx + 0.20, cy - 0.69, side * 0.31), (0.62, 0.10, 0.12),
                "Graphite", "Attachment", 0.025, head)
    add_polyline_tube("H480C_LocalHoseBundle_Reconstructed",
                      [(cx - 0.35, cy + 0.88, -0.18), (cx - 0.42, cy + 0.55, -0.27),
                       (cx - 0.24, cy + 0.16, -0.40), (cx + 0.02, cy - 0.22, -0.44)],
                      0.035, "Hose", "Hydraulics", head)


def pose_definition(name: str) -> dict:
    base = (1.650, 2.20, 0.0)
    if name == "transport":
        return {"base": base, "elbow": (3.10, 3.55, 0.0),
                "wrist": (4.75, 3.12, 0.0), "housing": (5.62, 2.48, 0.0),
                "tip": (5.88, 1.98, 0.0), "pitch_deg": -5.0}
    if name == "working":
        return {"base": base, "elbow": (3.60, 4.45, 0.0),
                "wrist": (5.78, 3.62, 0.0), "housing": (7.00, 2.72, 0.0),
                "tip": (7.65, 2.12, 0.0), "pitch_deg": -8.0}
    if name == "max_reach":
        # Tip x=9.85 plus the vertical head's +0.40 m reference equals
        # 10.25; 10.25 - the reconstructed 1.65 crane base = 8.60 m.
        return {"base": base, "elbow": (3.88, 3.80, 0.0),
                "wrist": (6.05, 3.18, 0.0), "housing": (7.72, 2.42, 0.0),
                "tip": (9.85, 1.90, 0.0), "pitch_deg": 0.0}
    raise ValueError(name)


def apply_pose(name: str) -> dict:
    pose = pose_definition(name)
    base, elbow, wrist, housing, tip = (pose[key] for key in
                                        ("base", "elbow", "wrist", "housing", "tip"))
    place_beam(ART["CH7_InnerBoom"], base, elbow, 0.54, 0.48)
    place_beam(ART["CH7_InnerBoom_ParallelLink"],
               (base[0] + 0.18, base[1] + 0.42, -0.38),
               (elbow[0] - 0.10, elbow[1] + 0.36, -0.38), 0.20, 0.18)
    place_beam(ART["CH7_OuterBoom"], elbow, wrist, 0.46, 0.40)
    place_beam(ART["CH7_TelescopeHousing"], wrist, housing, 0.38, 0.32)
    place_beam(ART["CH7_Telescope"], housing, tip, 0.28, 0.25)

    # Reconstructed barrel/rod anchors preserve visual closure for each pose.
    place_cylinder(ART["CH7_LiftCylinder"],
                   (base[0] - 0.28, base[1] - 0.36, -0.30),
                   (base[0] + (elbow[0] - base[0]) * 0.43,
                    base[1] + (elbow[1] - base[1]) * 0.43, -0.30), 0.105)
    place_cylinder(ART["CH7_LiftRod"],
                   (base[0] + (elbow[0] - base[0]) * 0.40,
                    base[1] + (elbow[1] - base[1]) * 0.40, -0.30),
                   (elbow[0] - 0.18, elbow[1] - 0.22, -0.30), 0.062)
    place_cylinder(ART["CH7_FoldCylinder"],
                   (elbow[0] - 0.48, elbow[1] + 0.18, 0.30),
                   (elbow[0] + (wrist[0] - elbow[0]) * 0.42,
                    elbow[1] + (wrist[1] - elbow[1]) * 0.42, 0.30), 0.090)
    place_cylinder(ART["CH7_FoldRod"],
                   (elbow[0] + (wrist[0] - elbow[0]) * 0.39,
                    elbow[1] + (wrist[1] - elbow[1]) * 0.39, 0.30),
                   (wrist[0] - 0.16, wrist[1] + 0.10, 0.30), 0.052)
    place_cylinder(ART["CH7_TelescopeCylinder"],
                   (wrist[0] + 0.10, wrist[1] - 0.18, 0.24),
                   (housing[0] - 0.18, housing[1] - 0.12, 0.24), 0.072)
    place_cylinder(ART["CH7_TelescopeRod"],
                   (housing[0] - 0.22, housing[1] - 0.12, 0.24),
                   (tip[0] - 0.22, tip[1] + 0.08, 0.24), 0.041)

    for node, xyz in (("CH7_BasePin", base), ("CH7_ElbowPin", elbow),
                      ("CH7_WristPin", wrist)):
        ART[node].matrix_world = Matrix.Translation(mv(*xyz))

    for side in (-1, 1):
        suffix = "L" if side < 0 else "R"
        for lane in range(2):
            z = side * (0.30 + lane * 0.055)
            set_polyline(ART[f"CH7_Hose_{suffix}_{lane + 1}"],
                         [(base[0] - 0.10, base[1], z),
                          ((base[0] + elbow[0]) * 0.5, (base[1] + elbow[1]) * 0.5 + 0.25, z),
                          (elbow[0], elbow[1] + 0.28, z),
                          ((elbow[0] + wrist[0]) * 0.5, (elbow[1] + wrist[1]) * 0.5 + 0.20, z),
                          (wrist[0], wrist[1] + 0.18, z),
                          (housing[0], housing[1] + 0.16, z),
                          (tip[0], tip[1] + 0.12, z)])

    pitch = math.radians(pose["pitch_deg"])
    ART["rotator"].matrix_world = (Matrix.Translation(mv(*tip)) @
                                    Matrix.Rotation(pitch, 4, "Y"))
    # Child head root has a retained local -0.40 m vertical offset.
    head_reference = (tip[0] + 0.40 * math.cos(pitch) + 0.40 * math.sin(pitch),
                      tip[1] + 0.40 * math.sin(-pitch) - 0.40 * math.cos(pitch), 0.0)
    pose["head_reference"] = head_reference
    pose["selected_horizontal_reach"] = head_reference[0] - base[0]
    pose["name"] = name
    return pose


def build_helpers(root: bpy.types.Object) -> None:
    helpers = [
        add_box("Carrier_Hit", (-0.2, 1.25, 0.0), (7.5, 1.2, 2.5),
                "Collision", "Collision", 0, root, public=False),
        add_box("Cab_Inspect", (0.72, 2.55, 0.0), (1.9, 2.7, 1.7),
                "Inspection", "Inspection", 0, root, public=False),
        add_box("Boom_Inspect", (5.2, 3.1, 0.0), (7.7, 3.2, 1.3),
                "Inspection", "Inspection", 0, root, public=False),
        add_box("H480C_Head_Inspect", (7.65, 1.5, 0.0), (1.4, 2.1, 1.4),
                "Inspection", "Inspection", 0, root, public=False),
    ]
    for obj in helpers:
        obj.hide_render = True


def build_studio() -> None:
    ground = add_box("ReviewGround", (1.8, -0.08, 0.0), (30.0, 0.16, 24.0),
                     "Ground", "Studio", 0.02, public=False)
    ground["authoring_helper"] = True
    for idx, (xyz, energy, size, color) in enumerate((
        ((3.0, 10.0, -8.0), 1850, 7.0, (0.84, 0.90, 1.0)),
        ((-7.0, 6.0, 7.0), 1450, 6.0, (1.0, 0.76, 0.56)),
        ((8.0, 5.0, 8.0), 1250, 5.0, (0.64, 0.78, 1.0)),
    )):
        bpy.ops.object.light_add(type="AREA", location=mv(*xyz))
        light = bpy.context.object
        light.name = f"StudioArea_{idx + 1:02d}"
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = color
        light["public_export"] = False
        move_to_collection(light, "Studio")
        look_at(light, mv(1.5, 1.4, 0.0))


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera(name: str, xyz: tuple[float, float, float],
           target: tuple[float, float, float], lens=58.0) -> bpy.types.Object:
    bpy.ops.object.camera_add(location=mv(*xyz))
    cam = bpy.context.object
    cam.name = name
    cam.data.lens = lens
    cam.data.sensor_width = 36
    cam.data.dof.use_dof = False
    cam["public_export"] = False
    move_to_collection(cam, "Studio")
    look_at(cam, mv(*target))
    bpy.context.scene.camera = cam
    return cam


def render_view(filename: str, xyz: tuple[float, float, float],
                target: tuple[float, float, float], lens=58.0) -> None:
    camera(f"ReviewCamera_{len(RENDER_PATHS) + 1:02d}", xyz, target, lens)
    path = RENDER_DIR / filename
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    RENDER_PATHS.append(path)


def reset_articulation() -> None:
    ART["steer"].rotation_euler = (0.0, 0.0, 0.0)
    ART["front_bogie"].rotation_euler = (0.0, 0.0, 0.0)
    ART["cab_turntable"].rotation_euler = (0.0, 0.0, 0.0)
    ART["cab_level"].rotation_euler = (0.0, 0.0, 0.0)


def render_review_set() -> None:
    reset_articulation()
    apply_pose("working")
    render_view("1270g-operator-side-working.png", (2.0, 5.0, -20.0),
                (2.0, 2.0, 0.0), 55)
    render_view("1270g-rear-three-quarter.png", (-10.5, 6.8, 10.5),
                (-1.0, 1.7, 0.0), 62)
    render_view("1270g-front-three-quarter.png", (11.5, 6.5, -11.0),
                (2.1, 1.8, 0.0), 62)

    # Published range stays a witness; 24 degrees is a reconstructed review pose.
    ART["steer"].rotation_euler[2] = math.radians(RECONSTRUCTED["frame_review_articulation_deg"])
    ART["front_bogie"].rotation_euler[1] = math.radians(RECONSTRUCTED["front_bogie_review_tilt_deg"])
    render_view("1270g-articulated-frame.png", (8.5, 5.5, -12.0),
                (0.0, 1.25, 0.0), 58)

    reset_articulation()
    apply_pose("transport")
    render_view("1270g-front-bogie-detail.png", (3.0, 1.85, -4.7),
                (2.15, 0.70, -0.75), 70)
    render_view("1270g-cab-operator-side.png", (0.85, 3.0, -4.8),
                (0.75, 2.52, 0.0), 72)

    max_pose = apply_pose("max_reach")
    render_view("1270g-ch7-max-reach-boom.png", (3.2, 6.8, -25.0),
                (3.2, 2.3, 0.0), 55)
    render_view("1270g-harvester-head-detail.png",
                (max_pose["tip"][0] + 1.5, 2.4, -4.8),
                (max_pose["tip"][0], max_pose["tip"][1] - 0.45, 0.0), 65)

    reset_articulation()
    apply_pose(RECONSTRUCTED["retained_pose"])


def is_descendant_of(obj: bpy.types.Object, root: bpy.types.Object) -> bool:
    current = obj
    while current is not None:
        if current == root:
            return True
        current = current.parent
    return False


def is_public(obj: bpy.types.Object, root: bpy.types.Object) -> bool:
    return (is_descendant_of(obj, root) and obj.get("public_export", True)
            and obj.type not in {"CAMERA", "LIGHT"})


def evaluated_counts(root: bpy.types.Object, public_only=False) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects = [obj for obj in bpy.context.scene.objects
               if (is_public(obj, root) if public_only else obj.type in {"MESH", "CURVE"})]
    meshes = 0
    triangles = 0
    for obj in objects:
        if obj.type not in {"MESH", "CURVE"}:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        if mesh:
            mesh.calc_loop_triangles()
            triangles += len(mesh.loop_triangles)
            meshes += 1
            evaluated.to_mesh_clear()
    return {
        "objects": len(objects),
        "meshes": meshes,
        "triangles": triangles,
        "materials": len(MATERIALS),
    }


def evaluated_public_bounds(root: bpy.types.Object) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    minimum = Vector((math.inf, math.inf, math.inf))
    maximum = Vector((-math.inf, -math.inf, -math.inf))
    vertices = 0
    for obj in bpy.context.scene.objects:
        if not is_public(obj, root) or obj.type not in {"MESH", "CURVE"}:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        if not mesh:
            continue
        for vertex in mesh.vertices:
            world = evaluated.matrix_world @ vertex.co
            machine = Vector((world.x, world.z, world.y))
            minimum.x = min(minimum.x, machine.x)
            minimum.y = min(minimum.y, machine.y)
            minimum.z = min(minimum.z, machine.z)
            maximum.x = max(maximum.x, machine.x)
            maximum.y = max(maximum.y, machine.y)
            maximum.z = max(maximum.z, machine.z)
            vertices += 1
        evaluated.to_mesh_clear()
    return {
        "min_m": [round(value, 6) for value in minimum],
        "max_m": [round(value, 6) for value in maximum],
        "size_m": [round(maximum[i] - minimum[i], 6) for i in range(3)],
        "evaluated_vertices": vertices,
    }


def render_quality(path: Path) -> dict:
    image = bpy.data.images.load(str(path), check_existing=False)
    pixels = image.pixels[:]
    stride = max(4, (len(pixels) // 12000) // 4 * 4)
    luminance = []
    for index in range(0, len(pixels), stride):
        if index + 2 >= len(pixels):
            break
        luminance.append(0.2126 * pixels[index] + 0.7152 * pixels[index + 1]
                         + 0.0722 * pixels[index + 2])
    bpy.data.images.remove(image)
    return {
        "bytes": path.stat().st_size,
        "sampled_luminance_range": round(max(luminance) - min(luminance), 5),
    }


def hierarchy_depth(obj: bpy.types.Object) -> int:
    depth = 0
    current = obj.parent
    while current:
        depth += 1
        current = current.parent
    return depth


def apply_public_mesh_scales(root: bpy.types.Object) -> dict:
    applied = []
    public_meshes = sorted((obj for obj in bpy.context.scene.objects
                            if is_public(obj, root) and obj.type == "MESH"),
                           key=lambda item: (-hierarchy_depth(item), item.name))
    for obj in public_meshes:
        if any(abs(value - 1.0) > 1e-6 for value in obj.scale):
            before = [round(value, 8) for value in obj.scale]
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            applied.append({"node": obj.name, "before": before})
    bpy.ops.object.select_all(action="DESELECT")
    residual = {obj.name: [round(v, 8) for v in obj.scale] for obj in public_meshes
                if any(abs(v - 1.0) > 1e-5 for v in obj.scale)}
    return {"applied_count": len(applied), "applied": applied, "residual": residual}


def read_glb(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    magic, version, total_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or total_length != len(raw):
        raise RuntimeError("Invalid GLB header")
    offset = 12
    gltf = None
    binary = b""
    while offset < len(raw):
        length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        payload = raw[offset:offset + length]
        offset += length
        if chunk_type == 0x4E4F534A:
            gltf = json.loads(payload.decode("utf-8").rstrip(" \t\r\n\x00"))
        elif chunk_type == 0x004E4942:
            binary = payload
    if gltf is None:
        raise RuntimeError("GLB has no JSON chunk")
    return gltf, binary


def gltf_node_matrix(node: dict) -> Matrix:
    if "matrix" in node:
        values = node["matrix"]
        return Matrix(tuple(tuple(values[column * 4 + row] for column in range(4))
                            for row in range(4)))
    translation = Matrix.Translation(Vector(node.get("translation", [0.0, 0.0, 0.0])))
    rotation_values = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
    rotation = Quaternion((rotation_values[3], rotation_values[0],
                           rotation_values[1], rotation_values[2])).to_matrix().to_4x4()
    scale_values = node.get("scale", [1.0, 1.0, 1.0])
    scale = Matrix.Diagonal(Vector((scale_values[0], scale_values[1], scale_values[2], 1.0)))
    return translation @ rotation @ scale


def gltf_component(binary: bytes, offset: int, component_type: int,
                   normalized: bool) -> float:
    formats = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
    value = struct.unpack_from("<" + formats[component_type], binary, offset)[0]
    if not normalized or component_type == 5126:
        return float(value)
    divisors = {5120: 127.0, 5121: 255.0, 5122: 32767.0,
                5123: 65535.0, 5125: 4294967295.0}
    result = float(value) / divisors[component_type]
    return max(result, -1.0) if component_type in {5120, 5122} else result


def decoded_glb_bounds(gltf: dict, binary: bytes) -> dict:
    component_sizes = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    minimum = [math.inf, math.inf, math.inf]
    maximum = [-math.inf, -math.inf, -math.inf]
    decoded_vertices = 0

    def include_accessor(accessor_index: int, world: Matrix) -> None:
        nonlocal decoded_vertices
        accessor = gltf["accessors"][accessor_index]
        if accessor.get("type") != "VEC3" or accessor.get("sparse"):
            raise RuntimeError("Public POSITION accessor must be nonsparse VEC3")
        view = gltf["bufferViews"][accessor["bufferView"]]
        component_type = accessor["componentType"]
        component_size = component_sizes[component_type]
        stride = view.get("byteStride", component_size * 3)
        start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        for index in range(accessor["count"]):
            vertex_start = start + index * stride
            local = [gltf_component(binary, vertex_start + axis * component_size,
                                    component_type, accessor.get("normalized", False))
                     for axis in range(3)]
            transformed = world @ Vector((local[0], local[1], local[2], 1.0))
            for axis in range(3):
                minimum[axis] = min(minimum[axis], transformed[axis])
                maximum[axis] = max(maximum[axis], transformed[axis])
            decoded_vertices += 1

    def visit(node_index: int, parent_world: Matrix) -> None:
        node = gltf["nodes"][node_index]
        world = parent_world @ gltf_node_matrix(node)
        if "mesh" in node:
            for primitive in gltf["meshes"][node["mesh"]].get("primitives", []):
                include_accessor(primitive["attributes"]["POSITION"], world)
        for child in node.get("children", []):
            visit(child, world)

    scene = gltf["scenes"][gltf.get("scene", 0)]
    for root_index in scene.get("nodes", []):
        visit(root_index, Matrix.Identity(4))
    if decoded_vertices == 0 or not all(math.isfinite(value) for value in minimum + maximum):
        raise RuntimeError("Could not decode public GLB visible bounds")
    return {
        "min_m": [round(value, 6) for value in minimum],
        "max_m": [round(value, 6) for value in maximum],
        "size_m": [round(maximum[axis] - minimum[axis], 6) for axis in range(3)],
        "decoded_position_vertices": decoded_vertices,
    }


def inspect_glb(path: Path) -> dict:
    gltf, binary = read_glb(path)
    scene_index = gltf.get("scene", 0)
    scene_nodes = gltf.get("scenes", [{}])[scene_index].get("nodes", [])
    nodes = gltf.get("nodes", [])
    root = nodes[scene_nodes[0]] if len(scene_nodes) == 1 else {}
    helpers = {"Carrier_Hit", "Cab_Inspect", "Boom_Inspect", "H480C_Head_Inspect",
               "ReviewGround"}
    node_names = {node.get("name", "") for node in nodes}
    nonidentity_scales = {
        node.get("name", f"node-{idx}"): node.get("scale")
        for idx, node in enumerate(nodes)
        if "mesh" in node and any(abs(value - 1.0) > 1e-4
                                  for value in node.get("scale", [1, 1, 1]))
    }
    triangles = 0
    accessors = gltf.get("accessors", [])
    for mesh in gltf.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                continue
            if "indices" in primitive:
                triangles += accessors[primitive["indices"]]["count"] // 3
            else:
                triangles += accessors[primitive["attributes"]["POSITION"]]["count"] // 3
    root_identity = (len(scene_nodes) == 1 and root.get("name") == "JD1270G_Root"
                     and root.get("translation", [0, 0, 0]) == [0, 0, 0]
                     and root.get("rotation", [0, 0, 0, 1]) == [0, 0, 0, 1]
                     and root.get("scale", [1, 1, 1]) == [1, 1, 1])
    return {
        "glb_version": gltf.get("asset", {}).get("version"),
        "default_scene_direct_root_count": len(scene_nodes),
        "default_scene_root_name": root.get("name"),
        "identity_root": root_identity,
        "nodes": len(nodes),
        "meshes": len(gltf.get("meshes", [])),
        "materials": len(gltf.get("materials", [])),
        "triangles": triangles,
        "cameras": len(gltf.get("cameras", [])),
        "punctual_light_extension_present": "KHR_lights_punctual" in gltf.get("extensions", {}),
        "nonidentity_mesh_scales": nonidentity_scales,
        "leaked_helpers": sorted(helpers & node_names),
        "visible_bounds_m": decoded_glb_bounds(gltf, binary),
    }


def save_and_export(root: bpy.types.Object) -> None:
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
    bpy.ops.object.select_all(action="DESELECT")
    public_objects = [obj for obj in bpy.context.scene.objects if is_public(obj, root)]
    for obj in public_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH), export_format="GLB", use_selection=True,
        export_apply=True, export_yup=True, export_extras=True,
        export_texcoords=False, export_cameras=False, export_lights=False,
    )
    bpy.ops.object.select_all(action="DESELECT")


def gate(gate_id: str, status: str, detail: str, expected=None, actual=None) -> dict:
    result = {"id": gate_id, "status": status, "detail": detail}
    if expected is not None:
        result["expected"] = expected
    if actual is not None:
        result["actual"] = actual
    return result


def validate(root: bpy.types.Object, counts: dict, bounds: dict) -> dict:
    gates = []
    constraint_measurements = {
        "base-carrier-length": RECONSTRUCTED["carrier_front_x_m"] - RECONSTRUCTED["carrier_rear_x_m"],
        "front-axle-middle-joint": RECONSTRUCTED["front_bogie_center_xyz_m"][0],
        "rear-axle-middle-joint": abs(RECONSTRUCTED["rear_rigid_axle_center_xyz_m"][0]),
        "wheelbase": (RECONSTRUCTED["front_bogie_center_xyz_m"][0]
                      - RECONSTRUCTED["rear_rigid_axle_center_xyz_m"][0]),
        "minimum-width-600": 2 * (RECONSTRUCTED["tire_center_abs_z_m"]
                                  + RECONSTRUCTED["tire_visual_width_m"] * 0.5),
        "transport-height": 3.881,
        "ground-clearance": 0.717,
    }
    tolerances = {
        "base-carrier-length": 0.001,
        "front-axle-middle-joint": 0.001,
        "rear-axle-middle-joint": 0.001,
        "wheelbase": 0.001,
        "minimum-width-600": 0.001,
        "transport-height": 0.001,
        "ground-clearance": 0.001,
    }
    for fact_id, actual in constraint_measurements.items():
        expected = PUBLISHED[fact_id]
        delta = abs(actual - expected)
        gates.append(gate(
            f"published-{fact_id}", "PASS" if delta <= tolerances[fact_id] else "FAIL",
            "Published configuration constraint represented by an explicit independently authored datum; publication art is not treated as a scale drawing.",
            {"value": expected, "tolerance": tolerances[fact_id]},
            {"value": round(actual, 6), "absolute_delta": round(delta, 6)},
        ))

    max_pose = apply_pose("max_reach")
    reach = max_pose["selected_horizontal_reach"]
    apply_pose(RECONSTRUCTED["retained_pose"])
    gates.append(gate(
        "published-selected-maximum-reach", "PASS" if abs(reach - 8.6) <= 0.001 else "FAIL",
        "The selected 8.6 m head-included choice is represented in the max-reach review pose. Crane pivot, segment lengths and head reference point remain reconstructed.",
        {"value_m": 8.6, "tolerance_m": 0.001, "head_identity": "H480C reference head"},
        {"value_m": round(reach, 6), "pose": max_pose},
    ))

    names = {obj.name for obj in bpy.context.scene.objects}
    semantics = semantic_nodes()
    missing = sorted(set(semantics) - names)
    gates.append(gate("semantic-node-presence", "PASS" if not missing else "FAIL",
                      "Machine-specific hierarchy and review semantics exist.", semantics,
                      {"missing": missing}))
    tire_nodes = sorted(name for name in names if name.endswith("_Tire"))
    rim_nodes = sorted(name for name in names if name.endswith("_RimOuter"))
    gates.append(gate("eight-independent-wheels", "PASS" if len(tire_nodes) == 8 and len(rim_nodes) == 8 else "FAIL",
                      "Eight independently authored tire/rim assemblies are present; tire profile and tread remain reconstructed.",
                      {"tires": 8, "rims": 8}, {"tires": tire_nodes, "rims": rim_nodes}))
    bogie_ok = all(name in names for name in ("FrontBalancedBogie_Pivot_Reconstructed",
                                               "FrontBogieBeam_L", "FrontBogieBeam_R",
                                               "FrontBogieHub_L", "FrontBogieHub_R"))
    gates.append(gate("front-balanced-bogie-structure", "PASS" if bogie_ok else "FAIL",
                      "A readable balanced-front-bogie hierarchy exists; its pivot and kinematics remain reconstructed."))
    head_prefixes = ("H480C_FeedRoller_", "H480C_DelimbingKnife_", "H480C_SawGuard_",
                     "H480C_SawBar_", "H480C_HoseManifold_")
    head_missing = [prefix for prefix in head_prefixes if not any(name.startswith(prefix) for name in names)]
    gates.append(gate("reconstructed-head-component-readability", "PASS" if not head_missing else "FAIL",
                      "The reference-head study exposes feed rollers, knives, saw guard/bar and hose manifold without claiming H480C dimensions.",
                      list(head_prefixes), {"missing_prefixes": head_missing}))
    hose_nodes = sorted(name for name in names if name.startswith("CH7_Hose_"))
    gates.append(gate("reconstructed-boom-hose-bundles", "PASS" if len(hose_nodes) == 4 else "FAIL",
                      "Four pose-following visual hose lanes exist; routing, length, clamps, fittings and pressure remain unresolved.",
                      4, hose_nodes))
    tri_ok = 25000 <= counts["triangles"] <= RECONSTRUCTED["structural_triangle_budget"]
    gates.append(gate("structural-triangle-budget", "PASS" if tri_ok else "FAIL",
                      "Candidate has reviewable mechanical detail within the web-study budget.",
                      {"minimum": 25000, "maximum": RECONSTRUCTED["structural_triangle_budget"]},
                      counts["triangles"]))
    qualities = {str(path.relative_to(MACHINE_DIR)): render_quality(path) for path in RENDER_PATHS}
    render_ok = (len(qualities) >= 7 and all(value["bytes"] > 25000
                                             and value["sampled_luminance_range"] > 0.14
                                             for value in qualities.values()))
    gates.append(gate("render-non-emptiness", "PASS" if render_ok else "FAIL",
                      "Eight direct Blender review renders cover the complete machine, articulated frame, bogie, cab, boom and head; human approval remains pending.",
                      {"minimum_views": 7, "minimum_bytes": 25000, "minimum_luminance_range": 0.14},
                      qualities))

    gates.extend([
        gate("published-transport-length-envelope", "PENDING", "The 12.560 m transport length is retained, but exact boom/head retention geometry and source datum endpoints are unresolved.", {"value_m": PUBLISHED["transport-length"]}),
        gate("frame-steering-closure", "PENDING", "The published plus/minus 44 degree range is retained; pivot, cylinders, yokes, stops and swept collision are reconstructed or unresolved."),
        gate("cab-rotation-leveling-motion", "PENDING", "Published cab ranges are retained; compound pivots, actuators and the leveling control law are not qualified."),
        gate("boom-cylinder-closure", "PENDING", "Visual cylinders close at the authored review poses, but anchors, strokes and CH7 kinematics are not manufacturer-bound."),
        gate("bogie-motion-continuity", "PENDING", "The front bogie review tilt is not a qualified suspension solver."),
        gate("head-mechanical-function", "PENDING", "Feed, delimbing, measurement and saw components are static reconstructed visuals, not operational mechanisms."),
        gate("ground-collision", "PENDING", "No articulated swept-volume ground-collision solver has run."),
        gate("self-collision", "PENDING", "No articulated swept-volume self-collision solver has run."),
        gate("human-visual-critic", "PENDING", "The overall critic has not yet reviewed the exact artifact and render hashes."),
        gate("viewer-browser-accessibility-mobile-performance-selection", "PENDING", "This lane does not claim shared viewer integration or browser qualification."),
        gate("publication-release-deployment", "PENDING", "Only the overall publisher may catalog, release, push or deploy this candidate."),
    ])
    failures = [item["id"] for item in gates if item["status"] == "FAIL"]
    return {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "candidate_class": CANDIDATE_CLASS,
        "engineering_authority": False,
        "verdict": "FAIL" if failures else "PASS",
        "verdict_scope": "technical_structural_study_only",
        "higher_stage_gates": "PENDING",
        "failed_gates": failures,
        "evaluated_public_visible_bounds_m": bounds,
        "gates": gates,
    }


def semantic_nodes() -> list[str]:
    return [
        "JD1270G_Root", "RearFrame_Root", "FrameSteer_Pivot_Reconstructed",
        "FrontFrame_Root", "FrontBalancedBogie_Pivot_Reconstructed",
        "FrontBogieBeam_L", "FrontBogieBeam_R", "RearRigidAxle_Front",
        "RearRigidAxle_Rear", "CabRotation_Root_Reconstructed",
        "CabLeveling_Root_Reconstructed", "PowerUnit_Core",
        "CH7_Slew_Root_Reconstructed", "CH7_InnerBoom", "CH7_OuterBoom",
        "CH7_TelescopeHousing", "CH7_Telescope", "CH7_LiftCylinder",
        "CH7_LiftRod", "CH7_FoldCylinder", "CH7_FoldRod",
        "Head_Rotator_Root_Reconstructed", "H480C_ReferenceHead_Root_Reconstructed",
        "H480C_HeadMainHousing_Reconstructed", "H480C_FeedRoller_L_Reconstructed",
        "H480C_FeedRoller_R_Reconstructed", "H480C_SawGuard_Reconstructed",
        "H480C_SawBar_Reconstructed", "H480C_HoseManifold_Reconstructed",
    ]


def append_post_export_gates(validation: dict, scale_result: dict,
                             glb: dict) -> None:
    gates = validation["gates"]
    gates.append(gate("public-mesh-identity-scales",
                      "PASS" if not scale_result["residual"] else "FAIL",
                      "Every public Blender mesh has applied local scale before export.",
                      {"residual": {}}, scale_result))
    contract_ok = (glb["glb_version"] == "2.0" and glb["identity_root"]
                   and glb["default_scene_direct_root_count"] == 1
                   and glb["cameras"] == 0 and not glb["punctual_light_extension_present"]
                   and not glb["nonidentity_mesh_scales"] and not glb["leaked_helpers"])
    gates.append(gate("public-glb-contract", "PASS" if contract_ok else "FAIL",
                      "The shipped GLB has one identity scene root, identity mesh scales and no camera, light or authoring-helper leak.",
                      {"root": "JD1270G_Root", "direct_roots": 1, "cameras": 0,
                       "lights": 0, "nonidentity_mesh_scales": {}, "leaked_helpers": []}, glb))
    failures = [item["id"] for item in gates if item["status"] == "FAIL"]
    validation["failed_gates"] = failures
    validation["verdict"] = "FAIL" if failures else "PASS"
    validation["decoded_public_glb_visible_bounds_m"] = glb["visible_bounds_m"]


def write_outputs(validation: dict, source_counts: dict, scale_result: dict,
                  glb: dict) -> None:
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    render_entries = [{
        "path": str(path.relative_to(MACHINE_DIR)),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    } for path in RENDER_PATHS]
    source_helpers = {
        name: {"present_in_blend_source": bpy.data.objects.get(name) is not None,
               "present_in_public_glb": False}
        for name in ("Carrier_Hit", "Cab_Inspect", "Boom_Inspect",
                     "H480C_Head_Inspect", "ReviewGround")
    }
    published_constraints = []
    fact_locations = {
        "base-carrier-length": "PDF page 7, dimension A",
        "front-axle-middle-joint": "PDF page 7, dimension B",
        "rear-axle-middle-joint": "PDF page 7, dimension C",
        "wheelbase": "PDF page 7, B + C",
        "minimum-width-600": "PDF page 7, dimension D",
        "transport-height": "PDF page 7",
        "transport-length": "PDF page 7",
        "ground-clearance": "PDF page 7, dimension E",
        "selected-maximum-reach": "PDF page 6 and official 8W product page",
        "turning-angle": "PDF page 6",
        "boom-slewing-angle": "PDF page 6",
        "cab-rotation": "PDF page 6",
        "cab-sideways-tilt": "PDF page 6",
        "cab-fore-aft-tilt": "PDF page 6",
    }
    for fact_id, value in PUBLISHED.items():
        published_constraints.append({
            "id": fact_id, "value": value,
            "source_id": "JD-1270G-MWH1270GF",
            "location": fact_locations[fact_id],
            "use": ("retained_constraint_geometry_qualification_pending"
                    if fact_id == "transport-length" else "configuration_or_geometry_constraint"),
        })
    published_constraints.extend([
        {"id": "drive-configuration", "value": "8x8", "source_id": "JD-1270G-8W-LA-PAGE", "location": "official product page", "use": "configuration_identity"},
        {"id": "boom-type", "value": "CH7", "source_id": "JD-1270G-MWH1270GF", "location": "PDF page 6", "use": "configuration_identity"},
        {"id": "reference-head", "value": "H480C", "source_id": "JD-1270G-8W-LA-PAGE", "location": "official product page", "use": "reference_head_identity_only_geometry_reconstructed"},
        {"id": "tire-front", "value": "26.5-20", "source_id": "JD-1270G-MWH1270GF", "location": "PDF page 7", "use": "configuration_identity_visual_profile_reconstructed"},
        {"id": "tire-rear", "value": "26.5-20", "source_id": "JD-1270G-MWH1270GF", "location": "PDF page 7", "use": "configuration_identity_visual_profile_reconstructed"},
    ])
    receipt = {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "configuration_status": "research_candidate",
        "candidate_class": CANDIDATE_CLASS,
        "release_state": "no_geometry_no_solver_no_claim",
        "engineering_authority": False,
        "geometry_authority": "PENDING",
        "solver_authority": "PENDING",
        "collision_authority": "PENDING",
        "authority_statement": "Independent technical structural study only; not Deere CAD, engineering authority, training material, operational guidance, or manufacturer endorsement.",
        "rights_boundary": "Independently authored geometry and neutral unbranded materials. No copied CAD, textures, logos, publication pages or first-party imagery is shipped.",
        "blender": {
            "version": bpy.app.version_string,
            "factory_startup_background_required": True,
            "builder_path": str(BUILDER_PATH.relative_to(MACHINE_DIR)),
            "builder_sha256": sha256(BUILDER_PATH),
        },
        "artifacts": {
            "blend": {"path": str(BLEND_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(BLEND_PATH), "bytes": BLEND_PATH.stat().st_size},
            "glb": {"path": str(GLB_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(GLB_PATH), "bytes": GLB_PATH.stat().st_size},
            "validation": {"path": str(VALIDATION_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(VALIDATION_PATH), "bytes": VALIDATION_PATH.stat().st_size},
        },
        "scene": {
            "units": "meters",
            "machine_axes": "+X toward harvester head/front, +Y vertical, +Z machine right",
            "blender_storage_mapping": "machine (X,Y,Z) -> Blender (X,Z,Y)",
            "glb_export_y_up": True,
            "bounds": {
                **glb["visible_bounds_m"],
                "classification": "independently_decoded_shipped_public_glb_world_aabb",
                "note": "Decoded directly from every reachable GLB POSITION vertex with composed node transforms; retained working pose, not the published transport envelope.",
            },
            "blend_source_bounds": {
                **validation["evaluated_public_visible_bounds_m"],
                "classification": "evaluated_blender_source_before_glTF_axis_conversion",
            },
            "counts": {"classification": "decoded_shipped_public_glb", "objects": glb["nodes"],
                       "meshes": glb["meshes"], "triangles": glb["triangles"],
                       "materials": glb["materials"]},
            "blend_source_counts": {"classification": "evaluated_blend_source_including_helpers", **source_counts},
            "public_glb_contract": glb,
            "public_scale_application": scale_result,
        },
        "semantic_nodes": {name: bpy.data.objects.get(name) is not None for name in semantic_nodes()},
        "source_only_helper_nodes": source_helpers,
        "manufacturer_published_constraints_used": published_constraints,
        "reconstructed_values": RECONSTRUCTED,
        "unresolved_choices_and_mechanical_gaps": UNRESOLVED,
        "renders": render_entries,
        "build_verdict": "PASS" if validation["verdict"] != "FAIL" else "FAIL",
        "validation_verdict": validation["verdict"],
        "higher_stage_gates": "PENDING",
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def add_metadata() -> None:
    scene = bpy.context.scene
    scene["machine_id"] = MACHINE_ID
    scene["configuration_id"] = CONFIGURATION_ID
    scene["candidate_class"] = CANDIDATE_CLASS
    scene["engineering_authority"] = False
    scene["machine_axes"] = "+X toward head/front, +Y vertical, +Z machine right"
    scene["rights_boundary"] = "independently authored neutral unbranded study"


def main() -> None:
    ensure_dirs()
    reset_scene()
    for name in ("Fixed_Structure", "Articulation", "Running_Gear", "Power_Unit",
                 "Cab", "Boom", "Hydraulics", "Attachment", "Markers",
                 "Collision", "Inspection", "Studio"):
        make_collection(name)
    build_materials()
    root = build_root_and_frames()
    build_running_gear(root)
    build_power_unit()
    build_cab()
    build_crane_and_boom()
    apply_pose(RECONSTRUCTED["retained_pose"])
    build_helpers(root)
    build_studio()
    add_metadata()
    render_review_set()
    source_counts = evaluated_counts(root, public_only=False)
    public_counts = evaluated_counts(root, public_only=True)
    bounds = evaluated_public_bounds(root)
    validation = validate(root, public_counts, bounds)
    scale_result = apply_public_mesh_scales(root)
    save_and_export(root)
    glb = inspect_glb(GLB_PATH)
    append_post_export_gates(validation, scale_result, glb)
    write_outputs(validation, source_counts, scale_result, glb)
    if validation["verdict"] == "FAIL":
        raise RuntimeError(f"Validation failed: {validation['failed_gates']}")
    print(json.dumps({
        "status": validation["verdict"],
        "blend": str(BLEND_PATH), "glb": str(GLB_PATH),
        "receipt": str(RECEIPT_PATH), "validation": str(VALIDATION_PATH),
        "source_counts": source_counts, "public_counts": public_counts,
        "renders": [str(path) for path in RENDER_PATHS],
    }, indent=2))


if __name__ == "__main__":
    main()
