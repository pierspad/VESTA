import json
import glob
import os
import sys

# We will just print the mapping out to be translated by the AI assistant directly,
# since I (the assistant) can do the translation in one go and patch the files.
# It is faster and doesn't require setting up an API key locally.

base_dir = "/home/ribben/Desktop/Various_Projects/VESTA/apps/srt-gui/src/lib/i18n/locales"
json_files = glob.glob(f"{base_dir}/*.json")

langs_to_translate = []
for f in json_files:
    lang_code = os.path.basename(f).split(".")[0]
    if lang_code not in ["en", "it"]:
        langs_to_translate.append(lang_code)

print(f"Languages to translate: {', '.join(langs_to_translate)}")
