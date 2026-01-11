import asyncio
import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sos.clients.memory import MemoryClient

async def print_state(client, label):
    state = await client.get_arf_state()
    alpha = state.get("alpha_drift", 0.0)
    regime = state.get("regime", "unknown")
    coherence = state.get("coherence_raw", 0.0)
    
    color = "\033[92m" # Green
    if regime == "plastic":
        color = "\033[91m" # Red
    elif regime == "consolidating":
        color = "\033[94m" # Blue
        
    print(f"[{label:15}] | Regime: {color}{regime:13}\033[0m | Alpha: {alpha:8.4f} | Coherence: {coherence:8.4f}")

async def run_demo():
    client = MemoryClient("http://localhost:8001", timeout_seconds=60)
    
    print("\n🌊 Starting Real Alpha Drift Demonstration (FRC 841.004)")
    print("-" * 80)
    
    # 1. Establish Baseline (The "Safe" Zone)
    # We feed it 5 similar items about Quantum Computing
    baseline = [
        "Quantum superposition is a fundamental principle of quantum mechanics.",
        "A qubit can exist in multiple states simultaneously.",
        "Quantum entanglement links particles across vast distances.",
        "Quantum computers use quantum bits (qubits) instead of classical bits.",
        "Quantum gates perform operations on qubits in a quantum circuit."
    ]
    
    print("\nPhase 1: Establishing Cognitive Baseline (Familiar Topics)")
    for i, msg in enumerate(baseline):
        await client.add(content=msg, metadata={"demo": "baseline"})
        await print_state(client, f"Stable {i+1}")
        await asyncio.sleep(0.5)

    # 2. Introduce SURPRISE (The "Shock" Zone)
    # We feed it something completely unrelated
    shocks = [
        "How to bake a perfect Neapolitan pizza at home in a wood-fired oven.",
        "The migratory patterns of Arctic terns are among the longest in the animal kingdom."
    ]
    
    print("\nPhase 2: Introducing NOVELTY SHOCK (Surprise Event)")
    for i, msg in enumerate(shocks):
        await client.add(content=msg, metadata={"demo": "shock"})
        await print_state(client, f"Shock {i+1}")
        await asyncio.sleep(0.5)

    # 3. Stabilization (The "Learning" Zone)
    # We feed it items related to the new topic to see it settle
    recovery = [
        "Pizza dough requires high hydration for a soft, airy crust.",
        "San Marzano tomatoes are the traditional choice for Neapolitan sauce.",
        "A 400-degree stone ensures the bottom of the pizza is charred and crispy."
    ]
    
    print("\nPhase 3: Cognitive Integration (Stabilizing on New Topic)")
    for i, msg in enumerate(recovery):
        await client.add(content=msg, metadata={"demo": "recovery"})
        await print_state(client, f"Stabilizing {i+1}")
        await asyncio.sleep(0.5)

    print("-" * 80)
    print("Demo complete. Observe how Alpha Drift (Plasticity) spiked during Phase 2!")

if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except Exception as e:
        print(f"❌ Error during demo: {e}")
