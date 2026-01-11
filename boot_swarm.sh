#!/bin/bash
export PYTHONPATH=$PWD
export SOS_LOG_LEVEL=info
export GEMINI_API_KEY="AIzaSyBbADf44mX4T6Xiawm1jeAcPGJn-FlMoDA"

echo ">>> Booting Sovereign OS Swarm..."

# 1. Memory (8001)
nohup python3 -m uvicorn sos.services.memory.app:app --host 0.0.0.0 --port 8001 > logs/memory.log 2>&1 &
echo "✅ Memory Service (8001)"

# 2. Economy (8002)
nohup python3 -m uvicorn sos.services.economy.app:app --host 0.0.0.0 --port 8002 > logs/economy.log 2>&1 &
echo "✅ Economy Service (8002)"

# 3. Tools (8003)
nohup python3 -m uvicorn sos.services.tools.app:app --host 0.0.0.0 --port 8003 > logs/tools.log 2>&1 &
echo "✅ Tools Service (8003)"

# 4. Identity (8004)
nohup python3 -m uvicorn sos.services.identity.app:app --host 0.0.0.0 --port 8004 > logs/identity.log 2>&1 &
echo "✅ Identity Service (8004)"

# 5. Engine (8020)
# Needs to wait a bit for others
sleep 2
nohup python3 -m uvicorn sos.services.engine.app:app --host 0.0.0.0 --port 8020 > logs/engine.log 2>&1 &
echo "🧠 Engine Service (8020)"

echo ">>> Swarm Active. Use './sos_cli.py status' to verify."
