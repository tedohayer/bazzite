# Steam bootstrap

Deck images ship `/usr/share/gamescope-session-plus/bootstrap_steam.tar.zst`,
a ready-to-run Steam client that is unpacked into `~/.local/share/Steam` the
first time Steam starts (by gamescope-session-plus in Game Mode, or by
`bazzite-steam` in Desktop Mode). Because it already contains a verified
client, Steam reaches the login screen without a network connection.

The archive is built during the image build by `build_files/tools/steam-bootstrap`
from `steam_client_steamrt64.manifest` in this directory. That file is Valve's
own client manifest, vendored unchanged. It pins the client version and the
sha256 of every package, so the build is reproducible and only changes when the
manifest does.

## Bumping the Steam client

```sh
./build_files/tools/steam-bootstrap-update
git diff build_files/bazzite-deck/steam_client_steamrt64.manifest
```

The script downloads the manifest Valve currently serves to Steam Deck stable
clients, checks that every package it lists is downloadable, and overwrites the
vendored copy. It prints the old and new versions; the version is the client's
build time as a Unix timestamp. Commit the manifest on its own. Nothing else
needs to change.

Every bump makes deck users download the bootstrap layer again (about 600 MB),
so there is no need to follow every client release. Bump when the bundled
client is months old, or when Valve changes something a first boot depends on.

To check a bump, build a deck image and boot it with no network. Steam should
reach the login screen, and `~/.local/share/Steam/logs/bootstrap_log.txt`
should end with `Verification complete` and contain no `Downloading manifest`
line.

## Where the pieces come from

Steam logs where it fetches updates from. In `logs/bootstrap_log.txt` of any
Steam install:

```text
Downloading manifest: https://client-update.fastly.steamstatic.com/steam_client_steamrt64
```

Manifests live at `https://client-update.steamstatic.com/steam_client_<channel>_<platform>`.
The channel is empty for stable desktop, or `publicbeta`, `steamdeck_stable` or
`steamdeck_publicbeta`. The platform is `steamrt64` on every channel, stable
included; `ubuntu12` is the old 32-bit client that the previous bootstrap
shipped. Each package entry's `file` is downloaded from the same host. Bazzite starts Steam with `-steamdeck`, so it
reads the `steamdeck_stable` channel.

A Steam install records what it has unpacked in `package/`, next to a copy of
the manifest. `steam-bootstrap` writes the same files for both the
`steam_client_steamrt64` and `steam_client_steamdeck_stable_steamrt64` names.
The `.installed` file has one `path,size;mtime;crc32` line per file
(directories have size `-1` and crc `0`, symlinks size `-2`), then
`OSVER=-183`, `VERSION=3`, and `SHA1=` with the uppercase SHA-1 of everything
above it. When this file is missing or wrong, Steam refuses to start offline
with "Steam needs to be online to update".

If a bump stops working offline, compare against a real install that runs the
same client version (the `version` in its `package/*.manifest` must match):

```sh
tar -xf bootstrap_steam.tar.zst -O Steam/package/steam_client_steamrt64.installed | sort > bootstrap.installed
sort ~/.local/share/Steam/package/steam_client_steamrt64.installed > real.installed
diff bootstrap.installed real.installed
```

Only the `SHA1=` line should differ, because the two files list the same
entries in a different order.
