#!/usr/bin/env bash
# Downloads the CUAD v1 dataset (Atticus Project, CC BY 4.0)
# https://github.com/TheAtticusProject/cuad
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)/data"
mkdir -p "$DIR"

echo "Downloading CUAD v1 into $DIR ..."
curl -sL -o "$DIR/cuad_data.zip" https://github.com/TheAtticusProject/cuad/raw/main/data.zip
unzip -o -q "$DIR/cuad_data.zip" -d "$DIR"
echo "Done. Files:"
ls -lh "$DIR"
