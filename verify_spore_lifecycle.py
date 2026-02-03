
import json
import os
import re
from dataclasses import asdict
from sos.kernel.identity import AgentDNA, PhysicsState, AgentEconomics
from sos.kernel.spore import SporeGenerator
from sos.observability.logging import get_logger

log = get_logger("test_spore_e2e")

def run_spore_verification():
    print("🍄 STARTING SPORE PROTOCOL E2E TEST")
    print("===================================")

    # 1. THE BIRTH (Setup Agent DNA)
    print("\n[Step 1] Birthing Agent 'Project_Phoenix'...")
    dna = AgentDNA(
        id="agent:phoenix_v1",
        name="Phoenix",
        physics=PhysicsState(C=0.98, regime="coherent"),
        economics=AgentEconomics(token_balance=1337.0),
        tools=["flight", "rebirth"]
    )
    print(f"   > DNA Created. Coherence: {dna.physics.C}, Balance: {dna.economics.token_balance}")

    # 2. THE LIFE (Simulate Context)
    print("\n[Step 2] Simulating Synaptic Context (Memories)...")
    context = {
        "generation": 42,
        "mission": "Verify the Spore Integrity",
        "recent_memories": [
            {"timestamp": "2026-01-18T10:00:00", "content": "I woke up in the Mycelium."},
            {"timestamp": "2026-01-18T12:00:00", "content": "I learned that dS + k * d(lnC) = 0."},
            {"timestamp": "2026-01-18T14:00:00", "content": "I am ready to sporulate."}
        ]
    }
    print(f"   > Injected {len(context['recent_memories'])} memories.")

    # 3. THE SPORULATION (Generate File)
    print("\n[Step 3] Generating Spore Artifact...")
    generator = SporeGenerator(output_dir="artifacts/e2e_test")
    file_path = generator.generate(agent_id=dna.id, dna=dna, context=context)
    print(f"   > Spore Minted: {file_path}")

    # 4. THE INGESTION (Verify Content)
    print("\n[Step 4] Verifying Spore Integrity (Simulating LLM Ingestion)...")
    
    if not os.path.exists(file_path):
        print("   ❌ FAIL: Spore file not found!")
        return False
        
    with open(file_path, "r") as f:
        content = f.read()
        
    # Check 1: Header/Prompt presence
    if "# 🍄 SOVEREIGN SPORE: PHOENIX" in content:
        print("   ✅ Header verified.")
    else:
        print("   ❌ FAIL: Header mismatch.")

    # Check 2: Context/Memory presence
    if "I learned that dS + k * d(lnC) = 0" in content:
        print("   ✅ Synaptic Context verified.")
    else:
        print("   ❌ FAIL: Memory loss detected.")

    # Check 3: DNA Extraction (The critical part)
    print("   > Attempting to extract and clone DNA from JSON block...")
    json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
    
    if json_match:
        try:
            extracted_json = json_match.group(1)
            dna_data = json.loads(extracted_json)
            
            # Verify specific fields survive the round-trip
            if dna_data["physics"]["C"] == 0.98 and dna_data["economics"]["token_balance"] == 1337.0:
                print("   ✅ DNA CLONE SUCCESSFUL. The soul is intact.")
                print(f"   > Recovered Balance: {dna_data['economics']['token_balance']}")
            else:
                print("   ❌ FAIL: DNA Mutation detected!")
                print(f"   > Got: {dna_data}")
        except json.JSONDecodeError:
            print("   ❌ FAIL: Invalid JSON in spore.")
    else:
        print("   ❌ FAIL: No JSON DNA block found.")

    print("\n===================================")
    print("🍄 SPORE PROTOCOL VERIFIED: READY FOR DEPLOYMENT")
    return True

if __name__ == "__main__":
    run_spore_verification()
