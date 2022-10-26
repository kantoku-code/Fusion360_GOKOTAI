import traceback
import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
from tkinter import *

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
        cmd.execute,
        command_execute,
        local_handlers=local_handlers
    )


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    execFullSize()


def command_activate(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    if isOrthographicCameraType():
        args.command.doExecute(False)
    else:
        futil.ui.messageBox('カメラを正投影に切り替えてください')


def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global _backUpVisualStyle
    futil.app.activeViewport.visualStyle = _backUpVisualStyle

    global local_handlers
    local_handlers = []


def isOrthographicCameraType():
    app: adsk.core.Application = adsk.core.Application.get()

    vp: adsk.core.Viewport = app.activeViewport

    cam: adsk.core.Camera = vp.camera
    return cam.cameraType == adsk.core.CameraTypes.OrthographicCameraType


def execFullSize():
    validation_Length = 254
    app: adsk.core.Application = adsk.core.Application.get()
    ui: adsk.core.UserInterface = app.userInterface
    vp: adsk.core.Viewport = app.activeViewport

    def get_dpi() -> float:
        screen = Tk()
        return screen.winfo_fpixels('1i')

    def getViewLength() -> float:
        cam: adsk.core.Camera = vp.camera

        screenVec: adsk.core.Vector3D = cam.eye.vectorTo(cam.target)
        vec: adsk.core.Vector3D = screenVec.crossProduct(cam.upVector)
        vec.normalize()
        vec.scaleBy(validation_Length * 0.1)

        pnt: adsk.core.Point3D = cam.target
        pnt.translateBy(vec)

        # p1: adsk.core.Point2D = vp.modelToViewSpace(cam.target)
        # p2: adsk.core.Point2D = vp.modelToViewSpace(pnt)

        p1: adsk.core.Point2D = vp.viewToScreen(vp.modelToViewSpace(cam.target))
        p2: adsk.core.Point2D = vp.viewToScreen(vp.modelToViewSpace(pnt))

        return p1.distanceTo(p2)

    def dumpmsg(s):
        adsk.core.Application.get().log(s)
        print(s)

    try:
        pixel2millimeter = 25.4 / get_dpi()
        dumpmsg(f'DPI {get_dpi()}')

        dist = getViewLength()
        dumpmsg(f'ViewSpace Dist {dist}-{dist * pixel2millimeter}')

        viewLength = dist * pixel2millimeter
        ratio = (viewLength / validation_Length) ** 2

        cam = vp.camera
        cam.viewExtents = cam.viewExtents * ratio
        vp.camera = cam
        vp.refresh()

        dist = getViewLength()
        dumpmsg(f'ViewSpace Dist {dist}-{dist * pixel2millimeter}')
        dumpmsg('**')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))