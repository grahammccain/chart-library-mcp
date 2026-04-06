#!/bin/bash
# Publish Chart Library to the official MCP Registry
# Prerequisites: PyPI upload must be done first (see below)
# This script opens a browser for GitHub login, then publishes.

set -e
cd "$(dirname "$0")"

echo "=== Step 1: Upload to PyPI (if not done yet) ==="
echo "Run this first if you haven't uploaded 1.1.1 to PyPI:"
echo "  twine upload dist/chartlibrary_mcp-1.1.1*"
echo ""
echo "Press Enter to continue with MCP Registry publish (Ctrl+C to abort)..."
read

echo "=== Step 2: Login to MCP Registry via GitHub ==="
./mcp-publisher.exe login github

echo ""
echo "=== Step 3: Publish to MCP Registry ==="
./mcp-publisher.exe publish

echo ""
echo "Done! Verify at: https://registry.modelcontextprotocol.io/v0.1/servers?search=chart-library"
