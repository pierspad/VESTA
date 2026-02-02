<script lang="ts">
  import { onMount } from "svelte";
  import {
    providers,
    providerOrder,
    modelsByProvider,
    getModelsForProvider,
    saveCustomModel,
    deleteCustomModel,
    getCustomModels,
    formatContextWindow,
    type ModelInfo,
    type CustomModel,
    type ProviderInfo,
  } from "./models";
  import { locale, currentLanguage, availableUILanguages, setLanguage } from "./i18n";

  // Types
  interface ApiKeyConfig {
    id: string;
    name: string;
    apiType: "gemini" | "openai" | "local" | "anthropic" | "openrouter" | "mistral";
    apiKey: string;
    apiUrl?: string;
    modelName?: string;  // Nome modello preferito
    isDefault: boolean;
  }

  // State
  let apiKeys = $state<ApiKeyConfig[]>([]);
  let selectedProvider = $state<string | null>(null);
  let showAddKey = $state(false);
  let showAddModel = $state(false);
  let error = $state<string | null>(null);
  let success = $state<string | null>(null);

  // Reactive translation
  let t = $derived($locale);

  // New key form
  let newKeyName = $state("");
  let newKeyType = $state<ApiKeyConfig["apiType"]>("gemini");
  let newKeyValue = $state("");
  let newKeyUrl = $state("");
  let newKeyModelName = $state("");

  // New custom model form
  let customModelName = $state("");
  let customModelApiId = $state("");
  let customModelProvider = $state("gemini");
  let customModelDescription = $state("");

  // Computed
  let selectedProviderInfo = $derived(selectedProvider ? providers[selectedProvider] : null);
  let selectedProviderModels = $derived(selectedProvider ? getModelsForProvider(selectedProvider) : []);
  let customModels = $state<CustomModel[]>([]);

  // Count keys per provider
  let keysPerProvider = $derived(() => {
    const counts: Record<string, number> = {};
    providerOrder.forEach((p) => {
      counts[p] = apiKeys.filter((k) => k.apiType === p).length;
    });
    return counts;
  });

  onMount(() => {
    loadApiKeys();
    customModels = getCustomModels();
  });

  function loadApiKeys() {
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

  function openAddKeyModal(providerId?: string, modelName?: string) {
    if (providerId) {
      newKeyType = providerId as ApiKeyConfig["apiType"];
      newKeyName = providers[providerId]?.name || "";
    }
    if (modelName) {
      newKeyModelName = modelName;
    }
    showAddKey = true;
  }

  function addApiKey() {
    if (!newKeyName.trim()) {
      error = t("settings.errorNameRequired");
      return;
    }

    // Per provider locali, la chiave può essere vuota
    if (newKeyType !== "local" && !newKeyValue.trim()) {
      error = t("settings.errorKeyRequired");
      return;
    }

    const newKey: ApiKeyConfig = {
      id: generateId(),
      name: newKeyName.trim(),
      apiType: newKeyType,
      apiKey: newKeyValue.trim(),
      apiUrl: newKeyUrl.trim() || undefined,
      modelName: newKeyModelName.trim() || undefined,
      isDefault: apiKeys.filter((k) => k.apiType === newKeyType).length === 0,
    };

    apiKeys = [...apiKeys, newKey];
    saveApiKeys();

    // Reset form
    newKeyName = "";
    newKeyValue = "";
    newKeyUrl = "";
    newKeyModelName = "";
    showAddKey = false;

    success = t("settings.keyAdded");
    setTimeout(() => (success = null), 3000);
  }

  function removeApiKey(id: string) {
    const key = apiKeys.find((k) => k.id === id);
    if (!key) return;

    if (!confirm(t("settings.confirmDeleteKey", { name: key.name }))) return;

    const wasDefault = key.isDefault;
    const keyType = key.apiType;
    apiKeys = apiKeys.filter((k) => k.id !== id);

    // Set new default if needed
    if (wasDefault) {
      const sameTypeKeys = apiKeys.filter((k) => k.apiType === keyType);
      if (sameTypeKeys.length > 0) {
        sameTypeKeys[0].isDefault = true;
      }
    }

    saveApiKeys();
    success = t("settings.keyDeleted");
    setTimeout(() => (success = null), 3000);
  }

  function setDefaultKey(id: string) {
    const key = apiKeys.find((k) => k.id === id);
    if (!key) return;

    // Remove default from same type
    apiKeys = apiKeys.map((k) => ({
      ...k,
      isDefault: k.apiType === key.apiType ? k.id === id : k.isDefault,
    }));
    saveApiKeys();
  }

  function maskApiKey(key: string): string {
    if (!key || key.length <= 8) return "••••••••";
    return key.substring(0, 4) + "••••" + key.substring(key.length - 4);
  }

  function selectProvider(providerId: string) {
    selectedProvider = selectedProvider === providerId ? null : providerId;
  }

  function onModelClick(model: ModelInfo) {
    // Apri modal pre-compilata quando si clicca su un modello
    openAddKeyModal(model.provider, model.name);
  }

  function addCustomModel() {
    if (!customModelName.trim() || !customModelApiId.trim()) {
      error = t("settings.errorModelRequired");
      return;
    }

    const model: CustomModel = {
      id: generateId(),
      name: customModelName.trim(),
      provider: customModelProvider,
      apiModelId: customModelApiId.trim(),
      description: customModelDescription.trim() || undefined,
    };

    saveCustomModel(model);
    customModels = getCustomModels();

    // Reset form
    customModelName = "";
    customModelApiId = "";
    customModelDescription = "";
    showAddModel = false;

    success = t("settings.modelAdded");
    setTimeout(() => (success = null), 3000);
  }

  function removeCustomModel(modelId: string) {
    if (!confirm(t("settings.confirmDeleteModel"))) return;
    deleteCustomModel(modelId);
    customModels = getCustomModels();
    success = t("settings.modelDeleted");
    setTimeout(() => (success = null), 3000);
  }

  // Export functions for other components
  export function getSelectedApiConfig(): ApiKeyConfig | null {
    return apiKeys.find((k) => k.isDefault) || apiKeys[0] || null;
  }

  export function getApiKeys(): ApiKeyConfig[] {
    return apiKeys;
  }
</script>

<div class="h-full flex flex-col p-6 overflow-auto bg-gradient-to-br from-gray-900 via-gray-900 to-gray-950">
  <!-- Header -->
  <div class="mb-6">
    <h2 class="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
      {t("settings.title")}
    </h2>
    <p class="text-gray-400 mt-1">
      {t("settings.subtitle")}
    </p>
  </div>

  <!-- Notifications -->
  {#if error}
    <div class="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3 animate-fade-in">
      <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="text-red-300 flex-1">{error}</span>
      <button onclick={() => (error = null)} class="text-red-400 hover:text-red-300">✕</button>
    </div>
  {/if}

  {#if success}
    <div class="mb-4 p-4 bg-green-500/10 border border-green-500/30 rounded-xl flex items-center gap-3 animate-fade-in">
      <svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
      </svg>
      <span class="text-green-300">{success}</span>
    </div>
  {/if}

  <div class="grid grid-cols-3 gap-6 flex-1">
    <!-- Left: Provider Icons + Language Selector -->
    <div class="space-y-4">
      <div class="glass-card p-4">
        <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">{t("settings.providers")}</h3>
        
        <div class="grid grid-cols-2 gap-3">
          {#each providerOrder as providerId}
            {@const provider = providers[providerId]}
            <button
              onclick={() => selectProvider(provider.id)}
              class="provider-card p-4 rounded-xl transition-all duration-300 flex flex-col items-center gap-2
                {selectedProvider === provider.id 
                  ? 'bg-gradient-to-br ' + provider.color + ' shadow-lg scale-105' 
                  : 'bg-white/5 hover:bg-white/10 border border-white/10'}"
            >
              <span class="text-2xl">{provider.icon}</span>
              <span class="text-xs font-medium text-center {selectedProvider === provider.id ? 'text-white' : 'text-gray-300'}">
                {provider.name.split(' ')[0]}
              </span>
              {#if keysPerProvider()[provider.id] > 0}
                <span class="absolute top-1 right-1 w-5 h-5 rounded-full bg-green-500 text-white text-xs flex items-center justify-center">
                  {keysPerProvider()[provider.id]}
                </span>
              {/if}
            </button>
          {/each}
        </div>
      </div>

      <!-- Language Selector -->
      <div class="glass-card p-4">
        <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">{t("settings.language")}</h3>
        <p class="text-xs text-gray-500 mb-3">{t("settings.languageDesc")}</p>
        <select 
          class="select-modern w-full"
          value={$currentLanguage}
          onchange={(e) => setLanguage((e.target as HTMLSelectElement).value)}
        >
          {#each availableUILanguages as lang}
            <option value={lang.code}>{lang.flag} {lang.nativeName}</option>
          {/each}
        </select>
      </div>

      <!-- Add Key Button -->
      <button
        onclick={() => openAddKeyModal(selectedProvider || undefined)}
        class="btn-primary w-full py-3"
      >
        <svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        {t("settings.addApiKey")}
      </button>

      <!-- Custom Models Button -->
      <button
        onclick={() => (showAddModel = true)}
        class="btn-secondary w-full py-3"
      >
        <svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        {t("settings.addCustomModel")}
      </button>
    </div>

    <!-- Center: Models for selected provider -->
    <div class="glass-card p-4 flex flex-col">
      <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">
        {#if selectedProviderInfo}
          {t("settings.models", { provider: selectedProviderInfo.name })}
        {:else}
          {t("settings.selectProvider")}
        {/if}
      </h3>

      {#if selectedProvider && selectedProviderInfo}
        <p class="text-sm text-gray-500 mb-4">{selectedProviderInfo.description}</p>
        
        <div class="flex-1 overflow-y-auto space-y-2">
          {#each selectedProviderModels as model}
            <button
              onclick={() => onModelClick(model)}
              class="w-full text-left p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors flex items-center gap-3 cursor-pointer"
            >
              <div class="flex-1">
                <div class="flex items-center gap-2">
                  <span class="text-white font-medium">{model.name}</span>
                  {#if model.recommended}
                    <span class="badge badge-success text-xs">{t("settings.recommended")}</span>
                  {/if}
                </div>
                {#if model.description}
                  <p class="text-xs text-gray-500 mt-1">{model.description}</p>
                {/if}
                <p class="text-xs text-gray-600 font-mono mt-1">{model.id}</p>
              </div>
              {#if model.contextWindow}
                <span class="text-xs text-gray-500 bg-white/5 px-2 py-1 rounded">
                  {formatContextWindow(model.contextWindow)} {t("settings.ctx")}
                </span>
              {/if}
            </button>
          {/each}
        </div>
      {:else}
        <div class="flex-1 flex items-center justify-center text-gray-500">
          <div class="text-center">
            <svg class="w-16 h-16 mx-auto mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <p>{t("settings.selectProviderHint")}</p>
          </div>
        </div>
      {/if}
    </div>

    <!-- Right: API Keys List -->
    <div class="glass-card p-4 flex flex-col">
      <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">
        {t("settings.apiKeys")}
      </h3>

      <div class="flex-1 overflow-y-auto space-y-3">
        {#each apiKeys as key}
          <div
            class="p-3 bg-white/5 rounded-xl border border-white/10 hover:border-white/20 transition-all
              {key.isDefault ? 'ring-1 ring-indigo-500/50' : ''}"
          >
            <div class="flex items-start gap-3">
              <div class="w-8 h-8 rounded-lg bg-gradient-to-br {providers[key.apiType]?.color || 'from-gray-500 to-gray-600'} flex items-center justify-center flex-shrink-0 text-sm">
                {providers[key.apiType]?.icon || "?"}
              </div>

              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-white text-sm truncate">{key.name}</span>
                  {#if key.isDefault}
                    <span class="badge badge-primary text-xs">{t("settings.default")}</span>
                  {/if}
                </div>
                <p class="text-xs text-gray-500">{providers[key.apiType]?.name || key.apiType}</p>
                <p class="text-xs text-gray-600 font-mono mt-1">{maskApiKey(key.apiKey)}</p>
                {#if key.modelName}
                  <p class="text-xs text-indigo-400 mt-1">Model: {key.modelName}</p>
                {/if}
              </div>

              <div class="flex items-center gap-1">
                {#if !key.isDefault}
                  <button
                    onclick={() => setDefaultKey(key.id)}
                    class="p-1.5 text-gray-500 hover:text-indigo-400 hover:bg-white/5 rounded transition-colors"
                    title={t("settings.setAsDefault")}
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                    </svg>
                  </button>
                {/if}
                <button
                  onclick={() => removeApiKey(key.id)}
                  class="p-1.5 text-gray-500 hover:text-red-400 hover:bg-white/5 rounded transition-colors"
                  title={t("settings.delete")}
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
          <div class="flex-1 flex items-center justify-center text-gray-500">
            <div class="text-center py-8">
              <svg class="w-12 h-12 mx-auto mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
              <p>{t("settings.noApiKeys")}</p>
              <p class="text-sm mt-1">{t("settings.addKeyHint")}</p>
            </div>
          </div>
        {/if}
      </div>

      <!-- Custom Models Section -->
      {#if customModels.length > 0}
        <div class="border-t border-white/10 mt-4 pt-4">
          <h4 class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">{t("settings.customModels")}</h4>
          <div class="space-y-2">
            {#each customModels as model}
              <div class="flex items-center justify-between p-2 bg-white/5 rounded-lg text-sm">
                <div>
                  <span class="text-white">{model.name}</span>
                  <span class="text-gray-500 text-xs ml-2">({providers[model.provider]?.name || model.provider})</span>
                </div>
                <button
                  onclick={() => removeCustomModel(model.id)}
                  class="text-gray-500 hover:text-red-400 p-1"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  </div>

  <!-- Modal: Add API Key -->
  {#if showAddKey}
    <div class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50" onclick={() => (showAddKey = false)}>
      <div class="bg-gray-900 border border-white/20 rounded-2xl p-6 w-full max-w-md animate-fade-in shadow-2xl" onclick={(e) => e.stopPropagation()}>
        <h3 class="text-xl font-bold text-white mb-4">{t("settings.modal.newKey")}</h3>

        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-400 mb-2">{t("settings.modal.keyName")}</label>
            <input
              type="text"
              bind:value={newKeyName}
              placeholder={t("settings.modal.keyNamePlaceholder")}
              class="input-modern w-full"
            />
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">{t("settings.modal.provider")}</label>
            <div class="grid grid-cols-6 gap-2">
              {#each providerOrder as providerId}
                {@const provider = providers[providerId]}
                <button
                  type="button"
                  onclick={() => (newKeyType = provider.id as any)}
                  class="p-3 rounded-lg transition-all flex flex-col items-center gap-1
                    {newKeyType === provider.id 
                      ? 'bg-gradient-to-br ' + provider.color + ' shadow-lg' 
                      : 'bg-white/10 hover:bg-white/15'}"
                >
                  <span class="text-lg">{provider.icon}</span>
                  <span class="text-xs {newKeyType === provider.id ? 'text-white' : 'text-gray-400'}">
                    {provider.name.split(' ')[0]}
                  </span>
                </button>
              {/each}
            </div>
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">{t("settings.modal.apiKey")}</label>
            <input
              type="password"
              bind:value={newKeyValue}
              placeholder={newKeyType === "local" ? t("settings.modal.apiKeyPlaceholderLocal") : t("settings.modal.apiKeyPlaceholder")}
              class="input-modern w-full"
            />
          </div>

          {#if providers[newKeyType]?.requiresApiUrl}
            <div>
              <label class="block text-sm text-gray-400 mb-2">
                {t("settings.modal.apiUrl")}
              </label>
              <input
                type="text"
                bind:value={newKeyUrl}
                placeholder={providers[newKeyType]?.defaultApiUrl || "http://localhost:11434"}
                class="input-modern w-full"
              />
            </div>
          {/if}

          <div>
            <label class="block text-sm text-gray-400 mb-2">{t("settings.modal.modelName")} ({t("settings.modal.description").split('(')[0].trim()})</label>
            <input
              type="text"
              bind:value={newKeyModelName}
              placeholder={t("settings.modal.modelNamePlaceholder")}
              class="input-modern w-full"
            />
            <p class="text-xs text-gray-500 mt-1">{t("settings.modal.modelApiIdHint")}</p>
          </div>

          <div class="flex gap-3 pt-2">
            <button onclick={() => (showAddKey = false)} class="btn-secondary flex-1">
              {t("settings.modal.cancel")}
            </button>
            <button onclick={addApiKey} class="btn-success flex-1">
              {t("settings.modal.save")}
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Modal: Add Custom Model -->
  {#if showAddModel}
    <div class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50" onclick={() => (showAddModel = false)}>
      <div class="bg-gray-900 border border-white/20 rounded-2xl p-6 w-full max-w-md animate-fade-in shadow-2xl" onclick={(e) => e.stopPropagation()}>
        <h3 class="text-xl font-bold text-white mb-4">{t("settings.modal.newModel")}</h3>

        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-400 mb-2">{t("settings.modal.modelName")}</label>
            <input
              type="text"
              bind:value={customModelName}
              placeholder={t("settings.modal.modelNamePlaceholder")}
              class="input-modern w-full"
            />
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">{t("settings.modal.modelApiId")}</label>
            <input
              type="text"
              bind:value={customModelApiId}
              placeholder={t("settings.modal.modelApiIdPlaceholder")}
              class="input-modern w-full"
            />
            <p class="text-xs text-gray-500 mt-1">{t("settings.modal.modelApiIdHint")}</p>
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">{t("settings.modal.provider")}</label>
            <select bind:value={customModelProvider} class="select-modern w-full">
              {#each providerOrder as providerId}
                {@const provider = providers[providerId]}
                <option value={provider.id}>{provider.name}</option>
              {/each}
            </select>
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">{t("settings.modal.description")}</label>
            <input
              type="text"
              bind:value={customModelDescription}
              placeholder={t("settings.modal.descriptionPlaceholder")}
              class="input-modern w-full"
            />
          </div>

          <div class="flex gap-3 pt-2">
            <button onclick={() => (showAddModel = false)} class="btn-secondary flex-1">
              {t("settings.modal.cancel")}
            </button>
            <button onclick={addCustomModel} class="btn-success flex-1">
              {t("settings.modal.add")}
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .provider-card {
    position: relative;
  }
</style>
