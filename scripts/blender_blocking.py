"""shot-speak blocking previs: a grey-box scene for 1 shot option.

This file runs inside Blender. shot-speak writes the blocking plan on the PLAN
line and saves the result as ``blocking.py``. Run it without a window:

    blender --background --factory-startup --python blocking.py -- --out FOLDER

It builds a floor with a 1 m grid, grey set boxes, faceless grey mannequins and
a camera with the lens, the height, the distance and the move of the option.
It writes 3 camera stills, 1 overhead plan, a short animatic and the scene file.

The grey boxes show framing, lens, camera path and positions only. They do not
show the look, the light, the colour or the identity of a person.
"""

import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

PLAN = None  # shot-speak writes the blocking plan on this line

SHADES = {
    "floor_a": (0.60, 0.61, 0.62, 1), "floor_b": (0.50, 0.51, 0.52, 1), "wall": (0.72, 0.72, 0.70, 1),
    "prop": (0.42, 0.43, 0.45, 1), "dark": (0.16, 0.16, 0.17, 1), "body": (0.36, 0.37, 0.39, 1),
    "nose": (0.95, 0.95, 0.95, 1), "back": (0.08, 0.08, 0.08, 1), "mark": (0.98, 0.85, 0.10, 1),
    "path": (0.95, 0.30, 0.05, 1), "start": (0.10, 0.70, 0.20, 1), "end": (0.85, 0.10, 0.10, 1),
    "walk": (0.10, 0.25, 0.60, 1), "ink": (0.02, 0.02, 0.02, 1), "thrown": (0.96, 0.94, 0.86, 1),
}
PLAN_Z = 6.0  # height of the overhead-plan marks: above every set box


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.environ.get("SHOTSPEAK_PREVIS_OUT", "")
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    if not out:
        raise SystemExit("Give the output folder: -- --out FOLDER")
    return os.path.abspath(out), "--no-animatic" not in argv, "--session" in argv


def material(name):
    key = "ss_" + name
    mat = bpy.data.materials.get(key)
    if mat is None:
        mat = bpy.data.materials.new(key)
        mat.diffuse_color = SHADES[name]
        mat.roughness = 0.9
    return mat


def colour_material(name, rgb):
    key = "ss_id_" + name
    mat = bpy.data.materials.get(key)
    if mat is None:
        mat = bpy.data.materials.new(key)
        mat.diffuse_color = (rgb[0], rgb[1], rgb[2], 1)
    return mat


def new_object(name, mesh, collection, mat=None, parent=None):
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if mat is not None:
        mesh.materials.append(mat)
    if parent is not None:
        obj.parent = parent
    return obj


