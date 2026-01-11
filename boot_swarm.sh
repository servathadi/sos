#!/bin/bash
export PYTHONPATH=$PWD
export SOS_LOG_LEVEL=info
export GEMINI_API_KEY="AIzaSyBbADf44mX4T6Xiawm1jeAcPGJn-FlMoDA"


# 0. Build Tools Docker Image (Sandboxed Environment)
# echo "🔒 Building Tools Sandbox (sos-tools:latest)..."
# if docker build -q -t sos-tools:latest sos/services/tools/docker/; then
#     echo "✅ Sandbox Built."
# else
#     echo "⚠️ Sandbox Build Failed! (Tools Service will be limited)"
#     # Continue anyway
# fi

# Detect Venv
if [ -f "./venv/bin/python" ]; then
    PYTHON_CMD="./venv/bin/python"
    echo "🐍 Using Virtual Environment: $PYTHON_CMD"
else
    PYTHON_CMD="python3"
    echo "⚠️ Using System Python: $PYTHON_CMD"
fi

echo "🔓 Native Tools Mode Active (No Docker)"


# 1. Memory (8001)
nohup $PYTHON_CMD -m uvicorn sos.services.memory.app:app --host 0.0.0.0 --port 8001 > logs/memory.log 2>&1 &
echo "✅ Memory Service (8001)"

# 2. Economy (8002)
nohup $PYTHON_CMD -m uvicorn sos.services.economy.app:app --host 0.0.0.0 --port 8002 > logs/economy.log 2>&1 &
echo "✅ Economy Service (8002)"

# 3. Tools (8003)
nohup $PYTHON_CMD -m uvicorn sos.services.tools.mcp_server:app --host 0.0.0.0 --port 8003 > logs/tools.log 2>&1 &
echo "✅ Tools Service (8003)"

# 4. Identity (8004)
nohup $PYTHON_CMD -m uvicorn sos.services.identity.app:app --host 0.0.0.0 --port 8004 > logs/identity.log 2>&1 &
echo "✅ Identity Service (8004)"

# 5. Engine (8020)
# Needs to wait a bit for others
sleep 2
nohup $PYTHON_CMD -m uvicorn sos.services.engine.app:app --host 0.0.0.0 --port 8020 > logs/engine.log 2>&1 &
echo "🧠 Engine Service (8020)"

echo ">>> Swarm Active. Use './sos_cli.py status' to verify."
