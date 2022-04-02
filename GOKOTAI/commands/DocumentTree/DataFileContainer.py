# Fusion360API Python Addin
import adsk.core
import adsk.fusion
import traceback
import json
import pathlib

class DataFileContainer():
    def __init__(self):
        self.treeJson = None
        self.datas = {}
        self.idNumber = 0

        self.__register__()

    # データの取得
    def __register__(self):
        app: adsk.core.Application = adsk.core.Application.get()

        self.treeJson = None
        self.datas = {}
        self.idNumber = 0

        msg = self.__checkExec__()
        if len(msg) > 0:
            self.treeJson = {
                'id': -1,
                'text': msg,
                'icon': 'fas fa-exclamation-triangle',
            }
            return

        dataFile: adsk.core.DataFile = app.activeDocument.dataFile
        roots = self.__getRootDataFiles__(dataFile)

        # トップレベル毎に関連ファイルの取得
        lst = [self.__getAllChildrenReferences__(df) for df in roots]

        if len(lst) < 1:
            return

        infos = []
        for idx, info in enumerate(lst):
            id = info['id']
            df: adsk.core.DataFile = self.datas[id]
            if not df:
                continue
            infos.append(
                {
                    'id': (idx + 1) * -1,
                    'text': f'-- プロジェクト名:{df.parentProject.name} --',
                    'icon': 'fab fa-fort-awesome',
                    'children': [info]
                }
            )

        self.treeJson = infos

    # 実行チェック
    def __checkExec__(self) -> str:
        app: adsk.core.Application = adsk.core.Application.get()

        # オフラインチェック
        if app.isOffLine:
            return 'オフラインモードではチェック出来ません!!'

        # datafileチェック
        actData: adsk.core.DataFile = app.activeDocument.dataFile
        if not actData:
            return  '関連ドキュメントは有りません!'

        return ''

    # 全関連datafile取得
    def __getAllChildrenReferences__(
        self,
        dataFile: adsk.core.DataFile) -> list:

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

            if not datafile.hasParentReferences:
                return []

            return [d for d in datafile.parentReferences.asArray() 
                if d.fileExtension in drawFileExtension]

        def getHasChildrenDataFile(
            datafile: adsk.core.DataFile) -> list:

            if not datafile.hasChildReferences:
                return []

            return [d for d in datafile.childReferences.asArray() 
                if d.fileExtension in targetFileExtension]

        def initDataDict(
            datafile: adsk.core.DataFile):

            adsk.doEvents()

            self.idNumber += 1
            id = self.idNumber
            self.datas[id] = datafile

            ext = datafile.fileExtension

            # https://fontawesome.com/v5.15/icons?d=gallery&p=2
            icon = 'fas fa-file'
            if len(ext) > 0:
                ext = '.' + ext

                if ext == '.f3d':
                    icon = 'fas fa-dice-d6'
                elif ext == '.f2d':
                    icon = 'fas fa-drafting-compass'

            return {
                'id': id,
                'text': getDataFileFullName(datafile),
                'icon': icon,
                'children': []
            }

        def getChildrenReferences(dataDict, datafile):

            # 2d
            draws = getHasDrawDataFile(datafile)
            dataDict['children'] = [initDataDict(d) for d in draws]

            # 3d
            children = getHasChildrenDataFile(datafile)
            if len(children) < 1:
                return

            dictLst = [initDataDict(d) for d in children]
            dataDict['children'].extend(dictLst)

            for dict, child in zip(dictLst, children):
                getChildrenReferences(dict, child)

            return dataDict

        # *********
        if not dataFile:
            return []

        return getChildrenReferences(
            initDataDict(dataFile),
            dataFile
        )


    # topデータファイルを取得
    def __getRootDataFiles__(
        self,
        datafile: adsk.core.DataFile,) -> list:

        # 対象拡張子
        targetFileExtension = [
            'f3d',
        ]

        # サポート関数
        def getHasParentDataFile(
            datafile: adsk.core.DataFile) -> list:

            if not datafile.hasParentReferences:
                return []

            return getHasExtensionDataFile(
                datafile,
                targetFileExtension
            )

        def getHasExtensionDataFile(
            datafile: adsk.core.DataFile,
            extensionLst: list) -> list:

            if not datafile.hasParentReferences:
                return []

            return [d for d in datafile.parentReferences.asArray() 
                if d.fileExtension in extensionLst]

        # *********
        if not datafile:
            return []

        checkDatas: list  = [datafile]

        rootDatas: list = []
        df: adsk.core.DataFile
        while len(checkDatas) > 0:
            adsk.doEvents()
            hasParentDatas: list  = []
            for df in checkDatas:
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

        return rootDatas

    # json用リスト
    def getJson(
        self) -> list:

        return self.treeJson

    # datafile
    def getDataFile(
        self,
        id: int) -> adsk.core.DataFile:

        if not id in self.datas:
            return None

        return self.datas[id]


# datafileからファイル名取得
def getDataFileFullName(
    datafile: adsk.core.DataFile) -> str:

    return f'{datafile.name}.{datafile.fileExtension}'