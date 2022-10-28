import traceback
import adsk.core
import adsk.fusion
from tkinter import *
import pathlib
import json

DEBUG = True
THIS_DIR = pathlib.Path(__file__).resolve().parent
CORRECTION_PATH = THIS_DIR / 'correction.json'
CORRECTION_KEY = 'correction_value'

DEBUG = True

class FullsizeFactry():
    def __init__(self) -> None:
        self.validation_Length = 254

        self.app: adsk.core.Application = adsk.core.Application.get()
        self.ui: adsk.core.UserInterface = self.app.userInterface
        self.vp: adsk.core.Viewport = self.app.activeViewport


    def isCorrectionOk(self, correctionTxt) -> str:
        if self._getReflectsCorrectionValues(1, correctionTxt) is None:
            return '補正の式が不正です!'

        if not self._getViewExtents(correctionTxt) > 0:
            return '補正の式の答えが0以上になるようにしてください!'

        return ''


    def execFullSize(self, correctionTxt):

        dumpmsg('**')
        dist = self._getViewLength()
        dumpmsg(f'Before Dist {dist}-{dist * 25.4 / self._get_dpi()}')

        viewExtents = self._getViewExtents(correctionTxt)

        cam: adsk.core.Camera = self.vp.camera
        cam.viewExtents = viewExtents

        self.vp.camera = cam
        self.vp.refresh()

        dist = self._getViewLength()
        dumpmsg(f'After Dist {dist}-{dist * 25.4 / self._get_dpi()}')

        setCorrection(correctionTxt)


    def getCorrectionTxt(self) -> str:
        return gatCorrection()


    def _getViewExtents(self, correctionTxt):
        try:
            dpi = self._get_dpi()
            pixel2millimeter = 25.4 / dpi
            dumpmsg(f'DPI {dpi}')

            dist = self._getViewLength()
            dumpmsg(f'ViewSpace Dist {dist}-{dist * pixel2millimeter}')

            viewLength = dist * pixel2millimeter
            ratio = (viewLength / self.validation_Length) ** 2

            cam: adsk.core.Camera = self.vp.camera
            return self._getReflectsCorrectionValues(cam.viewExtents * ratio, correctionTxt)

        except:
            if self.ui:
                self.ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


    def _getViewLength(self) -> float:
        cam: adsk.core.Camera = self.vp.camera

        screenVec: adsk.core.Vector3D = cam.eye.vectorTo(cam.target)
        vec: adsk.core.Vector3D = screenVec.crossProduct(cam.upVector)
        vec.normalize()
        vec.scaleBy(self.validation_Length * 0.1)

        pnt: adsk.core.Point3D = cam.target
        pnt.translateBy(vec)

        p1: adsk.core.Point2D = self.vp.modelToViewSpace(cam.target)
        p2: adsk.core.Point2D = self.vp.modelToViewSpace(pnt)

        return p1.distanceTo(p2)


    def _get_dpi(self) -> float:
        screen = Tk()
        return screen.winfo_fpixels('1i')


    def _getReflectsCorrectionValues(self, value, correction):
        try:
            return eval(f'{value}{correction}')
        except:
            return None


def dumpmsg(s):
    if DEBUG:
        adsk.core.Application.get().log(s)
        print(s)


def gatCorrection() -> str:
    if not CORRECTION_PATH.exists():
        setCorrection()

    with open(str(CORRECTION_PATH)) as f:
        data = f.read()
    
    dict = json.loads(data)
    if not CORRECTION_KEY in dict:
        setCorrection()
        return '*1'

    return dict[CORRECTION_KEY]


def setCorrection(txt = '*1'):
    try:
        with open(str(CORRECTION_PATH), 'w') as f:
            f.write(
                json.dumps(
                    {CORRECTION_KEY : txt}
                )
            )

    except:
        pass