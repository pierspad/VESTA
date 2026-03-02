<script lang="ts">
  import { onMount } from "svelte";
  import {
    availableUILanguages,
    currentLanguage,
    locale,
    setLanguage,
  } from "./i18n";
  import {
    getModelsForProvider,
    loadAndValidateApiKeys,
    providers,
    type ApiKeyConfig,
    type ModelInfo,
  } from "./models";

  const allProviderIds = ["local", "google", "openai", "anthropic"];

  let apiKeys = $state<ApiKeyConfig[]>([]);
  let selectedProviderType = $state<string>("google"); // "local" or "google"
  let selectedFamily = $state<string | null>(null);

  let showAddKey = $state(false);
  let showAddModel = $state(false);
  let error = $state<string | null>(null);
  let success = $state<string | null>(null);

  let t = $derived($locale);

  let newKeyName = $state("");
  let newKeyType = $state<ApiKeyConfig["apiType"]>("google");
  let newKeyValue = $state("");
  let newKeyUrl = $state("");
  let newKeyModelName = $state("");
  let showNewKeyPassword = $state(false);

  let currentProviderModels = $derived(
    getModelsForProvider(selectedProviderType),
  );

  let families = $derived.by(() => {
    const fams = new Set<string>();
    currentProviderModels.forEach((m) => {
      if (m.family) fams.add(m.family);
    });
    return Array.from(fams).sort();
  });

  $effect(() => {
    if (
      families.length > 0 &&
      (!selectedFamily || !families.includes(selectedFamily))
    ) {
      selectedFamily = families[0];
    }
  });

  let filteredModels = $derived(
    selectedFamily
      ? currentProviderModels.filter((m) => m.family === selectedFamily)
      : [],
  );

  onMount(() => {
    loadApiKeys();

    const handleKeydown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (deleteConfirmId) {
          cancelDelete();
        } else if (showAddKey) {
          showAddKey = false;
        }
      }
    };

    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  });

  function loadApiKeys() {
    apiKeys = loadAndValidateApiKeys();
  }

  function saveApiKeys() {
    localStorage.setItem("srt-tools-api-keys", JSON.stringify(apiKeys));
    // Dispatch custom event to notify other tabs in the same window
    window.dispatchEvent(new CustomEvent("apikeys-updated"));
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

    if (newKeyType !== "local") {
      if (!newKeyUrl.trim()) {
        error =
          t("settings.errorEndpointRequired");
        return;
      }
      if (!newKeyValue.trim()) {
        error = t("settings.errorKeyRequired");
        return;
      }
    }

    if (newKeyType === "local" && !newKeyUrl.trim()) {
      error =
        t("settings.errorEndpointRequired");
      return;
    }

    if (newKeyType === "google" && !newKeyValue.trim().startsWith("AIza")) {
      error =
        t("settings.errorInvalidGoogleKey");
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

    newKeyName = "";
    newKeyValue = "";
    newKeyUrl = "";
    newKeyModelName = "";
    showAddKey = false;

    success = t("settings.keyAdded");
    setTimeout(() => (success = null), 3000);
  }

  let deleteConfirmId = $state<string | null>(null);
  let deleteConfirmName = $state<string>("");

  function askDeleteApiKey(id: string) {
    const key = apiKeys.find((k) => k.id === id);
    if (!key) return;
    deleteConfirmId = id;
    deleteConfirmName = key.name;
  }

  function cancelDelete() {
    deleteConfirmId = null;
    deleteConfirmName = "";
  }

  function confirmDeleteApiKey() {
    if (!deleteConfirmId) return;

    const key = apiKeys.find((k) => k.id === deleteConfirmId);
    if (!key) {
      cancelDelete();
      return;
    }

    const wasDefault = key.isDefault;
    const keyType = key.apiType;
    apiKeys = apiKeys.filter((k) => k.id !== deleteConfirmId);

    if (wasDefault) {
      const sameTypeKeys = apiKeys.filter((k) => k.apiType === keyType);
      if (sameTypeKeys.length > 0) {
        sameTypeKeys[0].isDefault = true;
      }
    }

    saveApiKeys();
    success = t("settings.keyDeleted");
    setTimeout(() => (success = null), 3000);
    cancelDelete();
  }

  function setDefaultKey(id: string) {
    const key = apiKeys.find((k) => k.id === id);
    if (!key) return;

    apiKeys = apiKeys.map((k) => ({
      ...k,
      isDefault: k.apiType === key.apiType ? k.id === id : k.isDefault,
    }));
    saveApiKeys();
  }

  let visibleKeyIds = $state<Set<string>>(new Set());

  let showCopySnackbar = $state(false);
  let copySnackbarTimeout: ReturnType<typeof setTimeout> | null = null;

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    showCopySnackbar = true;
    if (copySnackbarTimeout) clearTimeout(copySnackbarTimeout);
    // Hide after 2 seconds
    copySnackbarTimeout = setTimeout(() => {
      showCopySnackbar = false;
    }, 2000);
  }

  function copyApiKey(key: string) {
    copyToClipboard(key);
  }

  function toggleKeyVisibility(keyId: string) {
    const newSet = new Set(visibleKeyIds);
    if (newSet.has(keyId)) {
      newSet.delete(keyId);
    } else {
      newSet.add(keyId);
    }
    visibleKeyIds = newSet;
  }

  function maskApiKey(key: string): string {
    if (!key || key.length <= 8) return "••••••••";
    return key.substring(0, 4) + "••••" + key.substring(key.length - 4);
  }

  function formatApiKeyForDisplay(key: string, isVisible: boolean): string {
    if (!key) return "—";
    if (isVisible) {
      return key
        .split("")
        .map((char) => {
          if (char === " ") return "␣"; // Space indicator
          if (char === "\t") return "→"; // Tab indicator
          if (char === "\n") return "↵"; // Newline indicator
          return char;
        })
        .join("");
    }
    return maskApiKey(key);
  }

  function hasSpecialChars(key: string): boolean {
    return /[\s\t\n]/.test(key);
  }

  function onModelClick(model: ModelInfo) {
    if (model.provider === "google") {
      newKeyUrl = "https://generativelanguage.googleapis.com/v1beta";
    }
    // Usa l'ID del modello, non il nome display
    openAddKeyModal(model.provider, model.id);
  }
