# テンプレートの一般的な構造を変更していないと仮定すると、このファイルには何の変更も必要ありません。
from . import commands
from .lib import fusion360utils as futil


def run(context):
    try:
        # これは commands/__init__.py で定義された各コマンドで start 関数を実行します。
        commands.start()

    except:
        futil.handle_error('run')


def stop(context):
    try:
        # アプリが作成したイベントハンドラをすべて削除する
        futil.clear_handlers()

        # これは commands/__init__.py で定義された各コマンドで start 関数を実行します。
        commands.stop()

    except:
        futil.handle_error('stop')