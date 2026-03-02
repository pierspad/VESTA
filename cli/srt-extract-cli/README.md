# srt-extract-cli

Command-line tool for extracting and analyzing data from SRT subtitle files.

## Installation

### From source

```bash
cargo install --path .
```

### Pre-built binaries

Download from the releases page or build using `./build_all.sh` from the project root.

## Usage

```bash
# Extract as JSON
srt-extract --input movie.srt --format json

# Get subtitle statistics
srt-extract --input movie.srt --format stats

# Get a summary
srt-extract --input movie.srt --format summary

# Debug format (detailed)
srt-extract --input movie.srt --format debug

# Save to file
srt-extract --input movie.srt --format json --output subtitles.json
```

## Output Formats

| Format | Description |
|--------|-------------|
| `json` | Full subtitle data as JSON array |
| `stats` | Statistics (count, duration, words, etc.) |
| `summary` | Brief overview of the file |
| `debug` | Detailed output for debugging |

## License

MIT
