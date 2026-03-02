# srt-translate-cli

Command-line tool for translating SRT subtitle files using AI/LLM APIs.

## Installation

### From source

```bash
cargo install --path .
```

### Pre-built binaries

Download from the releases page or build using `./build_all.sh` from the project root.

## Usage

```bash
# Basic usage with config file
srt-translate --input movie.srt --output movie.it.srt

# Specify target language
srt-translate -i movie.srt -o movie.es.srt --lang Spanish

# Use specific provider and model
srt-translate -i movie.srt -o movie.fr.srt --provider google --model gemini-2.5-flash

# Adjust batch size for speed/quality trade-off
srt-translate -i movie.srt -o movie.de.srt --batch-size 50

# Add context for better translation
srt-translate -i movie.srt -o movie.it.srt --context "Pulp Fiction, Tarantino film"
```

## Configuration

Create a `config.toml` file in the working directory:

```toml
[api]
type = "google"
keys = ["AIza...your-api-key"]
model = "gemini-2.5-flash"

[translation]
target_language = "Italian"
batch_size = 25
```

Alternatively, use environment variables:

```bash
export GOOGLE_API_KEY="AIza..."
export TARGET_LANGUAGE="Italian"
```

## License

MIT
