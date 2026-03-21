#!/bin/bash
set -e
cd "$(dirname "$0")/.."
echo "Building React frontend..."
npm run build
echo "Copying to src/aegis/viewer/static/..."
rm -rf ../src/aegis/viewer/static
cp -r dist ../src/aegis/viewer/static
echo "Done. React build copied to src/aegis/viewer/static/"
