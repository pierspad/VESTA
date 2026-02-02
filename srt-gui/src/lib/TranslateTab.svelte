<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import { listen } from "@tauri-apps/api/event";
  import { open, save } from "@tauri-apps/plugin-dialog";
  import { onMount, onDestroy } from "svelte";

  // Tipi
  interface SrtFileInfo {
    path: string;
    subtitle_count: number;
    first_subtitle: string;
    last_subtitle: string;
  }

  interface TranslateConfig {
    input_path: string;
    output_path: string;
    target_lang: string;
    api_key: string;
    api_type: string;
    batch_size: number;
    title_context: string | null;
    api_url: string | null;
    model: string | null;
  }

  interface TranslateProgressEvent {
    message: string;
    current_batch: number;
    total_batches: number;
    percentage: number;
    eta_seconds: number | null;
  }

  interface TranslateResult {
    success: boolean;
    message: string;
    output_path: string | null;
    translated_count: number;
  }

  // State
  let inputPath = $state("");
  let outputPath = $state("");
  let targetLang = $state("it");
  let apiKey = $state("");
  let apiType = $state("gemini");
  let batchSize = $state(10);
  let titleContext = $state("");
  let apiUrl = $state("");
  let model = $state("");

  let fileInfo = $state<SrtFileInfo | null>(null);
  let isTranslating = $state(false);
  let progress = $state<TranslateProgressEvent | null>(null);
  let logs = $state<string[]>([]);
  let error = $state<string | null>(null);
  let result = $state<TranslateResult | null>(null);

  let unlistenProgress: (() => void) | null = null;
  let unlistenComplete: (() => void) | null = null;

  // Languages
  const languages = [
    { code: "it", name: "Italiano" },
    { code: "en", name: "English" },
    { code: "es", name: "Español" },
    { code: "fr", name: "Français" },
    { code: "de", name: "Deutsch" },
    { code: "pt", name: "Português" },
    { code: "ja", name: "日本語" },
    { code: "ko", name: "한국어" },
    { code: "zh", name: "中文" },
  ];

  const apiTypes = [
    { value: "gemini", name: "Google Gemini" },
    { value: "openai", name: "OpenAI" },
    { value: "local", name: "Local LLM" },
  ];

  onMount(async () => {
    // Listen for progress events
    unlistenProgress = await listen<TranslateProgressEvent>(
      "translate-progress",
      (event) => {
        progress = event.payload;
        addLog(event.payload.message);
      }
    );

    unlistenComplete = await listen<TranslateResult>(
      "translate-complete",
      (event) => {
        result = event.payload;
        isTranslating = false;
        addLog(`✅ ${event.payload.message}`);
      }
    );
  });

  onDestroy(() => {
    unlistenProgress?.();
    unlistenComplete?.();
  });

  function addLog(message: string) {
    const timestamp = new Date().toLocaleTimeString();
    logs = [...logs, `[${timestamp}] ${message}`];
  }

  async function selectInputFile() {
    try {
      const selected = await open({
        multiple: false,
        filters: [{ name: "SRT Files", extensions: ["srt"] }],
      });

      if (selected) {
        inputPath = selected as string;
        await loadFileInfo();

        // Auto-generate output path
        if (!outputPath) {
          outputPath = inputPath.replace(".srt", `.${targetLang}.srt`);
        }
      }
    } catch (e) {
      error = `Errore selezione file: ${e}`;
    }
  }

  async function selectOutputFile() {
    try {
      const selected = await save({
        filters: [{ name: "SRT Files", extensions: ["srt"] }],
        defaultPath: outputPath || undefined,
      });

      if (selected) {
        outputPath = selected;
      }
    } catch (e) {
      error = `Errore selezione file: ${e}`;
    }
  }

  async function loadFileInfo() {
    if (!inputPath) return;

    try {
      fileInfo = await invoke<SrtFileInfo>("load_srt_for_translate", {
        path: inputPath,
      });
      addLog(`📄 Caricato file con ${fileInfo.subtitle_count} sottotitoli`);
    } catch (e) {
      error = `Errore caricamento file: ${e}`;
      fileInfo = null;
    }
  }

  async function startTranslation() {
    if (!inputPath || !outputPath || !apiKey) {
      error = "Compila tutti i campi obbligatori";
      return;
    }

    error = null;
    result = null;
    progress = null;
    isTranslating = true;
    addLog("🚀 Avvio traduzione...");

    const config: TranslateConfig = {
      input_path: inputPath,
      output_path: outputPath,
      target_lang: targetLang,
      api_key: apiKey,
      api_type: apiType,
      batch_size: batchSize,
      title_context: titleContext || null,
      api_url: apiUrl || null,
      model: model || null,
    };

    try {
      const res = await invoke<TranslateResult>("start_translation", {
        config,
      });
      result = res;
      isTranslating = false;
    } catch (e) {
      error = `Errore traduzione: ${e}`;
      isTranslating = false;
      addLog(`❌ Errore: ${e}`);
    }
  }

  async function cancelTranslation() {
    try {
      await invoke("cancel_translation");
      isTranslating = false;
      addLog("⚠️ Traduzione annullata");
    } catch (e) {
      error = `Errore annullamento: ${e}`;
    }
  }

  function formatEta(seconds: number | null): string {
    if (seconds === null) return "...";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  }
