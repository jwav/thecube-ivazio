#!/usr/bin/env bash
journalctl -u thecubeivazio.cubemaster.service -f --no-pager --output=short-iso-plain --no-hostname
