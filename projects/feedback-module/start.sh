#!/bin/bash
# Usage: ./start.sh [port] [allowed-origins]
export FEEDBACK_PORT=${1:-3333}
export ALLOWED_ORIGINS=${2:-*}
node server.js
