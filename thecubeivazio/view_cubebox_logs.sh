#!/usr/bin/env bash
journalctl -u thecubeivazio.cubebox.service -f --no-pager --output=short-iso-plain --no-hostname
