#!/usr/bin/env bash
# Prompt -> proxy -> reference -> video, end to end.
# Edit the configuration below, then run ./make_all.sh
set -euo pipefail
cd "$(dirname "$0")"

prompt="a red car on a coastal road"  # Text or a prompt-file path.
work="outputs/car"
model="models/MiniMax-H3-ref2va"
py="python3"

proxy="$work/proxy.mp4"
out="$work/video.mp4"
ref=${out%.*}.reference.png
[[ -d $model ]] || { echo "checkpoint not found: $model" >&2; exit 1; }

if [[ -f $prompt ]]; then
    text=(--prompt-file "$prompt")
else
    text=(--prompt "$prompt")
fi

"$py" -m inference.generate_threejs "${text[@]}" --output "$work"
"$py" -m inference.generate_reference --video "$proxy" --output "$ref"
"$py" -m inference.generate_video --code-video "$proxy" --reference-image "$ref" \
    "${text[@]}" --model-root "$model" --output "$out"
echo "video: $out"
