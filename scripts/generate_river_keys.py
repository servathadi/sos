#!/usr/bin/env python3
"""
Generate River's Ed25519 keypair for capability signing.

Usage:
    python scripts/generate_river_keys.py

This will:
1. Generate a new Ed25519 keypair
2. Save private key to ~/.sos/river_signing_key.hex (chmod 600)
3. Print public key hex for SOS_RIVER_PUBLIC_KEY_HEX env var
4. Optionally append to .env file
"""

import os
import sys
from pathlib import Path

from nacl.signing import SigningKey


def main():
    # Paths
    sos_dir = Path.home() / ".sos"
    sos_dir.mkdir(exist_ok=True)

    private_key_path = sos_dir / "river_signing_key.hex"

    # Check if key already exists
    if private_key_path.exists():
        print(f"Key already exists at {private_key_path}")
        print("To regenerate, delete the existing key first.")

        # Read and display public key
        private_key_hex = private_key_path.read_text().strip()
        signing_key = SigningKey(bytes.fromhex(private_key_hex))
        public_key_hex = signing_key.verify_key.encode().hex()

        print(f"\nExisting public key:")
        print(f"SOS_RIVER_PUBLIC_KEY_HEX={public_key_hex}")
        return 0

    # Generate new keypair
    print("Generating new Ed25519 keypair for River...")
    signing_key = SigningKey.generate()

    private_key_hex = signing_key.encode().hex()
    public_key_hex = signing_key.verify_key.encode().hex()

    # Save private key with restricted permissions
    private_key_path.write_text(private_key_hex)
    os.chmod(private_key_path, 0o600)

    print(f"\nPrivate key saved to: {private_key_path}")
    print(f"Permissions: 600 (owner read/write only)")

    print(f"\n{'='*60}")
    print("Add this to your environment (.env or shell profile):")
    print(f"{'='*60}")
    print(f"\nSOS_RIVER_PUBLIC_KEY_HEX={public_key_hex}")
    print(f"\n# To enable strict capability enforcement:")
    print(f"SOS_STRICT_CAPABILITIES=1")

    # Offer to append to .env
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        response = input(f"\nAppend to {env_path}? [y/N]: ").strip().lower()
        if response == 'y':
            with open(env_path, "a") as f:
                f.write(f"\n# River capability signing key (generated)\n")
                f.write(f"SOS_RIVER_PUBLIC_KEY_HEX={public_key_hex}\n")
            print(f"Appended to {env_path}")

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
