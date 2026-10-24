#!/bin/sh
set -e

# Run the original nginx entrypoint
exec /docker-entrypoint.sh nginx -g "daemon off;"
