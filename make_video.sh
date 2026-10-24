#!/usr/bin/env bash
# Proxy video -> reference image -> MiniMax-H3 video.
# Edit the configuration below, then run ./make_video.sh
set -euo pipefail
cd "$(dirname "$0")"

proxy="outputs/car/proxy.mp4"
prompt="a red car on a coastal road"  # Text or a prompt-file path.
out="outputs/car/video.mp4"
model="models/MiniMax-H3-ref2va"
py="python3"

ref=${out%.*}.reference.png
[[ -f $proxy ]] || { echo "proxy not found: $proxy" >&2; exit 1; }
[[ -d $model ]] || { echo "checkpoint not found: $model" >&2; exit 1; }

if [[ -f $prompt ]]; then
    text=(--prompt-file "$prompt")
else
    text=(--prompt "$prompt")
fi

"$py" -m inference.generate_reference --video "$proxy" --output "$ref"
"$py" -m inference.generate_video --code-video "$proxy" --reference-image "$ref" \
    "${text[@]}" --model-root "$model" --output "$out"
