import json
import adsk.core
import os
from ...lib import fusion360utils as futil
from ... import config
import traceback
from .DataFileContainer import DataFileContainer

app = adsk.core.Application.get()
ui = app.userInterface

# TODO ********************* Change these names *********************
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_DocumentTree'
CMD_NAME = 'ドキュメント　ツリー'
CMD_Description = '関連ドキュメントをツリー表示します'
PALETTE_NAME = 'Document Tree'
IS_PROMOTED = True

# Using "global" variables by referencing values from /config.py
PALETTE_ID = config.sample_palette_id

# Specify the full path to the local html. You can also use a web URL
# such as 'https://www.autodesk.com/'
PALETTE_URL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'html', 'index.html')

# The path function builds a valid OS path. This fixes it to be a valid local URL.
PALETTE_URL = PALETTE_URL.replace('\\', '/')

# Set a default docking behavior for the palette
PALETTE_DOCKING = adsk.core.PaletteDockingStates.PaletteDockStateRight

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = config.design_workspace
TAB_ID = config.design_tab_id
TAB_NAME = config.design_tab_name

PANEL_ID = config.doc_panel_id
PANEL_NAME = config.doc_panel_name
PANEL_AFTER = config.doc_panel_after

COMMAND_BESIDE_ID = ''

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

_dataContainer = None
_myCustomEventId = 'MyCustomEventId'
_customEvent: adsk.core.CustomEvent = None

# Executed when add-in is run.
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

def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME}: Command created event.')

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)

def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME}: {args.firingEvent.name}')

    palettes = ui.palettes
    palette = palettes.itemById(PALETTE_ID)

    if palette:
        palette.deleteMe()

    palette = palettes.add(
        id=PALETTE_ID,
        name=PALETTE_NAME,
        htmlFileURL=PALETTE_URL,
        isVisible=True,
        showCloseButton=True,
        isResizable=True,
        width=400,
        height=300,
        useNewWebBrowser=True
    )
    futil.add_handler(palette.closed, palette_closed)
    futil.add_handler(palette.navigatingURL, palette_navigating)
    futil.add_handler(palette.incomingFromHTML, palette_incoming)
    futil.log(f'{CMD_NAME}: Created a new palette: ID = {palette.id}, Name = {palette.name}')

    if palette.dockingState == adsk.core.PaletteDockingStates.PaletteDockStateFloating:
        palette.dockingState = PALETTE_DOCKING

    palette.isVisible = True

    global _myCustomEventId, _customEvent
    try:
        futil.app.unregisterCustomEvent(_myCustomEventId)
    except:
        pass
    _customEvent = futil.app.registerCustomEvent(_myCustomEventId)
    onCustomEvent = MyCustomEventHandle()
    _customEvent.add(onCustomEvent)

    eventArgs = {'Value': 1}
    app.fireCustomEvent(_myCustomEventId, json.dumps(eventArgs))
    a=1

def palette_closed(args: adsk.core.UserInterfaceGeneralEventArgs):
    futil.log(f'{CMD_NAME}: {args.firingEvent.name}')


def palette_navigating(args: adsk.core.NavigationEventArgs):
    futil.log(f'{CMD_NAME}: {args.firingEvent.name}')


def palette_incoming(html_args: adsk.core.HTMLEventArgs):
    futil.log(f'{CMD_NAME}: {html_args.firingEvent.name}')

    global _dataContainer
    if html_args.action == 'htmlLoaded':

        _dataContainer = DataFileContainer()
        jstreeJson = _dataContainer.getJson()


        html_args.returnData = json.dumps({
            'action': 'send',
            'data': jstreeJson,
        })

    elif html_args.action == 'open_active':
        data = json.loads(html_args.data)

        datafile: adsk.core.DataFile = _dataContainer.getDataFile(
            int(data['id'])
        )

        if not datafile:
            return

        # if datafile.fileExtension == 'f2d':
        #     futil.ui.messageBox('f2dファイルのオープンは中止しています')
        #     return

        execOpenDataFiles([datafile])

def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}: {args.firingEvent.name}')

    global local_handlers
    local_handlers = []

    global _myCustomEventId
    futil.app.unregisterCustomEvent(_myCustomEventId)


# ****************

class MyCustomEventHandle(adsk.core.CustomEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            futil.log(f'{CMD_NAME}: {args.firingEvent.name}')
            futil.log('hoge')
            a=1
        except:
            futil.log('Failed:\n{}'.format(traceback.format_exc()))



# ファイルを開く
def execOpenDataFiles(
    dataFiles: list):

    docs: adsk.core.Documents = futil.app.documents

    def getDocFromDatafileId(id) -> adsk.fusion.FusionDocument:
        for d in docs:
            if not d.dataFile:
                continue

            if d.dataFile.id == id:
                return d
        return None

    df: adsk.core.DataFile
    for df in dataFiles:
        doc: adsk.fusion.FusionDocument = getDocFromDatafileId(df.id)
        adsk.doEvents()
        if doc:
            futil.log(f'{CMD_NAME}: call doc.activate')
            doc.activate()
        else:
            futil.log(f'{CMD_NAME}: call doc.open')
            docs.open(df)