def box_mesh(name, size, centre=(0, 0, 0)):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(centre), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def cone_mesh(name, r1, r2, height, base_z=0.0, segments=16):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=r1, radius2=r2, depth=height)
    bmesh.ops.translate(bm, vec=Vector((0, 0, base_z + height / 2)), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def sphere_mesh(name, radius, centre):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=radius)
    bmesh.ops.translate(bm, vec=Vector(centre), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    return mesh


def build_floor(collection, half):
    """A floor of 1 m squares in 2 greys: the measurement grid."""
    verts, faces = [], []
    for iy in range(-half, half + 1):
        for ix in range(-half, half + 1):
            verts.append((ix, iy, 0.0))
    row = 2 * half + 1
    for iy in range(2 * half):
        for ix in range(2 * half):
            a = iy * row + ix
            faces.append((a, a + 1, a + row + 1, a + row))
    mesh = bpy.data.meshes.new("floor_grid_1m")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material("floor_a"))
    mesh.materials.append(material("floor_b"))
    for index, poly in enumerate(mesh.polygons):
        poly.material_index = (index // (2 * half) + index % (2 * half)) % 2
    mesh.update()
    obj = bpy.data.objects.new("floor_grid_1m", mesh)
    collection.objects.link(obj)
    return obj


def build_set(collection, items):
    for item in items:
        at = item["at"]
        if item["type"] == "box":
            size = item["size"]
            obj = new_object("set_" + item["name"], box_mesh(item["name"], size, (0, 0, size[2] / 2)), collection,
                             material(item["shade"]))
        else:
            obj = new_object("set_" + item["name"], cone_mesh(item["name"], item["radius"], item["radius"], item["height"]),
                             collection, material(item["shade"]))
        obj.location = at


def build_person(collection, subject):
    """A faceless grey mannequin from primitives, 1.75 m tall. The origin is between the feet. It faces local +X."""
    root = bpy.data.objects.new("person_" + subject["id"], None)
    root.empty_display_size = 0.3
    collection.objects.link(root)
    body, name = material("body"), subject["id"]
    band = colour_material(subject["colour"], subject["rgb"])
    if subject.get("shape") == "animal":  # a four-legged stand-in, 0.72 m tall, about 0.9 m long
        parts = [(cone_mesh(f"{name}_leg_{n}", 0.035, 0.045, 0.36), body, (x, y, 0))
                 for n, (x, y) in enumerate(((0.26, 0.09), (0.26, -0.09), (-0.26, 0.09), (-0.26, -0.09)))]
        parts += [
            (box_mesh(name + "_trunk", (0.70, 0.24, 0.24), (0, 0, 0.47)), body, (0, 0, 0)),
            (box_mesh(name + "_neck", (0.12, 0.12, 0.20), (0.36, 0, 0.58)), body, (0, 0, 0)),
            (sphere_mesh(name + "_head", 0.10, (0.42, 0, 0.62)), body, (0, 0, 0)),
            (box_mesh(name + "_band", (0.14, 0.25, 0.25), (0.05, 0, 0.47)), band, (0, 0, 0)),
            (box_mesh(name + "_nose", (0.09, 0.06, 0.06), (0.54, 0, 0.60)), material("nose"), (0, 0, 0)),
            (box_mesh(name + "_back", (0.16, 0.04, 0.04), (-0.42, 0, 0.56)), material("back"), (0, 0, 0)),
        ]
    else:
        parts = person_parts(name, body, band)
    for mesh, mat, offset in parts:
        obj = new_object(mesh.name, mesh, collection, mat, root)
        obj.location = offset
        obj.hide_render = subject["hidden"]
    place_person(collection, subject, root, name)
    return root


def person_parts(name, body, band):
    return [
        (cone_mesh(name + "_leg_l", 0.07, 0.09, 0.86), body, (0, 0.10, 0)),
        (cone_mesh(name + "_leg_r", 0.07, 0.09, 0.86), body, (0, -0.10, 0)),
        (box_mesh(name + "_hips", (0.22, 0.36, 0.18), (0, 0, 0.92)), body, (0, 0, 0)),
        (box_mesh(name + "_torso", (0.22, 0.40, 0.46), (0, 0, 1.22)), body, (0, 0, 0)),
        (cone_mesh(name + "_arm_l", 0.045, 0.055, 0.62, 0.80), body, (0, 0.255, 0)),
        (cone_mesh(name + "_arm_r", 0.045, 0.055, 0.62, 0.80), body, (0, -0.255, 0)),
        (cone_mesh(name + "_neck", 0.05, 0.05, 0.10, 1.44), body, (0, 0, 0)),
        (sphere_mesh(name + "_head", 0.115, (0, 0, 1.63)), body, (0, 0, 0)),
        (box_mesh(name + "_band", (0.235, 0.415, 0.12), (0, 0, 1.30)), band, (0, 0, 0)),
        (box_mesh(name + "_nose", (0.05, 0.05, 0.05), (0.125, 0, 1.63)), material("nose"), (0, 0, 0)),
        (box_mesh(name + "_back", (0.02, 0.10, 0.40), (-0.115, 0, 1.22)), material("back"), (0, 0, 0)),
    ]


def place_person(collection, subject, root, name):
    root.rotation_euler = (0, 0, math.radians(subject["facing_deg"]))
    root.location = subject["at"]
    if "track" in subject:
        for frame, at in enumerate(subject["track"], start=1):
            root.location = at
            root.keyframe_insert("location", frame=frame)
    # A T mark on the floor at the start position.
    start = subject["track"][0] if "track" in subject else subject["at"]
    mark = new_object("mark_" + name, box_mesh("mark_" + name, (0.08, 0.5, 0.01), (0, 0, 0.006)), collection, material("mark"))
    mark.location = (start[0], start[1], 0)
    stem = new_object("mark_stem_" + name, box_mesh("mark_stem_" + name, (0.3, 0.08, 0.01), (-0.15, 0, 0.006)), collection, material("mark"))
    stem.location = (start[0], start[1], 0)
    stem.rotation_euler = mark.rotation_euler = (0, 0, math.radians(subject["facing_deg"]))


def build_prop(collection, prop):
    """A thrown object from primitives: a bone, a ball, a disc or a stick. One key for each frame."""
    name, shape, mat = "prop_" + prop["id"], prop["shape"], material("thrown")
    root = bpy.data.objects.new(name, None)
    root.empty_display_size = 0.1
    collection.objects.link(root)
    if shape == "bone":  # a bar across the jaws with a knob at each end
        bar = new_object(name + "_bar", cone_mesh(name + "_bar", 0.022, 0.022, 0.24, -0.12, 10), collection, mat, root)
        bar.rotation_euler = (math.radians(90), 0, 0)
        for side in (-1, 1):
            for lift in (-0.022, 0.022):
                new_object(f"{name}_knob_{side}_{lift}", sphere_mesh(name + "_knob", 0.036, (0, side * 0.125, lift)), collection, mat, root)
    elif shape == "disc":
        new_object(name + "_disc", cone_mesh(name + "_disc", 0.13, 0.13, 0.025, -0.012, 24), collection, mat, root)
    elif shape == "stick":
        bar = new_object(name + "_bar", cone_mesh(name + "_bar", 0.015, 0.015, 0.5, -0.25, 8), collection, mat, root)
        bar.rotation_euler = (math.radians(90), 0, 0)
    else:
        new_object(name + "_ball", sphere_mesh(name + "_ball", 0.11, (0, 0, 0)), collection, mat, root)
    for frame, at in enumerate(prop["track"], start=1):
        root.location = at
        root.keyframe_insert("location", frame=frame)
    return root


def basis(pos, aim, roll_deg):
    """The same rule as scripts/previs.py: right, up and forward for a camera sample."""
    forward = (Vector(aim) - Vector(pos)).normalized()
    right = forward.cross(Vector((0, 0, 1)))
    if right.length_squared < 1e-8:
        right = Vector((1, 0, 0))
    right.normalize()
    up = right.cross(forward)
    if roll_deg:
        c, s = math.cos(math.radians(roll_deg)), math.sin(math.radians(roll_deg))
        right, up = right * c + up * s, up * c - right * s
    return right, up, forward


def camera_quaternion(sample):
    right, up, forward = basis(sample[0:3], sample[3:6], sample[7])
    return Matrix((right, up, -forward)).transposed().to_quaternion()


def build_camera(scene, collection, plan):
    data = bpy.data.cameras.new("shot_camera")
    data.sensor_fit = "HORIZONTAL" if plan["resolution"][0] >= plan["resolution"][1] else "VERTICAL"
    data.sensor_width = data.sensor_height = plan["camera"]["sensor_mm"]
    data.clip_start, data.clip_end = 0.03, 600
    cam = bpy.data.objects.new("shot_camera", data)
    collection.objects.link(cam)
    cam.rotation_mode = "QUATERNION"
    samples = plan["camera"]["samples"]
    zooms = len({s[6] for s in samples}) > 1
    previous = None
    for frame, sample in enumerate(samples, start=1):
        quat = camera_quaternion(sample)
        if previous is not None and previous.dot(quat) < 0:
            quat.negate()
        previous = quat
        cam.location = sample[0:3]
        cam.rotation_quaternion = quat
        cam.keyframe_insert("location", frame=frame)
        cam.keyframe_insert("rotation_quaternion", frame=frame)
        data.lens = sample[6]
        if zooms:
            data.keyframe_insert("lens", frame=frame)
    scene.camera = cam
    return cam


def strip(collection, name, a, b, width, shade):
    """A flat strip from a to b at the height of the plan marks."""
    a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
    length = (b - a).length
    if length < 1e-4:
        return None
    obj = new_object(name, box_mesh(name, (length, width, 0.02)), collection, material(shade))
    obj.location = ((a.x + b.x) / 2, (a.y + b.y) / 2, PLAN_Z)
    obj.rotation_euler = (0, 0, math.atan2(b.y - a.y, b.x - a.x))
    return obj


def wedge(collection, name, at, toward, size, shade):
    """A flat triangle at ``at`` that points at ``toward``."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(size, 0, 0), (-size * 0.6, size * 0.6, 0), (-size * 0.6, -size * 0.6, 0)], [], [(0, 1, 2)])
    obj = new_object(name, mesh, collection, material(shade))
    obj.location = (at[0], at[1], PLAN_Z + 0.05)
    obj.rotation_euler = (0, 0, math.atan2(toward[1] - at[1], toward[0] - at[0]))
    return obj


def label(collection, name, text, at, size):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = text
    curve.size = size
    curve.align_x = "CENTER"
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    curve.materials.append(material("ink"))
    obj.location = (at[0], at[1], PLAN_Z + 0.1)
    return obj


def build_plan_marks(collection, plan, scale):
    """The overhead plan: camera path, start and end camera, each person and each person's path."""
    samples = plan["camera"]["samples"]
    step = max(1, len(samples) // 60)
    points = samples[::step] + [samples[-1]]
    width = 0.012 * scale
    for index in range(len(points) - 1):
        a, b = points[index], points[index + 1]
        if math.dist(a[0:2], b[0:2]) < 1.5:  # a longer gap is a hard cut, not a move
            strip(collection, f"plan_path_{index:03d}", a, b, width, "path")
    size = 0.035 * scale
    first, last = samples[0], samples[-1]
    moves = math.dist(first[0:2], last[0:2]) > size * 2
    for name, sample, shade in (("START", first, "start"), ("END", last, "end")) if moves else (("START", first, "start"),):
        aim = sample[3:6]
        if math.dist(sample[0:2], aim[0:2]) < 1e-3:
            aim = (sample[0], sample[1] + 1, 0)
        wedge(collection, "plan_cam_" + name.lower(), sample, aim, size, shade)
    offset = size * 1.5
    label(collection, "plan_label_start", "CAM START" if moves else "CAMERA", (first[0], first[1] - offset - size * 0.6, 0), size * 0.75)
    if moves:
        label(collection, "plan_label_end", "CAM END", (last[0], last[1] - offset - size * 0.6, 0), size * 0.75)
    for subject in plan["subjects"]:
        track = subject.get("track") or [subject["at"]]
        mat = colour_material(subject["colour"], subject["rgb"])
        disc = new_object("plan_" + subject["id"], cone_mesh("plan_" + subject["id"], size * 0.55, size * 0.55, 0.02, 0, 24), collection, mat)
        mid = track[(len(track) - 1) // 2]
        disc.location = (mid[0], mid[1], PLAN_Z + 0.03)
        face = math.radians(subject["facing_deg"])
        nose = (mid[0] + math.cos(face) * size * 0.9, mid[1] + math.sin(face) * size * 0.9, 0)
        wedge(collection, "plan_face_" + subject["id"], nose, (nose[0] + math.cos(face), nose[1] + math.sin(face), 0), size * 0.4, "ink")
        label(collection, "plan_label_" + subject["id"], subject["id"], (mid[0], mid[1] + size * 1.0, 0), size * 0.75)
        if math.dist(track[0][0:2], track[-1][0:2]) > 0.2:
            strip(collection, "plan_walk_" + subject["id"], track[0], track[-1], width, "walk")
    for prop in plan.get("props", []):
        track = prop["track"]
        mid = track[(len(track) - 1) // 2]
        start = track[0]
        if math.dist(start[0:2], mid[0:2]) > 0.3:  # the throw: a dashed line from where the object is on the first frame
            pieces = 8
            for n in range(0, pieces, 2):
                a = [start[i] + (mid[i] - start[i]) * n / pieces for i in range(2)]
                b = [start[i] + (mid[i] - start[i]) * (n + 1) / pieces for i in range(2)]
                strip(collection, f"plan_throw_{prop['id']}_{n}", a, b, width, "mark")
        dot = new_object("plan_" + prop["id"], cone_mesh("plan_" + prop["id"], size * 0.28, size * 0.28, 0.02, 0, 16), collection, material("thrown"))
        dot.location = (mid[0], mid[1], PLAN_Z + 0.06)
        label(collection, "plan_label_" + prop["id"], prop["label"], (mid[0] + size * 1.6, mid[1] - size * 0.3, 0), size * 0.6)


def plan_extent(plan):
    xs, ys = [], []
    for sample in plan["camera"]["samples"]:
        xs.append(sample[0])
        ys.append(sample[1])
    for subject in plan["subjects"]:
        for at in subject.get("track") or [subject["at"]]:
            xs.append(at[0])
            ys.append(at[1])
    return min(xs), max(xs), min(ys), max(ys)


def build_plan_camera(scene, collection, plan):
    x0, x1, y0, y1 = plan_extent(plan)
    w, h = plan["resolution"]
    margin = 2.5
    wide, tall = (x1 - x0) + 2 * margin, (y1 - y0) + 2 * margin
    scale = max(wide, tall * w / h) if w >= h else max(tall, wide * h / w)
    data = bpy.data.cameras.new("plan_camera")
    data.type = "ORTHO"
    data.ortho_scale = scale
    data.clip_end = 200
    cam = bpy.data.objects.new("plan_camera", data)
    collection.objects.link(cam)
    cam.location = ((x0 + x1) / 2, (y0 + y1) / 2, 60)
    return cam, scale


def setup_render(scene, plan):
    render = scene.render
    engine = "BLENDER_EEVEE"
    try:
        render.engine = "BLENDER_WORKBENCH"
        engine = "BLENDER_WORKBENCH"
    except TypeError:
        render.engine = "BLENDER_EEVEE"
    render.resolution_x, render.resolution_y = plan["resolution"]
    render.resolution_percentage = 100
    render.fps = plan["fps"]
    render.film_transparent = False
    render.dither_intensity = 0.0  # flat greys compress to small files
    render.use_stamp = False
    for name in dir(render):  # no date, host name or file name in the image files
        if name.startswith("use_stamp_"):
            setattr(render, name, False)
    scene.frame_start, scene.frame_end = 1, plan["frames"]
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("ss_world")
    world.color = (0.80, 0.82, 0.84)
    scene.world = world
    if engine == "BLENDER_WORKBENCH":
        shading = scene.display.shading
        shading.light = "STUDIO"
        shading.use_world_space_lighting = True  # the floor keeps its tone at a floor-level camera
        shading.color_type = "MATERIAL"
        shading.show_shadows = True
        shading.shadow_intensity = 0.35
        scene.display.light_direction = (0.25, 0.35, 0.9)  # a high light: short shadows that stay near each object
        shading.show_cavity = True
        shading.show_object_outline = True
        scene.display.render_aa = "5"
    else:
        sun = bpy.data.lights.new("ss_sun", "SUN")
        sun.energy = 3.0
        lamp = bpy.data.objects.new("ss_sun", sun)
        scene.collection.objects.link(lamp)
        lamp.rotation_euler = (math.radians(50), 0, math.radians(30))
    return engine


def render_still(scene, path, frame):
    scene.frame_set(frame)
    settings = scene.render.image_settings
    if hasattr(settings, "media_type"):
        settings.media_type = "IMAGE"
    settings.file_format = "PNG"
    settings.color_mode = "RGB"
    settings.compression = 90
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=scene.name)


def render_animatic(scene, out):
    """A low-resolution movie of the move. Optional: a failure here does not fail the previs."""
    settings = scene.render.image_settings
    try:
        if hasattr(settings, "media_type"):
            settings.media_type = "VIDEO"
        settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
        scene.render.ffmpeg.audio_codec = "NONE"
        scene.render.filepath = os.path.join(out, "animatic_")
        bpy.ops.render.render(animation=True, scene=scene.name)
        made = sorted(f for f in os.listdir(out) if f.startswith("animatic_") and f.endswith(".mp4"))
        if not made:
            return "No movie file was written."
        os.replace(os.path.join(out, made[-1]), os.path.join(out, "animatic.mp4"))
        return None
    except Exception as exc:  # noqa: BLE001 - optional output
        return f"{type(exc).__name__}: {exc}"


def hidden_people(scene, plan, people):
    """For each still: the set box that stands between the camera and a person's head."""
    found = []
    try:
        layer = scene.view_layers[0]
        for name, frame in plan["stills"].items():
            scene.frame_set(frame)
            layer.update()
            sample = plan["camera"]["samples"][frame - 1]
            origin = Vector(sample[0:3])
            for subject, root in people:
                if subject["hidden"]:
                    continue
                head = root.matrix_world.translation + Vector((0, 0, subject.get("head_z", 1.62)))
                direction = head - origin
                distance = direction.length
                hit, _loc, _normal, _index, obj, _matrix = scene.ray_cast(layer.depsgraph, origin, direction.normalized(),
                                                                         distance=max(0.0, distance - 0.2))
                if hit and obj is not None and obj.name.startswith("set_"):
                    found.append(f"{name} still: {obj.name[4:]} hides the head of {subject['id']}.")
    except Exception as exc:  # noqa: BLE001 - a check, not a build step
        found.append(f"The line-of-sight check did not run: {type(exc).__name__}.")
    return found


def main():
    out, animatic, session = arguments()
    os.makedirs(out, exist_ok=True)
    plan = PLAN
    name = "shotspeak_option_" + plan["label"]
    if bpy.app.background and not session:
        scene = bpy.context.scene
        scene.name = name
        for obj in list(scene.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    else:  # a live Blender session: keep the user's scene, build in a new scene
        scene = bpy.data.scenes.new(name)
        window = getattr(bpy.context, "window", None)
        if window is not None:
            window.scene = scene
    blocking = bpy.data.collections.new(name + "_blocking")
    marks = bpy.data.collections.new(name + "_plan_marks")
    scene.collection.children.link(blocking)
    scene.collection.children.link(marks)

    build_floor(blocking, plan["floor_half"])
    build_set(blocking, plan["set"])
    people = [(subject, build_person(blocking, subject)) for subject in plan["subjects"]]
    for prop in plan.get("props", []):
        build_prop(blocking, prop)
    shot_camera = build_camera(scene, blocking, plan)
    plan_camera, scale = build_plan_camera(scene, marks, plan)
    build_plan_marks(marks, plan, scale)
    engine = setup_render(scene, plan)

    def show_marks(visible):
        for obj in marks.objects:
            obj.hide_render = not visible

    result = {"label": plan["label"], "engine": engine, "blender": bpy.app.version_string, "files": [], "hidden": []}
    show_marks(False)
    scene.camera = shot_camera
    for still, frame in plan["stills"].items():
        render_still(scene, os.path.join(out, f"still_{still}.png"), frame)
        result["files"].append(f"still_{still}.png")
    result["hidden"] = hidden_people(scene, plan, people)
    if animatic:
        problem = render_animatic(scene, out)
        if problem:
            result["animatic_problem"] = problem
        else:
            result["files"].append("animatic.mp4")
    show_marks(True)
    scene.camera = plan_camera
    if engine == "BLENDER_WORKBENCH":
        scene.display.shading.show_shadows = False
        scene.display.shading.light = "FLAT"  # the plan is a diagram: exact colours
    render_still(scene, os.path.join(out, "plan_overhead.png"), plan["stills"]["mid"])
    result["files"].append("plan_overhead.png")
    show_marks(False)
    if engine == "BLENDER_WORKBENCH":
        scene.display.shading.show_shadows = True
        scene.display.shading.light = "STUDIO"
    scene.camera = shot_camera
    scene.frame_set(1)
    scene.render.filepath = "//render"  # no folder name of this machine in the scene file
    blend = os.path.join(out, "blocking.blend")
    try:
        if bpy.app.background and not session:
            bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True, copy=True)
        else:
            bpy.data.libraries.write(blend, {scene}, compress=True)
        result["files"].append("blocking.blend")
    except Exception as exc:  # noqa: BLE001
        result["blend_problem"] = f"{type(exc).__name__}: {exc}"
    with open(os.path.join(out, "result.json"), "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("shot-speak previs: wrote " + ", ".join(result["files"]))


if __name__ == "__main__":
    main()