</script>

<div class="h-full flex flex-col p-6 overflow-auto">
  <!-- Header -->
  <div class="mb-6">
    <h2 class="text-2xl font-bold text-white">Traduzione Sottotitoli</h2>
    <p class="text-gray-400">
      Traduci file SRT usando LLM (Gemini, OpenAI, Local)
    </p>
  </div>

  <div class="flex-1 grid grid-cols-2 gap-6">
    <!-- Left Column: Configuration -->
    <div class="space-y-4">
      <!-- File Input -->
      <div class="bg-gray-800 rounded-lg p-4">
        <h3 class="text-lg font-semibold mb-3 text-blue-400">File</h3>

        <div class="space-y-3">
          <div>
            <label for="input-path" class="block text-sm text-gray-400 mb-1">File SRT Input</label>
            <div class="flex gap-2">
              <input
                id="input-path"
                type="text"
                bind:value={inputPath}
                placeholder="Seleziona file..."
                class="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
                readonly
              />
              <button
                onclick={selectInputFile}
                class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm"
              >
                Sfoglia
              </button>
            </div>
          </div>

          <div>
            <label for="output-path" class="block text-sm text-gray-400 mb-1">File Output</label>
            <div class="flex gap-2">
              <input
                id="output-path"
                type="text"
                bind:value={outputPath}
                placeholder="Seleziona destinazione..."
                class="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
              />
              <button
                onclick={selectOutputFile}
                class="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded text-sm"
              >
                Sfoglia
              </button>
            </div>
          </div>

          {#if fileInfo}
            <div class="text-sm text-gray-400 bg-gray-700 rounded p-2">
              <p><strong>{fileInfo.subtitle_count}</strong> sottotitoli</p>
              <p class="truncate">Primo: "{fileInfo.first_subtitle}"</p>
            </div>
          {/if}
        </div>
      </div>

      <!-- API Configuration -->
      <div class="bg-gray-800 rounded-lg p-4">
        <h3 class="text-lg font-semibold mb-3 text-blue-400">
          Configurazione API
        </h3>

        <div class="space-y-3">
          <div>
            <label for="api-type" class="block text-sm text-gray-400 mb-1">Tipo API</label>
            <select
              id="api-type"
              bind:value={apiType}
              class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
            >
              {#each apiTypes as type}
                <option value={type.value}>{type.name}</option>
              {/each}
            </select>
          </div>

          <div>
            <label for="api-key" class="block text-sm text-gray-400 mb-1">API Key</label>
            <input
              id="api-key"
              type="password"
              bind:value={apiKey}
              placeholder="Inserisci la tua API key..."
              class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
            />
          </div>

          {#if apiType === "local"}
            <div>
              <label for="api-url" class="block text-sm text-gray-400 mb-1">URL API (opzionale)</label>
              <input
                id="api-url"
                type="text"
                bind:value={apiUrl}
                placeholder="http://localhost:11434"
                class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
              />
            </div>
          {/if}

          <div>
            <label for="model" class="block text-sm text-gray-400 mb-1">Modello (opzionale)</label>
            <input
              id="model"
              type="text"
              bind:value={model}
              placeholder="es: gemini-1.5-flash"
              class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
            />
          </div>
        </div>
      </div>

      <!-- Translation Options -->
      <div class="bg-gray-800 rounded-lg p-4">
        <h3 class="text-lg font-semibold mb-3 text-blue-400">
          Opzioni Traduzione
        </h3>

        <div class="space-y-3">
          <div>
            <label for="target-lang" class="block text-sm text-gray-400 mb-1">Lingua Target</label>
            <select
              id="target-lang"
              bind:value={targetLang}
              class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
            >
              {#each languages as lang}
                <option value={lang.code}>{lang.name}</option>
              {/each}
            </select>
          </div>

          <div>
            <label for="batch-size" class="block text-sm text-gray-400 mb-1">Batch Size: {batchSize}</label>
            <input
              id="batch-size"
              type="range"
              bind:value={batchSize}
              min="5"
              max="50"
              step="5"
              class="w-full"
            />
          </div>

          <div>
            <label for="title-context" class="block text-sm text-gray-400 mb-1">Contesto (es: titolo film)</label>
            <input
              id="title-context"
              type="text"
              bind:value={titleContext}
              placeholder="Titolo del film/serie..."
              class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
            />
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-3">
        {#if isTranslating}
          <button
            onclick={cancelTranslation}
            class="flex-1 py-3 bg-red-600 hover:bg-red-700 rounded-lg font-semibold"
          >
            Annulla
          </button>
        {:else}
          <button
            onclick={startTranslation}
            disabled={!inputPath || !outputPath || !apiKey}
            class="flex-1 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-semibold"
          >
            🚀 Avvia Traduzione
          </button>
        {/if}
      </div>
    </div>

    <!-- Right Column: Progress & Logs -->
    <div class="space-y-4">
      <!-- Progress -->
      {#if isTranslating || progress}
        <div class="bg-gray-800 rounded-lg p-4">
          <h3 class="text-lg font-semibold mb-3 text-blue-400">Progresso</h3>

          <div class="space-y-3">
            <!-- Progress Bar -->
            <div class="w-full bg-gray-700 rounded-full h-4 overflow-hidden">
              <div
                class="h-full bg-blue-600 transition-all duration-300"
                style="width: {progress?.percentage || 0}%"
              ></div>
            </div>

            <div class="flex justify-between text-sm text-gray-400">
              <span>
                Batch {progress?.current_batch || 0} / {progress?.total_batches ||
                  0}
              </span>
              <span>{Math.round(progress?.percentage || 0)}%</span>
            </div>

            {#if progress?.eta_seconds}
              <p class="text-sm text-gray-400">
                ETA: {formatEta(progress.eta_seconds)}
              </p>
            {/if}

            {#if progress?.message}
              <p class="text-sm text-gray-300">{progress.message}</p>
            {/if}
          </div>
        </div>
      {/if}

      <!-- Result -->
      {#if result}
        <div
          class="bg-gray-800 rounded-lg p-4 border-l-4 {result.success
            ? 'border-green-500'
            : 'border-red-500'}"
        >
          <h3
            class="text-lg font-semibold mb-2 {result.success
              ? 'text-green-400'
              : 'text-red-400'}"
          >
            {result.success ? "✅ Completato" : "❌ Errore"}
          </h3>
          <p class="text-gray-300">{result.message}</p>
          {#if result.output_path}
            <p class="text-sm text-gray-400 mt-2">
              Output: {result.output_path}
            </p>
          {/if}
        </div>
      {/if}

      <!-- Error -->
      {#if error}
        <div class="bg-red-900/30 border border-red-600 rounded-lg p-4">
          <p class="text-red-400">{error}</p>
        </div>
      {/if}

      <!-- Logs -->
      <div class="bg-gray-800 rounded-lg p-4 flex-1">
        <h3 class="text-lg font-semibold mb-3 text-blue-400">Log</h3>

        <div
          class="h-64 overflow-y-auto bg-gray-900 rounded p-3 font-mono text-xs space-y-1"
        >
          {#each logs as log}
            <p class="text-gray-400">{log}</p>
          {/each}
          {#if logs.length === 0}
            <p class="text-gray-600">Nessun log...</p>
          {/if}
        </div>
      </div>
    </div>
  </div>
</div>
