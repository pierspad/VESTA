# srt-translate

Library for translating SRT subtitle files using LLM APIs (Google Gemini, OpenAI, local models).

## Features

- ✅ Batch translation with configurable batch size
- ✅ Support for Google Gemini API (native)
- ✅ Support for local LLMs (Ollama, LM Studio)
- ✅ Rate limiting with automatic retry
- ✅ Progress callbacks for UI integration
- ✅ Cancellation support via tokio-util CancellationToken
- ✅ Automatic repair of incomplete translations

## Installation

Add to your `Cargo.toml`:

```toml
[dependencies]
srt-translate = { path = "../lib/srt-translate" }
```

## Usage

```rust
use srt_translate::{Translator, TranslatorConfig, ApiType};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let config = TranslatorConfig {
        api_type: ApiType::Google,
        api_keys: vec!["YOUR_API_KEY".to_string()],
        model: Some("gemini-2.5-flash".to_string()),
        target_language: "Italian".to_string(),
        batch_size: 25,
        ..Default::default()
    };
    
    let translator = Translator::new(config)?;
    
    // Use with srt-parser subtitles...
    
    Ok(())
}
```

## Supported Providers

| Provider | API Type | Notes |
|----------|----------|-------|
| Google Gemini | `google` | Native Gemini API (requires AIza... key) |
| Local LLM | `local` | Ollama, LM Studio, etc. (OpenAI-compatible) |

## License

MIT
