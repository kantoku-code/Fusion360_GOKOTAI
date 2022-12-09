import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
from .LowPoly_Factry import LowPoly_Factry

app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_low_poly'
CMD_NAME = 'ローポリ'
CMD_Description = 'ローポリゴンSTLをエクスポートします。'

# パネルにコマンドを昇格させることを指定します。
IS_PROMOTED = True

# TODO *** コマンドボタンが作成される場所を定義します。 ***
# これは、ワークスペース、タブ、パネル、および 
# コマンドの横に挿入されます。配置するコマンドを指定しない場合は
# 最後に挿入されます。

WORKSPACE_ID = config.design_workspace
TAB_ID = config.design_tab_id
TAB_NAME = config.design_tab_name

PANEL_ID = config.io_panel_id
PANEL_NAME = config.io_panel_name
PANEL_AFTER = config.io_panel_after

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

UNITS_MAP = {
    'センチメートル': 'cm',
    'ミリメートル': 'mm',
    'メートル': 'm',
    'インチ': 'in',
    'フィート': 'ft',
}

FILE_STRUCTRE_ITEMS = [
    '1ファイル',
    'ボディ毎に1ファイル',
]

_bodyIpt: adsk.core.SelectionCommandInput = None
_unitIpt: adsk.core.DropDownCommandInput = None
_unit = 'mm'
_fileStructureIpt: adsk.core.DropDownCommandInput = None
_fileStructure = 0
_toleranceIpt: adsk.core.FloatSliderCommandInput = None
_tolerance = 0.1

_points = []

_fact: 'LowPoly_Factry' = None

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

    # other
    global _fact
    _fact = LowPoly_Factry()

    # **inputs**
    inputs: adsk.core.CommandInputs = cmd.commandInputs

    global _bodyIpt
    _bodyIpt = inputs.addSelectionInput(
        'bodyIptId',
        '選択',
        'ボディを選択'
    )
    _bodyIpt.setSelectionLimits(0)
    _bodyIpt.addSelectionFilter(adsk.core.SelectionCommandInput.Bodies)
    _bodyIpt.addSelectionFilter(adsk.core.SelectionCommandInput.Occurrences)
    _bodyIpt.addSelectionFilter(adsk.core.SelectionCommandInput.RootComponents)

    global _unitIpt, _unit
    _unitIpt = inputs.addDropDownCommandInput(
        '_unitIptId',
        '単位のタイプ',
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    unitItems = _unitIpt.listItems
    for key in UNITS_MAP.keys():
        select = True if UNITS_MAP[key] == _unit else False
        unitItems.add(key, select, '')

    global _fileStructureIpt, _fileStructure
    _fileStructureIpt = inputs.addDropDownCommandInput(
        '_fileStructureIptId',
        '構造',
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    fileItems = _fileStructureIpt.listItems
    for fs in FILE_STRUCTRE_ITEMS:
        fileItems.add(fs, False, '')
    fileItems.item(0).isSelected = True

    global _toleranceIpt, _tolerance
    _toleranceIpt = inputs.addFloatSliderCommandInput(
        'toleranceIptId',
        'トレランス',
        futil.app.activeProduct.unitsManager.defaultLengthUnits,
        0.0001,
        2,
        False,
    )
    _toleranceIpt.valueOne = _tolerance

    # **event**
    futil.add_handler(
        cmd.destroy,
        command_destroy,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.execute,
        command_execute,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.validateInputs,
        command_validateInputs,
        local_handlers=local_handlers
    )


def command_validateInputs(args: adsk.core.ValidateInputsEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global _bodyIpt
    if _bodyIpt.selectionCount < 1:
        args.areInputsValid = False


def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global local_handlers
    local_handlers = []


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    path = getExportPath()
    if len(path) < 1:
        return

    global _bodyIpt
    bodies = [_bodyIpt.selection(idx).entity for idx in range(_bodyIpt.selectionCount)]

    global _unitIpt
    unitsMgr: adsk.core.UnitsManager = futil.app.activeProduct.unitsManager
    ratio = unitsMgr.convert(
        1,
        unitsMgr.internalUnits,
        UNITS_MAP[_unitIpt.selectedItem.name],
    )

    global _fileStructureIpt
    isOneFile = True if _fileStructureIpt.selectedItem.index == 0 else False

    global _fact, _toleranceIpt
    _fact.export_meshes(
        bodies,
        _toleranceIpt.valueOne,
        ratio,
        path,
        isOneFile,
    )

    # ***
    global _unit
    _unit = UNITS_MAP[_unitIpt.selectedItem.name]

    global _fileStructure
    _fileStructure = _fileStructureIpt.selectedItem.index

    global _tolerance
    _tolerance = _toleranceIpt.valueOne


def getExportPath() -> str:
    dlg: adsk.core.FileDialog = futil.app.userInterface.createFileDialog()
    dlg.title = 'export'
    dlg.isMultiSelectEnabled = False
    dlg.filter = 'STLファイル(*.stl)'
    dlg.initialFilename = futil.app.activeDocument.name

    if dlg.showSave() != adsk.core.DialogResults.DialogOK:
        return ''

    return dlg.filename