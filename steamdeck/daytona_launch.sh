#!/bin/bash
# Daytona USA (Sega PC, 1996, the original software-rendered Windows 95 port) Steam Deck / Proton launch wrapper.
#
# Steam > Daytona USA > Properties > Launch Options:
#   /home/deck/Games/DaytonaUSA/daytona_launch.sh %command%
# Shortcut target: /home/deck/Games/DaytonaUSA/game/DAYTONA.EXE, Start In: /home/deck/Games/DaytonaUSA/game/
#
# DAYTONA.EXE is patched (patch_exe.py): no CD hunt, MUSIC.BIN (announcer and jingles) read from game/, CD music
# that keeps looping under ogg-winmm, the D-pad and both triggers read, a steering dead zone, no busy wait.
# Settings live in game/DAYTONA.INI (the exe asks for .\DAYTONA.INI itself). No fake CD-ROM drive, no registry.
#
# Every launch sets DLL overrides so Wine loads the wrappers sitting beside the exe:
#   winmm.dll   ogg-winmm: CD audio from Music/TrackNN.ogg
#   ddraw.dll   dgVoodoo2 2.79.3: 16-bit DirectDraw -> D3D11 -> DXVK, the game's 640x400 picture over the screen
#
# RENDERER (set before the script path in Launch Options, default dgvoodoo):
#   dgvoodoo  ddraw from dgVoodoo2
#   wined3d   plain Wine ddraw
#   Example:  RENDERER=wined3d /home/deck/Games/DaytonaUSA/daytona_launch.sh %command%

set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$HERE/launch.log"
# A file RENDERER beside this script holding e.g. wined3d wins over the default (switch it from Desktop Mode).
[ -z "${RENDERER:-}" ] && [ -s "$HERE/RENDERER" ] && RENDERER="$(tr -d ' \n' < "$HERE/RENDERER")"
RENDERER="${RENDERER:-dgvoodoo}"
log() { echo "[$(date '+%H:%M:%S')] $*" >>"$LOG"; }
: >"$LOG"
log "args: $*"
log "RENDERER=$RENDERER  STEAM_COMPAT_DATA_PATH=${STEAM_COMPAT_DATA_PATH:-unset}"

# Proton appends its own overrides after ours.
OVR="winmm=n,b"
case "$RENDERER" in
  dgvoodoo) OVR="$OVR;ddraw=n,b" ;;
  wined3d)  OVR="$OVR;ddraw=b" ;;
  *)        log "unknown RENDERER '$RENDERER', using dgvoodoo"; OVR="$OVR;ddraw=n,b" ;;
esac
export WINEDLLOVERRIDES="${OVR}${WINEDLLOVERRIDES:+;$WINEDLLOVERRIDES}"
log "WINEDLLOVERRIDES=$WINEDLLOVERRIDES"

# Debugging: if a file named PROTON_LOG exists beside this script, Proton writes
# steam-<appid>.log here (crash addresses, exceptions). Create / delete it from Desktop Mode; no launch-option edit.
if [ -e "$HERE/PROTON_LOG" ]; then
  export PROTON_LOG=1 PROTON_LOG_DIR="$HERE"
  log "PROTON_LOG on -> $HERE/steam-*.log"
  # Extra Wine debug channels for that log: a file WINEDEBUG beside this script holding e.g. +ddraw
  if [ -s "$HERE/WINEDEBUG" ]; then
    export WINEDEBUG="+timestamp,+tid,+seh,+loaddll,$(tr -d ' \n' < "$HERE/WINEDEBUG")"
    log "WINEDEBUG=$WINEDEBUG"
  fi
fi

# Frame rate / GPU load overlay (DXVK, on top of dgVoodoo's D3D11): a file DXVK_HUD beside this script
# holding e.g. fps,gpuload. Create / delete it from Desktop Mode.
if [ -s "$HERE/DXVK_HUD" ]; then
  export DXVK_HUD="$(tr -d ' \n' < "$HERE/DXVK_HUD")"
  log "DXVK_HUD=$DXVK_HUD"
fi

for f in DAYTONA.EXE DAYTONA.INI DAYTONA.DAT MUSIC.BIN RES_USA.DLL PC_LOGO.BIN CS0POLY.BIN TEX_C0.BIN winmm.dll winmm.ini ddraw.dll dgVoodoo.conf Music/Track02.ogg Music/Track22.ogg; do
  [ -e "$HERE/game/$f" ] || log "WARNING: game/$f missing"
done

log "exec: $*"
exec "$@"
