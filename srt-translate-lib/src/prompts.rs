//! # Translation Prompts Module
//!
//! Questo modulo contiene tutti i prompt utilizzati per la traduzione dei sottotitoli.
//! Centralizzare i prompt qui rende il codice più pulito e facilita le modifiche future.

use crate::language_info::get_language_info;

/// Genera il prompt per la traduzione singola di un sottotitolo
pub fn build_single_translation_prompt(
    text: &str,
    target_lang: &str,
    context: Option<&str>,
) -> String {
    let context_info = if let Some(ctx) = context {
        format!("\n\nContext: This subtitle is from \"{}\". Use this context to better understand references, names, and cultural elements for more accurate translation.", ctx)
    } else {
        String::new()
    };

    let lang_info = get_language_info(target_lang);

    format!(
        "You are a professional subtitle translator specializing in film and TV content.
Your task is to translate the following subtitle text to {} with the highest quality possible.
{}
{}
CRITICAL RULES:
1. Translate ALL lines in the subtitle text - never skip any line
2. Maintain the exact same number of lines as the original
3. Each line break in the original MUST be preserved in the translation
4. Keep the same tone, register, and emotional intensity
5. Preserve cultural references when possible, or adapt them naturally
6. Keep translations concise - subtitles must be brief and readable
7. Maintain any emphasis, sarcasm, or humor
8. Use natural, colloquial language appropriate for spoken dialogue
9. Preserve character voice and personality
10. Translate profanity and vulgar language accurately - do NOT censor or soften it
11. IMPORTANT: Translate ALL content including sound effects, background noises, and action descriptions in square brackets (e.g., [Chuckles] -> [Ridacchia], [Door slams] -> [Sbatte la porta], [Music playing] -> [Musica in sottofondo])
12. Keep square brackets around translated sound effects and actions
13. Return ONLY the translated text, no explanations, quotes, or additional formatting

Original subtitle text:
{}

Translation:",
        lang_info.full_name, lang_info.examples, context_info, text
    )
}

/// Genera il prompt per la traduzione batch di più sottotitoli
pub fn build_batch_translation_prompt(
    texts_with_ids: &[(u32, String)],
    target_lang: &str,
    context: Option<&str>,
) -> String {
    let mut input_list = String::new();
    for (id, text) in texts_with_ids {
        input_list.push_str(&format!("ID:{} | TEXT:{}\n", id, text));
    }

    let context_info = if let Some(ctx) = context {
        format!("\n\nContext: These subtitles are from \"{}\". Use this context to better understand references, names, and cultural elements for more accurate translation.", ctx)
    } else {
        String::new()
    };

    let lang_info = get_language_info(target_lang);

    format!(
        "You are a professional subtitle translator specializing in film and TV content.
Your task is to translate the following subtitle texts to {} with the highest quality possible.
{}
{}
CRITICAL RULES:
1. Translate ALL lines in each subtitle text - never skip any line
2. For each subtitle, maintain the exact same number of lines as the original
3. Each line break in the original MUST be preserved in the translation
4. Keep the same tone, register, and emotional intensity for each subtitle
5. Preserve cultural references when possible, or adapt them naturally
6. Keep translations concise - subtitles must be brief and readable
7. Maintain any emphasis, sarcasm, or humor
8. Use natural, colloquial language appropriate for spoken dialogue
9. Preserve character voice and personality
10. Translate profanity and vulgar language accurately - do NOT censor or soften it
11. IMPORTANT: Translate ALL content including sound effects, background noises, and action descriptions in square brackets (e.g., [Chuckles] -> [Ridacchia], [Door slams] -> [Sbatte la porta], [Music playing] -> [Musica in sottofondo])
12. Keep square brackets around translated sound effects and actions
13. Return ONLY the translations in the EXACT format: ID:number | TRANSLATION:text
14. One translation per line in the response
15. Do NOT add explanations, quotes, or other text
16. If a subtitle text contains multiple lines separated by newlines, translate all of them and preserve the line breaks in the translation

Input subtitles:
{}

Output format example:
ID:1 | TRANSLATION:translated text here
ID:2 | TRANSLATION:first line of translation
second line of translation
ID:3 | TRANSLATION:another single line translation

Now translate:",
        lang_info.full_name, lang_info.examples, context_info, input_list
    )
}

/// Genera il prompt per la traduzione con contesto migliorato (usato per il repair)
pub fn build_context_enhanced_translation_prompt(
    text: &str,
    target_lang: &str,
    title_context: Option<&str>,
    surrounding_context: Option<&str>,
) -> String {
    let title_info = if let Some(ctx) = title_context {
        format!("\n\nTitle Context: This subtitle is from \"{}\". Use this context to better understand references, names, and cultural elements.", ctx)
    } else {
        String::new()
    };

    let surrounding_info = if let Some(ctx) = surrounding_context {
        format!("\n\n{}", ctx)
    } else {
        String::new()
    };

    let lang_info = get_language_info(target_lang);

    format!(
        "You are a professional subtitle translator specializing in film and TV content.
Your task is to translate the following subtitle text to {} with the highest quality possible.

This is a REPAIR task - this subtitle was missing from the initial translation and needs to be translated now.
You have access to surrounding subtitles (before and after) that were already translated to maintain consistency.
{}{}
{}

CRITICAL RULES:
1. Translate ALL lines in the subtitle text - never skip any line
2. Maintain the exact same number of lines as the original
3. Each line break in the original MUST be preserved in the translation
4. Keep the same tone, register, and emotional intensity as the surrounding translations
5. Use consistent terminology, names, and style with the surrounding context
6. Keep translations concise - subtitles must be brief and readable
7. Maintain any emphasis, sarcasm, or humor
8. Use natural, colloquial language appropriate for spoken dialogue
9. Preserve character voice and personality
10. Translate profanity and vulgar language accurately - do NOT censor or soften it
11. IMPORTANT: Translate ALL content including sound effects, background noises, and action descriptions in square brackets (e.g., [Chuckles] -> [Ridacchia], [Door slams] -> [Sbatte la porta], [Music playing] -> [Musica in sottofondo])
12. Keep square brackets around translated sound effects and actions
13. Return ONLY the translated text, no explanations, quotes, or additional formatting

Original subtitle text to translate:
{}

Translation:",
        lang_info.full_name, title_info, surrounding_info, lang_info.examples, text
    )
}
