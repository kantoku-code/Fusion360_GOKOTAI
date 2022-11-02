import traceback
import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
from .FullsizeFactory import FullsizeFactry
# import threading

app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_Fullsize'
CMD_NAME = '原寸大'
CMD_Description = '原寸大表示にします'

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


# ************
_fact: 'FullsizeFactry' = None
# # スレッド停止用
# _stopFlag = None
# EVENT_TIMER = 0.1
# _eventCoordination = False
_correctionIpt: adsk.core.TextBoxCommandInput = None
_messageIpt: adsk.core.TextBoxCommandInput = None
_lockIpt: adsk.core.BoolValueCommandInput = None

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

    global _backUpVisualStyle
    _backUpVisualStyle = futil.app.activeViewport.visualStyle

    cmd: adsk.core.Command = adsk.core.Command.cast(args.command)
    cmd.isPositionDependent = True
    cmd.isOKButtonVisible = False

    futil.add_handler(
        cmd.destroy,
        command_destroy,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.activate,
        command_activate,
        local_handlers=local_handlers
    )

    futil.add_handler(
        cmd.executePreview,
        command_executePreview,
        local_handlers=local_handlers
    )




    # inputs
    inputs: adsk.core.CommandInputs = cmd.commandInputs

    global _fact
    _fact = FullsizeFactry()

    correctionTxt = _fact.getCorrectionTxt()

    global _correctionIpt
    _correctionIpt = inputs.addTextBoxCommandInput(
        'correctionIptId',
        '補正',
        correctionTxt,
        1,
        False
    )

    global _lockIpt
    _lockIpt = inputs.addBoolValueInput(
        'lockIptId',
        'スケールのロック',
        True,
        '',
        False
    )


    global _messageIpt
    _messageIpt = inputs.addTextBoxCommandInput(
        'messageIptId',
        '情報',
        '',
        2,
        True
    )

    # global _stopFlag
    # _stopFlag = threading.Event()
    # myThread = MyThread(_stopFlag, EVENT_TIMER)
    # myThread.start()


def command_executePreview(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    # global _eventCoordination
    # if _eventCoordination:
    #     return

    try:
        global _correctionIpt
        correctionTxt = _correctionIpt.text

        global _messageIpt
        _messageIpt.text = ''

        global _fact
        msg = _fact.isCorrectionOk(correctionTxt)
        if len(msg) > 0:
            _messageIpt.text = msg
            return

        _fact.execFullSize(correctionTxt)

    except:
        pass


def command_activate(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    if isOrthographicCameraType():
        args.command.doExecute(False)
    else:
        futil.ui.messageBox('カメラを正投影に切り替えてください')


def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    # try:
    #     global _stopFlag
    #     _stopFlag.set()
    # except:
    #     pass

    global local_handlers
    local_handlers = []


def isOrthographicCameraType():
    app: adsk.core.Application = adsk.core.Application.get()

    vp: adsk.core.Viewport = app.activeViewport

    cam: adsk.core.Camera = vp.camera
    return cam.cameraType == adsk.core.CameraTypes.OrthographicCameraType


def getReflectsCorrectionValues(value, correction):
    try:
        return eval(f'{value}{correction}')
    except:
        return None


# class MyThread(threading.Thread):
#     def __init__(self, event, timer):
#         threading.Thread.__init__(self)
#         self.stopped = event
#         self.timer = timer
#     def run(self):
#         while not self.stopped.wait(self.timer):
#             global _eventCoordination
#             _eventCoordination = False
#             futil.log('-----Thread-----')