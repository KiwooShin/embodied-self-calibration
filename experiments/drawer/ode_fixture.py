"""Independent ODE implementation using slider joints, spring drives and contact."""

from contextlib import contextmanager
import ode

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
        gain=1.0,
    ):
        self.gain = gain
        self.world = ode.World()
        self.world.setGravity((0, 0, 0))
        self.world.setCFM(1e-5)
        self.world.setLinearDamping(0.06)
        self.space = ode.SimpleSpace()
        self.contacts = ode.JointGroup()
        self.geoms = []
        self.origin = origin
        self.trace = []
        self.steps = 0
        self.sign = -1 if reversed_pull else 1
        self.axes = []
        parent = None
        if teacher:
            parent, _ = self.slide(None, (1, 0, 0), 1800)
        carriage, _ = self.slide(parent, (1, 0, 0), 1800)
        self.tool, _ = self.slide(carriage, (0, 0, 1), 1800)
        self.drawer, _ = self.slide(None, (1, 0, 0), 0, -0.001, 0.15)
        self.handle, _ = self.slide(self.drawer, (0, 0, 1), 18, 0, 0.09)
        self.teacher = teacher
        self.previous = (0.0, 0.0)
        y = 0.18 if free else 0
        self.box(self.tool, (-gap, 0, 0.045), (0.012, 0.015, 0.012))
        self.box(self.handle, (0.014, y, 0.046), (0.012, 0.032, 0.038))
        self.box(self.handle, (-0.001, y, 0.060), (0.033, 0.032, 0.012))
        self.box(self.handle, (0.034, y, 0.014), (0.016, 0.020, 0.018))
        if latched:
            self.box(None, (origin + 0.055, y, 0.014), (0.018, 0.030, 0.034))

    def slide(self, parent, axis, k, lo=-0.14, hi=0.16):
        body = ode.Body(self.world)
        mass = ode.Mass()
        mass.setParameters(0.25, 0, 0, 0, 0.002, 0.002, 0.002, 0, 0, 0)
        body.setMass(mass)
        body.setPosition((self.origin, 0, 0))
        joint = ode.SliderJoint(self.world)
        joint.attach(body, parent)
        joint.setAxis(axis)
        joint.setParam(ode.ParamLoStop, lo)
        joint.setParam(ode.ParamHiStop, hi)
        self.axes.append((joint, k))
        return body, joint

    def box(self, body, center, size):
        g = ode.GeomBox(self.space, lengths=size)
        if body is None:
            g.setPosition(center)
        else:
            g.setBody(body)
            g.setOffsetPosition(center)
        self.geoms.append(g)

    def contact(self, _, a, b):
        if a.getBody() == b.getBody():
            return
        for point in ode.collide(a, b):
            point.setMu(0.5)
            joint = ode.ContactJoint(self.world, self.contacts, point)
            joint.attach(a.getBody(), b.getBody())

    def read(self):
        x, _, z = self.tool.getPosition()
        return dict(
            tool_x_mm=round(1000 * (x - self.origin), 2),
            tool_z_mm=round(1000 * z, 2),
            handle_z_mm=round(1000 * self.handle.getPosition()[2], 2),
            drawer_x_mm=round(1000 * (self.drawer.getPosition()[0] - self.origin), 2),
        )

    def move(self, pull_mm, lift_mm, seconds=0.6):
        if abs(pull_mm) > 110 or not 0 <= lift_mm <= 80:
            raise ValueError("command outside fixture envelope")
        start_x, start_z = self.previous
        end_x, end_z = self.gain * self.sign * pull_mm / 1000, lift_mm / 1000
        n = round(seconds / DT)
        for i in range(1, n + 1):
            f = min(1.0, i / (0.75 * n))
            x, z = start_x + f * (end_x - start_x), start_z + f * (end_z - start_z)
            horizontal = [0.35 * x, 0.65 * x] if self.teacher else [x]
            for target, (joint, k) in zip(horizontal + [z, 0.0, 0.0], self.axes):
                force = (
                    k * (target - joint.getPosition())
                    - (12 if k else 3) * joint.getPositionRate()
                )
                joint.addForce(max(-35, min(35, force)))
            self.space.collide(None, self.contact)
            self.world.step(DT)
            self.contacts.empty()
            self.steps += 1
            if self.steps % 12 == 0:
                self.trace.append(dict(tick=self.steps, **self.read()))
        self.previous = (end_x, end_z)
        return self.read()


@contextmanager
def station(**kwargs):
    yield Drawer(**kwargs)
