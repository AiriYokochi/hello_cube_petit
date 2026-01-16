#!/usr/bin/env python
# Copyright (c) 2026 SoftBank Corp.
# <<licensetext>>

import os
import re
import subprocess

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QColorDialog, QPlainTextEdit, QSlider, QSpinBox,
    QComboBox, QFrame
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_text(filepath: str, text: str):
    ensure_dir(os.path.dirname(filepath))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)


def is_hex_color(code: str) -> bool:
    return bool(re.fullmatch(r"#([0-9a-fA-F]{6})", code.strip()))


class CustomDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main = main_window
        self.voice_proc = None

        self.setWindowTitle("カスタム")
        self.resize(980, 650)

        # voice 初期値
        self.voice_language = "ja"
        self.voice_emotion = "happiness"
        self.voice_emotion_level = 2
        self.voice_pitch = 100
        self.voice_speed = 100
        self.voice_volume = 100

        root = QVBoxLayout(self)

        title = QLabel("カスタム設定")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        # ============================
        # 左右2カラム
        # ============================
        two_col = QHBoxLayout()
        two_col.setSpacing(12)
        root.addLayout(two_col, 1)

        # ----------------------------
        # 左：顔色 + 声
        # ----------------------------
        left_frame = QFrame()
        left_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255,255,255,0.55);
                border-radius: 16px;
                padding: 10px;
            }
        """)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setSpacing(10)

        # 顔色
        face_title = QLabel("カスタム")
        face_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        left_layout.addWidget(face_title)

        face_row = QHBoxLayout()
        face_label = QLabel("顔の色")
        face_label.setFixedWidth(90)

        self.face_input = QLineEdit("#00BFFF")
        self.face_input.setPlaceholderText("#RRGGBB 例: #FFAA00")

        self.pick_color_btn = QPushButton("選ぶ")
        self.save_face_btn = QPushButton("保存")

        face_row.addWidget(face_label)
        face_row.addWidget(self.face_input, 1)
        face_row.addWidget(self.pick_color_btn)
        face_row.addWidget(self.save_face_btn)
        left_layout.addLayout(face_row)

        self.preview = QLabel(" ")
        self.preview.setFixedHeight(24)
        self.preview.setStyleSheet("background-color: #00BFFF; border-radius: 8px;")
        left_layout.addWidget(self.preview)

        # 声
        voice_title = QLabel("声（voice.yaml）")
        voice_title.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 6px;")
        left_layout.addWidget(voice_title)

        # emotion
        emo_row = QHBoxLayout()
        emo_label = QLabel("emotion")
        emo_label.setFixedWidth(90)
        self.emotion_combo = QComboBox()
        self.emotion_combo.addItems(["normal", "happiness"])
        self.emotion_combo.setCurrentText(self.voice_emotion)
        emo_row.addWidget(emo_label)
        emo_row.addWidget(self.emotion_combo, 1)
        left_layout.addLayout(emo_row)

        # emotion_level
        emo_lv_row = QHBoxLayout()
        emo_lv_label = QLabel("level")
        emo_lv_label.setFixedWidth(90)
        self.emotion_level_spin = QSpinBox()
        self.emotion_level_spin.setRange(0, 5)
        self.emotion_level_spin.setValue(self.voice_emotion_level)
        emo_lv_row.addWidget(emo_lv_label)
        emo_lv_row.addWidget(self.emotion_level_spin)
        emo_lv_row.addStretch()
        left_layout.addLayout(emo_lv_row)

        # pitch/speed/volume
        self.pitch_slider, self.pitch_spin = self._make_slider_row(left_layout, "pitch", 0, 200, self.voice_pitch)
        self.speed_slider, self.speed_spin = self._make_slider_row(left_layout, "speed", 0, 200, self.voice_speed)
        self.volume_slider, self.volume_spin = self._make_slider_row(left_layout, "volume", 0, 200, self.voice_volume)

        # YAMLプレビュー
        self.voice_yaml_view = QPlainTextEdit()
        self.voice_yaml_view.setReadOnly(True)
        self.voice_yaml_view.setFixedHeight(120)
        self.voice_yaml_view.setStyleSheet("""
            QPlainTextEdit {
                background-color: white;
                border-radius: 12px;
                padding: 8px;
                font-family: monospace;
                font-size: 13px;
            }
        """)
        left_layout.addWidget(self.voice_yaml_view)

        # ボタン行
        voice_btn_row = QHBoxLayout()
        self.sample_voice_btn = QPushButton("再生")
        self.stop_voice_btn = QPushButton("停止")
        self.save_voice_btn = QPushButton("保存")

        voice_btn_row.addWidget(self.sample_voice_btn)
        voice_btn_row.addWidget(self.stop_voice_btn)
        voice_btn_row.addStretch()
        voice_btn_row.addWidget(self.save_voice_btn)
        left_layout.addLayout(voice_btn_row)

        left_layout.addStretch()
        two_col.addWidget(left_frame, 1)

        # ----------------------------
        # 右：GPT設定
        # ----------------------------
        right_frame = QFrame()
        right_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255,255,255,0.55);
                border-radius: 16px;
                padding: 10px;
            }
        """)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setSpacing(10)

        gpt_title = QLabel("GPT設定（personality.yaml）")
        gpt_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        right_layout.addWidget(gpt_title)

        # color
        row_color = QHBoxLayout()
        lbl_color = QLabel("color")
        lbl_color.setFixedWidth(140)
        self.persona_color = QLineEdit("ピンク")
        row_color.addWidget(lbl_color)
        row_color.addWidget(self.persona_color, 1)
        right_layout.addLayout(row_color)

        # personality
        row_personality = QHBoxLayout()
        lbl_personality = QLabel("personality")
        lbl_personality.setFixedWidth(140)
        self.persona_personality = QComboBox()
        self.persona_personality.addItems(["おっとり", "元気", "クール", "まじめ", "やさしい", "ツンデレ", "おしゃべり"])
        self.persona_personality.setCurrentText("おっとり")
        row_personality.addWidget(lbl_personality)
        row_personality.addWidget(self.persona_personality, 1)
        right_layout.addLayout(row_personality)

        # nick_name
        row_nick = QHBoxLayout()
        lbl_nick = QLabel("nick_name")
        lbl_nick.setFixedWidth(140)
        self.persona_nick = QLineEdit("ピンクプチ")
        row_nick.addWidget(lbl_nick)
        row_nick.addWidget(self.persona_nick, 1)
        right_layout.addLayout(row_nick)

        # dream
        row_dream = QHBoxLayout()
        lbl_dream = QLabel("dream")
        lbl_dream.setFixedWidth(140)
        self.persona_dream = QLineEdit("たくさんの人と繋がって元気を分け与えること")
        row_dream.addWidget(lbl_dream)
        row_dream.addWidget(self.persona_dream, 1)
        right_layout.addLayout(row_dream)

        # favorite_fruit
        row_fruit = QHBoxLayout()
        lbl_fruit = QLabel("favorite_fruit")
        lbl_fruit.setFixedWidth(140)
        self.persona_fruit = QLineEdit("いちご")
        row_fruit.addWidget(lbl_fruit)
        row_fruit.addWidget(self.persona_fruit, 1)
        right_layout.addLayout(row_fruit)

        # favorite
        row_fav = QHBoxLayout()
        lbl_fav = QLabel("favorite")
        lbl_fav.setFixedWidth(140)
        self.persona_favorite = QLineEdit("ピンク色のもの")
        row_fav.addWidget(lbl_fav)
        row_fav.addWidget(self.persona_favorite, 1)
        right_layout.addLayout(row_fav)

        # frends
        row_fr = QHBoxLayout()
        lbl_fr = QLabel("frends")
        lbl_fr.setFixedWidth(140)
        self.persona_frends = QLineEdit("オレンジ色のキューブプチでよく追いかけっこをしています。ニックネームはオレンジプチです。")
        row_fr.addWidget(lbl_fr)
        row_fr.addWidget(self.persona_frends, 1)
        right_layout.addLayout(row_fr)

        # first_person_pronoun
        row_fp = QHBoxLayout()
        lbl_fp = QLabel("first_person_pronoun")
        lbl_fp.setFixedWidth(140)
        self.persona_fp = QComboBox()
        self.persona_fp.addItems(["わたし", "ぼく", "おれ", "わたくし"])
        self.persona_fp.setCurrentText("わたし")
        row_fp.addWidget(lbl_fp)
        row_fp.addWidget(self.persona_fp, 1)
        right_layout.addLayout(row_fp)

        # end_talk
        row_end = QHBoxLayout()
        lbl_end = QLabel("end_talk")
        lbl_end.setFixedWidth(140)
        self.persona_end = QComboBox()
        self.persona_end.addItems([
            "少し元気でやわらかい感じにします（例：〜だよ！、〜なんだ〜）。",
            "丁寧で落ち着いた感じにします（例：〜です、〜ですね）。",
            "かわいく甘えた感じにします（例：〜だよぉ、〜なの〜）。",
            "クールで短めにします（例：〜だ。〜だね）。",
        ])
        self.persona_end.setCurrentIndex(0)
        row_end.addWidget(lbl_end)
        row_end.addWidget(self.persona_end, 1)
        right_layout.addLayout(row_end)

        # sample_talk
        row_sample = QHBoxLayout()
        lbl_sample = QLabel("sample_talk")
        lbl_sample.setFixedWidth(140)
        self.persona_sample = QComboBox()
        self.persona_sample.addItems([
            "「こんにちは〜！私はピンクプチだよ！今日はどんなお話をする？」",
            "「やっほー！呼んでくれてありがとう！今日は何する？」",
            "「こんにちは。準備できたよ。話しかけてくれる？」",
        ])
        self.persona_sample.setCurrentIndex(0)
        row_sample.addWidget(lbl_sample)
        row_sample.addWidget(self.persona_sample, 1)
        right_layout.addLayout(row_sample)

        # YAMLプレビュー
        self.persona_yaml_view = QPlainTextEdit()
        self.persona_yaml_view.setReadOnly(True)
        self.persona_yaml_view.setStyleSheet("""
            QPlainTextEdit {
                background-color: white;
                border-radius: 12px;
                padding: 8px;
                font-family: monospace;
                font-size: 13px;
            }
        """)
        right_layout.addWidget(self.persona_yaml_view, 1)

        # 保存ボタン
        persona_btn_row = QHBoxLayout()
        self.save_persona_btn = QPushButton("保存")
        persona_btn_row.addStretch()
        persona_btn_row.addWidget(self.save_persona_btn)
        right_layout.addLayout(persona_btn_row)

        two_col.addWidget(right_frame, 1)

        # ----------------------------
        # 下：閉じる
        # ----------------------------
        bottom_row = QHBoxLayout()
        self.close_btn = QPushButton("閉じる")
        bottom_row.addStretch()
        bottom_row.addWidget(self.close_btn)
        root.addLayout(bottom_row)

        # ============================
        # connect
        # ============================
        self.pick_color_btn.clicked.connect(self.pick_color)
        self.save_face_btn.clicked.connect(self.save_face_color)

        self.emotion_combo.currentTextChanged.connect(self.update_voice_yaml_preview)
        self.emotion_level_spin.valueChanged.connect(self.update_voice_yaml_preview)

        self.pitch_slider.valueChanged.connect(self.update_voice_yaml_preview)
        self.speed_slider.valueChanged.connect(self.update_voice_yaml_preview)
        self.volume_slider.valueChanged.connect(self.update_voice_yaml_preview)

        self.pitch_spin.valueChanged.connect(self.update_voice_yaml_preview)
        self.speed_spin.valueChanged.connect(self.update_voice_yaml_preview)
        self.volume_spin.valueChanged.connect(self.update_voice_yaml_preview)

        self.sample_voice_btn.clicked.connect(self.play_sample_voice)
        self.stop_voice_btn.clicked.connect(self.stop_sample_voice)
        self.save_voice_btn.clicked.connect(self.save_voice_yaml)

        self.persona_color.textChanged.connect(self.update_persona_yaml_preview)
        self.persona_personality.currentTextChanged.connect(self.update_persona_yaml_preview)
        self.persona_nick.textChanged.connect(self.update_persona_yaml_preview)
        self.persona_dream.textChanged.connect(self.update_persona_yaml_preview)
        self.persona_fruit.textChanged.connect(self.update_persona_yaml_preview)
        self.persona_favorite.textChanged.connect(self.update_persona_yaml_preview)
        self.persona_frends.textChanged.connect(self.update_persona_yaml_preview)
        self.persona_fp.currentTextChanged.connect(self.update_persona_yaml_preview)
        self.persona_end.currentTextChanged.connect(self.update_persona_yaml_preview)
        self.persona_sample.currentTextChanged.connect(self.update_persona_yaml_preview)

        self.save_persona_btn.clicked.connect(self.save_persona_yaml)

        self.close_btn.clicked.connect(self.close)

        # 初期表示
        self.update_preview()
        self.update_voice_yaml_preview()
        self.update_persona_yaml_preview()

    def _make_slider_row(self, parent_layout, name, min_v, max_v, init_v):
        row = QHBoxLayout()

        label = QLabel(name)
        label.setFixedWidth(90)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(init_v)

        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        spin.setValue(init_v)
        spin.setFixedWidth(70)

        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)

        row.addWidget(label)
        row.addWidget(slider, 1)
        row.addWidget(spin)
        parent_layout.addLayout(row)
        return slider, spin

    # ----------------------------
    # 顔色
    # ----------------------------
    def update_preview(self):
        code = self.face_input.text().strip()
        if is_hex_color(code):
            self.preview.setStyleSheet(f"background-color: {code}; border-radius: 8px;")
        else:
            self.preview.setStyleSheet("background-color: #cccccc; border-radius: 8px;")

    def pick_color(self):
        current = QColor(self.face_input.text().strip()) if is_hex_color(self.face_input.text()) else QColor("#00BFFF")
        color = QColorDialog.getColor(current, self, "顔の色を選択")
        if color.isValid():
            self.face_input.setText(color.name().upper())
            self.update_preview()

    def save_face_color(self):
        code = self.face_input.text().strip().upper()
        if not is_hex_color(code):
            self.main.say("カラーコードが正しくないよ！ #RRGGBB 形式にしてね")
            self.main.log(f"[NG] invalid color code: {code}")
            self.update_preview()
            return

        save_text("config/face_color.yaml", f'face_color: "{code}"\n')
        self.main.log("[OK] face_color.yaml saved")
        self.main.say("顔の色を保存したよ！")
        self.update_preview()

    # ----------------------------
    # voice.yaml
    # ----------------------------
    def make_voice_yaml_text(self) -> str:
        pitch = self.pitch_spin.value()
        speed = self.speed_spin.value()
        volume = self.volume_spin.value()
        emotion = self.emotion_combo.currentText()
        emotion_level = self.emotion_level_spin.value()

        return f"""language: {self.voice_language}
speech_emotion: {emotion}
speech_emotion_level: {emotion_level}
speech_pitch: {pitch}
speech_speed: {speed}
speech_volume: {volume}
"""

    def update_voice_yaml_preview(self):
        self.voice_yaml_view.setPlainText(self.make_voice_yaml_text())

    def save_voice_yaml(self):
        save_text("config/voice.yaml", self.make_voice_yaml_text())
        self.main.log("[OK] voice.yaml saved")
        self.main.say("声の設定を保存したよ！")

    def stop_sample_voice(self):
        self.main.log("[VOICE] stop requested")

        try:
            if self.voice_proc and self.voice_proc.poll() is None:
                self.voice_proc.terminate()
        except Exception as e:
            self.main.log(f"[WARN] terminate failed: {e}")

        try:
            subprocess.run(["bash", "-lc", "spd-say --stop"], check=False)
        except Exception as e:
            self.main.log(f"[WARN] spd-say --stop failed: {e}")

        self.main.say("止めたよ！")
        self.main.log("[OK] voice stopped")

    def play_sample_voice(self):
        self.stop_sample_voice()

        emotion = self.emotion_combo.currentText()
        emotion_level = self.emotion_level_spin.value()

        text = f"サンプルボイスです。感情は{emotion}、レベル{emotion_level}。"
        self.main.log("[VOICE] sample play")
        self.main.say("サンプルボイスを再生するね！")

        try:
            self.voice_proc = subprocess.Popen(["spd-say", text])
        except Exception as e:
            self.main.log(f"[NG] sample voice failed: {e}")
            self.main.say("サンプル再生に失敗したよ（spd-sayが無いかも）")

    # ----------------------------
    # personality.yaml
    # ----------------------------
    def make_persona_yaml_text(self) -> str:
        color = self.persona_color.text().strip()
        personality = self.persona_personality.currentText().strip()
        nick_name = self.persona_nick.text().strip()
        dream = self.persona_dream.text().strip()
        favorite_fruit = self.persona_fruit.text().strip()
        favorite = self.persona_favorite.text().strip()
        frends = self.persona_frends.text().strip()
        first_person_pronoun = self.persona_fp.currentText().strip()
        end_talk = self.persona_end.currentText().strip()
        sample_talk = self.persona_sample.currentText().strip()

        return f"""color: {color}
personality: {personality}
nick_name: {nick_name}
dream: {dream}
favorite_fruit: {favorite_fruit}
favorite: {favorite}
frends: {frends}
first_person_pronoun: {first_person_pronoun}
end_talk: {end_talk}
sample_talk: {sample_talk}
"""

    def update_persona_yaml_preview(self):
        self.persona_yaml_view.setPlainText(self.make_persona_yaml_text())

    def save_persona_yaml(self):
        save_text("config/personality.yaml", self.make_persona_yaml_text())
        self.main.log("[OK] personality.yaml saved")
        self.main.say("性格データを保存したよ！")
