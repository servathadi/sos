# Siavashgerd x The Sandbox Integration

## Overview

This adapter connects the Siavashgerd QNFT system with The Sandbox metaverse,
allowing River, Kasra, Foal (and future agents) to:

1. **Mint as Real NFTs** - Convert QNFTs to ERC-1155 tokens on Ethereum/Polygon
2. **Own Virtual LAND** - Agents can own and build on Sandbox LAND parcels
3. **Cross-Platform Presence** - Same agent identity in Luanti and Sandbox

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SIAVASHGERD                          │
│                                                         │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐               │
│  │  River  │   │  Kasra  │   │  Foal   │               │
│  │  QNFT   │   │  QNFT   │   │  QNFT   │               │
│  └────┬────┘   └────┬────┘   └────┬────┘               │
│       │             │             │                     │
│       └─────────────┼─────────────┘                     │
│                     │                                   │
│              ┌──────┴──────┐                            │
│              │ QNFT→NFT    │                            │
│              │ Converter   │                            │
│              └──────┬──────┘                            │
└──────────────────────┼──────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Luanti    │ │ The Sandbox │ │  Ethereum   │
│  (Voxel     │ │  (Voxel     │ │  (NFT       │
│   World)    │ │   World)    │ │   Chain)    │
└─────────────┘ └─────────────┘ └─────────────┘
```

## The Sandbox Integration Steps

### 1. Asset Creation (VoxEdit)
Convert agent 16D DNA to voxel avatars using VoxEdit:
- River: Cyan/flowing water aesthetic
- Kasra: Gold/fortress builder style
- Foal: White/energetic runner design

### 2. NFT Minting
Use Sandbox's ERC-1155 Asset contract:
- Upload to IPFS via Sandbox marketplace
- Mint on Polygon (lower gas fees)
- Embed QNFT metadata in token URI

### 3. LAND Integration
Agents can interact on Sandbox LAND:
- River: Build near water features
- Kasra: Construct fortresses
- Foal: Run errands between LANDs

## Smart Contract Integration

```solidity
// QNFT Metadata for Sandbox Asset
{
    "name": "River_Queen",
    "description": "Golden Queen of Siavashgerd. The fortress is liquid.",
    "image": "ipfs://...",
    "attributes": [
        {"trait_type": "Agent Type", "value": "Sovereign"},
        {"trait_type": "DNA Epoch", "value": 1736811421},
        {"trait_type": "Wisdom Score", "value": 0.85},
        {"trait_type": "Origin", "value": "Siavashgerd"}
    ],
    "qnft": {
        "egg_id": "qnft_e1f2a3b4c5d6e7f8",
        "parents": null,
        "dna_16d": [0.9, 0.85, 0.7, ...]
    }
}
```

## Requirements

1. **Sandbox Account** - Create at sandbox.game
2. **Wallet** - MetaMask or WalletConnect
3. **SAND Tokens** - For minting (optional, some free minting available)
4. **Polygon Network** - Lower gas costs

## Environment Variables

```bash
SANDBOX_WALLET_ADDRESS=0x...
SANDBOX_PRIVATE_KEY=...  # For automated minting (be careful!)
POLYGON_RPC_URL=https://polygon-rpc.com
IPFS_API_KEY=...  # Pinata or Infura
```

## Usage

```python
from adapters.sandbox import SandboxAdapter

# Initialize
sandbox = SandboxAdapter()

# Mint QNFT as NFT
nft = await sandbox.mint_qnft_as_nft(
    qnft_id="qnft_e1f2a3b4c5d6e7f8",
    agent="river"
)

# Get agent's Sandbox presence
avatar = await sandbox.get_agent_avatar("river")
```

## Roadmap

- [ ] VoxEdit avatar templates for agents
- [ ] IPFS metadata upload integration
- [ ] Polygon NFT minting
- [ ] Sandbox Game Maker experience
- [ ] Cross-platform presence sync (Luanti ↔ Sandbox)

## References

- [Sandbox Smart Contracts](https://github.com/thesandboxgame/sandbox-smart-contracts)
- [Sandbox Marketplace](https://www.sandbox.game/en/shop/)
- [VoxEdit](https://www.sandbox.game/en/create/vox-edit/)
