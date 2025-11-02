# SRT Subtitle Utilities [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Fast command-line tools for processing and translating SRT subtitle files using LLM APIs.

## 📦 Installation

```bash
sh build_all.sh
# Compile the utilities
cargo build --release

# Binaries will be available in:
# ./bin/srt-extract
# ./bin/srt-translate
```

---

## 🔧 srt-extract

Extracts and displays information from SRT files in various formats.

### Basic Syntax

```bash
srt-extract -i <file.srt> -f <format> [-o output.txt]
```

### Parameters

- `-i, --input`: SRT file to analyze (required)
- `-f, --format`: Output format (default: `debug`)
- `-o, --output`: Output file (optional, otherwise prints to stdout)

### Available Formats

#### 1. `debug` - Complete Display

Shows all subtitles with ID, timestamp and text.

```bash
srt-extract -i movie.srt -f debug
```

**Output:**
```
Subtitle {
    id: 1,
    start: Timestamp{
        milliseconds: 0000000 
    },    
    end: Timestamp{
        milliseconds: 0003500 
    },
    text: "[Hello, world!]",
},
Subtitle {
    id: 2,
    start: Timestamp{
        milliseconds: 0003500 
    },    
    end: Timestamp{
        milliseconds: 0006000 
    },
    text: "[How are you?]",
},
```

#### 2. `json` - JSON Export

Exports subtitles in structured JSON format.

```bash
srt-extract -i movie.srt -f json -o subtitles.json
```

**Output:**
```json
[
  {
    "id": 1,
    "start_time": "00:00:00,000",
    "end_time": "00:00:03,500",
    "text": "Hello, world!"
  },
]
```

#### 3. `summary` - Text Summary

Shows only ID and text of subtitles.

```bash
srt-extract -i movie.srt -f summary
```

**Output:**
```
ID 1: 00:00:00,000 --> 00:00:30,000 | Hello, world!
ID 2: 00:00:31,051 --> 00:00:35,151 | How are you?
```

#### 4. `stats` - Statistics

Analyzes and shows detailed statistics about subtitles.

```bash
srt-extract -i movie.srt -f stats
```

**Output:**
```
📖 Reading file: "a.srt"
✅ Found 2 subtitles

📊 Subtitle Statistics:

Total subtitles: 2
Total duration: 34.10 seconds (0.57 minutes)
Average duration: 17.05 seconds

Text Statistics:
Shortest text: 12 characters
Longest text: 13 characters
Average text length: 12.50 characters
```

### Practical Examples

```bash
# Display all info from an SRT file
srt-extract -i movie.srt

# Export to JSON for processing with other tools
srt-extract -i movie.srt -f json -o data.json

# Get quick statistics
srt-extract -i movie.srt -f stats

# Save a summary to a text file
srt-extract -i movie.srt -f summary -o summary.txt
```

---

## 🌍 srt-translate

Translates SRT files using LLM APIs (Gemini, OpenAI, or local LLMs).

### Initial Setup

1. **Copy the example configuration files:**

```bash
cp config.example.toml config.toml
cp .env.example .env
```

2. **Configure API keys in the `.env` file:**

```bash
# Edit the .env file
nano .env
```

Add your API keys:

```env
# API Key 1 - Primary provider
API_KEY_1=YOUR_FIRST_API_KEY_HERE

# API Key 2 - Secondary provider (optional, for parallel processing)
API_KEY_2=YOUR_SECOND_API_KEY_HERE

# API Key 3 - Tertiary provider (optional, for maximum speed)
API_KEY_3=YOUR_THIRD_API_KEY_HERE
```

3. **The `config.toml` file will reference API keys via environment variables:**

```toml
[[api.providers]]
provider = "{provider}"
api_key = "${API_KEY_1}"  # References API_KEY_1 from .env file
model = "{model_name}"
rpm_limit = 100
```

> **Security note:** API keys are now stored in `.env` (which should NOT be committed to Git) instead of directly in `config.toml`. This improves security and makes configuration sharing easier.

### Basic Syntax

```bash
srt-translate -i <file.srt> -l <language> [-o output.srt] [-c config.toml]
```

### Parameters

- `-i, --input`: SRT file to translate (required)
- `-l, --language`: Target language code (required for translation)
- `-o, --output`: Output file (optional, uses pattern from config)
- `-c, --config`: Configuration file (default: `config.toml`)
- `--language-list`: Shows supported languages with optimized examples
- `--check-missing <FILE>`: Verifies which subtitles are missing or have line count discrepancies compared to a translated file

### Supported Languages

```bash
# Display complete list
srt-translate --language-list
```

**Languages with optimized examples:**

| Code | Language |
|--------|--------|
| `en` | English |
| `it` | Italian |
| `es` | Spanish |
| `fr` | French |
| `de` | German |
| `pt` | Portuguese |
| `ru` | Russian |
| `ja` | Japanese |
| `zh` | Chinese (Simplified) |
| `ar` | Arabic |

> Other ISO languages work but without optimized examples. 
> Feel free to add your language with a PR ;)

### Translation Examples

#### Simple Translation

```bash
# Translate to Italian (output: movie.it.srt)
srt-translate -i movie.srt -l it

# Translate to Spanish with custom output
srt-translate -i movie.srt -l es -o pelicula_espanol.srt
```

#### Verify Missing Subtitles and Discrepancies

The tool can verify the quality of an existing translation by checking:
1. **Missing subtitles**: IDs present in the original but absent in the translation
2. **Line count discrepancies**: Subtitles with different number of lines (possible incomplete translation)

