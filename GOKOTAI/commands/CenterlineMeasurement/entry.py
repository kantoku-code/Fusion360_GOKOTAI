import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
from .CenterlineMeasurementFactry import CenterlineMeasurementFactry as fact


app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_CenterlineMeasurement'
CMD_NAME = '中心線長さ'
CMD_Description = '選択されたパイプ形状の合計長さ測定'

# パネルにコマンドを昇格させることを指定します。
IS_PROMOTED = True

# TODO *** コマンドボタンが作成される場所を定義します。 ***
# これは、ワークスペース、タブ、パネル、および 
# コマンドの横に挿入されます。配置するコマンドを指定しない場合は
# 最後に挿入されます。

WORKSPACE_ID = config.design_workspace
TAB_ID = config.design_tab_id
TAB_NAME = config.design_tab_name

PANEL_ID = config.inspect_panel_id
PANEL_NAME = config.inspect_panel_name
PANEL_AFTER = config.inspect_panel_after

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
_surfIpt: adsk.core.SelectionCommandInput = None

_txtIpt: adsk.core.TextBoxCommandInput = None

_sktIpt: adsk.core.BoolValueCommandInput = None
_sktValue: bool = False


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

    unitMgr: adsk.fusion.FusionUnitsManager = futil.app.activeProduct.unitsManager

    global _surfIpt
    _surfIpt = inputs.addSelectionInput(
        'surfIptId',
        '面',
        unitMgr.formatInternalValue(0)
    )
    _surfIpt.addSelectionFilter(adsk.core.SelectionCommandInput.Faces)
    _surfIpt.setSelectionLimits(0)

    global _txtIpt
    _txtIpt = inputs.addTextBoxCommandInput(
        'txtTptId',
        '合計長さ',
        unitMgr.formatInternalValue(0),
        1,
        True
    )

    global _sktIpt, _sktValue
    _sktIpt = inputs.addBoolValueInput(
        'sktIptId',
        '結果をスケッチで作成',
        True,
        '',
        _sktValue
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

    futil.add_handler(
        cmd.inputChanged,
        command_inputChanged,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.execute,
        command_execute,
        local_handlers=local_handlers
    )

    # futil.add_handler(
    #     cmd.preSelect,
    #     command_preSelect,
    #     local_handlers=local_handlers
    # )


def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global local_handlers
    local_handlers = []


def command_executePreview(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    fact.drawCG(getSelectAllFaces())


def command_inputChanged(args: adsk.core.InputChangedEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    length = fact.getAllLength(getSelectAllFaces())

    unitMgr: adsk.fusion.FusionUnitsManager = futil.app.activeProduct.unitsManager
    msg = unitMgr.formatInternalValue(length)

    global _txtIpt, _surfIpt
    _txtIpt.text = msg
    _surfIpt.commandPrompt = '合計:' + msg


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global _sktIpt, _sktValue
    _sktValue = _sktIpt.value

    if not _sktValue:
        return

    fact.drawSketch(getSelectAllFaces())


def command_preSelect(args: adsk.core.SelectionEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    if not fact.hasCenterCurve(args.selection.entity):
        args.isSelectable = False


def getSelectAllFaces():
    global _surfIpt
    return [_surfIpt.selection(idx).entity for idx in range(_surfIpt.selectionCount)]