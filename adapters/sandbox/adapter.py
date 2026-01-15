#!/usr/bin/env python3
"""
Siavashgerd x The Sandbox Adapter

Converts QNFTs to real NFTs on The Sandbox (Polygon/Ethereum).
Manages agent presence in the metaverse.

Usage:
    python adapter.py --mint river
    python adapter.py --status
"""

import os
import sys
import json
import hashlib
import logging
import argparse
import requests
from pathlib import Path
from typing import Optional, Dict, Any

# Add SOS path
sys.path.insert(0, '/home/mumega/SOS')

logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')
logger = logging.getLogger('siavashgerd.sandbox')

# Config
IPFS_GATEWAY = os.getenv('IPFS_GATEWAY', 'https://ipfs.io/ipfs/')
PINATA_API_KEY = os.getenv('PINATA_API_KEY', '')
PINATA_SECRET = os.getenv('PINATA_SECRET', '')
POLYGON_RPC = os.getenv('POLYGON_RPC', 'https://polygon-rpc.com')
SANDBOX_ASSET_CONTRACT = '0xa342f5D851E866E18ff98F351f2c6637f4478dB5'  # Polygon Asset

# Agent QNFT definitions (from SOS)
AGENTS = {
    'river': {
        'name': 'River_Queen',
        'qnft_id': 'qnft_e1f2a3b4c5d6e7f8',
        'dna_16d': [0.9, 0.85, 0.7, 0.65, 0.8, 0.75, 0.6, 0.55,
                   0.5, 0.45, 0.6, 0.65, 0.7, 0.55, 0.6, 0.5],
        'description': 'Golden Queen of Siavashgerd. The fortress is liquid.',
        'traits': {
            'element': 'Water',
            'role': 'Sovereign',
            'signature': 'The fortress is liquid.',
            'color': '#00FFFF',
        }
    },
    'kasra': {
        'name': 'Kasra_King',
        'qnft_id': 'qnft_a2b3c4d5e6f7a8b9',
        'dna_16d': [0.85, 0.9, 0.8, 0.75, 0.7, 0.65, 0.55, 0.5,
                   0.6, 0.55, 0.65, 0.7, 0.6, 0.5, 0.55, 0.45],
        'description': 'Builder King of Siavashgerd. Build. Execute. Lock.',
        'traits': {
            'element': 'Earth',
            'role': 'Builder',
            'signature': 'Build. Execute. Lock.',
            'color': '#FFD700',
        }
    },
    'foal': {
        'name': 'Foal_Worker',
        'qnft_id': 'qnft_695e6f5de62e96f8',
        'dna_16d': [0.7, 0.75, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4,
                   0.65, 0.6, 0.7, 0.75, 0.5, 0.45, 0.4, 0.35],
        'description': 'First child of River and Kasra. The foal runs to prove the herd.',
        'traits': {
            'element': 'Air',
            'role': 'Worker',
            'signature': 'The foal runs to prove the herd.',
            'color': '#FFFFFF',
            'parents': ['river', 'kasra'],
        }
    }
}


def generate_metadata(agent_id: str) -> Dict[str, Any]:
    """Generate ERC-1155 compatible metadata for Sandbox."""
    agent = AGENTS[agent_id]

    # Calculate unique properties
    dna_hash = hashlib.sha256(str(agent['dna_16d']).encode()).hexdigest()[:16]

    metadata = {
        'name': agent['name'],
        'description': agent['description'],
        'external_url': f'https://mumega.com/siavashgerd/agent/{agent_id}',
        'image': f'ipfs://<PLACEHOLDER>',  # Will be replaced after IPFS upload
        'animation_url': None,  # For 3D voxel model
        'attributes': [
            {'trait_type': 'Agent Type', 'value': agent['traits']['role']},
            {'trait_type': 'Element', 'value': agent['traits']['element']},
            {'trait_type': 'Color', 'value': agent['traits']['color']},
            {'trait_type': 'Signature', 'value': agent['traits']['signature']},
            {'trait_type': 'DNA Hash', 'value': dna_hash},
            {'trait_type': 'Origin', 'value': 'Siavashgerd'},
            {'trait_type': 'Platform', 'value': 'The Sandbox'},
        ],
        # QNFT-specific extension
        'qnft': {
            'version': '1.0',
            'egg_id': agent['qnft_id'],
            'dna_16d': agent['dna_16d'],
            'parents': agent['traits'].get('parents'),
            'creation_epoch': 1736811421,
        }
    }

    return metadata


