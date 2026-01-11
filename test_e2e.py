import time
import subprocess
import requests
import sys
import os
import json

env = os.environ.copy()
env["PYTHONPATH"] = os.getcwd()
env["GEMINI_API_KEY"] = "AIzaSyBbADf44mX4T6Xiawm1jeAcPGJn-FlMoDA"

os.makedirs("artifacts", exist_ok=True)

print(">>> [E2E] Launching SOS Swarm...")

mem_proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "sos.services.memory.app:app", "--host", "0.0.0.0", "--port", "8001"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
tools_proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "sos.services.tools.app:app", "--host", "0.0.0.0", "--port", "8003"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
eng_proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "sos.services.engine.app:app", "--host", "0.0.0.0", "--port", "8020"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    time.sleep(8)
    
    # 1. Stimulus
    payload = {
        "message": "Verify tools. Search 'moon phase'. Draft 'Moon Ritual' QNFT.",
        "agent_id": "river_e2e",
        "model": "gemini-2.0",
        "tools_enabled": True
    }
    
    # 2. Execution
    print(">>> Sending Stimulus...")
    resp = requests.post("http://localhost:8020/chat", json=payload, timeout=45)
    print(f">>> Response Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))

except Exception as e:
    print(f"❌ Failed: {e}")
    # Print engine stderr for debugging
    print(eng_proc.stderr.read().decode())

finally:
    mem_proc.terminate()
    tools_proc.terminate()
    eng_proc.terminate()
