<script lang="ts">
  import Sidebar from "./lib/Sidebar.svelte";
  import TranslateTab from "./lib/TranslateTab.svelte";
  import SyncTab from "./lib/SyncTab.svelte";

  let activeTab = $state<"translate" | "sync">("translate");
</script>

<main class="flex h-screen bg-gray-900 text-gray-100">
  <!-- Sidebar -->
  <Sidebar {activeTab} onTabChange={(tab) => (activeTab = tab)} />

  <!-- Main Content -->
  <div class="flex-1 overflow-hidden">
    {#if activeTab === "translate"}
      <TranslateTab />
    {:else}
      <SyncTab />
    {/if}
  </div>
</main>
