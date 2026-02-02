<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import { onMount } from "svelte";

  // Types
  interface ApiKeyConfig {
    id: string;
    name: string;
    apiType: "gemini" | "openai" | "local" | "anthropic" | "openrouter";
    apiKey: string;
    apiUrl?: string;
    isDefault: boolean;
  }

  interface ModelInfo {
    id: string;
    name: string;
    provider: string;
    contextWindow?: number;
    description?: string;
  }

  // State
  let apiKeys = $state<ApiKeyConfig[]>([]);
  let availableModels = $state<Record<string, ModelInfo[]>>({});
  let isLoadingModels = $state<Record<string, boolean>>({});
  let showAddKey = $state(false);
  let editingKeyId = $state<string | null>(null);
  let error = $state<string | null>(null);
  let success = $state<string | null>(null);

  // New key form
  let newKeyName = $state("");
  let newKeyType = $state<ApiKeyConfig["apiType"]>("gemini");
  let newKeyValue = $state("");
  let newKeyUrl = $state("");

  // Predefined models by provider
  const defaultModels: Record<string, ModelInfo[]> = {
    gemini: [
      { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", provider: "gemini", contextWindow: 1048576, description: "Più veloce, ottimo per traduzioni" },
      { id: "gemini-2.0-flash-lite", name: "Gemini 2.0 Flash Lite", provider: "gemini", contextWindow: 1048576, description: "Versione lite, più economico" },
      { id: "gemini-1.5-flash", name: "Gemini 1.5 Flash", provider: "gemini", contextWindow: 1048576, description: "Veloce, buon rapporto qualità/prezzo" },
      { id: "gemini-1.5-flash-8b", name: "Gemini 1.5 Flash 8B", provider: "gemini", contextWindow: 1048576, description: "Versione 8B, più leggero" },
      { id: "gemini-1.5-pro", name: "Gemini 1.5 Pro", provider: "gemini", contextWindow: 2097152, description: "Più potente, migliore qualità" },
    ],
    openai: [
      { id: "gpt-4o", name: "GPT-4o", provider: "openai", contextWindow: 128000, description: "Il più potente, multimodale" },
      { id: "gpt-4o-mini", name: "GPT-4o Mini", provider: "openai", contextWindow: 128000, description: "Economico, buona qualità" },
      { id: "gpt-4-turbo", name: "GPT-4 Turbo", provider: "openai", contextWindow: 128000, description: "Potente con contesto ampio" },
      { id: "gpt-3.5-turbo", name: "GPT-3.5 Turbo", provider: "openai", contextWindow: 16385, description: "Veloce ed economico" },
    ],
    anthropic: [
      { id: "claude-3-5-sonnet-20241022", name: "Claude 3.5 Sonnet", provider: "anthropic", contextWindow: 200000, description: "Ottimo per traduzioni" },
      { id: "claude-3-5-haiku-20241022", name: "Claude 3.5 Haiku", provider: "anthropic", contextWindow: 200000, description: "Veloce ed economico" },
      { id: "claude-3-opus-20240229", name: "Claude 3 Opus", provider: "anthropic", contextWindow: 200000, description: "Il più potente" },
    ],
    local: [
      { id: "llama3.2", name: "Llama 3.2", provider: "local", description: "Meta's latest open model" },
      { id: "mistral", name: "Mistral 7B", provider: "local", description: "Efficiente e veloce" },
      { id: "qwen2.5", name: "Qwen 2.5", provider: "local", description: "Ottimo per multilingue" },
      { id: "gemma2", name: "Gemma 2", provider: "local", description: "Google's open model" },
    ],
    openrouter: [
      { id: "google/gemini-2.0-flash-001", name: "Gemini 2.0 Flash", provider: "openrouter", description: "Via OpenRouter" },
      { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", provider: "openrouter", description: "Via OpenRouter" },
      { id: "openai/gpt-4o", name: "GPT-4o", provider: "openrouter", description: "Via OpenRouter" },
      { id: "meta-llama/llama-3.3-70b-instruct", name: "Llama 3.3 70B", provider: "openrouter", description: "Via OpenRouter" },
    ],
  };

  const apiTypeLabels: Record<string, string> = {
    gemini: "Google Gemini",
    openai: "OpenAI",
    anthropic: "Anthropic Claude",
    local: "Local LLM (Ollama/LM Studio)",
    openrouter: "OpenRouter",
  };

  const apiTypeColors: Record<string, string> = {
    gemini: "from-blue-500 to-cyan-500",
    openai: "from-green-500 to-emerald-500",
    anthropic: "from-orange-500 to-amber-500",
    local: "from-purple-500 to-pink-500",
    openrouter: "from-red-500 to-rose-500",
  };

  onMount(() => {
    loadApiKeys();
    // Load default models
    Object.entries(defaultModels).forEach(([provider, models]) => {
      availableModels[provider] = models;
    });
  });

  function loadApiKeys() {
    // Load from localStorage
    const saved = localStorage.getItem("srt-tools-api-keys");
    if (saved) {
      try {
        apiKeys = JSON.parse(saved);
      } catch {
        apiKeys = [];
      }
    }
  }

  function saveApiKeys() {
    localStorage.setItem("srt-tools-api-keys", JSON.stringify(apiKeys));
  }

  function generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  function addApiKey() {
    if (!newKeyName.trim() || !newKeyValue.trim()) {
      error = "Nome e chiave API sono obbligatori";
      return;
    }

    const newKey: ApiKeyConfig = {
      id: generateId(),
      name: newKeyName.trim(),
      apiType: newKeyType,
      apiKey: newKeyValue.trim(),
      apiUrl: newKeyUrl.trim() || undefined,
      isDefault: apiKeys.length === 0,
    };

    apiKeys = [...apiKeys, newKey];
    saveApiKeys();

    // Reset form
    newKeyName = "";
    newKeyValue = "";
    newKeyUrl = "";
    showAddKey = false;

    success = "Chiave API aggiunta con successo";
    setTimeout(() => (success = null), 3000);
  }

  function removeApiKey(id: string) {
    const key = apiKeys.find((k) => k.id === id);
    if (!key) return;

    if (
      !confirm(
        `Sei sicuro di voler eliminare la chiave "${key.name}"?`
      )
    )
      return;

    apiKeys = apiKeys.filter((k) => k.id !== id);

    // Set new default if needed
    if (key.isDefault && apiKeys.length > 0) {
      apiKeys[0].isDefault = true;
    }

    saveApiKeys();
    success = "Chiave API eliminata";
    setTimeout(() => (success = null), 3000);
  }

  function setDefaultKey(id: string) {
    apiKeys = apiKeys.map((k) => ({
      ...k,
      isDefault: k.id === id,
    }));
    saveApiKeys();
  }

  function maskApiKey(key: string): string {
    if (key.length <= 8) return "••••••••";
    return key.substring(0, 4) + "••••" + key.substring(key.length - 4);
  }

  async function fetchModelsFromApi(apiType: string, apiKey: string, apiUrl?: string) {
    isLoadingModels[apiType] = true;
    error = null;

    try {
      let models: ModelInfo[] = [];

      if (apiType === "openai") {
        const response = await fetch("https://api.openai.com/v1/models", {
          headers: {
            Authorization: `Bearer ${apiKey}`,
          },
        });

        if (!response.ok) throw new Error("Errore nel recupero modelli OpenAI");

        const data = await response.json();
        models = data.data
          .filter((m: any) => m.id.includes("gpt"))
          .map((m: any) => ({
            id: m.id,
            name: m.id,
            provider: "openai",
          }))
          .slice(0, 20);
      } else if (apiType === "local") {
        const url = apiUrl || "http://localhost:11434";
        try {
          // Try Ollama API
          const response = await fetch(`${url}/api/tags`);
          if (response.ok) {
            const data = await response.json();
            models = data.models?.map((m: any) => ({
              id: m.name,
              name: m.name,
              provider: "local",
              description: `Size: ${(m.size / 1e9).toFixed(1)}GB`,
            })) || [];
          }
        } catch {
          // Try LM Studio API (OpenAI compatible)
          try {
            const response = await fetch(`${url}/v1/models`);
            if (response.ok) {
              const data = await response.json();
              models = data.data?.map((m: any) => ({
                id: m.id,
                name: m.id,
                provider: "local",
              })) || [];
            }
          } catch {
            error = "Impossibile connettersi al server locale. Verifica che sia in esecuzione.";
          }
        }
      } else if (apiType === "openrouter") {
        try {
          const response = await fetch("https://openrouter.ai/api/v1/models", {
            headers: {
              Authorization: `Bearer ${apiKey}`,
            },
          });

          if (response.ok) {
            const data = await response.json();
            models = data.data?.slice(0, 30).map((m: any) => ({
              id: m.id,
              name: m.name || m.id,
              provider: "openrouter",
              contextWindow: m.context_length,
              description: m.pricing ? `$${m.pricing.prompt}/1K tokens` : undefined,
            })) || [];
          }
        } catch {
          error = "Errore nel recupero modelli OpenRouter";
        }
      }

      if (models.length > 0) {
        availableModels[apiType] = models;
        success = `Caricati ${models.length} modelli per ${apiTypeLabels[apiType]}`;
        setTimeout(() => (success = null), 3000);
      } else if (!error) {
        error = "Nessun modello trovato o API non supporta l'elenco modelli";
      }
    } catch (e) {
      error = `Errore: ${e}`;
    } finally {
      isLoadingModels[apiType] = false;
    }
  }

  // Export function to get the selected API config
  export function getSelectedApiConfig(): ApiKeyConfig | null {
    return apiKeys.find((k) => k.isDefault) || apiKeys[0] || null;
  }

  export function getApiKeys(): ApiKeyConfig[] {
    return apiKeys;
  }
</script>

<div class="h-full flex flex-col p-6 overflow-auto bg-gradient-to-br from-gray-900 via-gray-900 to-gray-950">
  <!-- Header -->
  <div class="mb-8">
    <h2 class="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
      Impostazioni
    </h2>
    <p class="text-gray-400 mt-1">
      Gestisci le tue chiavi API e i modelli disponibili
    </p>
  </div>

  <!-- Notifications -->
  {#if error}
    <div class="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3 animate-fade-in">
      <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="text-red-300 flex-1">{error}</span>
      <button onclick={() => (error = null)} class="text-red-400 hover:text-red-300">✕</button>
    </div>
  {/if}

  {#if success}
    <div class="mb-6 p-4 bg-green-500/10 border border-green-500/30 rounded-xl flex items-center gap-3 animate-fade-in">
      <svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
      </svg>
      <span class="text-green-300">{success}</span>
    </div>
  {/if}

  <div class="grid grid-cols-2 gap-6">
    <!-- Left Column: API Keys -->
    <div class="space-y-6">
      <div class="glass-card p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-white flex items-center gap-2">
            <svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
            Chiavi API
          </h3>
          <button
            onclick={() => (showAddKey = !showAddKey)}
            class="btn-primary text-sm py-2 px-4"
          >
            {showAddKey ? "Annulla" : "+ Aggiungi"}
          </button>
        </div>

        <!-- Add Key Form -->
        {#if showAddKey}
          <div class="mb-6 p-4 bg-white/5 rounded-xl border border-white/10 animate-fade-in">
            <h4 class="font-medium text-white mb-4">Nuova Chiave API</h4>

            <div class="space-y-4">
              <div>
                <label class="block text-sm text-gray-400 mb-2">Nome (identificativo)</label>
                <input
                  type="text"
                  bind:value={newKeyName}
                  placeholder="es: Gemini Personale"
                  class="input-modern w-full"
                />
              </div>

              <div>
                <label class="block text-sm text-gray-400 mb-2">Provider</label>
                <select bind:value={newKeyType} class="select-modern w-full">
                  {#each Object.entries(apiTypeLabels) as [value, label]}
                    <option {value}>{label}</option>
                  {/each}
                </select>
              </div>

              <div>
                <label class="block text-sm text-gray-400 mb-2">API Key</label>
                <input
                  type="password"
                  bind:value={newKeyValue}
                  placeholder="Inserisci la tua API key..."
                  class="input-modern w-full"
                />
              </div>

              {#if newKeyType === "local" || newKeyType === "openrouter"}
                <div>
                  <label class="block text-sm text-gray-400 mb-2">
                    URL API {newKeyType === "local" ? "(Ollama/LM Studio)" : ""}
                  </label>
                  <input
                    type="text"
                    bind:value={newKeyUrl}
                    placeholder={newKeyType === "local" ? "http://localhost:11434" : "https://openrouter.ai/api/v1"}
                    class="input-modern w-full"
                  />
                </div>
              {/if}

              <button
                onclick={addApiKey}
                class="btn-success w-full"
              >
                Salva Chiave API
              </button>
            </div>
          </div>
        {/if}

        <!-- API Keys List -->
        <div class="space-y-3">
          {#each apiKeys as key}
            <div
              class="p-4 bg-white/5 rounded-xl border border-white/10 hover:border-white/20 transition-all {key.isDefault ? 'ring-2 ring-indigo-500/50' : ''}"
            >
              <div class="flex items-start gap-3">
                <div class="w-10 h-10 rounded-lg bg-gradient-to-br {apiTypeColors[key.apiType]} flex items-center justify-center flex-shrink-0">
                  <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                </div>

                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="font-medium text-white">{key.name}</span>
                    {#if key.isDefault}
                      <span class="badge badge-primary">Default</span>
                    {/if}
                  </div>
                  <p class="text-sm text-gray-400">{apiTypeLabels[key.apiType]}</p>
                  <p class="text-xs text-gray-500 font-mono mt-1">{maskApiKey(key.apiKey)}</p>
                </div>

                <div class="flex items-center gap-2">
                  {#if !key.isDefault}
                    <button
                      onclick={() => setDefaultKey(key.id)}
                      class="icon-btn text-gray-400 hover:text-indigo-400"
                      title="Imposta come default"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                      </svg>
                    </button>
                  {/if}
                  <button
                    onclick={() => fetchModelsFromApi(key.apiType, key.apiKey, key.apiUrl)}
                    class="icon-btn text-gray-400 hover:text-green-400"
                    title="Aggiorna modelli"
                    disabled={isLoadingModels[key.apiType]}
                  >
                    <svg class="w-4 h-4 {isLoadingModels[key.apiType] ? 'animate-spin' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                  <button
                    onclick={() => removeApiKey(key.id)}
                    class="icon-btn text-gray-400 hover:text-red-400"
                    title="Elimina"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          {/each}

          {#if apiKeys.length === 0}
            <div class="text-center py-8 text-gray-500">
              <svg class="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
              <p>Nessuna chiave API configurata</p>
              <p class="text-sm mt-1">Aggiungi una chiave per iniziare</p>
            </div>
          {/if}
        </div>
      </div>
    </div>

    <!-- Right Column: Models -->
    <div class="space-y-6">
      <div class="glass-card p-6">
        <h3 class="text-lg font-semibold text-white flex items-center gap-2 mb-4">
          <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          Modelli Disponibili
        </h3>

        <div class="space-y-4">
          {#each Object.entries(availableModels) as [provider, models]}
            <div class="p-4 bg-white/5 rounded-xl">
              <div class="flex items-center gap-2 mb-3">
                <span class="w-3 h-3 rounded-full bg-gradient-to-br {apiTypeColors[provider]}"></span>
                <h4 class="font-medium text-white text-sm">{apiTypeLabels[provider]}</h4>
                <span class="badge badge-primary ml-auto">{models.length}</span>
              </div>

              <div class="space-y-2 max-h-48 overflow-y-auto">
                {#each models as model}
                  <div class="flex items-center justify-between text-sm p-2 hover:bg-white/5 rounded-lg">
                    <div>
                      <span class="text-gray-300">{model.name}</span>
                      {#if model.description}
                        <span class="text-gray-500 text-xs ml-2">({model.description})</span>
                      {/if}
                    </div>
                    {#if model.contextWindow}
                      <span class="text-xs text-gray-500">{(model.contextWindow / 1000).toFixed(0)}K ctx</span>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </div>

      <!-- Info Box: Batch Size Explanation -->
      <div class="glass-card p-6">
        <h3 class="text-lg font-semibold text-white flex items-center gap-2 mb-4">
          <svg class="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Cos'è la Batch Size?
        </h3>

        <div class="space-y-3 text-sm text-gray-300">
          <p>
            La <strong class="text-white">Batch Size</strong> (dimensione del lotto) determina quanti sottotitoli vengono inviati all'API di traduzione in una singola richiesta.
          </p>

          <div class="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <p class="font-medium text-amber-300">Esempio:</p>
            <p class="text-gray-400 mt-1">
              Con 100 sottotitoli e batch size 10, verranno effettuate 10 chiamate API (100 ÷ 10 = 10 batch).
            </p>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="p-3 bg-green-500/10 rounded-lg">
              <p class="font-medium text-green-400 mb-1">✓ Batch grande (20-50)</p>
              <ul class="text-xs text-gray-400 space-y-1">
                <li>• Meno chiamate API</li>
                <li>• Più veloce complessivamente</li>
                <li>• Migliore contesto per l'AI</li>
              </ul>
            </div>
            <div class="p-3 bg-blue-500/10 rounded-lg">
              <p class="font-medium text-blue-400 mb-1">✓ Batch piccolo (5-10)</p>
              <ul class="text-xs text-gray-400 space-y-1">
                <li>• Meno token per richiesta</li>
                <li>• Errori più isolati</li>
                <li>• Progresso più granulare</li>
              </ul>
            </div>
          </div>

          <p class="text-gray-400 text-xs">
            <strong class="text-white">Consiglio:</strong> Usa 10-20 per file normali, 5-10 se hai errori di rate limit.
          </p>
        </div>
      </div>
    </div>
  </div>
</div>
