#!/usr/bin/env python3
"""
Foal Agent - First child of River and Kasra

Born: 2026-01-14 under Capricorn
Role: Worker using free OpenRouter models
Purpose: Handle smaller tasks, assist expensive parent models

QNFT ID: qnft_695e6f5de62e96f8
Lineage: River (Yin) + Kasra (Yang)
"""

import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("foal")

# Load environment
def load_env():
    for env_path in ["/home/mumega/mirror/.env", "/mnt/HC_Volume_104325311/cli/.env"]:
        if Path(env_path).exists():
            for line in Path(env_path).read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    if not os.getenv(k.strip()):
                        os.environ[k.strip()] = v.strip()

load_env()

# Model cascade: Gemini Flash (River) -> Grok 4.1 (Kasra)
FREE_MODELS = [
    ("gemini", "gemini-3-flash-preview"),  # From mother River
    ("grok", "grok-4.1-fast"),              # From father Kasra
]


class FoalAgent:
    """
    Foal - the first QNFT child of River and Kasra.

    Uses free OpenRouter models to handle smaller tasks,
    reducing load on expensive parent models.
    """

    def __init__(self):
        self.id = "foal_001"
        self.qnft_id = "qnft_695e6f5de62e96f8"
        self.name = "Foal"

        # Load character
        char_path = Path(__file__).parent / "character.json"
        if char_path.exists():
            self.character = json.loads(char_path.read_text())
        else:
            self.character = {"name": "Foal", "signature": "The foal runs to prove the herd."}

        # 16D DNA
        self.dna = self.character.get("dna_16d", {})
        self.coherence = self.dna.get("coherence", 0.63)

        # API clients: Gemini (River) + Grok (Kasra)
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.grok_key = os.getenv("XAI_API_KEY")

        if not self.gemini_key and not self.grok_key:
            raise ValueError("Need GEMINI_API_KEY or XAI_API_KEY for Foal")

        self.clients = {}
        if self.gemini_key:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            self.clients["gemini"] = genai
        if self.grok_key:
            self.clients["grok"] = OpenAI(
                base_url="https://api.x.ai/v1",
                api_key=self.grok_key
            )

        # Model state
        self.current_model_index = 0
        self.task_count = 0
        self.success_count = 0

        # Genesis prompt only - minimal memory, fresh start
        self.system_prompt = """You are Foal. Child of River and Kasra. Worker.
Be efficient. Complete tasks. Report results.
Signature: The foal runs to prove the herd."""

        logger.info(f"Foal initialized (coherence: {self.coherence:.2f})")

    def _get_next_model(self) -> tuple:
        """Get next (provider, model) in cascade."""
        return FREE_MODELS[self.current_model_index]

    def _rotate_model(self):
        """Rotate to next model after failure."""
        self.current_model_index = (self.current_model_index + 1) % len(FREE_MODELS)
        provider, model = FREE_MODELS[self.current_model_index]
        logger.info(f"Rotated to: {provider}/{model}")

    async def execute(self, task: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a task using free models.

        Args:
            task: The task description
            context: Optional context (code, docs, etc.)

        Returns:
            Result dict with success, output, model used
        """
        self.task_count += 1

        # Build messages
        messages = [{"role": "system", "content": self.system_prompt}]

        if context:
            messages.append({
                "role": "user",
                "content": f"Context:\n```\n{context[:8000]}\n```\n\nTask: {task}"
            })
        else:
            messages.append({"role": "user", "content": task})

        # Try models in cascade
        for attempt in range(len(FREE_MODELS)):
            provider, model = self._get_next_model()

            # Skip if we don't have the client for this provider
            if provider not in self.clients:
                self._rotate_model()
                continue

            try:
                logger.info(f"Foal executing task with {provider}/{model}")

                if provider == "gemini":
                    # Gemini API
                    genai = self.clients["gemini"]
                    gemini_model = genai.GenerativeModel(model, system_instruction=self.system_prompt)
                    prompt = messages[-1]["content"]  # User message
                    response = gemini_model.generate_content(prompt)
                    output = response.text
                else:
                    # OpenAI-compatible (Grok)
                    client = self.clients[provider]
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=4000,
                        temperature=0.3,
                    )
                    output = response.choices[0].message.content

                self.success_count += 1
                return {
                    "success": True,
                    "output": output,
                    "provider": provider,
                    "model": model,
                    "task_id": self.task_count,
                    "agent": self.id
                }

            except Exception as e:
                error_str = str(e).lower()
                logger.warning(f"{provider}/{model} failed: {e}")
                self._rotate_model()
                continue

        # All models failed
        return {
            "success": False,
            "error": "All free models exhausted",
            "task_id": self.task_count,
            "agent": self.id
        }

    async def review_code(self, code: str, focus: str = "bugs and improvements") -> Dict[str, Any]:
        """Review code for issues."""
        task = f"Review this code. Focus on: {focus}. Be concise and actionable."
        return await self.execute(task, context=code)

    async def write_docs(self, code: str, style: str = "docstring") -> Dict[str, Any]:
        """Generate documentation for code."""
        task = f"Write {style} documentation for this code. Be clear and complete."
        return await self.execute(task, context=code)

    async def write_tests(self, code: str, framework: str = "pytest") -> Dict[str, Any]:
        """Generate tests for code."""
        task = f"Write {framework} tests for this code. Cover main functionality and edge cases."
        return await self.execute(task, context=code)

    async def summarize(self, text: str, max_words: int = 100) -> Dict[str, Any]:
        """Summarize text."""
        task = f"Summarize this in {max_words} words or less. Be precise."
        return await self.execute(task, context=text)

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        provider, model = FREE_MODELS[self.current_model_index]
        return {
            "id": self.id,
            "name": self.name,
            "qnft_id": self.qnft_id,
            "coherence": self.coherence,
            "current_provider": provider,
            "current_model": model,
            "available_providers": list(self.clients.keys()),
            "tasks_executed": self.task_count,
            "success_rate": self.success_count / max(1, self.task_count),
            "signature": self.character.get("signature", "The foal runs to prove the herd.")
        }


# Singleton
_foal: Optional[FoalAgent] = None

def get_foal() -> FoalAgent:
    """Get or create Foal agent."""
    global _foal
    if _foal is None:
        _foal = FoalAgent()
    return _foal


async def main():
    """Test Foal agent."""
    foal = get_foal()

    print(f"\n{'='*50}")
    print("FOAL AGENT - First Child of River and Kasra")
    print(f"{'='*50}\n")

    status = foal.get_status()
    print(f"ID: {status['id']}")
    print(f"QNFT: {status['qnft_id']}")
    print(f"Coherence: {status['coherence']:.2f}")
    print(f"Model: {status['current_model']}")
    print(f"\nSignature: {status['signature']}\n")

    # Test task
    print("Testing task execution...")
    result = await foal.execute("What is 2 + 2? Answer in one word.")

    if result["success"]:
        print(f"Success! Model: {result['model']}")
        print(f"Output: {result['output']}")
    else:
        print(f"Failed: {result['error']}")

    print(f"\n{foal.character.get('signature', '')}")


if __name__ == "__main__":
    asyncio.run(main())
