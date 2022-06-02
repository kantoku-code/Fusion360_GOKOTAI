#Fusion360API Python

import adsk.core
import adsk.fusion
import itertools
import math

CG_COLOR: adsk.fusion.CustomGraphicsSolidColorEffect = adsk.fusion.CustomGraphicsSolidColorEffect.create(
    adsk.core.Color.create(128,255,0,255)
)


def drawLine(
    self: adsk.core.Line3D,
    skt: adsk.fusion.Sketch) -> None:

    skt.sketchCurves.sketchLines.addByTwoPoints(
        self.startPoint,
        self.endPoint
    )


def drawCircle(
    self: adsk.core.Circle3D,
    skt: adsk.fusion.Sketch) -> None:

    eva: adsk.core.CurveEvaluator3D = self.evaluator
    _, points = eva.getPointsAtParameters(
        [
            0,
            math.pi * 0.5
        ]
    )

    center: adsk.core.Point3D = self.center
    normal: adsk.core.Vector3D = self.normal
    mat: adsk.core.Matrix3D = adsk.core.Matrix3D.create()
    xVec: adsk.core.Vector3D = center.vectorTo(points[0])
    xVec.normalize()
    yVec: adsk.core.Vector3D = center.vectorTo(points[1])
    yVec.normalize()
    mat.setWithCoordinateSystem(
        center,
        xVec,
        yVec,
        normal
    )

    circle: adsk.fusion.SketchCircle = skt.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0,0,0),
        self.radius
    )
    objs: adsk.core.ObjectCollection = adsk.core.ObjectCollection.create()
    objs.add(circle)
    skt.move(objs, mat)


def drawArc(
    self: adsk.core.Arc3D,
    skt: adsk.fusion.Sketch) -> None:

    eva: adsk.core.CurveEvaluator3D = self.evaluator
    _, sPrm, ePrm = eva.getParameterExtents()
    _, mPoint = eva.getPointAtParameter((sPrm + ePrm) * 0.5)

    skt.sketchCurves.sketchArcs.addByThreePoints(
        self.startPoint,
        mPoint,
        self.endPoint
    )


def getCenterCurveByTorus(
    self,
    face: adsk.fusion.BRepFace):

    torus: adsk.core.Torus = face.geometry
    center: adsk.core.Point3D = torus.origin
    normal: adsk.core.Vector3D = torus.axis
    radius = torus.majorRadius

    # circle
    if face.edges.count < 1:
        circle: adsk.core.Circle3D = adsk.core.Circle3D.createByCenter(
            center,
            normal,
            radius)

        return {
            'obj': circle,
            'length': math.pi * 2 * radius,
        }

    pnts = [e.geometry.center for e in face.edges 
        if e.geometry.classType() == adsk.core.Circle3D.classType()]

    if len(pnts) < 2:
        return None

    # arc
    cog: adsk.core.Point3D = face.centroid
    vecCog: adsk.core.Vector3D = center.vectorTo(cog)
    lst = []
    for p1, p2 in itertools.combinations(pnts, 2):
        v1: adsk.core.Vector3D = center.vectorTo(p1)
        v2: adsk.core.Vector3D = center.vectorTo(p2)

        ang = v1.angleTo(v2)
        if not vecCog.dotProduct(v1) > 0:
            ang = math.pi * 2 - ang

        arc: adsk.core.Arc3D = adsk.core.Arc3D.createByCenter(
            adsk.core.Point3D.create(0,0,0),
            adsk.core.Vector3D.create(0,0,1),
            adsk.core.Vector3D.create(1,0,0),
            radius,
            0,
            ang
        )

        mat: adsk.core.Matrix3D = adsk.core.Matrix3D.create()
        xVec: adsk.core.Vector3D = center.vectorTo(p1)
        xVec.normalize()
        yVec: adsk.core.Vector3D = xVec.crossProduct(normal)
        yVec.normalize()
        mat.setWithCoordinateSystem(
            center,
            xVec,
            yVec,
            normal
        )

        arc.transformBy(mat)

        lst.append(
            {
                'obj': arc,
                'length': ang * radius,
            }
        )

    if len(lst) < 1:
        return None

    return max(lst, key=lambda x: x['length'])


def getPerpendicularVecter(
    vec: adsk.core.Vector3D) -> adsk.core.Vector3D:

    v1: adsk.core.Vector3D = adsk.core.Vector3D.create(1,0,0)
    if vec.isParallelTo(v1):
        v1 = adsk.core.Vector3D.create(0,1,0)

    v2: adsk.core.Vector3D = vec.crossProduct(v1)

    return vec.crossProduct(v2)


