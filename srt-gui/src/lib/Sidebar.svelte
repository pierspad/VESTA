<script lang="ts">
  interface Props {
    activeTab: "translate" | "sync";
    onTabChange: (tab: "translate" | "sync") => void;
  }

  let { activeTab, onTabChange }: Props = $props();
</script>

<aside class="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
  <!-- Logo / Title -->
  <div class="p-4 border-b border-gray-700">
    <h1 class="text-xl font-bold text-blue-400">SRT Tools</h1>
    <p class="text-sm text-gray-400">Traduzione & Sincronizzazione</p>
  </div>

  <!-- Navigation -->
  <nav class="flex-1 p-4 space-y-2">
    <button
      class="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors {activeTab ===
      'translate'
        ? 'bg-blue-600 text-white'
        : 'text-gray-300 hover:bg-gray-700'}"
      onclick={() => onTabChange("translate")}
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
          d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
        />
      </svg>
      <span>Traduzione</span>
    </button>

    <button
      class="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors {activeTab ===
      'sync'
        ? 'bg-blue-600 text-white'
        : 'text-gray-300 hover:bg-gray-700'}"
      onclick={() => onTabChange("sync")}
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
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <span>Sincronizzazione</span>
    </button>
  </nav>

  <!-- Footer -->
  <div class="p-4 border-t border-gray-700 text-xs text-gray-500">
    <p>v0.1.0</p>
    <p>Powered by Tauri + Svelte</p>
  </div>
</aside>
