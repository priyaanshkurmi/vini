#!/bin/bash

VINI_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$VINI_DIR/backend"
AVATAR_DIR="$VINI_DIR/avatar"
LOG_DIR="$VINI_DIR/logs"

mkdir -p "$LOG_DIR"

echo ""
echo "  ██╗   ██╗██╗███╗   ██╗██╗"
echo "  ██║   ██║██║████╗  ██║██║"
echo "  ██║   ██║██║██╔██╗ ██║██║"
echo "  ╚██╗ ██╔╝██║██║╚██╗██║██║"
echo "   ╚████╔╝ ██║██║ ╚████║██║"
echo "    ╚═══╝  ╚═╝╚═╝  ╚═══╝╚═╝"
echo ""
echo "  Embodied Emotional AI Desktop Agent"
echo "  ─────────────────────────────────────"
echo ""

# ── Ollama ────────────────────────────────────────────────────────────────────
echo "  [1/3] Starting Ollama..."
if pgrep -x "ollama" > /dev/null; then
  echo "        Already running."
else
  ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
  sleep 2
  echo "        Started."
fi

# ── Backend ───────────────────────────────────────────────────────────────────
echo "  [2/3] Starting backend..."
cd "$BACKEND_DIR"
source venv/bin/activate
uvicorn main:app --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

# Wait until backend responds
echo "        Waiting for backend..."
for i in {1..20}; do
  if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "        Ready."
    break
  fi
  sleep 1
done

# ── Avatar ────────────────────────────────────────────────────────────────────
echo "  [3/3] Starting avatar..."
cd "$AVATAR_DIR"
npm start > "$LOG_DIR/avatar.log" 2>&1 &
AVATAR_PID=$!
sleep 2
echo "        Started."

echo ""
echo "  ─────────────────────────────────────"
echo "  VINI is online. Starting CLI..."
echo "  ─────────────────────────────────────"
echo ""

# ── Interactive CLI ───────────────────────────────────────────────────────────
cd "$BACKEND_DIR"
source venv/bin/activate
python cli.py voice

# ── Cleanup when CLI exits ────────────────────────────────────────────────────
echo "  Shutting down..."
kill $BACKEND_PID 2>/dev/null
kill $AVATAR_PID  2>/dev/null
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "electron" 2>/dev/null
echo "  VINI stopped."

