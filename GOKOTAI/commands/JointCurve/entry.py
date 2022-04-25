import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
import math

app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_JointCurve'
CMD_NAME = '連結線'
CMD_Description = '線を連結したスケッチを作成します'

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

_tolerance = [
    1.0,
    0.1,
    0.01
]
_crvIpt: adsk.core.SelectionCommandInput = None
_toleranceIpt: adsk.core.DropDownCommandInput = None

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

    global _crvIpt
    _crvIpt = inputs.addSelectionInput(
        'crvIptId',
        '曲線',
        'スケッチの曲線を選択'
    )
    _crvIpt.addSelectionFilter = adsk.core.SelectionCommandInput.SketchCurves
    _crvIpt.setSelectionLimits(0)


    global _toleranceIpt
    _toleranceIpt = inputs.addDropDownCommandInput(
        'toleranceIptId',
        'トレランス',
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    listItems: adsk.core.ListItems = _toleranceIpt.listItems
    listItems.add('低', False, '')
    listItems.add('中', True, '')
    listItems.add('高', False, '')

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

    futil.add_handler(
        cmd.validateInputs,
        command_validateInputs,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.preSelect,
        command_preSelect,
        local_handlers=local_handlers
    )

def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global local_handlers
    local_handlers = []


def command_executePreview(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')


    global _crvIpt
    if _crvIpt.selectionCount < 1:
        return

    sktCrv: adsk.fusion.SketchCurve = _crvIpt.selection(0).entity
    refSkt: adsk.fusion.Sketch = sktCrv.parentSketch
    occ: adsk.fusion.Occurrence = refSkt.assemblyContext

    comp: adsk.fusion.Component = None
    mat: adsk.core.Matrix3D = None
    if occ:
        if occ.isReferencedComponent:
            # link occ
            comp = getRoot()
        else:
            # inner occ
            comp = refSkt.parentComponent
            mat = occ.transform2
        pass
    else:
        # root
        comp = getRoot()

    crvs = getSelectEntityWorldGeometrys()
    if len(crvs) < 1:
        return

    global _toleranceIpt, _tolerance
    tolerance = _tolerance[_toleranceIpt.selectedItem.index]

    initConvertCurves(crvs, comp, tolerance, mat)

    args.isValidResult = True


def command_validateInputs(args: adsk.core.ValidateInputsEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global _crvIpt
    if _crvIpt.selectionCount < 1:
        args.areInputsValid = False
        return

    crvs = getSelectEntityWorldGeometrys()
    if len(crvs) < 1:
        args.areInputsValid = False


def command_preSelect(args: adsk.core.SelectionEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')
    try:
        sktCrv: adsk.fusion.SketchCurve = adsk.fusion.SketchCurve.cast(
            args.selection.entity
        )
        if not sktCrv:
            args.isSelectable = False
            return

        if not initChainedCurves(
            getSelectEntityWorldGeometrys(),
            sktCrv.worldGeometry):

            args.isSelectable = False

    except:
        args.isSelectable = False


# ******************
def convertCurve(
    crv: adsk.core.NurbsCurve3D,
    skt: adsk.fusion.Sketch,
    tolerance: float):

    eva: adsk.core.CurveEvaluator3D = crv.evaluator
    _, sPnt, ePnt = eva.getEndPoints()
    _, prms = eva.getParametersAtPoints(
        [sPnt, ePnt]
    )
    _, pnts = eva.getStrokes(prms[0], prms[1], tolerance)

    objs: adsk.core.ObjectCollection = adsk.core.ObjectCollection.create()
    [objs.add(c) for c in pnts]

    skt.sketchCurves.sketchFittedSplines.add(objs)


def initConvertCurves(
    geos: list,
    comp: adsk.fusion.Component,
    tolerance: float,
    mat: adsk.core.Matrix3D):

    crvs = []
    for geo in geos:
        if hasattr(geo, 'asNurbsCurve'):
            crvs.append(geo.asNurbsCurve)
        else:
            crvs.append(geo)

    crv: adsk.core.NurbsCurve3D = initChainedCurves(crvs)
    if not crv:
        return

    skt: adsk.fusion.Sketch = comp.sketches.add(comp.xYConstructionPlane)
    skt.name = 'Joint Curve'

    if mat:
        mat.invert()
        crv.transformBy(mat)

    skt.isComputeDeferred = True
    convertCurve(crv, skt, tolerance)
    skt.isComputeDeferred = False


def initChainedCurves(crvs: list, ent: adsk.core.NurbsCurve3D = None) -> adsk.core.NurbsCurve3D:
    if ent:
        crvs.append(ent)

    crv: adsk.core.NurbsCurve3D = crvs.pop(0)
    sPnt: adsk.core.Point3D = crv.controlPoints[0]
    ePnt: adsk.core.Point3D = crv.controlPoints[-1]
    chainedLst = [crv]

    for crv in crvs:
        sTmp: adsk.core.Point3D = crv.controlPoints[0]
        eTmp: adsk.core.Point3D = crv.controlPoints[-1]

        if ePnt.isEqualTo(sTmp):
            chainedLst.append(crv)
            ePnt = eTmp
        elif sPnt.isEqualTo(eTmp):
            chainedLst.insert(0, crv)
            sPnt = sTmp
        elif sPnt.isEqualTo(sTmp):
            chainedLst.insert(0, reverseNurbsCurve(crv))
            sPnt = eTmp
        elif ePnt.isEqualTo(eTmp):
            chainedLst.append(reverseNurbsCurve(crv))
            ePnt = sTmp
        else:
            return None

    crv = chainedLst.pop(0)
    for c in chainedLst:
        crv = crv.merge(c)

    return crv


def getSelectEntityWorldGeometrys() -> list:
    global _crvIpt
    if _crvIpt.selectionCount < 1:
        return []

    geos = [_crvIpt.selection(idx).entity.worldGeometry
        for idx in range(_crvIpt.selectionCount)]

    crvs = []
    for geo in geos:
        if hasattr(geo, 'asNurbsCurve'):
            crvs.append(geo.asNurbsCurve)
        else:
            crvs.append(geo)

    return crvs


def reverseNurbsCurve(curve: adsk.core.NurbsCurve3D) -> adsk.core.NurbsCurve3D:
    _, points, degree, knots, isRational, weights, isPeriodic = curve.getData()
    points = points[::-1]
    weights = weights[::-1]

    if isRational:
        return adsk.core.NurbsCurve3D.createRational(points, degree, knots, weights, isPeriodic)
    else:
        return adsk.core.NurbsCurve3D.createNonRational(points, degree, knots, isPeriodic)


def getRoot() -> adsk.fusion.Component:
    app: adsk.core.Application = adsk.core.Application.get()
    des: adsk.fusion.Design = app.activeProduct
    return des.rootComponent