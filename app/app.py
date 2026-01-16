#!/usr/bin/env python

# Copyright (c) 2026 SoftBank Corp.
# 
# <<licensetext>>

import sys
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit,
    QPlainTextEdit, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame
)
import actions
import hardware_check
from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem
import commands
from custom_dialog import CustomDialog

class CommandMenuDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main = main_window
        self.setWindowTitle("コマンド集")
        self.resize(620, 480)

        self.selected_cmd = None  # ← 選択中コマンドを保持

        layout = QVBoxLayout(self)

        title = QLabel("どのコマンドを見る？")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # --- カテゴリボタン ---
        btn_row = QHBoxLayout()
        self.btn_bringup = QPushButton("起動")
        self.btn_radicon = QPushButton("ラジコン")
        self.btn_talk = QPushButton("お話")
        btn_row.addWidget(self.btn_bringup)
        btn_row.addWidget(self.btn_radicon)
        btn_row.addWidget(self.btn_talk)
        layout.addLayout(btn_row)

        # --- コマンド一覧 ---
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        # --- 選択したコマンド表示欄（コピー対象） ---
        self.cmd_view = QPlainTextEdit()
        self.cmd_view.setReadOnly(True)
        self.cmd_view.setPlaceholderText("ここにコマンドが表示されます")
        self.cmd_view.setFixedHeight(90)
        self.cmd_view.setStyleSheet("""
            QPlainTextEdit {
                background-color: white;
                border-radius: 12px;
                padding: 8px;
                font-family: monospace;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.cmd_view)

        # --- コピー / 閉じる ---
        action_row = QHBoxLayout()
        self.copy_btn = QPushButton("コピー")
        self.close_btn = QPushButton("閉じる")
        action_row.addWidget(self.copy_btn)
        action_row.addStretch()
        action_row.addWidget(self.close_btn)
        layout.addLayout(action_row)

        # --- connect ---
        self.btn_bringup.clicked.connect(self.show_bringup)
        self.btn_radicon.clicked.connect(self.show_radicon)
        self.btn_talk.clicked.connect(self.show_talk)

        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.copy_btn.clicked.connect(self.copy_command)
        self.close_btn.clicked.connect(self.close)

        # 最初はラジコン表示
        self.show_radicon()

    # ----------------------------
    # 表示切り替え
    # ----------------------------
    def _reset_selection(self):
        self.selected_cmd = None
        self.cmd_view.clear()

    def show_radicon(self):
        self.list_widget.clear()
        self._reset_selection()

        for cmd in commands.RADICON_COMMANDS:
            item = QListWidgetItem(f"🚗 {cmd['title']}")
            item.setData(Qt.UserRole, cmd)
            self.list_widget.addItem(item)

    def show_bringup(self):
        self.list_widget.clear()
        self._reset_selection()

        # ※ここは本当は BRINGUP_COMMANDS を作るのがおすすめ！
        # いまは仮でRADICON_COMMANDSになってたので、そのまま合わせてます
        for cmd in commands.RADICON_COMMANDS:
            item = QListWidgetItem(f"🤖 {cmd['title']}")
            item.setData(Qt.UserRole, cmd)
            self.list_widget.addItem(item)

    def show_talk(self):
        self.list_widget.clear()
        self._reset_selection()

        for cmd in commands.TALK_COMMANDS:
            item = QListWidgetItem(f"💬 {cmd['title']}")
            item.setData(Qt.UserRole, cmd)
            self.list_widget.addItem(item)

    # ----------------------------
    # クリック時
    # ----------------------------
    def on_item_clicked(self, item):
        cmd = item.data(Qt.UserRole)
        self.selected_cmd = cmd

        # 表示欄にコマンドを出す（コピーしやすい）
        self.cmd_view.setPlainText(cmd["command"])

        # コンソールに出す
        self.main.log("----------")
        self.main.log(f"[CMD] {cmd['title']}")
        self.main.log(cmd["command"])

        # 吹き出しで喋る（説明）
        self.main.say(cmd["desc"])

    # ----------------------------
    # コピー
    # ----------------------------
    def copy_command(self):
        if not self.selected_cmd:
            self.main.say("先にコマンドを選んでね！")
            return

        cmd_text = self.selected_cmd["command"]

        # クリップボードへコピー
        QApplication.clipboard().setText(cmd_text)

        self.main.log(f"[COPY] {self.selected_cmd['title']} をコピーしました")
        self.main.say("コピーしたよ！")

class HardwareCheckWorker(QThread):
    log = Signal(str)
    summary = Signal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        logs, summary, results = hardware_check.run_hardware_check()

        for line in logs:
            self.log.emit(line)

        self.summary.emit(summary)


# ----------------------------
# メインUI
# ----------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Launcher")
        self.resize(900, 600)

        # 背景水色
        self.setStyleSheet("""
            QWidget {
                background-color: #8fd3ff;
                font-size: 16px;
            }
            QPushButton {
                background-color: white;
                border-radius: 14px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f2fbff;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ----------------------------
        # 上半分（会話エリア）
        # ----------------------------
        top_area = QHBoxLayout()
        top_area.setSpacing(12)

        # ロボット画像
        self.robot_img = QLabel()
        self.robot_img.setFixedSize(140, 140)
        self.robot_img.setStyleSheet("background-color: white; border-radius: 20px;")
        self.robot_img.setAlignment(Qt.AlignCenter)

        # 画像がある場合ここで読み込み（robot.png を同じフォルダに置く）
        pix = QPixmap("img/Cube_petit_CAD.png")
        if not pix.isNull():
            self.robot_img.setPixmap(pix.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.robot_img.setText("ROBOT")

        # 吹き出し＋入力欄
        right_top = QVBoxLayout()
        right_top.setSpacing(8)

        self.balloon = QLabel("こんにちは！何がしたい？")
        self.balloon.setStyleSheet("""
            QLabel {
                background-color: white;
                border-radius: 18px;
                padding: 12px;
            }
        """)
        self.balloon.setWordWrap(True)
        self.balloon.setMinimumHeight(80)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("入力...")
        self.input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border-radius: 14px;
                padding: 10px;
            }
        """)
        self.enter_btn = QPushButton("Enter")
        self.enter_btn.clicked.connect(self.on_enter)

        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.enter_btn)

        right_top.addWidget(self.balloon)
        right_top.addLayout(input_row)

        top_area.addWidget(self.robot_img)
        top_area.addLayout(right_top, 1)

        # ----------------------------
        # 下半分（ボタン＋コンソール）
        # ----------------------------
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255,255,255,0.35);
                border-radius: 18px;
                padding: 12px;
            }
        """)
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setSpacing(10)

        # 6ボタン
        grid = QGridLayout()
        grid.setSpacing(10)

        self.btn_hw = QPushButton("ハードウェアチェック")
        self.btn_cmd = QPushButton("コマンド集")
        self.btn_intro = QPushButton("機能紹介")
        self.btn_custom = QPushButton("カスタム")
        self.btn_youtube = QPushButton("YouTubeを開く")
        self.btn_web = QPushButton("Webページを開く")

        self.btn_hw.clicked.connect(self.run_hardware_check)
        self.btn_cmd.clicked.connect(self.open_command_menu)
        self.btn_intro.clicked.connect(lambda: self.log("[UI] 機能紹介（未実装）"))
        self.btn_custom.clicked.connect(self.open_custom)
        self.btn_youtube.clicked.connect(self.open_youtube)
        self.btn_web.clicked.connect(self.open_chrome)
        grid.addWidget(self.btn_hw, 0, 0)
        grid.addWidget(self.btn_cmd, 0, 2)
        grid.addWidget(self.btn_intro, 0, 1)
        grid.addWidget(self.btn_custom, 1, 0)
        grid.addWidget(self.btn_youtube, 1, 1)
        grid.addWidget(self.btn_web, 1, 2)

        # コンソール風ログ
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0b0f14;
                color: #67ff7a;
                border-radius: 12px;
                padding: 10px;
                font-family: monospace;
                font-size: 14px;
            }
        """)
        self.console.setFixedHeight(180)

        # 戻るボタン
        back_row = QHBoxLayout()
        self.back_btn = QPushButton("戻る")
        self.back_btn.clicked.connect(self.on_back)
        back_row.addWidget(self.back_btn)
        back_row.addStretch()

        bottom_layout.addLayout(grid)
        bottom_layout.addWidget(self.console)
        bottom_layout.addLayout(back_row)

        # ----------------------------
        # 全体に配置
        # ----------------------------
        root.addLayout(top_area, 1)
        root.addWidget(bottom_frame, 1)

    def open_custom(self):
        self.log("[UI] カスタム画面を開きます")
        self.say("カスタムしよう！")

        dlg = CustomDialog(self)
        dlg.exec()

    def open_youtube(self):
        self.log("[UI] YouTubeを開きます")
        self.say("YouTubeを開くね！")
        actions.open_youtube()

    def open_chrome(self):
        self.log("[UI] Chromeを開きます")
        self.say("Chromeを開くね！")

        ok = actions.open_chrome("https://airiyokochi.github.io/cube_petit/#/ja")
        if ok:
            self.log("[OK] Chrome起動成功")
        else:
            self.log("[WARN] Chromeが見つからなかったのでデフォルトブラウザで開きました")

    def open_command_menu(self):
        dlg = CommandMenuDialog(self)
        dlg.exec()            

    def log(self, text: str):
        self.console.appendPlainText(text)

    def say(self, text: str):
        self.balloon.setText(text)

    def on_enter(self):
        msg = self.input.text().strip()
        if not msg:
            return
        self.log(f"[USER] {msg}")
        self.say(f"了解！「{msg}」だね。")
        self.input.clear()

    def on_back(self):
        self.log("[UI] 戻るが押されました")
        self.say("戻るよ！")

    def run_hardware_check(self):
        self.say("ハードウェアチェックを開始するね！")
        self.log("===== Hardware Check Start =====")

        self.worker = HardwareCheckWorker()
        self.worker.log.connect(self.log)
        self.worker.summary.connect(self.say)
        self.worker.finished.connect(lambda: self.log("===== Hardware Check End ====="))
        self.worker.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
