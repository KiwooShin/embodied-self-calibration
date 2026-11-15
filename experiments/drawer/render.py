"""Create an RTX replay image for each unique measured pose using Isaac Sim."""

import argparse
import json
from pathlib import Path

from views import key, scenes

parser = argparse.ArgumentParser()
parser.add_argument("records", type=Path, nargs="+")
parser.add_argument("--cache", type=Path, required=True)
args = parser.parse_args()
args.cache.mkdir(parents=True, exist_ok=True)
poses = set()
for record in args.records:
    for name, case in json.loads(record.read_text())["conditions"].items():
        for _, _, frames in scenes(name, case):
            poses.update(frames)

from isaacsim import SimulationApp

app = SimulationApp({"headless": True, "renderer": "RayTracedLighting"})
try:
    import numpy as np
    import omni.replicator.core as rep
    import omni.usd
    from PIL import Image
    from pxr import Gf, Sdf, UsdGeom, UsdLux, UsdShade

    stage = omni.usd.get_context().get_stage()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    def material(name, color, metallic, roughness):
        path = "/Materials/" + name
        mat = UsdShade.Material.Define(stage, path)
        sh = UsdShade.Shader.Define(stage, path + "/Shader")
        sh.CreateIdAttr("UsdPreviewSurface")
        for prop, value in [("metallic", metallic), ("roughness", roughness)]:
            sh.CreateInput(prop, Sdf.ValueTypeNames.Float).Set(value)
        sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
        mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
        return mat

    silver = material("Aluminium", (0.48, 0.58, 0.65), 0.62, 0.30)
    dark = material("Graphite", (0.062, 0.085, 0.11), 0.48, 0.32)
    floor = material("Table", (0.08, 0.105, 0.13), 0.10, 0.62)
    teal = material("Tool", (0.025, 0.52, 0.43), 0.24, 0.25)
    gold = material("Handle", (0.87, 0.47, 0.065), 0.55, 0.25)
    blue = material("Drawer", (0.10, 0.26, 0.54), 0.48, 0.25)
    coral = material("Stop", (0.75, 0.105, 0.045), 0.24, 0.35)

    def xyz(x, y, z):
        return Gf.Vec3d(x / 1000, y / 1000, z / 1000)

    def box(path, center, size, mat):
        geom = UsdGeom.Cube.Define(stage, path)
        geom.CreateSizeAttr(1.0)
        geom.AddTranslateOp().Set(xyz(*center))
        geom.AddScaleOp().Set(Gf.Vec3f(*xyz(*size)))
        UsdShade.MaterialBindingAPI.Apply(geom.GetPrim()).Bind(mat)

    def group(name):
        return UsdGeom.Xform.Define(stage, "/" + name).AddTranslateOp()

    tool, drawer, handle, stop = [
        group(n) for n in ("Tool", "Drawer", "Handle", "Stop")
    ]
    extension = group("Extension")
    carriage = group("Carriage")
    box("/Carriage/Base", (0, -35, 5), (27, 15, 10), dark)
    box("/Carriage/Tower", (0, -36, 34), (14, 12, 55), silver)
    box("/Carriage/Guide", (-5, -30, 34), (4, 3, 48), dark)
    box("/Bench", (20, 0, -19), (1800, 1200, 18), floor)
    box("/Plate", (26, 0, -7), (335, 137, 6), dark)
    for y in (-38, 31):
        box("/Rail" + str(y + 40), (21, y, -2), (299, 6, 7), silver)
    for i in range(29):
        box(
            "/Tick" + str(i),
            (i * 10 - 120, -54, -3.7),
            (0.6, 6 if i % 5 == 0 else 3, 0.4),
            silver,
        )
    # Carriage and drawer housings illustrate the mount. Gold and teal contact
    # surfaces, catch and stop have the dimensions of the simulated fixture.
    box("/Drawer/Bed", (30, 10, 0), (84, 44, 6), blue)
    box("/Handle/Face", (14, 0, 46), (12, 32, 38), gold)
    box("/Handle/Lip", (-1, 0, 60), (33, 32, 12), gold)
    box("/Handle/Catch", (34, 0, 14), (16, 20, 18), gold)
    box("/Handle/Spine", (25, 7, 30), (33, 9, 8), gold)
    box("/Tool/Pin", (0, 0, 45), (12, 15, 12), teal)
    box("/Tool/Shank", (0, -15, 45), (10, 18, 9), teal)
    box("/Tool/Bracket", (-4, -27, 30), (12, 8, 39), teal)
    box("/Stop/Block", (55, 0, 14), (18, 30, 34), coral)
    box("/Extension/Body", (0, 33, 14), (39, 12, 18), silver)
    for i in range(3):
        box("/Extension/Groove" + str(i), (i * 7 - 7, 26.8, 14), (2, 0.5, 12), dark)

    UsdLux.DomeLight.Define(stage, "/Dome").CreateIntensityAttr(370)
    light = UsdLux.DistantLight.Define(stage, "/Key")
    light.CreateIntensityAttr(2600)
    light.CreateAngleAttr(8)
    light.AddRotateXYZOp().Set(Gf.Vec3f(32, -26, -18))
    cam = UsdGeom.Camera.Define(stage, "/Camera")
    cam.CreateHorizontalApertureAttr(32)
    cam.CreateFocalLengthAttr(33)
    cam.CreateClippingRangeAttr(Gf.Vec2f(0.005, 12))
    cam.AddTransformOp().Set(
        Gf.Matrix4d()
        .SetLookAt(xyz(170, -300, 174), xyz(24, 0, 28), Gf.Vec3d(0, 0, 1))
        .GetInverse()
    )
    product = rep.create.render_product("/Camera", (660, 364))
    rgb = rep.AnnotatorRegistry.get_annotator("rgb")
    rgb.attach(product)
    for _ in range(10):
        rep.orchestrator.step(rt_subframes=3)
    for p in sorted(poses):
        out = args.cache / (key(p) + ".jpg")
        if out.exists():
            continue
        tx, tz, dx, hz, free, teacher, latched = p
        # Omit the laterally displaced drawer from the free-space camera view.
        for node, show in [
            (drawer, not free),
            (handle, not free),
            (stop, latched and not free),
            (extension, teacher),
        ]:
            UsdGeom.Imageable(node.GetAttr().GetPrim()).GetVisibilityAttr().Set(
                "inherited" if show else "invisible"
            )
        offset = 0
        carriage.Set(xyz(tx, 0, 0))
        tool.Set(xyz(tx, 0, tz))
        handle.Set(xyz(dx, offset, hz))
        drawer.Set(xyz(dx, offset, 0))
        stop.Set(xyz(0, offset, 0))
        extension.Set(xyz(tx * 0.35, 0, 0))
        rep.orchestrator.step(rt_subframes=3)
        frame = np.asarray(rgb.get_data())[..., :3].copy()
        if frame.shape != (364, 660, 3) or frame.std() < 4:
            raise RuntimeError("Missing RTX camera image")
        Image.fromarray(frame).save(out, quality=93)
    print("Rendered", len(poses), "distinct poses", flush=True)
except Exception:
    import traceback

    traceback.print_exc()
    raise
else:
    app.close()
