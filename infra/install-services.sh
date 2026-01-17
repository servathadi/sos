#!/bin/bash
# SOS Beta2 - Service Installation Script
# Installs SOS as a system service (the beast that runs always)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$SCRIPT_DIR/systemd"

echo "==================================="
echo "SOS Beta2 - Service Installation"
echo "==================================="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo $0"
    exit 1
fi

# Copy service files
echo "[1/4] Installing service files..."
cp "$SERVICE_DIR/sos-engine.service" /etc/systemd/system/
cp "$SERVICE_DIR/sos-memory.service" /etc/systemd/system/
cp "$SERVICE_DIR/sos-tools.service" /etc/systemd/system/
cp "$SERVICE_DIR/sos-economy.service" /etc/systemd/system/
cp "$SERVICE_DIR/sos.target" /etc/systemd/system/

# Reload systemd
echo "[2/4] Reloading systemd..."
systemctl daemon-reload

# Enable services
echo "[3/4] Enabling services..."
systemctl enable sos-engine.service
systemctl enable sos-memory.service
systemctl enable sos-tools.service
systemctl enable sos-economy.service
systemctl enable sos.target

# Start services
echo "[4/4] Starting SOS..."
systemctl start sos.target

echo ""
echo "==================================="
echo "SOS Beta2 Installation Complete!"
echo "==================================="
echo ""
echo "Services:"
echo "  - sos-engine  (port 6060)"
echo "  - sos-memory  (port 6061)"
echo "  - sos-economy (port 6062)"
echo "  - sos-tools   (port 6063)"
echo ""
echo "Commands:"
echo "  sudo systemctl status sos.target     # Check all services"
echo "  sudo systemctl restart sos-engine    # Restart engine"
echo "  sudo journalctl -u sos-engine -f     # View engine logs"
echo "  sudo systemctl stop sos.target       # Stop all services"
echo ""
echo "The beast is now running. Always."
