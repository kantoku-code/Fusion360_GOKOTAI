# Open Affected Documents
import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_MinimumBoundingBox'
CMD_NAME = '最小境界ボックス'
CMD_Description = '最小サイズなる(とは限らない)境界ボックスを作成'

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

# **** 設定 ****
_bodyIpt: adsk.core.SelectionCommandInput = None

_quantizeIpt: adsk.core.DropDownCommandInput = None

# 切り上げ単位の追加を行いたい場合はこちらの
# リストに文字列として追加して下さい。
_roundUpUnits = [
    '無し',
    '0.001',
    '0.01',
    '0.5',
    '0.1',
    '1',
    '5',
    '10',
    '100',
]

# デフォルトを変更したい場合は、上記リストの
# 中からこちらを設定して下さい。
_ddDefault = '1'

_fixAxisIpt: adsk.core.BoolValueCommandInput = None

# 方向固定のデフォルトをOnにしたい場合は以下を "True" にして下さい
_fixAxisDefault = False
# **** 設定 ****


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
        '調べるソリッドボディを選択'
    )
    _bodyIpt.addSelectionFilter('SolidBodies')

    global _quantizeIpt, _ddItemsDict, _ddDefault
    _quantizeIpt = inputs.addDropDownCommandInput(
        'quantizeIptId',
        '切り上げ単位',
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    ddItems = _quantizeIpt.listItems
    for item in _roundUpUnits:
        isDefault = False
        if _ddDefault == item:
            isDefault = True
        ddItems.add(
            item,
            isDefault,
            ''
        )

    global _fixAxisIpt, _fixAxisDefault
    _fixAxisIpt = inputs.addBoolValueInput(
        'fixAxisIptId',
        '方向を固定',
        True,
        '',
        _fixAxisDefault
    )

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

    global _bodyIpt, _quantizeIpt, _fixAxisIpt
    initBox(
        _bodyIpt.selection(0).entity,
        _quantizeIpt.selectedItem.name,
        _fixAxisIpt.value,
    )

    args.isValidResult = True

# ******************
def initBox(
    body: adsk.fusion.BRepBody,
    roundUpStr: str,
    isFixAxis: bool):

    app: adsk.core.Application = adsk.core.Application.get()
    des: adsk.fusion.Design = app.activeProduct
    unitMgr: adsk.core.UnitsManager = des.unitsManager

    # ---------
    def is_num(s):
        try:
            float(s)
        except ValueError:
            return False
        else:
            return True

    def roundUp(value, roundUpUnit):
        v = unitMgr.convert(
            value,
            unitMgr.internalUnits,
            unitMgr.defaultLengthUnits
        )

        q, mod = divmod(v ,roundUpUnit)

        if mod > 0:
            q += 1
        
        res = unitMgr.convert(
            q * roundUpUnit,
            unitMgr.defaultLengthUnits,
            unitMgr.internalUnits
        )

        return res

    def getDisplayValue(value):
        return unitMgr.formatInternalValue(
            value,
            unitMgr.defaultLengthUnits,
        )

    # ***********

    # get bbox
    xAxis: adsk.core.Vector3D = None
    yAxis: adsk.core.Vector3D = None
    if isFixAxis:
        xAxis = adsk.core.Vector3D.create(1, 0, 0)
        yAxis = adsk.core.Vector3D.create(0, 1, 0)
    else:
        phyProp: adsk.fusion.PhysicalProperties = body.getPhysicalProperties(
            adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy
        )
        _, xAxis, yAxis, _ = phyProp.getPrincipalAxes()

    measMgr: adsk.core.MeasureManager = app.measureManager
    oriBBox: adsk.core.OrientedBoundingBox3D = measMgr.getOrientedBoundingBox(
        body,
        xAxis,
        yAxis
    )

    # resize
    if is_num(roundUpStr):
        oriBBox.length = roundUp(oriBBox.length, float(roundUpStr))
        oriBBox.width = roundUp(oriBBox.width, float(roundUpStr))
        oriBBox.height = roundUp(oriBBox.height, float(roundUpStr))

    # update bbox
    mat: adsk.core.Matrix3D = None
    if body.assemblyContext:
        mat = body.assemblyContext.transform2
        mat.invert()

        pnt: adsk.core.Point3D = oriBBox.centerPoint.copy()
        pnt.transformBy(mat)
        xAxis.transformBy(mat)
        yAxis.transformBy(mat)
        oriBBox.centerPoint = pnt
        oriBBox.setOrientation(xAxis, yAxis)

    # init temp body
    tempMgr: adsk.fusion.TemporaryBRepManager = adsk.fusion.TemporaryBRepManager.get()
    tmpBody: adsk.fusion.BRepBody = tempMgr.createBox(oriBBox)

    # add body
    isParametric: bool = True
    if des.designType == adsk.fusion.DesignTypes.DirectDesignType:
        isParametric = False

    comp: adsk.fusion.Component = body.parentComponent
    baseFeat: adsk.fusion.BaseFeature = None
    if isParametric:
        baseFeat = comp.features.baseFeatures.add()

    bodies: adsk.fusion.BRepBodies = comp.bRepBodies
    if isParametric:
        baseFeat.startEdit()
        try:
            box: adsk.fusion.BRepBody = bodies.add(tmpBody, baseFeat)
            box.opacity = 0.5
            if mat != adsk.core.Matrix3D.create():
                box.tra
        except:
            pass
        finally:
            baseFeat.finishEdit()
            box: adsk.fusion.BRepBody = baseFeat.bodies[0]
    else:
        box: adsk.fusion.BRepBody = bodies.add(tmpBody)
        box.opacity = 0.5

    name = f'{getDisplayValue(oriBBox.length)} x '
    name += f'{getDisplayValue(oriBBox.width)} x '
    name += f'{getDisplayValue(oriBBox.height)}'
    if box:
        box.name = name