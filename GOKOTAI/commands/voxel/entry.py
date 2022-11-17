import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
from .VoxelFactry import VoxelFactry
import time

app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_voxel'
CMD_NAME = 'ボクセル'
CMD_Description = '指定したボディを元にボクセル化します。'

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
_insideIpt: adsk.core.BoolValueCommandInput = None
_combinIpt: adsk.core.BoolValueCommandInput = None
_infoIpt: adsk.core.TextBoxCommandInput = None

_fact: 'VoxelFactry' = None
_completed = False #executeの後にexecutePreviewが発生する対策用

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
        '分割レベル',
        1,
        10,
        1,
        3
    )

    global _infoIpt
    _infoIpt = inputs.addTextBoxCommandInput(
        'infoIptId',
        '1辺の長さ',
        '-',
        1,
        True
    )

    global _insideIpt
    _insideIpt = inputs.addBoolValueInput(
        'insideIptId',
        '中身もボクセル化',
        True,
        '',
        True
    )

    global _combinIpt
    _combinIpt = inputs.addBoolValueInput(
        'combinIptId',
        '全てを結合する',
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

    futil.add_handler(
        cmd.execute,
        command_execute,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.inputChanged,
        command_inputChanged,
        local_handlers=local_handlers
    )

    global _fact
    _fact = VoxelFactry()

    global _completed
    _completed = False


def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global local_handlers
    local_handlers = []


def command_executePreview(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global _completed
    if _completed:
        return

    global _fact
    base_Box: adsk.fusion.BRepBody = _fact.get_base_box()

    if not base_Box:
        return

    root: adsk.fusion.Component = futil.app.activeProduct.rootComponent
    cgGroup: adsk.fusion.CustomGraphicsGroup = root.customGraphicsGroups.add()

    cgBox: adsk.fusion.CustomGraphicsBRepBody = cgGroup.addBRepBody(base_Box)
    cgBox.setOpacity(0.2, True)

    futil.log(f'{CMD_NAME}:{args.firingEvent.name} - done')


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    t = time.time()

    global _completed
    _completed = True

    global _fact, _insideIpt, _combinIpt
    _fact.create_voxel(_insideIpt.value, _combinIpt.value)

    futil.log(f'{CMD_NAME}:execute time:{time.time() - t}s')


def command_inputChanged(args: adsk.core.InputChangedEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global _bodyIpt, _countIpt
    if not args.input in [_bodyIpt, _countIpt]:
        return

    global _fact
    if _bodyIpt.selectionCount > 0:
        _fact.set_body(_bodyIpt.selection(0).entity)
    else:
        _fact.set_body(None)

    _fact.set_division_level(_countIpt.value)


    unitSize = _fact.get_unit_size()

    global _infoIpt
    if unitSize < 0:
        _infoIpt.text = '-'
    else:
        unitMgr: adsk.core.UnitsManager = futil.app.activeProduct.unitsManager
        _infoIpt.text = unitMgr.formatInternalValue(unitSize)