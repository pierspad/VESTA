# srt-parser

Fast and reliable SRT (SubRip) subtitle file parser written in Rust.

## Features

- ✅ Parse SRT files with proper error handling
- ✅ Support for various timestamp formats
- ✅ Handle edge cases (empty lines, BOM, etc.)
- ✅ Serialize/deserialize with serde
- ✅ Zero dependencies beyond anyhow and serde

## Installation

Add to your `Cargo.toml`:

```toml
[dependencies]
srt-parser = { path = "../core/srt-parser" }
```

Or when published to crates.io:

```toml
[dependencies]
srt-parser = "0.1"
```

## Usage

```rust
use srt_parser::SrtParser;

fn main() -> anyhow::Result<()> {
    // Parse from file
    let subtitles = SrtParser::parse_file("movie.srt")?;
    
    for sub in &subtitles {
        println!("{}: {} -> {}", sub.id, sub.start_time, sub.end_time);
        println!("   {}", sub.text);
    }
    
    Ok(())
}
```

## License

MIT
