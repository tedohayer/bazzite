#!/usr/bin/env bash
#
# Install Gamescope Session supporting files for Bazzite.
#
# Builds the Steam bootstrap archive used by gamescope-session-plus
# and sets component metadata attributes for tracking.
#
set -xeuo pipefail

echo "::group::Install gamescope session"
trap 'echo "::endgroup::"' EXIT

# -- Create gamescope-session-plus directory --
# Ensure the target directory exists before writing files.
echo "==> Creating gamescope-session-plus directory..."
mkdir -p /usr/share/gamescope-session-plus/

# -- Build Steam bootstrap archive --
# Assemble the Steam client pinned by the vendored Valve manifest.
STEAM_BOOTSTRAP=/usr/share/gamescope-session-plus/bootstrap_steam.tar.zst
echo "==> Building Steam bootstrap archive..."
/ctx/tools/steam-bootstrap \
    /ctx/bazzite-deck/steam_client_steamrt64.manifest \
    "${STEAM_BOOTSTRAP}"

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
