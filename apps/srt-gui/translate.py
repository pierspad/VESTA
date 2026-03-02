import json
import glob
import os

missing_keys_map = {
  "flashcards.targetLangSubsDesc": "The subtitle file in the language you want to learn",
  "flashcards.nativeLangSubsDesc": "Subtitle file in your native language, used as reference/translation",
  "flashcards.mediaFileDesc": "Video = audio clips + screenshots. Audio = audio clips only",
  "flashcards.contextLines": "Context Lines",
  "flashcards.filters": "Filters",
  "flashcards.exportFormat": "Export Format",
  "flashcards.exportAPKG": "APKG (Anki package, ready to import)",
  "flashcards.exportAPKGDesc": "Single .apkg file with everything included. Just double-click to import.",
  "flashcards.exportTSV": "TSV + media files (subs2srs classic)",
  "flashcards.exportTSVDesc": "Generates a .tsv file + media folder. Import into Anki manually.",
  "flashcards.cpuCores": "CPU Cores",
  "flashcards.cpuEco": "Eco",
  "flashcards.cpuBalanced": "Balanced",
  "flashcards.cpuPerformance": "Performance",
  "flashcards.cpuFullPower": "Full Power",
  "flashcards.cpuCoresUsage": "Parallel threads",
  "flashcards.noteTypeLanguage": "Language",
  "flashcards.fieldsLabel": "Fields",
  "flashcards.logs": "Logs",
  "flashcards.tagField": "Tag",
  "flashcards.sequenceField": "Sequence",
  "flashcards.audioField": "Audio clip",
  "flashcards.snapshotField": "Snapshot image",
  "flashcards.videoField": "Video clip",

  "provider.local": "Local LLM",
  "translate.subPerBatch": "sub/batch",
  "translate.batchPrecise": "Precise",
  "translate.batchBalanced": "Balanced",
  "translate.batchFast": "Fast",
  "translate.batchTurbo": "Turbo",
  "translate.contextOptional": "optional",
  "translate.logs": "Logs",
  "translate.waitingForTranslation": "Waiting for translation to start...",

  "sync.loadSrt": "Load SRT",
  "sync.loadAudio": "Load Audio/Video",
  "sync.loadSession": "Load Session",
  "sync.saveSession": "Save Session",
  "sync.saveFile": "Save File",
  "sync.wizard.title": "Synchronization Wizard",
  "sync.statusTitle": "Status",
  "sync.srtPlaceholder": "Load an SRT file to start",
  "sync.subtitles": "Subtitles",

  "transcribe.modelTiny": "Tiny",
  "transcribe.modelBase": "Base",
  "transcribe.modelSmall": "Small",
  "transcribe.modelMedium": "Medium",
  "transcribe.modelLarge": "Large",
  "transcribe.notDownloaded": "to download",
  "transcribe.speed": "Speed",
  "transcribe.sourceLanguage": "Source language",
  "transcribe.autoDetect": "Auto-detect",
  "transcribe.segmentShort": "Short",
  "transcribe.segmentMedium": "Medium",
  "transcribe.segmentStandard": "Standard",
  "transcribe.segmentLong": "Long",
  "transcribe.files": "Files",
  "transcribe.noInputMediaSelected": "no input media selected",
  "transcribe.noOutputFileSelected": "no output file selected",
  "transcribe.startTranscription": "Start Transcription",

  "provider.google": "Google Gemini",
  "provider.openai": "OpenAI GPT",
  "provider.anthropic": "Anthropic Claude",
  "settings.soonBadge": "Soon",
  "provider.google.desc": "Google Gemini native API (requires AIza... key)",
  "settings.modal.optional": "optional"
}

