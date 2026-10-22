#!/bin/sh
# Dev container start: keep the node_modules volume in step with package.json and pnpm-lock.yaml.
# The volume is filled once, when it is first created, so a dependency added later would be missing
# (the "Failed to resolve import" error). A hash of the two files is stored inside the volume; when it
# differs, the install runs again. Nothing is deleted: only missing or changed packages are touched.
set -e
STAMP=node_modules/.deps-hash
HASH=$(cat package.json pnpm-lock.yaml | sha256sum | cut -d' ' -f1)
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$HASH" ]; then
  echo "[entrypoint] package.json or pnpm-lock.yaml changed: installing dependencies..."
  pnpm install --frozen-lockfile
  echo "$HASH" > "$STAMP"
fi
exec "$@"
