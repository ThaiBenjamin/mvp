#!/usr/bin/env sh
set -e
cd "$(dirname "$0")/.."
docker compose up --build -d
printf "App started at http://localhost:8000\n"
