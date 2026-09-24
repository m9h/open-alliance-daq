#!/usr/bin/env bash
# Pull finished run CSVs from the acquisition Pi to the analysis machine.
# Usage: pull-runs.sh [user@host] [remote_dir] [local_dir]
# Defaults match the lab layout: Pi 4 at 192.168.108.194, ~/hplc-runs on both ends.
# Only complete files move: rsync copies to a temp name and renames, and the logger writes each
# CSV in one pass, so a run that is still recording is skipped until the next tick because the
# size keeps changing (--size-only is deliberately NOT used).
set -euo pipefail
SRC="${1:-mhough@192.168.108.194}"
RDIR="${2:-hplc-runs}"
LDIR="${3:-$HOME/hplc-runs}"
mkdir -p "$LDIR"
rsync -a --quiet --include='*.csv' --exclude='*' -e "ssh -o BatchMode=yes -o ConnectTimeout=10" "$SRC:$RDIR/" "$LDIR/"
