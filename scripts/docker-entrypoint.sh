#!/bin/sh
set -e

DATA_DIR="${ADLEY_DATA_DIR:-/data}"
mkdir -p "$DATA_DIR"

if [ ! -w "$DATA_DIR" ]; then
  echo "ERROR: Data directory is not writable: $DATA_DIR" >&2
  exit 1
fi

echo "Adley starting (data_dir=$DATA_DIR, storage=${STORAGE_BACKEND:-json})"

exec "$@"
