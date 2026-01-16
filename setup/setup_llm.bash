#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MODELS_DIR="${SCRIPT_DIR}/../models"

echo "=== Ollama Install & Model Download ==="
echo "[INFO] SCRIPT_DIR = ${SCRIPT_DIR}"
echo "[INFO] MODELS_DIR = ${MODELS_DIR}"
echo ""

if command -v ollama >/dev/null 2>&1; then
  echo "[OK] ollama is already installed: $(command -v ollama)"
else
  echo "[INFO] Installing ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
  echo "[OK] ollama installed"
fi

echo ""

mkdir -p "${MODELS_DIR}"
cd "${MODELS_DIR}"

echo "[INFO] Pulling model: qwen2.5:7b-instruct"
ollama pull qwen2.5:7b-instruct

echo ""
echo "[OK] Download finished!"
echo ""

echo "=== Installed Models ==="
ollama list
