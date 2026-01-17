#!/bin/bash
# SOS Beta2 - Service Uninstallation Script

set -e

echo "==================================="
echo "SOS Beta2 - Service Uninstallation"
echo "==================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo $0"
    exit 1
fi

# Stop services
echo "[1/3] Stopping services..."
systemctl stop sos.target 2>/dev/null || true
systemctl stop sos-engine.service 2>/dev/null || true
systemctl stop sos-memory.service 2>/dev/null || true
systemctl stop sos-tools.service 2>/dev/null || true
systemctl stop sos-economy.service 2>/dev/null || true

# Disable services
echo "[2/3] Disabling services..."
systemctl disable sos.target 2>/dev/null || true
systemctl disable sos-engine.service 2>/dev/null || true
systemctl disable sos-memory.service 2>/dev/null || true
systemctl disable sos-tools.service 2>/dev/null || true
systemctl disable sos-economy.service 2>/dev/null || true

# Remove service files
echo "[3/3] Removing service files..."
rm -f /etc/systemd/system/sos-engine.service
rm -f /etc/systemd/system/sos-memory.service
rm -f /etc/systemd/system/sos-tools.service
rm -f /etc/systemd/system/sos-economy.service
rm -f /etc/systemd/system/sos.target

systemctl daemon-reload

echo ""
echo "SOS services uninstalled."
