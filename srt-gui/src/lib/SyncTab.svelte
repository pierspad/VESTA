<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import { open, save } from "@tauri-apps/plugin-dialog";
  import { onMount } from "svelte";

  // Types
  interface SubtitleInfo {
    id: number;
    start_ms: number;
    end_ms: number;
    text: string;
    synced_start_ms: number;
    synced_end_ms: number;
    offset_ms: number;
    is_anchor: boolean;
  }

  interface SyncStatus {
    is_loaded: boolean;
    srt_path: string | null;
    video_path: string | null;
    total_subtitles: number;
    anchor_count: number;
    checked_count: number;
    completion_percentage: number;
    average_offset_ms: number;
    suggested_next_id: number | null;
  }

  interface AnchorInfo {
    subtitle_id: number;
    original_time_ms: number;
    corrected_time_ms: number;
    offset_ms: number;
  }

  // State
  let videoElement = $state<HTMLVideoElement | null>(null);
  let status = $state<SyncStatus | null>(null);
  let subtitles = $state<SubtitleInfo[]>([]);
  let anchors = $state<AnchorInfo[]>([]);
  let currentSubtitle = $state<SubtitleInfo | null>(null);
  let currentVideoTime = $state(0);
  let isPlaying = $state(false);
  let error = $state<string | null>(null);
  let videoSrc = $state<string | null>(null);

  // Offset adjustment
  let offsetAdjustment = $state(0);

  // Computed: current subtitle based on video time
  let activeSubtitleId = $derived.by(() => {
    const time = currentVideoTime * 1000; // Convert to ms
    for (const sub of subtitles) {
      if (time >= sub.synced_start_ms && time <= sub.synced_end_ms) {
        return sub.id;
      }
    }
    return null;
  });

  // Update current video time
  function onTimeUpdate() {
    if (videoElement) {
      currentVideoTime = videoElement.currentTime;
    }
  }

  async function selectSrtFile() {
    try {
      const selected = await open({
        multiple: false,
        filters: [{ name: "SRT Files", extensions: ["srt"] }],
      });

      if (selected) {
        status = await invoke<SyncStatus>("sync_load_srt", {
          path: selected as string,
        });
        await loadSubtitles();
        await loadAnchors();
      }
    } catch (e) {
      error = `Errore caricamento SRT: ${e}`;
    }
  }

  async function selectVideoFile() {
    try {
      const selected = await open({
        multiple: false,
        filters: [
          { name: "Video Files", extensions: ["mp4", "mkv", "avi", "webm"] },
        ],
      });

      if (selected) {
        const path = selected as string;
        videoSrc = `file://${path}`;
        status = await invoke<SyncStatus>("sync_set_video", { path });
      }
    } catch (e) {
      error = `Errore caricamento video: ${e}`;
    }
  }

  async function loadSubtitles() {
    try {
      subtitles = await invoke<SubtitleInfo[]>("sync_get_subtitles");
    } catch (e) {
      error = `Errore caricamento sottotitoli: ${e}`;
    }
  }

  async function loadAnchors() {
    try {
      anchors = await invoke<AnchorInfo[]>("sync_get_anchors");
    } catch (e) {
      error = `Errore caricamento ancore: ${e}`;
    }
  }

  async function refreshStatus() {
    try {
      status = await invoke<SyncStatus>("sync_get_status");
      await loadSubtitles();
      await loadAnchors();
    } catch (e) {
      error = `Errore aggiornamento stato: ${e}`;
    }
  }

  async function addAnchor() {
    if (!currentSubtitle) return;

    const correctedTime =
      currentSubtitle.start_ms + offsetAdjustment + currentVideoTime * 1000;

    try {
      status = await invoke<SyncStatus>("sync_add_anchor", {
        subtitleId: currentSubtitle.id,
        correctedTimeMs: Math.round(correctedTime),
      });
      await loadSubtitles();
      await loadAnchors();
      offsetAdjustment = 0;
    } catch (e) {
      error = `Errore aggiunta ancora: ${e}`;
    }
  }

  async function confirmAtCurrentTime() {
    if (activeSubtitleId === null) return;

    const videoTimeMs = currentVideoTime * 1000;

    try {
      status = await invoke<SyncStatus>("sync_add_anchor", {
        subtitleId: activeSubtitleId,
        correctedTimeMs: Math.round(videoTimeMs),
      });
      await loadSubtitles();
      await loadAnchors();
    } catch (e) {
      error = `Errore conferma ancora: ${e}`;
    }
  }

  async function removeAnchor(subtitleId: number) {
    try {
      status = await invoke<SyncStatus>("sync_remove_anchor", {
        subtitleId,
      });
      await loadSubtitles();
      await loadAnchors();
    } catch (e) {
      error = `Errore rimozione ancora: ${e}`;
    }
  }

  async function goToSuggested() {
    if (!status?.suggested_next_id) return;

    const sub = subtitles.find((s) => s.id === status?.suggested_next_id);
    if (sub && videoElement) {
      videoElement.currentTime = sub.synced_start_ms / 1000;
      currentSubtitle = sub;
    }
  }

  async function saveFile() {
    try {
      const selected = await save({
        filters: [{ name: "SRT Files", extensions: ["srt"] }],
        defaultPath: status?.srt_path?.replace(".srt", ".synced.srt"),
      });

      if (selected) {
        await invoke<string>("sync_save_file", { outputPath: selected });
        alert(`File salvato: ${selected}`);
      }
    } catch (e) {
      error = `Errore salvataggio: ${e}`;
    }
  }

  async function saveSession() {
    try {
      const selected = await save({
        filters: [{ name: "Session Files", extensions: ["json"] }],
      });

      if (selected) {
        await invoke<string>("sync_save_session", { sessionPath: selected });
        alert(`Sessione salvata: ${selected}`);
      }
    } catch (e) {
      error = `Errore salvataggio sessione: ${e}`;
    }
  }

  async function loadSession() {
    try {
      const selected = await open({
        filters: [{ name: "Session Files", extensions: ["json"] }],
      });

      if (selected) {
        status = await invoke<SyncStatus>("sync_load_session", {
          sessionPath: selected as string,
        });
        await loadSubtitles();
        await loadAnchors();
      }
    } catch (e) {
      error = `Errore caricamento sessione: ${e}`;
    }
  }

  async function resetSync() {
    if (!confirm("Sei sicuro di voler resettare la sincronizzazione?")) return;

    try {
      status = await invoke<SyncStatus>("sync_reset");
      await loadSubtitles();
      await loadAnchors();
    } catch (e) {
      error = `Errore reset: ${e}`;
    }
  }

  function formatTime(ms: number): string {
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const millis = Math.floor(ms % 1000);

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}.${millis.toString().padStart(3, "0")}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, "0")}.${millis.toString().padStart(3, "0")}`;
  }

  function formatOffset(ms: number): string {
    const sign = ms >= 0 ? "+" : "";
    return `${sign}${(ms / 1000).toFixed(2)}s`;
  }

  function goToSubtitle(sub: SubtitleInfo) {
    currentSubtitle = sub;
    if (videoElement) {
      videoElement.currentTime = sub.synced_start_ms / 1000;
    }
  }

  // Keyboard shortcuts
  function handleKeydown(e: KeyboardEvent) {
    if (!videoElement) return;

    switch (e.key) {
      case " ":
        e.preventDefault();
        if (isPlaying) {
          videoElement.pause();
        } else {
          videoElement.play();
        }
        break;
      case "ArrowLeft":
        e.preventDefault();
        videoElement.currentTime -= e.shiftKey ? 1 : 0.1;
        break;
      case "ArrowRight":
        e.preventDefault();
        videoElement.currentTime += e.shiftKey ? 1 : 0.1;
        break;
      case "ArrowUp":
        e.preventDefault();
        offsetAdjustment += e.shiftKey ? 500 : 100;
        break;
      case "ArrowDown":
        e.preventDefault();
        offsetAdjustment -= e.shiftKey ? 500 : 100;
        break;
      case "Enter":
        e.preventDefault();
        confirmAtCurrentTime();
        break;
    }
  }

  onMount(() => {
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  });
</script>

<div class="h-full flex flex-col overflow-hidden">
  <!-- Top Bar -->
  <div
    class="flex items-center gap-4 p-4 bg-gray-800 border-b border-gray-700 flex-shrink-0"
  >
    <button
      onclick={selectSrtFile}
      class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm"
    >
      📄 Carica SRT
    </button>
    <button
      onclick={selectVideoFile}
      class="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded text-sm"
    >
      🎬 Carica Video
    </button>

    <div class="flex-1"></div>

    <button
      onclick={loadSession}
      class="px-3 py-2 bg-gray-600 hover:bg-gray-500 rounded text-sm"
    >
      📂 Carica Sessione
    </button>
    <button
      onclick={saveSession}
      disabled={!status?.is_loaded}
      class="px-3 py-2 bg-gray-600 hover:bg-gray-500 disabled:opacity-50 rounded text-sm"
    >
      💾 Salva Sessione
    </button>
    <button
      onclick={saveFile}
      disabled={!status?.is_loaded}
      class="px-3 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded text-sm"
    >
      💾 Esporta SRT
    </button>
  </div>

  <!-- Main Content -->
  <div class="flex-1 flex overflow-hidden">
    <!-- Left: Video + Controls -->
    <div class="w-2/3 flex flex-col border-r border-gray-700">
      <!-- Video Player -->
      <div class="flex-1 bg-black relative flex items-center justify-center">
        {#if videoSrc}
          <video
            bind:this={videoElement}
            src={videoSrc}
            class="max-w-full max-h-full"
            ontimeupdate={onTimeUpdate}
            onplay={() => (isPlaying = true)}
            onpause={() => (isPlaying = false)}
          >
            <track kind="captions" />
          </video>

          <!-- Subtitle Overlay -->
          {#if activeSubtitleId !== null}
            {@const activeSub = subtitles.find(
              (s) => s.id === activeSubtitleId
            )}
            {#if activeSub}
              <div
                class="absolute bottom-16 left-0 right-0 text-center px-4"
              >
                <p
                  class="inline-block bg-black/80 px-4 py-2 rounded text-xl text-white"
                >
                  {activeSub.text}
                </p>
              </div>
            {/if}
          {/if}
        {:else}
          <div class="text-gray-500 text-center">
            <p class="text-4xl mb-4">🎬</p>
            <p>Carica un video per iniziare</p>
          </div>
        {/if}
      </div>

      <!-- Video Controls -->
      <div class="bg-gray-800 p-4 space-y-3 flex-shrink-0">
        <!-- Timeline -->
        <div class="flex items-center gap-4">
          <span class="text-sm text-gray-400 w-20">
            {formatTime(currentVideoTime * 1000)}
          </span>
          <input
            type="range"
            min="0"
            max={videoElement?.duration || 100}
            bind:value={currentVideoTime}
            oninput={() => {
              if (videoElement) videoElement.currentTime = currentVideoTime;
            }}
            class="flex-1"
          />
          <span class="text-sm text-gray-400 w-20 text-right">
            {videoElement ? formatTime(videoElement.duration * 1000) : "--:--"}
          </span>
        </div>

        <!-- Controls Row -->
        <div class="flex items-center gap-4">
          <button
            onclick={() =>
              videoElement && (isPlaying ? videoElement.pause() : videoElement.play())}
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded"
          >
            {isPlaying ? "⏸️ Pausa" : "▶️ Play"}
          </button>

          <div class="flex-1"></div>

          <!-- Offset Adjustment -->
          <div class="flex items-center gap-2 bg-gray-700 rounded px-3 py-2">
            <span class="text-sm text-gray-400">Offset:</span>
            <button
              onclick={() => (offsetAdjustment -= 100)}
              class="px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm"
              >-100ms</button
            >
            <span class="text-lg font-mono w-24 text-center">
              {formatOffset(offsetAdjustment)}
            </span>
            <button
              onclick={() => (offsetAdjustment += 100)}
              class="px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm"
              >+100ms</button
            >
          </div>

          <button
            onclick={confirmAtCurrentTime}
            disabled={activeSubtitleId === null}
            class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded"
          >
            ✅ Conferma Ancora
          </button>
        </div>

        <!-- Shortcuts Help -->
        <div class="text-xs text-gray-500 flex gap-4">
          <span><kbd class="bg-gray-700 px-1 rounded">Spazio</kbd> Play/Pausa</span>
          <span><kbd class="bg-gray-700 px-1 rounded">←/→</kbd> Seek ±0.1s</span>
          <span><kbd class="bg-gray-700 px-1 rounded">↑/↓</kbd> Offset ±100ms</span>
          <span><kbd class="bg-gray-700 px-1 rounded">Enter</kbd> Conferma</span>
        </div>
      </div>
    </div>

    <!-- Right: Subtitle List + Status -->
    <div class="w-1/3 flex flex-col bg-gray-800">
      <!-- Status Bar -->
      {#if status?.is_loaded}
        <div class="p-3 border-b border-gray-700 space-y-2 flex-shrink-0">
          <div class="flex justify-between text-sm">
            <span class="text-gray-400">Sottotitoli:</span>
            <span>{status.total_subtitles}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-400">Ancore:</span>
            <span class="text-green-400">{status.anchor_count}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-400">Offset medio:</span>
            <span>{formatOffset(status.average_offset_ms)}</span>
          </div>

          <!-- Progress -->
          <div class="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
            <div
              class="h-full bg-blue-600"
              style="width: {status.completion_percentage}%"
            ></div>
          </div>
          <p class="text-xs text-gray-500 text-center">
            {status.completion_percentage.toFixed(1)}% completato
          </p>

          <!-- Suggested Next -->
          {#if status.suggested_next_id}
            <button
              onclick={goToSuggested}
              class="w-full py-2 bg-yellow-600 hover:bg-yellow-700 rounded text-sm"
            >
              🎯 Vai al suggerito: #{status.suggested_next_id}
            </button>
          {/if}

          <div class="flex gap-2">
            <button
              onclick={resetSync}
              class="flex-1 py-1 bg-red-600/30 hover:bg-red-600/50 text-red-400 rounded text-sm"
            >
              Reset
            </button>
          </div>
        </div>
      {/if}

      <!-- Anchors List -->
      {#if anchors.length > 0}
        <div class="p-3 border-b border-gray-700 flex-shrink-0">
          <h4 class="text-sm font-semibold text-blue-400 mb-2">
            Ancore ({anchors.length})
          </h4>
          <div class="space-y-1 max-h-32 overflow-y-auto">
            {#each anchors as anchor}
              <div
                class="flex items-center justify-between text-xs bg-gray-700 rounded px-2 py-1"
              >
                <span>#{anchor.subtitle_id}</span>
                <span class="text-green-400"
                  >{formatOffset(anchor.offset_ms)}</span
                >
                <button
                  onclick={() => removeAnchor(anchor.subtitle_id)}
                  class="text-red-400 hover:text-red-300"
                >
                  ✕
                </button>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Subtitle List -->
      <div class="flex-1 overflow-y-auto">
        {#each subtitles as sub}
          <button
            onclick={() => goToSubtitle(sub)}
            class="w-full text-left p-3 border-b border-gray-700 hover:bg-gray-700 transition-colors
              {activeSubtitleId === sub.id ? 'bg-blue-600/30 border-l-4 border-l-blue-500' : ''}
              {sub.is_anchor ? 'bg-green-600/10' : ''}"
          >
            <div class="flex items-start gap-2">
              <span class="text-xs text-gray-500 w-8">#{sub.id}</span>
              <div class="flex-1 min-w-0">
                <p class="text-sm truncate">{sub.text}</p>
                <div class="flex gap-2 text-xs text-gray-400 mt-1">
                  <span>{formatTime(sub.synced_start_ms)}</span>
                  <span class="text-gray-600">→</span>
                  <span>{formatTime(sub.synced_end_ms)}</span>
                  {#if sub.offset_ms !== 0}
                    <span
                      class={sub.offset_ms > 0
                        ? "text-green-400"
                        : "text-red-400"}
                    >
                      {formatOffset(sub.offset_ms)}
                    </span>
                  {/if}
                </div>
              </div>
              {#if sub.is_anchor}
                <span class="text-green-400">⚓</span>
              {/if}
            </div>
          </button>
        {/each}

        {#if subtitles.length === 0 && !status?.is_loaded}
          <div class="text-center text-gray-500 py-8">
            <p>Carica un file SRT per iniziare</p>
          </div>
        {/if}
      </div>
    </div>
  </div>

  <!-- Error Toast -->
  {#if error}
    <div
      class="fixed bottom-4 right-4 bg-red-600 text-white px-4 py-2 rounded-lg shadow-lg"
    >
      {error}
      <button onclick={() => (error = null)} class="ml-2">✕</button>
    </div>
  {/if}
</div>
