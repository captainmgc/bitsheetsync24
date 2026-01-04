#!/bin/bash
# Uninstall Bitrix24 Sync Daemon systemd service

set -e

SERVICE_NAME="bitrix-sync"
SYSTEMD_DIR="/etc/systemd/system"

echo "========================================="
echo "Bitrix24 Sync Daemon Uninstaller"
echo "========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Stop service if running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "⏸️  Stopping service..."
    systemctl stop "$SERVICE_NAME"
fi

# Disable service
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "🔓 Disabling service..."
    systemctl disable "$SERVICE_NAME"
fi

# Remove service file
if [ -f "${SYSTEMD_DIR}/${SERVICE_NAME}.service" ]; then
    echo "🗑️  Removing service file..."
    rm -f "${SYSTEMD_DIR}/${SERVICE_NAME}.service"
fi

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload
systemctl reset-failed

echo ""
echo "========================================="
echo "✅ Service uninstalled successfully!"
echo "========================================="
echo ""
echo "Note: Log files in logs/ directory were kept."
echo "To remove them manually: rm -rf logs/"
