#!/usr/bin/env python

# Copyright (c) 2026 SoftBank Corp.
# 
# <<licensetext>>

import requests


def ask_ollama(prompt: str, model: str = "qwen2.5:7b-instruct") -> str:
    """
    Ollamaに問い合わせて返答テキストを返す
    """
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
           "num_predict": 120
        }
    }

    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()

    data = r.json()
    return data.get("response", "").strip()
