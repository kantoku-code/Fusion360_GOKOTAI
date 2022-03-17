# Open Affected Documents
import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
import math

app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_MinimumBoundingRectangle'
CMD_NAME = '最小境界長方形'
CMD_Description = '平坦な面の境界から最小となる長方形のスケッチを作成'

# パネルにコマンドを昇格させることを指定します。
IS_PROMOTED = True

# TODO *** コマンドボタンが作成される場所を定義します。 ***
# これは、ワークスペース、タブ、パネル、および 
# コマンドの横に挿入されます。配置するコマンドを指定しない場合は
# 最後に挿入されます。

WORKSPACE_ID = config.design_workspace
TAB_ID = config.design_tab_id
TAB_NAME = config.design_tab_name

PANEL_ID = config.create_panel_id
PANEL_NAME = config.create_panel_name
PANEL_AFTER = config.create_panel_after

COMMAND_BESIDE_ID = ''

# コマンドアイコンのリソースの場所、ここではこのディレクトリの中に
# "resources" という名前のサブフォルダを想定しています。
ICON_FOLDER = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    'resources',
    ''
)

# イベントハンドラのローカルリストで、参照を維持するために使用されます。
# それらは解放されず、ガベージコレクションされません。
local_handlers = []

_surfIpt: adsk.core.SelectionCommandInput = None
_outerIpt: adsk.core.BoolValueCommandInput = None


# アドイン実行時に実行されます。
def start():
    # コマンドの定義を作成する。
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID,
        CMD_NAME,
        CMD_Description,
        ICON_FOLDER
    )

    # コマンド作成イベントのイベントハンドラを定義します。
    # このハンドラは、ボタンがクリックされたときに呼び出されます。
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** ユーザーがコマンドを実行できるように、UIにボタンを追加します。 ********
    # ボタンが作成される対象のワークスペースを取得します。
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    toolbar_tab = workspace.toolbarTabs.itemById(TAB_ID)
    if toolbar_tab is None:
        toolbar_tab = workspace.toolbarTabs.add(TAB_ID, TAB_NAME)

    # ボタンが作成されるパネルを取得します。
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    if panel is None:
        panel = toolbar_tab.toolbarPanels.add(PANEL_ID, PANEL_NAME, PANEL_AFTER, False)

    # 指定された既存のコマンドの後に、UI のボタンコマンド制御を作成します。
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

    # コマンドをメインツールバーに昇格させるかどうかを指定します。
    control.isPromoted = IS_PROMOTED


# アドイン停止時に実行されます。
def stop():
    # このコマンドのさまざまなUI要素を取得する
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # ボタンコマンドの制御を削除する。
    if command_control:
        command_control.deleteMe()

    # コマンドの定義を削除します。
    if command_definition:
        command_definition.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    cmd: adsk.core.Command = adsk.core.Command.cast(args.command)
    cmd.isPositionDependent = True

    # **inputs**
    inputs: adsk.core.CommandInputs = cmd.commandInputs

    global _surfIpt
    _surfIpt = inputs.addSelectionInput(
        'surfIptId',
        '平らな面',
        '平らな面を選択'
    )
    _surfIpt.addSelectionFilter('PlanarFaces')

    global _outerIpt
    _outerIpt = inputs.addBoolValueInput(
        'innerIptId',
        '外周は除外する',
        True,
        '',
        False
    )


    # **event**
    futil.add_handler(
        cmd.destroy,
        command_destroy,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.executePreview,
        command_executePreview,
        local_handlers=local_handlers
    )


def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global local_handlers
    local_handlers = []


