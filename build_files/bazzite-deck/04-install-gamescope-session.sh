#!/usr/bin/env bash
#
# Install Gamescope Session supporting files for Bazzite.
#
# Installs the Steam bootstrap archive used by gamescope-session-plus
# and sets component metadata attributes for tracking.
#
set -xeuo pipefail

echo "::group::Install gamescope session"
trap 'echo "::endgroup::"' EXIT

# -- Create gamescope-session-plus directory --
# Ensure the target directory exists before writing files.
echo "==> Creating gamescope-session-plus directory..."
mkdir -p /usr/share/gamescope-session-plus/

# -- Install Steam bootstrap archive --
# Copy the archive published by the steam_bootstrap workflow.
STEAM_BOOTSTRAP=/usr/share/gamescope-session-plus/bootstrap_steam.tar.zst
echo "==> Installing Steam bootstrap archive..."
cp /tmp/steam-bootstrap/bootstrap_steam.tar.zst "${STEAM_BOOTSTRAP}"

# -- Set component metadata attributes --
# Tag the bootstrap archive with component and update-interval for tracking.
echo "==> Setting component metadata attributes..."
setfattr \
    -n user.component \
    -v "steam-bootstrap" \
    "${STEAM_BOOTSTRAP}"

setfattr \
    -n user.update-interval \
    -v "yearly" \
    "${STEAM_BOOTSTRAP}"
