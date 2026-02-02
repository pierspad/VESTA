<script lang="ts">
  import Sidebar from "./lib/Sidebar.svelte";
  import TranslateTab from "./lib/TranslateTab.svelte";
  import SyncTab from "./lib/SyncTab.svelte";
  import SettingsTab from "./lib/SettingsTab.svelte";

  let activeTab = $state<"translate" | "sync" | "settings">("translate");
</script>

<main class="flex h-screen bg-gradient-to-br from-gray-900 via-gray-950 to-gray-900 text-gray-100">
  <!-- Sidebar -->
  <Sidebar {activeTab} onTabChange={(tab) => (activeTab = tab)} />

  <!-- Main Content -->
  <div class="flex-1 overflow-hidden">
    {#if activeTab === "translate"}
      <TranslateTab />
    {:else if activeTab === "sync"}
      <SyncTab />
    {:else}
      <SettingsTab />
    {/if}
  </div>
</main>
