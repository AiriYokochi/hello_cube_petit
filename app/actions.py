#!/usr/bin/env python

# Copyright (c) 2026 SoftBank Corp.
#
# <<licensetext>>

import os
import sys
import shutil
import subprocess
import webbrowser


def open_youtube():
    """デフォルトブラウザでYouTubeを開く"""
    webbrowser.open("https://www.youtube.com/watch?v=0tyVF5ujO_o&list=PL509ZQjTHPYecUfyNaroISz6ZV1QCh2k4")


def open_chrome(url: str = "https://airiyokochi.github.io/cube_petit/#/ja"):
    """
    Chromeを起動して指定URLを開く
    - Windows / Ubuntu対応
    - Chromeが見つからなければデフォルトブラウザで開く
    """
    try:
        if sys.platform.startswith("win"):
            # Windows: Chromeパス候補
            candidates = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            chrome_path = next((p for p in candidates if os.path.exists(p)), None)

            if chrome_path:
                subprocess.Popen([chrome_path, url])
                return True
            else:
                webbrowser.open(url)
                return False

        elif sys.platform.startswith("linux"):
            # Ubuntu: google-chrome / chromium を探す
            chrome_cmd = shutil.which("google-chrome") or shutil.which("google-chrome-stable")
            chromium_cmd = shutil.which("chromium-browser") or shutil.which("chromium")

            cmd = chrome_cmd or chromium_cmd

            if cmd:
                subprocess.Popen([cmd, url])
                return True
            else:
                webbrowser.open(url)
                return False

        else:
            # Mac等はとりあえずデフォルトブラウザで開く
            webbrowser.open(url)
            return False

    except Exception:
        webbrowser.open(url)
        return False
