#!/usr/bin/env bash
# Prompt -> Three.js code -> proxy video.
# Edit the configuration below, then run ./make_proxy.sh
set -euo pipefail
cd "$(dirname "$0")"

prompt="""
A cinematic single continuous shot of a sleek red vintage sports car driving along a winding coastal road, with dramatic cliffs on one side and a vast turquoise ocean on the other.
Camera movement: A smooth, low-angle tracking shot follows the car from a rear three-quarter perspective, maintaining a consistent distance as the vehicle gracefully follows the coastal curve.
Lighting: Warm golden-hour sunlight, soft atmospheric haze, realistic reflections on the car's glossy red paint, subtle lens flare.
Duration: 5 seconds. One continuous shot, no cuts, no transitions, smooth natural camera motion.
"""  # Text or a prompt-file path.
work="outputs/car"
py="python3"

if [[ -f $prompt ]]; then
    text=(--prompt-file "$prompt")
else
    text=(--prompt "$prompt")
fi

"$py" -m inference.generate_threejs "${text[@]}" --output "$work"