missing_keys_map_it = {
  "flashcards.targetLangSubsDesc": "Il file sottotitoli nella lingua che vuoi imparare",
  "flashcards.nativeLangSubsDesc": "File sottotitoli nella tua lingua madre, usato come riferimento/traduzione",
  "flashcards.mediaFileDesc": "Video = clip audio + screenshot. Audio = solo clip audio",
  "flashcards.contextLines": "Righe di Contesto",
  "flashcards.filters": "Filtri",
  "flashcards.exportFormat": "Formato Esportazione",
  "flashcards.exportAPKG": "APKG (pacchetto Anki, pronto all'importazione)",
  "flashcards.exportAPKGDesc": "Un singolo file .apkg con tutto incluso. Doppio click per importare.",
  "flashcards.exportTSV": "TSV + file media (classico subs2srs)",
  "flashcards.exportTSVDesc": "Genera un file .tsv + cartella media. Importa in Anki manualmente.",
  "flashcards.cpuCores": "Core CPU",
  "flashcards.cpuEco": "Eco",
  "flashcards.cpuBalanced": "Bilanciato",
  "flashcards.cpuPerformance": "Prestazioni",
  "flashcards.cpuFullPower": "Potenza Max",
  "flashcards.cpuCoresUsage": "Thread paralleli",
  "flashcards.noteTypeLanguage": "Lingua",
  "flashcards.fieldsLabel": "Campi",
  "flashcards.logs": "Log",
  "flashcards.tagField": "Tag",
  "flashcards.sequenceField": "Sequenza",
  "flashcards.audioField": "Clip audio",
  "flashcards.snapshotField": "Immagine screenshot",
  "flashcards.videoField": "Clip video",

  "provider.local": "LLM Locale",
  "translate.subPerBatch": "sub/batch",
  "translate.batchPrecise": "Preciso",
  "translate.batchBalanced": "Bilanciato",
  "translate.batchFast": "Veloce",
  "translate.batchTurbo": "Turbo",
  "translate.contextOptional": "(opzionale)",
  "translate.logs": "Log",
  "translate.waitingForTranslation": "In attesa dell'avvio della traduzione...",

  "sync.loadSrt": "Carica SRT",
  "sync.loadAudio": "Carica Audio/Video",
  "sync.loadSession": "Carica Sessione",
  "sync.saveSession": "Salva Sessione",
  "sync.saveFile": "Salva File",
  "sync.wizard.title": "Wizard Sincronizzazione",
  "sync.statusTitle": "Stato",
  "sync.srtPlaceholder": "Carica un file SRT per iniziare",
  "sync.subtitles": "Sottotitoli",

  "transcribe.modelTiny": "Tiny",
  "transcribe.modelBase": "Base",
  "transcribe.modelSmall": "Small",
  "transcribe.modelMedium": "Medium",
  "transcribe.modelLarge": "Large",
  "transcribe.notDownloaded": "da scaricare",
  "transcribe.speed": "Velocità",
  "transcribe.sourceLanguage": "Lingua sorgente",
  "transcribe.autoDetect": "Rilevamento automatico",
  "transcribe.segmentShort": "Breve",
  "transcribe.segmentMedium": "Medio",
  "transcribe.segmentStandard": "Standard",
  "transcribe.segmentLong": "Lungo",
  "transcribe.files": "File",
  "transcribe.noInputMediaSelected": "nessun media di input selezionato",
  "transcribe.noOutputFileSelected": "nessun file di output selezionato",
  "transcribe.startTranscription": "Avvia Trascrizione",

  "provider.google": "Google Gemini",
  "provider.openai": "OpenAI GPT",
  "provider.anthropic": "Anthropic Claude",
  "settings.soonBadge": "Presto",
  "provider.google.desc": "API nativa Google Gemini (richiede chiave AIza...)",
  "settings.modal.optional": "opzionale"
}

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

def go():
    base_dir = "/home/ribben/Desktop/Various_Projects/VESTA/apps/srt-gui/src/lib/i18n/locales"
    json_files = glob.glob(f"{base_dir}/*.json")
    
    # Process Italian explicitly
    it_file = f"{base_dir}/it.json"
    if os.path.exists(it_file):
        with open(it_file, "r") as f:
            data = json.load(f)
        for k, v in missing_keys_map_it.items():
            data[k] = v
        write_json(it_file, data)
        print("Updated it.json")
    
    # Process English explicitly
    en_file = f"{base_dir}/en.json"
    if os.path.exists(en_file):
        with open(en_file, "r") as f:
            data = json.load(f)
        for k, v in missing_keys_map.items():
            data[k] = v
        write_json(en_file, data)
        print("Updated en.json")
    
    for f in json_files:
        lang_code = os.path.basename(f).split(".")[0]
        if lang_code in ["en", "it"]:
            continue
            
        with open(f, "r") as fi:
            data = json.load(fi)
            
        for k, v in missing_keys_map.items():
            if k not in data:
                data[k] = v
                
        write_json(f, data)
        print(f"Updated {lang_code}.json")

if __name__ == "__main__":
    go()
