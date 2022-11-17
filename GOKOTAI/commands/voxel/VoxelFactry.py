from pickle import FALSE
import traceback
import adsk.fusion
import adsk.core
from enum import IntEnum, auto
import pathlib

THIS_DIR = pathlib.Path(__file__).resolve().parent
SMT_DIR = THIS_DIR / 'temp'
SMT_PATH = str(SMT_DIR / 'voxel.smt')
# _temppath = r'C:\temp\temp.smt'

INTERSECTION_BOOLEAN = adsk.fusion.BooleanTypes.IntersectionBooleanType
# UNION_BOOLEAN = adsk.fusion.BooleanTypes.UnionBooleanType
DIFFERENCE_BOOLEAN = adsk.fusion.BooleanTypes.DifferenceBooleanType

class RelativeStatus(IntEnum):
    INCLUDE = auto()
    COLLISION = auto()
    UNRELATED = auto()

DEBUG = True


def run(context):
    ui = adsk.core.UserInterface.cast(None)
    try:
        app: adsk.core.Application = adsk.core.Application.get()
        ui = app.userInterface
        des: adsk.fusion.Design = app.activeProduct
        root: adsk.fusion.Component = des.rootComponent

        fact = VoxelFactry(
            root.bRepBodies[0],
            6
        )
        # oct = fact.test()
        # a, b = fact.get_voxel_bodies()
        # print(f'{len(a)} : {len(b)}')
        fact.test()
        iptMgr: adsk.core.ImportManager = app.importManager
        smtOpt: adsk.core.SMTImportOptions = iptMgr.createSMTImportOptions(_temppath)
        iptMgr.importToTarget2(smtOpt, root)

        a=1


    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class VoxelFactry():

    def __init__(
        self,
        body: adsk.fusion.BRepBody = None,
        division_level: int = 1) -> None:

        self.app: adsk.core.Application = adsk.core.Application.get()
        self.des: adsk.fusion.Design = self.app.activeProduct
        self.tmpMgr: adsk.fusion.TemporaryBRepManager = adsk.fusion.TemporaryBRepManager.get()
        self.vecX: adsk.core.Vector3D = adsk.core.Vector3D.create(1,0,0)
        self.vecY: adsk.core.Vector3D = adsk.core.Vector3D.create(0,1,0)

        self.body: adsk.fusion.BRepBody = None
        self.base_BBox: adsk.core.OrientedBoundingBox3D = None
        if body:
            self.set_body(body)
        self.division_level = division_level


    def set_body(self, body: adsk.fusion.BRepBody) -> None:
        self.body = body
        self._set_base_BBox()


    def set_division_level(self, level: int) -> None:
        self.division_level = level


    def get_unit_size(self) -> float:
        if not self.body:
            return -1

        return self.base_BBox.length / (2 ** self.division_level)


    def get_base_box(self) -> adsk.fusion.BRepBody:
        if not self.base_BBox:
            return None

        return self.tmpMgr.createBox(self.base_BBox)


    def create_voxel(
        self,
        isInside: bool = True,
        isCombin: bool = False):

        stackBBoxes, includeBBoxes, unrelatedBBoxes = self._get_voxel_bodies()
        dump(f'{len(stackBBoxes)}:{len(includeBBoxes)}:{len(unrelatedBBoxes)}')


        if isInside:
            stackBBoxes.extend(includeBBoxes)
        else:
            unrelatedBBoxes.extend(includeBBoxes)

        if isCombin:
            bodies = self._get_combine_body_list(unrelatedBBoxes)
        else:
            bodies = [self.tmpMgr.createBox(b) for b in stackBBoxes]

        # export
        self._export_smt(bodies)

        # import
        iptMgr: adsk.core.ImportManager = self.app.importManager
        smtOpt: adsk.core.SMTImportOptions = iptMgr.createSMTImportOptions(SMT_PATH)
        smtOpt.isViewFit = False
        iptMgr.importToTarget2(smtOpt, self.des.rootComponent)


    def _get_combine_body_list(self, bBoxes: list) -> list:
        bodies = [self.tmpMgr.createBox(b) for b in bBoxes]
        targetBody: adsk.fusion.BRepBody = self.tmpMgr.createBox(self.base_BBox)

        [self.tmpMgr.booleanOperation(targetBody, b, DIFFERENCE_BOOLEAN) for b in bodies]
        
        return [targetBody]


    def _export_smt(self, bodies: list):
        if not SMT_DIR.exists():
            SMT_DIR.mkdir()

        self.tmpMgr.exportToFile(bodies, SMT_PATH)


    def _get_voxel_bodies(self):
        includeBBoxes = []
        stackBBoxes = [self.base_BBox]
        unrelatedBBoxes = []

        for _ in range(self.division_level):

            if len(stackBBoxes) < 1:
                break

            tmp = []
            [tmp.extend(self._get_oct_BBoxes(b)) for b in stackBBoxes]
            stackBBoxes = tmp

            bodies = [self.tmpMgr.createBox(b) for b in stackBBoxes]
            
            nextStack = []
            for body, bbox in zip(bodies, stackBBoxes):
                res = self._get_relative_status(body, self.body)
                if res == RelativeStatus.INCLUDE:
                    includeBBoxes.append(bbox)
                elif res == RelativeStatus.COLLISION:
                    nextStack.append(bbox)
                else:
                    unrelatedBBoxes.append(bbox)

            stackBBoxes = nextStack

        return stackBBoxes, includeBBoxes, unrelatedBBoxes


    def _get_oct_BBoxes(self, bBox: adsk.core.OrientedBoundingBox3D) -> list:

        length = bBox.length
        unitLength = length * 0.5
        toBaseLength = -length * 0.5 + unitLength * 0.5
        basePoint: adsk.core.Point3D = bBox.centerPoint.copy()
        basePoint.translateBy(
            adsk.core.Vector3D.create(toBaseLength, toBaseLength ,toBaseLength)
        )

        points = []
        for ix in range(2):
            for iy in range(2):
                for iz in range(2):
                    points.append(
                        adsk.core.Point3D.create(
                            basePoint.x + unitLength * ix,
                            basePoint.y + unitLength * iy,
                            basePoint.z + unitLength * iz,
                        )
                    )

        bBoxes = [adsk.core.OrientedBoundingBox3D.create(
            pnt,
            self.vecY,
            self.vecX,
            unitLength,
            unitLength,
            unitLength,
        ) for pnt in points]

        return bBoxes


    def _get_BBox(self, body: adsk.fusion.BRepBody) -> adsk.core.OrientedBoundingBox3D:
        if not body:
            return None

        clone: adsk.fusion.BRepBody = self.tmpMgr.copy(body)

        measMgr: adsk.core.MeasureManager = self.app.measureManager
        bBox: adsk.core.OrientedBoundingBox3D = measMgr.getOrientedBoundingBox(
            clone,
            self.vecY,
            self.vecX,
        )

        maxLength = max([bBox.width, bBox.length, bBox.height])

        return adsk.core.OrientedBoundingBox3D.create(
            bBox.centerPoint,
            self.vecY,
            self.vecX,
            maxLength,
            maxLength,
            maxLength,
        )


    def _set_base_BBox(self):
        if not self.body:
            return None

        self.base_BBox = self._get_BBox(self.body)


    def _get_relative_status(
        self,
        body1: adsk.fusion.BRepBody,
        body2: adsk.fusion.BRepBody,) -> RelativeStatus:

        volume = body1.volume
        self.tmpMgr.booleanOperation(body1, body2, INTERSECTION_BOOLEAN)

        if body1.volume == 0:
            return RelativeStatus.UNRELATED
        elif body1.volume == volume:
            return RelativeStatus.INCLUDE
        else:
            return RelativeStatus.COLLISION


def dump(s):
    if not DEBUG:
        return

    adsk.core.Application.get().log(f'{s}')
    print(f'{s}')