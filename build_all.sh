#!/bin/bash

cargo build --release

mkdir -p bin
cp target/release/srt-extract bin/
cp target/release/srt-translate bin/

echo "Build complete! Binaries are available in:"
echo "   - bin/srt-extract"
echo "   - bin/srt-translate"

