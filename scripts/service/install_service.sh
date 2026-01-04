#!/bin/bash
# Install Bitrix24 Sync Daemon as systemd service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="bitrix-sync"
SERVICE_FILE="${SCRIPT_DIR}/${SERVICE_NAME}.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "========================================="
echo "Bitrix24 Sync Daemon Installer"
echo "========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p "${SCRIPT_DIR}/logs"
chown captain:captain "${SCRIPT_DIR}/logs"

# Stop service if already running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "⏸️  Stopping existing service..."
    systemctl stop "$SERVICE_NAME"
fi

# Copy service file
echo "📋 Installing service file..."
cp "$SERVICE_FILE" "${SYSTEMD_DIR}/${SERVICE_NAME}.service"

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Enable service
echo "✅ Enabling service..."
systemctl enable "$SERVICE_NAME"

# Start service
echo "▶️  Starting service..."
systemctl start "$SERVICE_NAME"

# Check status
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo "========================================="
    echo "✅ Service installed and started successfully!"
    echo "========================================="
    echo ""
    echo "Useful commands:"
    echo "  Status:  sudo systemctl status ${SERVICE_NAME}"
    echo "  Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
    echo "  Stop:    sudo systemctl stop ${SERVICE_NAME}"
    echo "  Start:   sudo systemctl start ${SERVICE_NAME}"
    echo "  Restart: sudo systemctl restart ${SERVICE_NAME}"
    echo "  Disable: sudo systemctl disable ${SERVICE_NAME}"
    echo ""
    systemctl status "$SERVICE_NAME" --no-pager -l
else
    echo ""
    echo "❌ Service failed to start. Check logs:"
    echo "  sudo journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi
