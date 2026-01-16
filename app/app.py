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
from llm_ollama import ask_ollama
from instruction_loader import (
    load_instruction_text,
    load_spec_summary_text,
    load_spec_full_text,
)
import requests
from PySide6.QtWidgets import QScrollArea


def is_ollama_available() -> bool:
    try:
        r = requests.get("http://localhost:11434", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False

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

class LLMWorker(QThread):
    finished_text = Signal(str)
    error = Signal(str)

    def __init__(self, prompt: str, model: str = "qwen2.5:7b-instruct"):
        super().__init__()
        self.prompt = prompt
        self.model = model

    def run(self):
        try:
            reply = ask_ollama(self.prompt, self.model)
            if not reply:
                reply = "うまく返事できなかったかも…もう一回言ってみて！"
            self.finished_text.emit(reply)
        except Exception as e:
            self.error.emit(str(e))

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
        self.balloon.setWordWrap(True)
        self.balloon.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.balloon.setStyleSheet("""
            QLabel {
                background-color: white;
                border-radius: 18px;
                padding: 12px;
            }
        """)

        # 吹き出しスクロール
        self.balloon_scroll = QScrollArea()
        self.balloon_scroll.setWidgetResizable(True)
        self.balloon_scroll.setFrameShape(QFrame.NoFrame)
        self.balloon_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
            }
        """)
        self.balloon_scroll.setWidget(self.balloon)

        # 高さを確保（ここ重要）
        self.balloon_scroll.setMinimumHeight(120)

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

        right_top.addWidget(self.balloon_scroll)
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

        self.instruction_text = load_instruction_text()
        self.spec_summary_text = load_spec_summary_text()
        self.spec_full_text = load_spec_full_text()
        self.llm_enabled = is_ollama_available()

        if self.llm_enabled:
            self.log("[LLM] Ollama OK (LLM enabled)")
            self.say("ローカルLLMが使えるよ！話しかけてね！")
        else:
            self.log("[LLM] Ollama NG (fallback mode)")
            self.say("いまは無能モードだよ…（LLMが起動してないかも）")
            



    def dumb_bot_reply(self, user_text: str) -> str:
        # かわいい無能ボット（適当に返す）
        if "こんにちは" in user_text:
            return "こんにちは！…えっと、次どうすればいい？"
        if "チェック" in user_text:
            return "チェックしたいんだね！ボタン押してみて！"
        if "ありがとう" in user_text:
            return "えへへ…どういたしまして！"

        return "ごめん、よくわかんなかった！もうちょっと簡単に言って〜！"

    def needs_spec_full(self, user_text: str) -> bool:
        keywords = [
            "仕様", "詳細", "できること", "使い方", "機能",
            "ハードウェアチェック", "カスタム", "コマンド集",
            "エラー", "動かない", "接続", "設定", "voice.yaml", "personality.yaml"
        ]
        return any(k in user_text for k in keywords)

    def on_llm_error(self, err: str):
        self.log(f"[LLM ERROR] {err}")

        # ここで無能モードに切り替える（安全）
        self.llm_enabled = False

        self.say("ごめんね、LLMが使えなくなったから無能モードになるよ…")
        self.log("[LLM] fallback to dumb bot mode")
        
    def on_llm_reply(self, text: str):
        self.say(text)
        self.log(f"[BOT] {text}")

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

        # 自動スクロールで一番下へ
        if hasattr(self, "balloon_scroll"):
            bar = self.balloon_scroll.verticalScrollBar()
            bar.setValue(bar.maximum())


    def on_enter(self):
        msg = self.input.text().strip()
        if not msg:
            return

        self.log(f"[USER] {msg}")
        self.input.clear()

        # LLMが使えないなら無能ボット
        if not self.llm_enabled:
            reply = self.dumb_bot_reply(msg)
            self.say(reply)
            self.log(f"[BOT] {reply}")
            return

        self.say("考え中…")

        # ===== 合わせ技プロンプト構築 =====
        parts = []

        # 1) いつも付ける：短いinstruction
        if self.instruction_text:
            parts.append(self.instruction_text)

        # 2) いつも付ける：仕様の超要約（軽い）
        if self.spec_summary_text:
            parts.append("【Cube petit仕様（要約）】\n" + self.spec_summary_text)

        # 3) 必要なときだけ付ける：仕様全文（重い）
        if self.needs_spec_full(msg) and self.spec_full_text:
            parts.append("【Cube petit仕様（詳細）】\n" + self.spec_full_text)

        parts.append(f"ユーザー: {msg}\nCube petit:")

        prompt = "\n\n".join(parts)

        # UI固まらないようにスレッド
        self.llm_worker = LLMWorker(prompt)
        self.llm_worker.finished_text.connect(self.on_llm_reply)
        self.llm_worker.error.connect(self.on_llm_error)
        self.llm_worker.start()

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
