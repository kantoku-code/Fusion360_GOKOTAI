# Open Affected Documents
import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** コマンドのID情報を指定します。 ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_openAffectedDocuments'
CMD_NAME = '関連ドキュメントを開く'
CMD_Description = '変更された場合、影響を受けるドキュメントを開きます'

# パネルにコマンドを昇格させることを指定します。
IS_PROMOTED = True

# TODO *** コマンドボタンが作成される場所を定義します。 ***
# これは、ワークスペース、タブ、パネル、および 
# コマンドの横に挿入されます。配置するコマンドを指定しない場合は
# 最後に挿入されます。

WORKSPACE_ID = config.design_workspace
TAB_ID = config.design_tab_id
TAB_NAME = config.design_tab_name

PANEL_ID = config.doc_panel_id
PANEL_NAME = config.doc_panel_name
PANEL_AFTER = config.doc_panel_after

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

# *********
# 関連するdatafileリスト
_datas: list = []

_tableIpt: adsk.core.TableCommandInput = None


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

    # **inputs**
    inputs: adsk.core.CommandInputs = args.command.commandInputs

    # text box
    msgLst = [
        '変更された場合、更新が必要と思われるドキュメントです。',
        'チェックの入っているものを開きます。'
    ]
    txtIpt: adsk.core.TextBoxCommandInput = inputs.addTextBoxCommandInput(
        'text_box',
        '',
        '\n'.join(msgLst),
        len(msgLst),
        True
    )

    msg = checkExec()
    if len(msg) > 0:
        txtIpt.text = msg
        args.command.isOKButtonVisible = False
        return

    # table
    global _datas
    _datas = getRootDataFiles(futil.app.activeDocument.dataFile)

    if len(_datas) < 1:
        txtIpt.text = '影響を受けるドキュメントは有りません!'
        args.command.isOKButtonVisible = False
        return

    global _tableIpt
    _tableIpt = inputs.addTableCommandInput(
        'table',
        'Table',
        10,
        '1:5'
    )

    df: adsk.core.DataFile
    for rowIdx, df in enumerate(_datas):
        _tableIpt.addCommandInput(
            inputs.addBoolValueInput(
                f'check{rowIdx}',
                '',
                True,
                '',
                True
            ),
            rowIdx,
            0
        )

        _tableIpt.addCommandInput(
            inputs.addTextBoxCommandInput(
                f'name{rowIdx}',
                'data_name',
                getDocumentFullName(df),
                1,
                True
            ),
            rowIdx,
            1
        )

    # **event**
    futil.add_handler(
        args.command.execute,
        command_execute,
        local_handlers=local_handlers
    )

    futil.add_handler(
        args.command.destroy,
        command_destroy,
        local_handlers=local_handlers
    )

def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global _tableIpt, _datas
    datas = getCheckOnDataFiles(
        _tableIpt.commandInputs,
        _datas
    )

    if len(datas) < 1:
        return

    execOpenDataFiles(datas)


def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}:{args.firingEvent.name}')

    global local_handlers
    local_handlers = []

# **************
# チェックされたdatafileを返す
def getCheckOnDataFiles(
    inputs: adsk.core.CommandInputs,
    dataFiles: list) -> list:

    lst = []
    for idxIpt, input in enumerate(inputs):
        if input.classType() != adsk.core.BoolValueCommandInput.classType():
            continue

        if input.value:
            idx = idxIpt // 2 - 1
            lst.append(dataFiles[idx])
    
    return lst


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
        # doc = None
        if doc:
            futil.log(f'{CMD_NAME}:doc.activate')
            doc.activate()
        else:
            futil.log(f'{CMD_NAME}:doc.open')
            docs.open(df)


# 実行前チェック
def checkExec() -> str:

    # オフラインチェック
    if futil.app.isOffLine:
        return 'オフラインモードではチェック出来ません!!'

    # datafileチェック
    actData: adsk.core.DataFile = app.activeDocument.dataFile
    if not actData:
        return  '影響を受けるドキュメントは有りません!'

    return ''

# datafileからファイル名取得
def getDocumentFullName(
    datafile: adsk.core.DataFile) -> str:

    return f'{datafile.name}.{datafile.fileExtension}'

# 関連データファイルを取得-親側のみ
def getRootDataFiles(
    datafile: adsk.core.DataFile,) -> list:
    
    # 対象拡張子
    targetFileExtension = [
        'f3d',
    ]
    drawFileExtension = [
        'f2d',
    ]

    # サポート関数
    def getHasDrawDataFile(
        datafile: adsk.core.DataFile) -> list:

        return getHasExtensionDataFile(
            datafile,
            drawFileExtension 
        )

    def getHasParentDataFile(
        datafile: adsk.core.DataFile) -> list:

        return getHasExtensionDataFile(
            datafile,
            targetFileExtension
        )

    def getHasExtensionDataFile(
        datafile: adsk.core.DataFile,
        extensionLst: list) -> list:

        return [d for d in datafile.parentReferences.asArray() 
            if d.fileExtension in extensionLst]


    # *********
    if not datafile:
        return []

    checkDatas: list  = [datafile]

    rootDatas: list = []
    drawDatas: list = []
    df: adsk.core.DataFile
    while len(checkDatas) > 0:
        hasParentDatas: list  = []
        for df in checkDatas:
            # 2d
            draws: list  = getHasDrawDataFile(df)
            if len(draws) > 0:
                drawDatas.extend(draws)
            # 3d
            parents: list  = getHasParentDataFile(df)
            if len(parents) < 1:
                rootDatas.append(df)
            else:
                hasParentDatas.extend(parents)

        if len(hasParentDatas) > 0:
            checkDatas = hasParentDatas
        else:
            checkDatas = []

    drawDatas.extend(rootDatas)
    return [df for df in drawDatas if df.id != datafile.id]