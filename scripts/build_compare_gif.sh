#!/bin/sh
# Build docs/video/bike-cliff/compare.gif: the 3 videos side by side, synced, 10 fps, 10 s, no audio.
# Needs ffmpeg and swift (macOS) for the label strip. Run from the repository root.
set -eu
dir=docs/video/bike-cliff
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
swiftc -o "$work/labels" scripts/compare_labels.swift
"$work/labels" "$work/labels.png"
ffmpeg -y -loglevel error -t 10 -i "$dir/1_noob.mp4" -t 10 -i "$dir/2_plain.mp4" -t 10 -i "$dir/3_skill.mp4" -i "$work/labels.png" -filter_complex \
"[0:v]fps=10,scale=320:180:flags=lanczos,pad=324:180:0:0:0x121212[a];[1:v]fps=10,scale=320:180:flags=lanczos,pad=324:180:0:0:0x121212[b];[2:v]fps=10,scale=320:180:flags=lanczos[c];[a][b][c]hstack=inputs=3[row];[3:v]format=rgb24[h];[h][row]vstack=inputs=2,split[s0][s1];[s0]palettegen=max_colors=100:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
-map_metadata -1 -fflags +bitexact -flags:v +bitexact -loop 0 "$dir/compare.gif"
