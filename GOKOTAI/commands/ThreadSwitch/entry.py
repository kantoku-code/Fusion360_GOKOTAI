import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_ThreadSwitch'
CMD_NAME = 'ネジモデル化スイッチ'
CMD_Description = '全てのネジのモデル化を切り替えます'

# パネルにコマンドを昇格させることを指定します。
IS_PROMOTED = True

# TODO *** コマンドボタンが作成される場所を定義します。 ***
# これは、ワークスペース、タブ、パネル、および 
# コマンドの横に挿入されます。配置するコマンドを指定しない場合は
# 最後に挿入されます。

WORKSPACE_ID = config.design_workspace
TAB_ID = config.design_tab_id
TAB_NAME = config.design_tab_name

PANEL_ID = config.modify_panel_id
PANEL_NAME = config.modify_panel_name
PANEL_AFTER = config.modify_panel_after

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

_modelIpt: adsk.core.BoolValueCommandInput = None


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

    des: adsk.fusion.Design = futil.app.activeProduct
    root: adsk.fusion.Component = des.rootComponent
    threads: adsk.fusion.ThreadFeatures = root.features.threadFeatures

    global _modelIpt
    msg = ''
    if des.designType != adsk.fusion.DesignTypes.ParametricDesignType:
        msg = '履歴をキャプチャでのみ、利用可能です!'
    else:
        msg = f'{threads.count}個のモデル化可能なネジが有ります。\n '
        msg += f'全てモデル化しますか？\n'

    _modelIpt = inputs.addBoolValueInput(
        'modelIptId',
        msg,
        True,
        '',
        True
    )

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

def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global local_handlers
    local_handlers = []


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global _modelIpt
    execModeled(_modelIpt.value)


def command_validateInputs(args: adsk.core.ValidateInputsEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    des: adsk.fusion.Design = futil.app.activeProduct

    if des.designType != adsk.fusion.DesignTypes.ParametricDesignType:
        args.areInputsValid = False


# ******************
def execModeled(isModeled: bool):
    app: adsk.core.Application = adsk.core.Application.get()
    ui = app.userInterface
    des: adsk.fusion.Design = app.activeProduct
    root: adsk.fusion.Component = des.rootComponent
    sels: adsk.core.Selections = ui.activeSelections

    tl: adsk.fusion.Timeline = des.timeline
    tlPos = tl.markerPosition

    threads: adsk.fusion.ThreadFeatures = root.features.threadFeatures
    thread: adsk.fusion.ThreadFeature
    for thread in threads:
        timeObj: adsk.fusion.TimelineObject = thread.timelineObject

        if thread.linkedFeatures.count < 1:
            # ThreadFeature
            timeObj.rollTo(True)
            if thread.isModeled != isModeled:
                thread.isModeled = isModeled
        else:
            # HoleFeature
            hole =  adsk.fusion.HoleFeature.cast(thread.linkedFeatures[0])
            if not hole:
                continue
            timeObj.rollTo(False)

            isModeledNumber = 1 if isModeled else 0

            sels.clear()
            sels.add(hole)

            app.executeTextCommand(u'Commands.Start FusionDcHoleEditCommand')
            dialogInfo = app.executeTextCommand(u'Toolkit.cmdDialog')
            if 'infoModeled' in dialogInfo:
                app.executeTextCommand(u'Commands.SetBool infoModeled {}'.format(isModeledNumber))
                app.executeTextCommand(u'NuCommands.CommitCmd')

    tl.markerPosition = tlPos
    sels.clear()