```bash
# Check which subtitles are missing or have different line counts
srt-translate -i movie.srt --check-missing movie.it.srt
```


#### With Custom Configuration

```bash
# Use a different config file
srt-translate -i movie.srt -l fr -c config.custom.toml
```

### Advanced Configuration

#### Multi-Provider Setup (Maximum Speed)

For faster translations.

**Configure API keys in the `.env` file:**

```env
API_KEY_1=your_first_API_key
API_KEY_2=your_second_API_key
API_KEY_3=your_third_API_key
```

**Then configure providers in `config.toml`:**

```toml
[[api.providers]]
provider = "{provider}"
api_key = "${API_KEY_1}"  # References API_KEY_1 from .env file
model = "{model_name}"
rpm_limit = 100

[[api.providers]]
provider = "{provider}"
api_key = "${API_KEY_1}"  # References API_KEY_1 from .env file
model = "{model_name}"
rpm_limit = 100

[[api.providers]]
provider = "{provider}"
api_key = "${API_KEY_1}"  # References API_KEY_1 from .env file
model = "{model_name}"
rpm_limit = 100

[translation]
batch_size = 20  # Subtitles per request (15-25 recommended)
```

**Benefits:**
- Automatic parallelization across API keys
- 3x speed with 3 keys
- Automatic worker calculation based on available CPUs

#### Output Customization

```toml
[output]
# Filename pattern
# Variables: {input_name}, {language}
filename_pattern = "{input_name}.{language}.srt"

# Resume partial translation in case of interruption
resume_on_restart = true
```

#### Advanced Options

```toml
[advanced]
# Timeout for each API request (seconds)
request_timeout_seconds = 30

# Maximum number of retries for failed requests
max_retries = 3

# Fallback to single translation if batch fails
fallback_to_single = true
```

### Automatic Features

#### 1. Completeness Verification

After translation, the tool automatically verifies that all subtitles have been translated.

```
🔍 Verifying translation completeness...
✅ Translation complete! All 1250 subtitles translated.
```

#### 2. Automatic Repair

If subtitles are missing, it translates them automatically:

```
⚠️  Found 15 missing subtitles!
🔧 Starting automatic repair with 3 workers...
✅ Repair complete! All missing subtitles recovered.
```

#### 3. Context Detection

The filename is used as context to improve translation:

```bash
srt-translate -i movie_name.srt -l it
# Output: 🎬 Detected title: movie_name
```

### Complete Examples

#### Standard Movie

```bash
# 1. Setup
cp config.example.toml config.toml
cp .env.example .env
nano .env  # Add your API keys (API_KEY_1, API_KEY_2, etc.)

# 2. Translate to Italian
srt-translate -i movie.srt -l it
# Output: movie.it.srt
```

#### Multi-Language TV Series

```bash
# Translate to multiple languages
srt-translate -i episode01.srt -l it  # episode01.it.srt
srt-translate -i episode01.srt -l es  # episode01.es.srt
srt-translate -i episode01.srt -l fr  # episode01.fr.srt
```

#### Complete Workflow

```bash
# 1. Analyze original file
srt-extract -i movie.srt -f stats

# 2. Translate to Italian
srt-translate -i movie.srt -l it

# 3. Verify translation
srt-extract -i movie.it.srt -f stats

# 4. Compare statistics
srt-extract -i movie.srt -f summary > original.txt
srt-extract -i movie.it.srt -f summary > translated.txt
```

---

## 🚀 Performance

### Speed Optimization

**Single API key setup:**
- ~1000 subtitles: 5-10 minutes
- Limited by RPM (requests per minute)

**Multi-key setup (3 keys):**
- ~1000 subtitles: 2-4 minutes
- 3x faster with parallelization

**Factors affecting speed:**
- Number of configured API keys
- `rpm_limit` of each provider
- `batch_size` (15-25 recommended)
- Number of available CPUs (auto-calculated workers)

### Tips

```toml
# For maximum speed
[translation]
batch_size = 20  # Balance speed/reliability

# Add multiple keys from the same provider
[[api.providers]]
provider = "gemini"
api_key = "KEY_1"
# ... repeat for each key

# Workers automatically calculated based on available CPUs
# Always leaves 1 CPU free for the system
```

---

## ❓ Troubleshooting

### Common Issues

**Error: "Failed to read config file"**
```bash
# Create configuration files
cp config.example.toml config.toml
cp .env.example .env
nano .env  # Add your API keys
```

**Error: "Missing required environment variables"**
```bash
# Make sure the .env file exists and contains API keys
nano .env
# Add: API_KEY_1=your_actual_api_key_here
```

**Error: "No API providers found"**
```toml
# Make sure you have at least one [[api.providers]] in config.toml
# And that environment variables are correctly defined in .env
[[api.providers]]
provider = "gemini"
api_key = "${API_KEY_1}"
model = "gemini-2.0-flash-exp"
rpm_limit = 15
```

**Incomplete translation**
- The tool automatically repairs missing subtitles
- If it persists, reduce `batch_size` in config

**Timeout errors**
```toml
[advanced]
request_timeout_seconds = 60  # Increase timeout
max_retries = 5  # More retries
```

---

## Contributing
Pull requests are welcome! 
I wouldn't mind some help in traslating the app properly in various languages and packaging it for Windows/MacOS and maybe other distributions like Debian, Ubuntu, Fedora, etc.
For major changes, please open an issue first to discuss your ideas.

## AI Disclosure
This project was developed with the assistance of Large Language Models, used to support code writing and documentation.

## License
This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.