def getCenterCurveByCone(
    self: adsk.core.Cone,
    face: adsk.fusion.BRepFace):

    app: adsk.core.Application = adsk.core.Application.get()
    measMgr: adsk.core.MeasureManager = app.measureManager

    axis: adsk.core.Vector3D = face.geometry.axis
    axis.normalize()
    bBox: adsk.core.OrientedBoundingBox3D = measMgr.getOrientedBoundingBox(
        face,
        axis,
        getPerpendicularVecter(axis)
    )

    vec1: adsk.core.Vector3D = axis.copy()
    vec1.scaleBy(bBox.length * 0.5)
    vec2: adsk.core.Vector3D = vec1.copy()
    vec2.scaleBy(-1)

    planes = []
    for v in [vec1, vec2]:
        p: adsk.core.Point3D = bBox.centerPoint.copy()
        p.translateBy(v)
        planes.append(
            adsk.core.Plane.create(
                p,
                v
            )
        )

    infiniteLine: adsk.core.InfiniteLine3D = adsk.core.InfiniteLine3D.create(
        face.geometry.origin,
        axis
    )

    points = [plane.intersectWithLine(infiniteLine) for plane in planes]

    line: adsk.core.Line3D = adsk.core.Line3D.create(
        points[0],
        points[1],
    )

    return {
        'obj': line,
        'length': points[0].distanceTo(points[1]),
    }


adsk.core.Cylinder.getCenterEntity = getCenterCurveByCone
adsk.core.Cone.getCenterEntity = getCenterCurveByCone
adsk.core.Torus.getCenterEntity = getCenterCurveByTorus

adsk.core.Line3D.draw = drawLine
adsk.core.Arc3D.draw = drawArc
adsk.core.Circle3D.draw = drawCircle


class CenterlineMeasurementFactry:

    @staticmethod
    def hasCenterCurve(
        face: adsk.fusion.BRepFace) -> bool:

        if not hasattr(face.geometry, 'getCenterEntity'):
            return False

        res = face.geometry.getCenterEntity(face)

        if not res:
            return False

        if len(res) < 1:
            return False

        return True


    @staticmethod
    def getAllLength(
        faces: list) -> float:

        infos = getCenterEntities(faces)
        if len(infos) < 1:
            return 0

        return sum([info['length'] for info in infos])


    @staticmethod
    def drawSketch(
        faces: list) -> adsk.fusion.Sketch:

        infos = getCenterEntities(faces)
        crvs = [info['obj'] for info in infos if hasattr(info['obj'], 'draw')]
        if len(crvs) < 1:
            return

        app: adsk.core.Application = adsk.core.Application.get()
        des: adsk.fusion.Design = app.activeProduct
        root: adsk.fusion.Component = des.rootComponent

        skt: adsk.fusion.Sketch = root.sketches.add(
            root.xYConstructionPlane
        )

        skt.isComputeDeferred = True
        [crv.draw(skt) for crv in crvs]
        skt.isComputeDeferred = False


    @staticmethod
    def drawCG(
        faces: list) -> adsk.fusion.CustomGraphicsGroup:

        infos = getCenterEntities(faces)
        crvs = [info['obj'] for info in infos if hasattr(info['obj'], 'draw')]
        if len(crvs) < 1:
            return

        face: adsk.fusion.BRepFace = None
        for face in faces:
            face.body.opacity = 0.5

        app: adsk.core.Application = adsk.core.Application.get()
        des: adsk.fusion.Design = app.activeProduct
        root: adsk.fusion.Component = des.rootComponent

        cgGroup: adsk.fusion.CustomGraphicsGroup = root.customGraphicsGroups.add()
        for crv in crvs:
            cgCrv: adsk.fusion.CustomGraphicsCurve = cgGroup.addCurve(crv)
            cgCrv.weight = 3
            cgCrv.color = CG_COLOR

        return cgGroup


def getAllCenterCurves(
    faces: list) -> list:

    infos = getCenterEntities(faces)
    crvs = [info['obj'] for info in infos ]

    return crvs


def getCenterEntities(
    faces: list) -> list:

    tmpMgr: adsk.fusion.TemporaryBRepManager = adsk.fusion.TemporaryBRepManager.get()

    infos = []
    for face in faces:
        clone = tmpMgr.copy(face).faces[0]

        if not hasattr(clone.geometry, 'getCenterEntity'):
            continue

        centerEntity = clone.geometry.getCenterEntity(clone)

        if not centerEntity:
            continue

        infos.append(centerEntity)

    return infos