//! # srt-sync-lib
//!
//! Libreria per la sincronizzazione manuale di sottotitoli SRT con video.
//! 
//! Questa libreria implementa un sistema di ancore (anchor points) per mappare
//! i tempi originali dei sottotitoli ai tempi corretti del video, usando
//! interpolazione lineare tra i punti di ancoraggio.

mod engine;
mod interpolator;
mod sampler;

pub use engine::{SyncEngine, SyncState};
pub use interpolator::{TimeMapper, AnchorPoint};
pub use sampler::{AdaptiveSampler, SamplerStrategy};
