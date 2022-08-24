import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface

# *************************
# 重心点の球体作成のデフォルトをチェック入れたい場合は、False->Trueに変更
_sphereSw_Default: bool = False

# 重心点の球体の直径-単位はCmです
SPHERE_SIZE = 0.01
# *************************


# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cog'
CMD_NAME = 'ボディの重心点'
CMD_Description = "ボディの重心点を作成します。"

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = config.design_workspace
TAB_ID = config.design_tab_id
TAB_NAME = config.design_tab_name

PANEL_ID = config.construction_panel_id
PANEL_NAME = config.construction_panel_name
PANEL_AFTER = config.construction_panel_after

COMMAND_BESIDE_ID = ''

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

_bodyIpt: adsk.core.SelectionCommandInput = None
_sphereSw: adsk.core.BoolValueCommandInput = None


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

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME} {args.firingEvent.name}')

    args.command.isPositionDependent = True
    inputs = args.command.commandInputs

    global _bodyIpt
    _bodyIpt = inputs.addSelectionInput(
        'bodyIptId',
        'ボディ',
        'ソリッドボディを選択してください',
    )
    _bodyIpt.addSelectionFilter(
        adsk.core.SelectionCommandInput.SolidBodies
    )

    global _sphereSw, _sphereSw_Default
    _sphereSw = inputs.addBoolValueInput(
        'sphereSwId',
        '重心点に球体作成',
        True,
        '',
        _sphereSw_Default
    )

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} {args.firingEvent.name}')
    global _bodyIpt
    body: adsk.fusion.BRepBody = _bodyIpt.selection(0).entity

    global _sphereSw, SPHERE_SIZE
    radius = -1
    if _sphereSw.value:
        radius = SPHERE_SIZE * 0.5

    initCOG(body, radius)


def command_preview(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} {args.firingEvent.name}')

    global _bodyIpt
    body: adsk.fusion.BRepBody = _bodyIpt.selection(0).entity
    body.opacity = 0.2

    initCOG_CG(body)


def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} {args.firingEvent.name}')

    global local_handlers
    local_handlers = []


def initCOG(
    body: adsk.fusion.BRepBody,
    radius: float = -1.0):

    cog: adsk.core.Point3D = body.physicalProperties.centerOfMass
    sphere: adsk.fusion.BRepBody = None
    if radius > 0:
        tmpMgr: adsk.fusion.TemporaryBRepManager = adsk.fusion.TemporaryBRepManager.get()
        sphere = tmpMgr.createSphere(
            cog,
            radius
        )

    comp: adsk.fusion.Component = body.parentComponent
    constPnts: adsk.fusion.ConstructionPoints = comp.constructionPoints
    pntIpt: adsk.fusion.ConstructionPointInput = constPnts.createInput()
    pntIpt.setByPoint(
        body.physicalProperties.centerOfMass
    )

    des: adsk.fusion.Design = comp.parentDesign

    baseFeat: adsk.fusion.BaseFeature = None
    if des.designType == adsk.fusion.DesignTypes.ParametricDesignType:
        baseFeat = comp.features.baseFeatures.add()

    bodies: adsk.fusion.BRepBodies = comp.bRepBodies
    cog_sphere: adsk.fusion.BRepBody = None
    cog_name = f'COG_{body.name}'
    if baseFeat:
        baseFeat.startEdit()
        try:
            constPnt: adsk.fusion.ConstructionPoint = constPnts.add(pntIpt)
            constPnt.name = cog_name
            if sphere:
                cog_sphere = bodies.add(sphere, baseFeat)
                cog_sphere.name = cog_name
        except:
            pass
        finally:
            baseFeat.finishEdit()
    else:
        constPnt: adsk.fusion.ConstructionPoint = constPnts.add(pntIpt)
        constPnt.name = cog_name
        if sphere:
            cog_sphere = bodies.add(sphere)
            cog_sphere.name = cog_name


def initCOG_CG(
    body: adsk.fusion.BRepBody):

    cog: adsk.core.Point3D = body.physicalProperties.centerOfMass

    occ: adsk.fusion.Occurrence = body.assemblyContext
    if occ:
        mat: adsk.core.Matrix3D = occ.transform2
        mat.invert()
        cog.transformBy(mat)

    comp: adsk.fusion.Component = body.parentComponent


    tmpMgr: adsk.fusion.TemporaryBRepManager = adsk.fusion.TemporaryBRepManager.get()
    sphere: adsk.fusion.BRepBody = tmpMgr.createSphere(
        cog,
        1.0
    )

    cgGroup: adsk.fusion.CustomGraphicsGroup = comp.customGraphicsGroups.add()
    cgBody:adsk.fusion.CustomGraphicsBRepBody = cgGroup.addBRepBody(sphere)

    cgBody.color = adsk.fusion.CustomGraphicsBasicMaterialColorEffect.create(
        adsk.core.Color.create(255, 0, 0, 255),
        adsk.core.Color.create(255, 0, 0, 255),
        adsk.core.Color.create(255, 0, 0, 255),
        adsk.core.Color.create(0, 0, 0, 255),
        10,
        0.5
    )

    cgBody.viewScale = adsk.fusion.CustomGraphicsViewScale.create(
        8,
        cog
    )