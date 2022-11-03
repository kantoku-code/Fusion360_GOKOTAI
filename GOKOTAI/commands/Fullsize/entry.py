import traceback
import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
from .FullsizeFactory import FullsizeFactry
import pathlib
import json

app = adsk.core.Application.get()
ui = app.userInterface

THIS_DIR = pathlib.Path(__file__).resolve().parent

# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_Fullsize'
CMD_NAME = '原寸大'
CMD_Description = '原寸大表示にします'
PALETTE_NAME = "原寸大"

# Using "global" variables by referencing values from /config.py
PALETTE_ID = config.fullsize_palette_id

# Specify the full path to the local html. You can also use a web URL
# such as 'https://www.autodesk.com/'
PALETTE_URL = str(THIS_DIR / 'index.html')

# The path function builds a valid OS path. This fixes it to be a valid local URL.
PALETTE_URL = PALETTE_URL.replace('\\', '/')

# Set a default docking behavior for the palette
PALETTE_DOCKING = adsk.core.PaletteDockingStates.PaletteDockStateFloating

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
# _lock_mode = False
# PRODUCT_TYPE_WHITE_LIST = (
#     'DesignProductType'
# )

PALETTE_WIDTH = 200
PALETTE_HEIGHT_NORMAL = 200


# ********

# Executed when add-in is run.
def start():
    global ui
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Add command created handler. The function passed here will be executed when the command is executed.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

    # Specify if the command is promoted to the main toolbar. 
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    palette = ui.palettes.itemById(PALETTE_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()

    # Delete the Palette
    if palette:
        palette.deleteMe()


# Event handler that is called when the user clicks the command button in the UI.
# To have a dialog, you create the desired command inputs here. If you don't need
# a dialog, don't create any inputs and the execute event will be immediately fired.
# You also need to connect to any command related events here.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME}: Command created event.')

    # Create the event handlers you will need for this instance of the command
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)
    # futil.add_handler(futil.app.cameraChanged, application_cameraChanged, local_handlers=local_handlers)

    global _fact
    _fact = FullsizeFactry()

    if not isOrthographicCameraType():
        futil.app.userInterface.messageBox(
            'カメラを正投影に切り替えてください'
        )

    # onWorkspaceActivated = MyWorkspaceActivatedHandler()
    # ui.workspaceActivated.add(onWorkspaceActivated)
    # _handlers.append(onWorkspaceActivated)

# def application_cameraChanged(args: adsk.core.CameraEventArgs):
#     # Code to react to the event.
#     futil.log('In application_cameraChanged event handler.')

#     global _lock_mode
#     if not _lock_mode:
#         return

#     global _fact
#     if _fact.getStateViewExtents() != args.viewport.camera.viewExtents:
#         _fact.reDraw()

# Because no command inputs are being added in the command created event, the execute
# event is immediately fired.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME}: Command execute event.')

    createPalette()


# Use this to handle a user closing your palette.
def palette_closed(args: adsk.core.UserInterfaceGeneralEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME}: Palette was closed.')

    global _handlers
    _handlers = []


# Use this to handle a user navigating to a new page in your palette.
def palette_navigating(args: adsk.core.NavigationEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME}: Palette navigating event.')

    # Get the URL the user is navigating to:
    url = args.navigationURL

    log_msg = f"User is attempting to navigate to {url}\n"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)

    # Check if url is an external site and open in user's default browser.
    if url.startswith("http"):
        args.launchExternally = True


# Use this to handle events sent from javascript in your palette.
def palette_incoming(html_args: adsk.core.HTMLEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME}: Palette incoming event.')

    message_data: dict = json.loads(html_args.data)
    message_action = html_args.action

    log_msg = f"Event received from {html_args.firingEvent.sender.name}\n"
    log_msg += f"Action: {message_action}\n"
    log_msg += f"Data: {message_data}"
    futil.log(log_msg, adsk.core.LogLevels.InfoLogLevel)

    # TODO ******** Your palette reaction code here ********

    palettes = ui.palettes
    palette: adsk.core.Palette = palettes.itemById(PALETTE_ID)

    global _fact

    if message_action == 'DOMContentLoaded':
        html_args.returnData = json.dumps(
            {
                'correction': _fact.getCorrectionTxt()
            }
        )

    elif message_action == 'btn-click':
        palettes = ui.palettes
        palette: adsk.core.Palette = palettes.itemById(PALETTE_ID)

        scale = ''
        if message_data['value'] == '100%':
            scale = 0
        elif message_data['value'] == '÷2':
            scale = -1
        elif message_data['value'] == '×2':
            scale = 1

        res = _fact.refresh(scale)
        palette.name = PALETTE_NAME + ' ' + res

    # elif message_action == 'lock-change':
    #     palettes = ui.palettes
    #     palette: adsk.core.Palette = palettes.itemById(PALETTE_ID)
        
    #     global _lock_mode
    #     _lock_mode = message_data['value']
        # a=1

    elif message_action == 'correction-change':
        correctionTxt = message_data['value']
        msg = _fact.isCorrectionOk(correctionTxt)
        html_args.returnData = json.dumps(
            {
                'value': msg
            }
        )
        if len(msg) > 0:
            return

        res =  _fact.setCorrectionTxt(correctionTxt)
        palette.name = PALETTE_NAME + ' ' + res


    elif message_action == 'response':
        pass

# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME}: Command destroy event.')

    global local_handlers
    local_handlers = []


# *********
def createPalette():
    palettes = ui.palettes
    palette = palettes.itemById(PALETTE_ID)
    if palette is None:
        palette = palettes.add(
            id=PALETTE_ID,
            name=PALETTE_NAME,
            htmlFileURL=PALETTE_URL,
            isVisible=True,
            showCloseButton=True,
            isResizable=False,
            # isResizable=True,
            width=PALETTE_WIDTH,
            height=PALETTE_HEIGHT_NORMAL,
            useNewWebBrowser=True
        )
        palette.setPosition(900,200)
        futil.add_handler(palette.closed, palette_closed)
        futil.add_handler(palette.navigatingURL, palette_navigating)
        futil.add_handler(palette.incomingFromHTML, palette_incoming)
        futil.log(f'{CMD_NAME}: Created a new palette: ID = {palette.id}, Name = {palette.name}')

    if palette.dockingState == adsk.core.PaletteDockingStates.PaletteDockStateFloating:
        palette.dockingState = PALETTE_DOCKING

    palette.isVisible = True


def isOrthographicCameraType():
    app: adsk.core.Application = adsk.core.Application.get()
    vp: adsk.core.Viewport = app.activeViewport
    cam: adsk.core.Camera = vp.camera

    return cam.cameraType == adsk.core.CameraTypes.OrthographicCameraType

# class MyWorkspaceActivatedHandler(adsk.core.WorkspaceEventHandler):
#     def __init__(self):
#         super().__init__()
#     def notify(self, args: adsk.core.WorkspaceEventArgs):
#         futil.log(f'{CMD_NAME}: {args.firingEvent.name}')

#         global ui
#         palettes = ui.palettes
#         palette = palettes.itemById(PALETTE_ID)

#         if not palette:
#             return

#         if not args.workspace.productType in PRODUCT_TYPE_WHITE_LIST:
#             palette.sendInfoToHTML(
#                 'command_event',
#                 json.dumps({'value': 'True'}) 
#             )
#         else:
#             palette.sendInfoToHTML(
#                 'command_event',
#                 json.dumps({'value': 'False'}) 
#             )