"""Procedural metric USD/PhysX fixture. Import inside a running Isaac Sim."""

from contextlib import contextmanager

from omni.physx import get_physx_interface, get_physx_simulation_interface
from pxr import Gf, PhysxSchema, Usd, UsdGeom, UsdPhysics, UsdUtils

DT = 1 / 240


class Drawer:
    def __init__(
        self,
        *,
        reversed_pull=False,
        latched=False,
        teacher=False,
        origin=0.0,
        gap=0.0,
        free=False,
    ):
        self.stage = Usd.Stage.CreateInMemory()
        UsdGeom.SetStageMetersPerUnit(self.stage, 1)
        UsdGeom.SetStageUpAxis(self.stage, UsdGeom.Tokens.z)
        scene = UsdPhysics.Scene.Define(self.stage, "/Physics")
        scene.CreateGravityMagnitudeAttr(0)
        self.origin = origin
        self.sign = -1 if reversed_pull else 1
        self.steps = 0
        self.trace = []
        # All joint frames coincide initially. Geometries are local offsets.
        carriage = self.body("Carriage")
        wrist = self.body("Tool")
        self.drives = []
        parent = None
        if teacher:
            base = self.body("Extension")
            self.drives.append(self.slide(None, base, "X", 1800))
            parent = base
        self.drives.append(self.slide(parent, carriage, "X", 1800))
        self.lift = self.slide(carriage, wrist, "Z", 1800)
        self.box("/Tool/Pin", (-gap, 0, 0.045), (0.012, 0.015, 0.012))
        drawer = self.body("Drawer")
        handle = self.body("Handle")
        self.slide(None, drawer, "X", 0, lower=-0.001, upper=0.15)
        self.slide(drawer, handle, "Z", 18, lower=0, upper=0.09)
        # Separate the mechanism laterally for a free-space measurement.
        y = 0.18 if free else 0
        self.box("/Handle/Face", (0.014, y, 0.046), (0.012, 0.032, 0.038))
        self.box("/Handle/Lip", (-0.001, y, 0.060), (0.033, 0.032, 0.012))
        self.box("/Handle/Catch", (0.034, y, 0.014), (0.016, 0.02, 0.018))
        if latched:
            self.box("/Stop", (origin + 0.055, y, 0.014), (0.018, 0.03, 0.034))

    def body(self, name):
        body = UsdGeom.Xform.Define(self.stage, "/" + name)
        body.AddTranslateOp().Set(Gf.Vec3d(self.origin, 0, 0))
        prim = body.GetPrim()
        UsdPhysics.RigidBodyAPI.Apply(prim)
        PhysxSchema.PhysxRigidBodyAPI.Apply(prim).CreateLinearDampingAttr(15.0)
        mass = UsdPhysics.MassAPI.Apply(prim)
        mass.CreateMassAttr(0.25)
        mass.CreateDiagonalInertiaAttr(Gf.Vec3f(0.002))
        mass.CreateCenterOfMassAttr(Gf.Vec3f(0))
        return body

    def box(self, path, center, size):
        box = UsdGeom.Cube.Define(self.stage, path)
        box.CreateSizeAttr(1.0)
        box.AddTranslateOp().Set(Gf.Vec3d(*center))
        box.AddScaleOp().Set(Gf.Vec3f(*size))
        prim = box.GetPrim()
        UsdPhysics.CollisionAPI.Apply(prim)
        collision = PhysxSchema.PhysxCollisionAPI.Apply(prim)
        collision.CreateContactOffsetAttr(0.0005)
        collision.CreateRestOffsetAttr(0.0)

    def slide(self, parent, child, axis, stiffness, lower=-0.14, upper=0.16):
        joint = UsdPhysics.PrismaticJoint.Define(
            self.stage, "/J" + child.GetPrim().GetName()
        )
        if parent is None:
            joint.CreateLocalPos0Attr(Gf.Vec3f(self.origin, 0, 0))
        else:
            joint.CreateBody0Rel().SetTargets([parent.GetPath()])
        joint.CreateBody1Rel().SetTargets([child.GetPath()])
        joint.CreateAxisAttr(axis)
        joint.CreateLowerLimitAttr(lower)
        joint.CreateUpperLimitAttr(upper)
        drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), "linear")
        drive.CreateTypeAttr("force")
        drive.CreateStiffnessAttr(stiffness)
        drive.CreateDampingAttr(12 if stiffness else 3)
        drive.CreateMaxForceAttr(35)
        return drive.CreateTargetPositionAttr(0)

    def read(self):
        physics = get_physx_interface()

        def pos(name):
            result = physics.get_rigidbody_transformation("/" + name)
            if not result["ret_val"]:
                raise RuntimeError(f"Missing simulated body {name}")
            return result["position"]

        tool, handle, drawer = pos("Tool"), pos("Handle"), pos("Drawer")
        return dict(
            tool_x_mm=round(1000 * (tool[0] - self.origin), 2),
            tool_z_mm=round(1000 * tool[2], 2),
            handle_z_mm=round(1000 * handle[2], 2),
            drawer_x_mm=round(1000 * (drawer[0] - self.origin), 2),
        )

    def move(self, pull_mm, lift_mm, seconds=0.6):
        if abs(pull_mm) > 110 or not 0 <= lift_mm <= 80:
            raise ValueError("command outside fixture envelope")
        # Teacher's two serial horizontal motors share the stroke unequally.
        shares = (0.35, 0.65) if len(self.drives) == 2 else (1,)
        drives = [*self.drives, self.lift]
        start = [drive.Get() for drive in drives]
        target = [self.sign * pull_mm * share / 1000 for share in shares] + [
            lift_mm / 1000
        ]
        sim = get_physx_simulation_interface()
        count = round(seconds / DT)
        for tick in range(1, count + 1):
            fraction = min(1.0, tick / (0.75 * count))
            for drive, old, new in zip(drives, start, target):
                drive.Set(old + fraction * (new - old))
            sim.simulate(DT, self.steps * DT)
            sim.fetch_results()
            self.steps += 1
            if self.steps % 12 == 0:
                self.trace.append(dict(tick=self.steps, **self.read()))
        return self.read()


@contextmanager
def station(**kwargs):
    fixture = Drawer(**kwargs)
    cache = UsdUtils.StageCache.Get()
    stage_id = cache.Insert(fixture.stage)
    sim = get_physx_simulation_interface()
    sim.attach_stage(stage_id.ToLongInt())
    try:
        yield fixture
    finally:
        sim.detach_stage()
        cache.Erase(stage_id)