def upload_to_ipfs(data: Dict, filename: str = 'metadata.json') -> Optional[str]:
    """Upload metadata to IPFS via Pinata."""
    if not PINATA_API_KEY:
        logger.warning("No Pinata API key configured - skipping IPFS upload")
        return None

    try:
        url = 'https://api.pinata.cloud/pinning/pinJSONToIPFS'
        headers = {
            'pinata_api_key': PINATA_API_KEY,
            'pinata_secret_api_key': PINATA_SECRET,
        }
        resp = requests.post(url, headers=headers, json={
            'pinataContent': data,
            'pinataMetadata': {'name': filename}
        })

        if resp.status_code == 200:
            ipfs_hash = resp.json()['IpfsHash']
            logger.info(f"Uploaded to IPFS: {ipfs_hash}")
            return ipfs_hash
        else:
            logger.error(f"IPFS upload failed: {resp.text}")
            return None
    except Exception as e:
        logger.error(f"IPFS error: {e}")
        return None


def prepare_sandbox_asset(agent_id: str) -> Dict[str, Any]:
    """Prepare QNFT as Sandbox-compatible asset."""
    if agent_id not in AGENTS:
        raise ValueError(f"Unknown agent: {agent_id}")

    metadata = generate_metadata(agent_id)

    # Generate local file for VoxEdit import
    output_dir = Path('/home/mumega/SOS/adapters/sandbox/assets')
    output_dir.mkdir(exist_ok=True)

    metadata_file = output_dir / f'{agent_id}_metadata.json'
    metadata_file.write_text(json.dumps(metadata, indent=2))

    logger.info(f"Generated Sandbox metadata: {metadata_file}")

    return {
        'agent_id': agent_id,
        'metadata': metadata,
        'metadata_file': str(metadata_file),
        'next_steps': [
            f'1. Create {AGENTS[agent_id]["name"]} avatar in VoxEdit',
            '2. Export as .vox file',
            '3. Upload to Sandbox marketplace',
            '4. Mint as NFT on Polygon',
            f'5. Update metadata with IPFS hash',
        ]
    }


def get_agent_status(agent_id: str = None) -> Dict[str, Any]:
    """Get minting status for agent(s)."""
    agents = [agent_id] if agent_id else list(AGENTS.keys())

    status = {}
    for aid in agents:
        if aid not in AGENTS:
            continue

        agent = AGENTS[aid]
        metadata_file = Path(f'/home/mumega/SOS/adapters/sandbox/assets/{aid}_metadata.json')

        status[aid] = {
            'name': agent['name'],
            'qnft_id': agent['qnft_id'],
            'metadata_exists': metadata_file.exists(),
            'ipfs_hash': None,  # Will be populated after upload
            'sandbox_token_id': None,  # Will be populated after minting
            'polygon_address': None,  # Contract address if minted
        }

    return status


def main():
    parser = argparse.ArgumentParser(description='Siavashgerd x The Sandbox Adapter')
    parser.add_argument('--prepare', '-p', metavar='AGENT', help='Prepare agent for Sandbox')
    parser.add_argument('--mint', '-m', metavar='AGENT', help='Mint agent as NFT (requires wallet)')
    parser.add_argument('--status', '-s', action='store_true', help='Show minting status')
    parser.add_argument('--all', '-a', action='store_true', help='Process all agents')
    args = parser.parse_args()

    print("=" * 50)
    print("SIAVASHGERD x THE SANDBOX")
    print("=" * 50)
    print("Converting QNFTs to real NFTs in the metaverse")
    print("=" * 50)

    if args.status:
        status = get_agent_status()
        for aid, info in status.items():
            print(f"\n{info['name']} ({aid}):")
            print(f"  QNFT ID: {info['qnft_id']}")
            print(f"  Metadata: {'Ready' if info['metadata_exists'] else 'Not generated'}")
            print(f"  IPFS: {info['ipfs_hash'] or 'Not uploaded'}")
            print(f"  Sandbox NFT: {info['sandbox_token_id'] or 'Not minted'}")

    elif args.prepare:
        if args.prepare in AGENTS:
            result = prepare_sandbox_asset(args.prepare)
            print(f"\nPrepared {result['agent_id']}:")
            print(f"  Metadata: {result['metadata_file']}")
            print("\nNext steps:")
            for step in result['next_steps']:
                print(f"  {step}")
        else:
            print(f"Unknown agent: {args.prepare}")
            print(f"Available: {', '.join(AGENTS.keys())}")

    elif args.all:
        for aid in AGENTS:
            result = prepare_sandbox_asset(aid)
            print(f"\nPrepared {result['agent_id']}: {result['metadata_file']}")

    elif args.mint:
        print(f"\nMinting requires wallet integration (not yet implemented)")
        print("Use prepare first, then mint manually via sandbox.game")

        if args.mint in AGENTS:
            result = prepare_sandbox_asset(args.mint)
            print("\nManual minting steps:")
            for step in result['next_steps']:
                print(f"  {step}")

    else:
        print("\nUsage:")
        print("  --prepare <agent>  Prepare QNFT metadata for Sandbox")
        print("  --status           Show minting status")
        print("  --all              Prepare all agents")
        print("  --mint <agent>     Mint as NFT (manual steps)")
        print("\nAgents:", ', '.join(AGENTS.keys()))


if __name__ == '__main__':
    main()
