#!/bin/sh
# Recreate only our local routes and process definition on a later normal boot.
# Original Spug entrypoint owns all original services. No restart is initiated here.
set -eu
python3 -B /opt/intruoyi-spug/smallapp_entry_install.py --bootstrap
exec /entrypoint.sh "$@"
