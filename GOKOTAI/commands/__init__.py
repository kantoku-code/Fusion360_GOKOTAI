# ここでは、アドインに追加されるコマンドを定義します。

# TODO 作成したコマンドに対応するモジュールをインポートします。
# コマンドを追加したい場合は、既存のディレクトリの一つを複製して、ここにインポートします。
# entryという名前のデフォルトのモジュールがあるとして、エイリアス(import "entry" as "my_module")を使う必要があります。
from .OAD import entry as oad
from .MinimumBoundingBox import entry as minimumBoundingBox
from .MinimumBoundingRectangle import entry as minimumBoundingRectangle
from .Meteor import entry as meteor

# TODO インポートしたモジュールをこのリストに追加してください。
# Fusionは自動的にstart()とstop()関数を呼び出します。
commands = [
    oad,
    minimumBoundingBox,
    minimumBoundingRectangle,
    meteor,
]


# 各モジュールに "start "関数を定義したと仮定しています。
# スタート機能は、アドインを起動したときに実行されます。
def start():
    for command in commands:
        command.start()


# 各モジュールに "stop "関数を定義していると仮定します。
# アドインが停止した際にstop関数が実行されます。
def stop():
    for command in commands:
        command.stop()