def command_executePreview(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global _surfIpt, _outerIpt
    createBoundSkecth(
        _surfIpt.selection(0).entity,
        _outerIpt.value,
    )

    args.isValidResult = True

# ******************
def createBoundSkecth(
    face: adsk.fusion.BRepFace,
    outer: bool,
    toleranceAng: float = 0.01) -> adsk.fusion.Sketch:

    # ***********
    def getPairVectors(
        minAng: float,
        maxAng: float,
        divisionCount: int,
        vecU: adsk.core.Vector3D,
        vecV: adsk.core.Vector3D) -> list:

        vecX: adsk.core.Vector3D = vecU.copy()
        vecY: adsk.core.Vector3D = vecV.copy()


        axis: adsk.core.Vector3D = vecX.crossProduct(vecY)
        mat: adsk.core.Matrix3D = adsk.core.Matrix3D.create()

        mat.setWithCoordinateSystem(
            adsk.core.Point3D.create(0,0,0),
            vecX,
            vecY,
            axis
        )

        mat.setToRotation(
            math.radians(minAng),
            axis,
            adsk.core.Point3D.create(0,0,0)
        )
        vecX.transformBy(mat)
        vecY.transformBy(mat)
        pairVecs = [[vecX.copy(), vecY.copy()]]

        stepAng: float = (maxAng - minAng) / divisionCount
        mat.setToRotation(
            math.radians(stepAng),
            axis,
            adsk.core.Point3D.create(0,0,0)
        )
        for idx in range(1, divisionCount + 1):
            vecX.transformBy(mat)
            vecY.transformBy(mat)
            pairVecs.append(
                [
                    vecX.copy(),
                    vecY.copy()
                ]
            )
        return pairVecs

    def getMinOrientedBBox(
        loop: adsk.fusion.BRepLoop,
        vecX: adsk.core.Vector3D,
        vecY: adsk.core.Vector3D,
        toleranceAng: float,) -> adsk.core.OrientedBoundingBox3D:

        divisionCount = 10

        minAng = 0
        maxAng = 90
        stepAng: float = toleranceAng + 1

        app: adsk.core.Application = adsk.core.Application.get()
        measMgr: adsk.core.MeasureManager = app.measureManager

        while stepAng > toleranceAng:
            stepAng: float = (maxAng - minAng) / divisionCount

            vecs = getPairVectors(
                minAng,
                maxAng,
                divisionCount,
                vecX,
                vecY
            )

            boxes = []
            for vecU, vecV in vecs:
                boxes.append(
                    measMgr.getOrientedBoundingBox(
                        loop,
                        vecU,
                        vecV
                    )
                )

            minBox = min(boxes, key=lambda x: x.length * x.width)

            hitAng = math.degrees(vecX.angleTo(minBox.lengthDirection))
            minAng = hitAng - stepAng
            maxAng = hitAng + stepAng

        return minBox


    def getThreePoints(
        bBox: adsk.core.OrientedBoundingBox3D) -> list:

        halfLength = bBox.length * 0.5
        halfWidth = bBox.width * 0.5

        scaleList = [
            [halfLength, halfWidth],
            [-halfLength, halfWidth],
            [-halfLength, -halfWidth],
        ]

        threePointVectors = []
        for l, w in scaleList:
            v1 = bBox.lengthDirection.copy()
            v1.scaleBy(l)
            v2 = bBox.widthDirection.copy()
            v2.scaleBy(w)
            v1.add(v2)
            threePointVectors.append(v1)

        pnts = []
        for vec in threePointVectors:
            pnt: adsk.core.Point3D = bBox.centerPoint.copy()
            pnt.translateBy(vec)
            pnts.append(
                pnt
            )

        return pnts

    def drawRectLines(
        skt: adsk.fusion.Sketch,
        ThreePointsList: list):

        sktLines: adsk.fusion.SketchLines = skt.sketchCurves.sketchLines
        skt.isComputeDeferred = True
        for p1, p2, p3 in ThreePointsList:
            sktLines.addThreePointRectangle(
                p1,
                p2,
                p3
            )
        skt.isComputeDeferred = False

    # **********
    # get loops
    if outer:
        innerLoops = [l for l in face.loops if not l.isOuter]
    else:
        innerLoops = [l for l in face.loops]
    
    if len(innerLoops) < 1:
        return None

    # create sketch
    comp: adsk.fusion.Component = face.body.parentComponent
    skt: adsk.fusion.Sketch = comp.sketches.addWithoutEdges(face)

    # get vector
    vecX: adsk.core.Vector3D = skt.xDirection
    vecY: adsk.core.Vector3D = skt.yDirection

    if face.assemblyContext:
        occMat: adsk.core.Matrix3D = face.assemblyContext.transform2
        vecX.transformBy(occMat)
        vecY.transformBy(occMat)

    # get Minimum OrientedBoundingBox3D
    minBBoxes = [getMinOrientedBBox(l, vecX, vecY, toleranceAng) for l in innerLoops]

    # get three points
    ThreePointsList = [getThreePoints(b) for b in minBBoxes]

    # get matrix
    mat: adsk.core.Matrix3D = None

    sktMat: adsk.core.Matrix3D = skt.transform
    sktMat.invert()

    if face.assemblyContext:
        occMat: adsk.core.Matrix3D = face.assemblyContext.transform2
        occMat.invert()

        occMat.transformBy(sktMat)
        mat = occMat
    else:
        mat = sktMat

    # transform three points
    if not mat.isEqualTo(adsk.core.Matrix3D.create()):
        for pnts in ThreePointsList:
            for pnt in pnts:
                pnt.transformBy(mat)

    # draw BoundingBox
    drawRectLines(
        skt,
        ThreePointsList
    )

    return skt