</script>

<div
  class="h-full flex flex-col p-6 overflow-hidden bg-gradient-to-br from-gray-900 via-gray-900 to-gray-950"
>
  <div class="mb-6 flex flex-col gap-4">
    <div
      class="glass-card p-3 flex items-center justify-between gap-4 overflow-x-auto"
    >
      <span
        class="text-xs font-bold text-gray-500 uppercase tracking-wide whitespace-nowrap px-2"
      >
        {t("settings.language")}
      </span>
      <div class="flex gap-2">
        {#each availableUILanguages as lang}
          <button
            onclick={() => setLanguage(lang.code)}
            class="flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all duration-200 border
              {$currentLanguage === lang.code
              ? 'bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border-indigo-500/50 text-white shadow-sm'
              : 'bg-white/5 hover:bg-white/10 text-gray-400 hover:text-gray-200 border-transparent hover:border-white/10'}"
          >
            <span class="text-base">{lang.flag}</span>
            <span class="text-xs font-medium uppercase">{lang.code}</span>
          </button>
        {/each}
      </div>
    </div>
  </div>

  {#if error}
    <div
      class="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3 animate-fade-in shrink-0"
    >
      <span class="text-red-300 flex-1">{error}</span>
      <button
        onclick={() => (error = null)}
        class="text-red-400 hover:text-red-300">✕</button
      >
    </div>
  {/if}

  {#if success}
    <div
      class="mb-4 p-4 bg-green-500/10 border border-green-500/30 rounded-xl flex items-center gap-3 animate-fade-in shrink-0"
    >
      <span class="text-green-300">{success}</span>
    </div>
  {/if}

  <div class="grid grid-cols-12 gap-6 flex-1 min-h-0">
    <div class="col-span-4 flex flex-col gap-4">
      <button
        onclick={() => openAddKeyModal(selectedProviderType)}
        class="btn-primary w-full py-3 flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20"
      >
        <svg
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 4v16m8-8H4"
          />
        </svg>
        <span>{t("settings.addCustomApiKey")}</span>
      </button>

      <div class="glass-card flex-1 flex flex-col min-h-0">
        <div class="p-4 border-b border-white/5">
          <div class="grid grid-cols-2 gap-2">
            {#each allProviderIds as pid}
              {@const provider = providers[pid]}
              {@const isEnabled = provider?.enabled ?? false}
              {@const isSelected = selectedProviderType === pid}
              <button
                onclick={() => {
                  if (isEnabled) selectedProviderType = pid;
                }}
                disabled={!isEnabled}
                class="relative py-2 px-3 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-2 justify-center
                  {isSelected && isEnabled
                  ? 'bg-white/10 text-white shadow-sm border border-white/10'
                  : isEnabled
                    ? 'text-gray-500 hover:text-gray-300 hover:bg-white/5 border border-transparent'
                    : 'text-gray-600 opacity-50 cursor-not-allowed border border-transparent'}"
              >
                {#if pid === "local"}
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    />
                  </svg>
                {:else if pid === "google"}
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    />
                    <path
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    />
                  </svg>
                {:else if pid === "openai"}
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path
                      d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z"
                    />
                  </svg>
                {:else if pid === "anthropic"}
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path
                      d="M17.304 3.541h-3.672l6.696 16.918H24l-6.696-16.918zm-10.608 0L0 20.459h3.744l1.368-3.576h7.056l1.368 3.576h3.744L10.584 3.541H6.696zm.096 10.454l2.4-6.252 2.376 6.252H6.792z"
                    />
                  </svg>
                {:else}
                  <span class="text-sm">🌐</span>
                {/if}
                <span class="truncate">{t(`provider.${pid}`) || provider?.name || pid}</span>
                {#if !isEnabled}
                  <span
                    class="absolute -top-1 -right-1 text-[8px] bg-amber-500/80 text-white px-1 py-0.5 rounded font-bold"
                    >{t("settings.soonBadge")}</span
                  >
                {/if}
              </button>
            {/each}
          </div>
        </div>

        <div class="flex-1 p-4 space-y-3">
          <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wide">
            {providers[selectedProviderType]?.name || selectedProviderType}
          </h3>
          <p class="text-sm text-gray-500 leading-relaxed">
            {t(`provider.${selectedProviderType}.desc`) || providers[selectedProviderType]?.description || ""}
          </p>
          {#if selectedProviderType === "google"}
            <div
              class="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg"
            >
              <p class="text-xs text-indigo-300">
                💡 {t("settings.googleProviderTip")}
              </p>
            </div>
          {:else if selectedProviderType === "local"}
            <div
              class="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg"
            >
              <p class="text-xs text-emerald-300">
                💡 {t("settings.localProviderTip")}
              </p>
            </div>
          {/if}
        </div>
      </div>
    </div>

    <div class="col-span-8 flex flex-col min-h-0">
      <div class="glass-card flex-1 flex flex-col min-h-0">
        <div class="p-4 border-b border-white/5">
          <h3
            class="text-sm font-semibold text-gray-400 uppercase tracking-wide"
          >
            {t("settings.apiKeys")}
          </h3>
        </div>

        <div class="flex-1 overflow-y-auto p-2 space-y-2">
          {#each apiKeys as key}
            <div
              class="p-3 bg-white/5 rounded-xl border border-white/10 hover:border-white/20 transition-all group
                {key.isDefault
                ? 'ring-1 ring-indigo-500/50 bg-indigo-500/5'
                : ''}"
            >
              <div class="flex items-start gap-3">
                <div
                  class="w-8 h-8 rounded-lg bg-gradient-to-br {providers[
                    key.apiType
                  ]?.color ||
                    'from-gray-500 to-gray-600'} flex items-center justify-center flex-shrink-0 text-white shadow-lg"
                >
                  {#if key.apiType === "local"}
                    <svg
                      class="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                      />
                    </svg>
                  {:else if key.apiType === "google"}
                    <svg
                      class="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      <path
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      />
                      <path
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      />
                      <path
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                      />
                      <path
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                      />
                    </svg>
                  {:else if key.apiType === "openai"}
                    <svg
                      class="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      <path
                        d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z"
                      />
                    </svg>
                  {:else if key.apiType === "anthropic"}
                    <svg
                      class="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      <path
                        d="M17.304 3.541h-3.672l6.696 16.918H24l-6.696-16.918zm-10.608 0L0 20.459h3.744l1.368-3.576h7.056l1.368 3.576h3.744L10.584 3.541H6.696zm.096 10.454l2.4-6.252 2.376 6.252H6.792z"
                      />
                    </svg>
                  {:else}
                    <span class="text-xs">?</span>
                  {/if}
                </div>

                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-0.5">
                    <span class="font-medium text-gray-200 text-sm truncate"
                      >{key.name}</span
                    >
                    {#if key.isDefault}
                      <svg
                        class="w-3.5 h-3.5 text-indigo-400"
                        fill="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          d="M16 4c.55 0 1 .45 1 1v4.38l1.71 1.71c.18.18.29.43.29.7V14c0 .55-.45 1-1 1h-5v5l-1 1-1-1v-5H6c-.55 0-1-.45-1-1v-2.21c0-.27.11-.52.29-.71L7 9.38V5c0-.55.45-1 1-1h8zm-1 2H9v3.62l-2 2V13h10v-1.38l-2-2V6z"
                        />
                      </svg>
                    {/if}
                  </div>
                  <div class="flex items-center gap-1.5">
                    <button
                      onclick={() => toggleKeyVisibility(key.id)}
                      class="text-[10px] text-gray-500 font-mono truncate hover:text-gray-300 transition-colors flex items-center gap-1"
                      title={t("settings.toggleVisibility")}
                    >
                      {#if visibleKeyIds.has(key.id)}
                        <svg
                          class="w-3 h-3 flex-shrink-0"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                          />
                        </svg>
                      {:else}
                        <svg
                          class="w-3 h-3 flex-shrink-0"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                          />
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                          />
                        </svg>
                      {/if}
                      <span class="truncate"
                        >{formatApiKeyForDisplay(
                          key.apiKey,
                          visibleKeyIds.has(key.id),
                        )}</span
                      >
                    </button>
                    <button
                      onclick={() => copyApiKey(key.apiKey)}
                      class="p-1 text-gray-500 hover:text-gray-300 transition-colors flex-shrink-0"
                      title="Copy"
                    >
                      <svg
                        class="w-3 h-3"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                      </svg>
                    </button>
                    {#if hasSpecialChars(key.apiKey)}
                      <span
                        class="text-[9px] bg-amber-500/20 text-amber-400 px-1 py-0.5 rounded flex-shrink-0"
                        title={t("settings.hasSpecialChars")}
                      >
                        ⚠
                      </span>
                    {/if}
                  </div>
                  {#if key.modelName}
                    <div class="text-[10px] text-indigo-400 mt-1 truncate">
                      {t("settings.model")}: {key.modelName}
                    </div>
                  {/if}
                </div>

                <div
                  class="flex flex-col gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity"
                >
                  {#if !key.isDefault}
                    <button
                      onclick={() => setDefaultKey(key.id)}
                      class="p-1.5 text-gray-500 hover:text-indigo-400 hover:bg-white/10 rounded transition-colors"
                      title={t("settings.setAsDefault")}
                    >
                      <svg
                        class="w-3.5 h-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M5 5a2 2 0 012-2h10a2 2 0 012 2v4.38l1.71 1.71c.18.18.29.43.29.7V14a2 2 0 01-2 2h-5v4l-2 2-2-2v-4H5a2 2 0 01-2-2v-2.21c0-.27.11-.52.29-.71L5 9.38V5z"
                        />
                      </svg>
                    </button>
                  {/if}
                  <button
                    onclick={() => askDeleteApiKey(key.id)}
                    class="p-1.5 text-gray-500 hover:text-red-400 hover:bg-white/10 rounded transition-colors"
                    title={t("settings.delete")}
                  >
                    <svg
                      class="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          {/each}

          {#if apiKeys.length === 0}
            <div
              class="flex-1 flex flex-col items-center justify-center text-gray-500 p-8 text-center opacity-50"
            >
              <svg
                class="w-10 h-10 mb-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
                />
              </svg>
              <p class="text-xs">{t("settings.noApiKeys")}</p>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>

  {#if showAddKey}
    <div
      class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      role="dialog"
      tabindex="-1"
      onmousedown={(e) => {
        if (e.target === e.currentTarget) showAddKey = false;
      }}
    >
      <div
        class="w-full max-w-lg overflow-hidden animate-fade-in shadow-2xl border border-white/20 bg-gray-900/98 backdrop-blur-xl rounded-xl"
        role="presentation"
        onmousedown={(e) => e.stopPropagation()}
      >
        <div class="p-6 border-b border-white/5 bg-white/5">
          <h3 class="text-xl font-bold text-white flex items-center gap-2">
            {t("settings.modal.addCustomApiKey")}
          </h3>
        </div>

        <div class="p-6 space-y-5">
          <div>
            <span
              class="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-2"
              >{t("settings.modal.provider")}</span
            >
            <div class="grid grid-cols-2 gap-3">
              <button
                type="button"
                onclick={() => {
                  newKeyType = "local";
                  newKeyName = providers.local.name;
                  newKeyUrl = providers.local.defaultApiUrl || "";
                  newKeyValue = "";
                }}
                class="flex items-center gap-3 p-3 rounded-lg transition-all duration-200 border text-left
                  {newKeyType === 'local'
                  ? 'bg-indigo-500/20 border-indigo-500/50 text-white'
                  : 'bg-white/5 hover:bg-white/10 border-transparent text-gray-400'}"
              >
                <div
                  class="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white shadow-lg"
                >
                  <svg
                    class="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    />
                  </svg>
                </div>
                <div class="flex flex-col">
                  <span class="text-sm font-bold"
                    >{t("settings.modal.localServer")}</span
                  >
                  <span class="text-[10px] opacity-70 leading-tight"
                    >{t("settings.modal.localServerDesc")}</span
                  >
                </div>
              </button>

              <button
                type="button"
                onclick={() => {
                  newKeyType = "google";
                  newKeyName = providers.google.name;
                  newKeyUrl = providers.google.defaultApiUrl || "";
                  newKeyValue = "";
                }}
                class="flex items-center gap-3 p-3 rounded-lg transition-all duration-200 border text-left
                  {newKeyType === 'google'
                  ? 'bg-indigo-500/20 border-indigo-500/50 text-white'
                  : 'bg-white/5 hover:bg-white/10 border-transparent text-gray-400'}"
              >
                <div
                  class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white shadow-lg"
                >
                  <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    />
                    <path
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    />
                  </svg>
                </div>
                <div class="flex flex-col">
                  <span class="text-sm font-bold">{t("settings.modal.providerGoogle")}</span>
                  <span class="text-[10px] opacity-70 leading-tight"
                    >{t("settings.modal.providerGoogleDesc")}</span
                  >
                </div>
              </button>

              <button
                type="button"
                disabled
                class="relative flex items-center gap-3 p-3 rounded-lg border text-left bg-white/5 border-transparent text-gray-600 opacity-50 cursor-not-allowed"
              >
                <div
                  class="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center text-white shadow-lg opacity-50"
                >
                  <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path
                      d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073z"
                    />
                  </svg>
                </div>
                <div class="flex flex-col">
                  <span class="text-sm font-bold">{t("settings.modal.providerOpenai")}</span>
                  <span class="text-[10px] opacity-70 leading-tight"
                    >{t("settings.modal.providerOpenaiDesc")}</span
                  >
                </div>
                <span
                  class="absolute -top-1 -right-1 text-[8px] bg-amber-500/80 text-white px-1.5 py-0.5 rounded font-bold"
                  >{t("settings.soonBadge")}</span
                >
              </button>

              <button
                type="button"
                disabled
                class="relative flex items-center gap-3 p-3 rounded-lg border text-left bg-white/5 border-transparent text-gray-600 opacity-50 cursor-not-allowed"
              >
                <div
                  class="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center text-white shadow-lg opacity-50"
                >
                  <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path
                      d="M17.304 3.541h-3.672l6.696 16.918H24l-6.696-16.918zm-10.608 0L0 20.459h3.744l1.368-3.576h7.056l1.368 3.576h3.744L10.584 3.541H6.696zm.096 10.454l2.4-6.252 2.376 6.252H6.792z"
                    />
                  </svg>
                </div>
                <div class="flex flex-col">
                  <span class="text-sm font-bold">{t("settings.modal.providerAnthropic")}</span>
                  <span class="text-[10px] opacity-70 leading-tight"
                    >{t("settings.modal.providerAnthropicDesc")}</span
                  >
                </div>
                <span
                  class="absolute -top-1 -right-1 text-[8px] bg-amber-500/80 text-white px-1.5 py-0.5 rounded font-bold"
                  >{t("settings.soonBadge")}</span
                >
              </button>
            </div>
          </div>

          <div class="space-y-4">
            <div>
              <label
                for="key-name"
                class="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-1.5"
                >{t("settings.modal.configName")}</label
              >
              <input
                id="key-name"
                type="text"
                bind:value={newKeyName}
                placeholder={t("settings.modal.configNamePlaceholder")}
                class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 outline-none transition-all placeholder-gray-600"
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div class="col-span-2">
                <label
                  for="api-url"
                  class="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-1.5"
                >
                  {t("settings.modal.apiEndpoint")}
                </label>
                <input
                  id="api-url"
                  type="text"
                  bind:value={newKeyUrl}
                  placeholder={providers[newKeyType]?.defaultApiUrl ||
                    "https://..."}
                  class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 outline-none transition-all placeholder-gray-600 font-mono"
                />
              </div>

              {#if newKeyType !== "local"}
                <div class="col-span-2">
                  <label
                    for="api-key"
                    class="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-1.5"
                    >{t("settings.modal.apiKey")}</label
                  >
                  <div class="relative">
                    <input
                      id="api-key"
                      type={showNewKeyPassword ? "text" : "password"}
                      bind:value={newKeyValue}
                      placeholder={newKeyType === "google"
                        ? "AIza..."
                        : "sk-..."}
                      class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 pr-20 text-sm text-white focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 outline-none transition-all placeholder-gray-600 font-mono"
                    />
                    <div
                      class="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1"
                    >
                      <button
                        type="button"
                        onclick={() =>
                          (showNewKeyPassword = !showNewKeyPassword)}
                        class="p-1.5 text-gray-500 hover:text-gray-300 transition-colors"
                        title={t("settings.toggleVisibility")}
                      >
                        {#if showNewKeyPassword}
                          <svg
                            class="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                            />
                          </svg>
                        {:else}
                          <svg
                            class="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                            />
                          </svg>
                        {/if}
                      </button>
                      <button
                        type="button"
                        onclick={() => copyToClipboard(newKeyValue)}
                        class="p-1.5 text-gray-500 hover:text-gray-300 transition-colors"
                        title="Copy"
                      >
                        <svg
                          class="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              {/if}

              <!-- Model ID - opzionale, il modello si sceglie nel tab Traduzione -->
              <div class="col-span-2 animate-fade-in">
                <label
                  for="model-id"
                  class="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-1.5"
                >
                  {t("settings.modal.defaultModel")}
                  <span class="text-gray-600 font-normal normal-case"
                    >({t("settings.modal.optional")})</span
                  >
                </label>
                <input
                  id="model-id"
                  type="text"
                  bind:value={newKeyModelName}
                  placeholder={newKeyType === "local"
                    ? "e.g. llama3.2, gemma3:27b..."
                    : "e.g. gemini-2.0-flash, gemini-1.5-pro..."}
                  class="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 outline-none transition-all placeholder-gray-600 font-mono"
                />
                <p class="text-[10px] text-gray-500 mt-1.5 leading-relaxed">
                  💡 {t("settings.modal.modelOptionalHint")}
                </p>
                {#if newKeyType === "google"}
                  <p class="text-[10px] text-gray-500 mt-1.5 leading-relaxed">
                    💡 {t("settings.modal.apiKeyHintGoogle")} <a
                      href="https://aistudio.google.com/apikey"
                      target="_blank"
                      class="text-blue-400 hover:text-blue-300 underline"
                      >aistudio.google.com/apikey</a
                    >
                  </p>
                {/if}
              </div>
            </div>
          </div>

          <div class="flex gap-3 pt-4 border-t border-white/5">
            <button
              onclick={() => (showAddKey = false)}
              class="flex-1 py-2.5 rounded-lg border border-white/10 text-gray-400 hover:bg-white/5 hover:text-white transition-all text-sm font-medium"
            >
              {t("settings.modal.cancel")}
            </button>
            <button
              onclick={addApiKey}
              class="flex-1 py-2.5 rounded-lg bg-indigo-500 hover:bg-indigo-400 text-white shadow-lg shadow-indigo-500/20 transition-all text-sm font-bold"
            >
              {t("settings.modal.save")}
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}

  {#if showCopySnackbar}
    <div
      class="fixed bottom-6 left-1/2 -translate-x-1/2 z-[60] animate-fade-in"
    >
      <div
        class="bg-gray-800 border border-gray-700 text-white px-4 py-2.5 rounded-lg shadow-xl flex items-center gap-2"
      >
        <svg
          class="w-4 h-4 text-green-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M5 13l4 4L19 7"
          />
        </svg>
        <span class="text-sm font-medium">{t("settings.keyCopied")}</span>
      </div>
    </div>
  {/if}

  {#if deleteConfirmId}
    <div
      class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      role="dialog"
      tabindex="-1"
      onmousedown={(e) => {
        if (e.target === e.currentTarget) cancelDelete();
      }}
    >
      <div
        class="w-full max-w-sm overflow-hidden animate-fade-in shadow-2xl border border-white/20 bg-gray-900/98 backdrop-blur-xl rounded-xl"
        role="presentation"
        onmousedown={(e) => e.stopPropagation()}
      >
        <div class="p-6 border-b border-white/5 bg-white/5">
          <h3 class="text-xl font-bold text-white">{t("app.title")}</h3>
        </div>

        <div class="p-6 space-y-4">
          <p class="text-gray-300">
            {t("settings.confirmDeleteKey", { name: deleteConfirmName })}
          </p>

          <div class="flex gap-3 pt-2">
            <button
              onclick={cancelDelete}
              class="flex-1 py-2.5 rounded-lg border border-white/10 text-gray-400 hover:bg-white/5 hover:text-white transition-all text-sm font-medium"
            >
              {t("settings.modal.cancel")}
            </button>
            <button
              onclick={confirmDeleteApiKey}
              class="flex-1 py-2.5 rounded-lg bg-red-500 hover:bg-red-400 text-white shadow-lg shadow-red-500/20 transition-all text-sm font-bold"
            >
              {t("settings.confirmDelete")}
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  ::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  ::-webkit-scrollbar-track {
    background: transparent;
  }
  ::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
  }
</style>
