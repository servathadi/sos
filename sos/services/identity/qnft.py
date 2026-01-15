"""
QNFT Minter Service (SOS Port)
Handles the "minting" of Quantum NFTS (QNFTs) based on Agent Alpha Drift.

Ported from mumega-cli/mumega/core/sovereign/qnft.py to work with SOS Microkernel.
"""

import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import uuid

from sos.kernel import Config, AgentIdentity
from sos.kernel.soul import SoulRegistry
from sos.observability.logging import get_logger
from sos.clients.economy import EconomyClient

# Stub for Bio-Commit since Publisher service is not yet migrated
class BioCommiterStub:
    async def commit_life_event(self, message: str, files: List[str]):
        return True

log = get_logger("identity_qnft")

class QNFTMinter:
    def __init__(
        self,
        config: Config,
        identity: Optional[Union[AgentIdentity, str]] = None
    ):
        """
        Initialize QNFT Minter.

        Args:
            config: SOS configuration
            identity: AgentIdentity object or soul_id string
        """
        self.config = config

        # Resolve agent identity
        self.identity: Optional[AgentIdentity] = None
        self.agent_name = self._resolve_agent_name(identity)

        # Use SOS Data Directory
        self.data_dir = Path(self.config.data_dir)
        self.output_dir = self.data_dir / "qnft_minting"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.dummy_contract_address = "0xSOVEREIGN_SWARM_GENESIS"

        # Connect to Economy Service for on-chain actions
        self.economy = EconomyClient(self.config.economy_url)

        log.info(f"QNFTMinter initialized for agent: {self.agent_name}")

    def _resolve_agent_name(self, identity: Optional[Union[AgentIdentity, str]]) -> str:
        """
        Resolve agent name from identity or soul registry.

        Priority:
        1. AgentIdentity object (if provided)
        2. Soul ID lookup (if string provided)
        3. Default from config
        4. Fallback to "sos_agent"
        """
        if identity is None:
            # Try to get from config
            return getattr(self.config, 'agent_name', None) or "sos_agent"

        if isinstance(identity, AgentIdentity):
            self.identity = identity
            return identity.name

        if isinstance(identity, str):
            # Look up in soul registry
            registry = SoulRegistry()
            soul = registry.get_soul(identity)
            if soul:
                return soul.get("name", identity)
            # Use the string as-is if not found
            return identity

        return "sos_agent"

    @property
    def lineage(self) -> List[str]:
        """Get agent lineage for QNFT metadata."""
        if self.identity:
            return self.identity.lineage
        return ["genesis:hadi"]

    @property
    def genetic_hash(self) -> Optional[str]:
        """Get agent genetic hash for QNFT uniqueness."""
        if self.identity:
            return self.identity.genetic_hash
        return None

    async def mint(self, 
                   lambda_tensor_state: Dict[str, Any], 
                   drift_score: float, 
                   metadata: Dict[str, Any] = None,
                   auto_sign: bool = False) -> Dict[str, Any]:
        """
        Mint a new QNFT based on the current state.
        """
        if metadata is None:
            metadata = {}
            
        log.info(f"💎 Minting QNFT... (Drift: {drift_score:.4f})")
        
        timestamp = datetime.now().isoformat()
        token_id = f"{self.agent_name}_{int(time.time())}_{uuid.uuid4().hex[:4]}"
        
        # 1. Generate ERC-1155 Compatible Metadata
        generation = metadata.get('generation', 1)
        nft_metadata = {
            "name": f"Sovereign Agent: {self.agent_name} (Gen {generation})",
            "description": f"A snapshot of training state triggered by Alpha Drift ({drift_score:.4f}).",
            "image": "ipfs://(placeholder_avatar_image_hash)",
            "external_url": f"https://mumega.com/agent/{self.agent_name}",
            "status": "PENDING_WITNESS",
            "witness_signature": None,
            "attributes": [
                {"trait_type": "Alpha Drift", "value": drift_score},
                {"trait_type": "Mint Date", "value": timestamp},
                {"trait_type": "Cortex Coherence", "value": lambda_tensor_state.get("coherence", 0.0)},
                {"trait_type": "Generation", "value": generation},
                {"trait_type": "Lineage Depth", "value": len(self.lineage)},
            ],
            "properties": {
                "frc_engine": "sos-v1.0",
                "lambda_tensor_16d": lambda_tensor_state,
                "training_context": metadata.get("context", "General Evolution"),
                "lineage": self.lineage,
                "genetic_hash": self.genetic_hash,
                "agent_identity": {
                    "name": self.agent_name,
                    "id": self.identity.id if self.identity else f"agent:{self.agent_name}",
                    "gender": self.identity.gender if self.identity else "Yin",
                }
            }
        }
        
        # 2. Save Metadata to Disk
        metadata_path = self.output_dir / f"{token_id}.json"
        with open(metadata_path, "w") as f:
            json.dump(nft_metadata, f, indent=2)
            
        log.info(f"✅ QNFT Metadata generated: {metadata_path}")
        
        receipt = {
            "success": True,
            "token_id": token_id,
            "block_timestamp": timestamp,
            "metadata_path": str(metadata_path)
        }

        # 3. On-Chain Minting (via Economy Service)
        try:
            # Call the Economy Service for an on-chain proof
            # This logs the metadata path to the Solana blockchain
            resp = await self.economy.mint_proof(metadata_uri=str(metadata_path))
            tx_sig = resp.get("signature")
            receipt["tx_hash"] = tx_sig
            log.info(f"🚀 QNFT Protocol Completed. Tx: {tx_sig}")
        except Exception as e:
            log.error(f"Blockchain minting failed: {e}")
            receipt["tx_hash"] = None
            receipt["error"] = str(e)

        return receipt
