import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
import math

app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_Meteor'
CMD_NAME = 'メテオ'
CMD_Description = 'ボディにZの上方向から大量の点を降り注ぎます'

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

_bodyIpt: adsk.core.SelectionCommandInput = None
_countIpt: adsk.core.IntegerSpinnerCommandInput = None

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

    global _bodyIpt
    _bodyIpt = inputs.addSelectionInput(
        'bodyIptId',
        'ボディ',
        'ボディを選択'
    )
    _bodyIpt.addSelectionFilter('Bodies')

    global _countIpt
    _countIpt = inputs.addIntegerSpinnerCommandInput(
        'countIptId',
        '分割数',
        1,
        30,
        1,
        10
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

    global _countIpt
    # unitMgr: adsk.core.UnitsManager = futil.app.activeProduct.unitsManager
    # pitch = unitMgr.convert(
    #     _countIpt.value,
    #     unitMgr.defaultLengthUnits,
    #     unitMgr.internalUnits
    # )

    global _bodyIpt
    initMeteorSketch(
        _bodyIpt.selection(0).entity,
        adsk.core.Vector3D.create(0,0,-1),
        _countIpt.value,
    )

    args.isValidResult = True

# ******************

def initMeteorSketch(
    targetBody: adsk.fusion.BRepBody,
    rayDirection: adsk.core.Vector3D,
    stepCount: int = 10,
    isRev: bool = False) -> adsk.fusion.Sketch:

    comp: adsk.fusion.Component = targetBody.parentComponent
    pnts = getPointsFromRayDirection(
        targetBody,
        rayDirection,
        stepCount,
    )

    if len(pnts) < 1:
        return

    skt: adsk.fusion.Sketch = comp.sketches.add(
        comp.xYConstructionPlane
    )

    sktPnts: adsk.fusion.SketchPoints = skt.sketchPoints
    skt.isComputeDeferred = True
    [sktPnts.add(p) for p in pnts]
    skt.isComputeDeferred = False

    return skt

def getPointsFromRayDirection(
    targetBody: adsk.fusion.BRepBody,
    rayDirection: adsk.core.Vector3D,
    stepCount: int = 10,
    isRev: bool = False) -> list:

    comp: adsk.fusion.Component = targetBody.parentComponent

    bBox: adsk.core.BoundingBox3D = targetBody.boundingBox
    minPnt: adsk.core.Point3D = bBox.minPoint
    maxPnt: adsk.core.Point3D = bBox.maxPoint

    stepX = (bBox.maxPoint.x - bBox.minPoint.x) / (stepCount - 1)
    stepY = (bBox.maxPoint.y - bBox.minPoint.y) / (stepCount - 1)

    tempPnts = []
    for idxX in range(stepCount):
        for idxY in range(stepCount):
            tempPnts.append(
                adsk.core.Point3D.create(
                    minPnt.x + stepX * idxX,
                    minPnt.y + stepY * idxY,
                    maxPnt.z + 1
                )
            )

    pnts = []
    hitPnts: adsk.core.ObjectCollection = adsk.core.ObjectCollection.create() 
    for pnt in tempPnts:
        hitPnts.clear()

        bodies: adsk.core.ObjectCollection = comp.findBRepUsingRay(
            pnt,
            rayDirection,
            adsk.fusion.BRepEntityTypes.BRepBodyEntityType,
            -1.0,
            True,
            hitPnts
        )

        if bodies.count < 1:
            continue

        bodyLst = [b for b in bodies]
        hitPntLst = [p for p in hitPnts]

        for body, pnt in zip(bodyLst, hitPntLst):
            if body == targetBody:
                pnts.append(pnt)
                continue

    return pnts