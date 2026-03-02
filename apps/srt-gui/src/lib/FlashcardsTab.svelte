<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import { listen } from "@tauri-apps/api/event";
  import { open } from "@tauri-apps/plugin-dialog";
  import { onDestroy, onMount, tick } from "svelte";
  import { locale } from "./i18n";
  import { languages } from "./models";
  import SearchableSelect from "./SearchableSelect.svelte";

  let t = $derived($locale);

  let targetSubsPath = $state("");
  let nativeSubsPath = $state("");
  let mediaPath = $state("");
  let mediaType = $state<"none" | "video" | "audio">("none");
  let outputDir = $state("");

  const OUTPUT_DIR_KEY = "vesta-last-output-dir";
  const NOTE_TYPE_LANGUAGE_KEY = "vesta-flashcards-note-type-language";
  const SERIES_MODE_KEY = "vesta-flashcards-series-mode";

  // ─── Series Mode State ───────────────────────────────────────────────────
  let seriesMode = $state(loadSeriesMode());

  function loadSeriesMode(): boolean {
    try {
      return localStorage.getItem(SERIES_MODE_KEY) === "true";
    } catch {
      return false;
    }
  }

  function toggleSeriesMode() {
    seriesMode = !seriesMode;
    localStorage.setItem(SERIES_MODE_KEY, String(seriesMode));
  }

  // Episode data for series mode
  interface EpisodeEntry {
    id: number;
    targetSubsPath: string;
    nativeSubsPath: string;
    mediaPath: string;
    mediaType: "none" | "video" | "audio";
  }

  let episodes = $state<EpisodeEntry[]>([]);
  let seriesOutputMode = $state<"single" | "separate">("separate");
  let seriesCurrentEpisode = $state(0);
  let seriesTotalEpisodes = $state(0);

  // Extract episode number from filename using common patterns
  function extractEpisodeNumber(filename: string): number | null {
    const base = filename.replace(/\.[^/.]+$/, "");
    // Match patterns: S01E03, E03, Ep03, Episode 03, x03, - 03, _03
    const patterns = [
      /[Ss]\d{1,2}[Ee](\d{1,4})/,
      /[Ee][Pp]?\.?\s*(\d{1,4})/i,
      /[Ee]pisode\.?\s*(\d{1,4})/i,
      /[Xx](\d{1,4})/,
      /[\s_\-\.](\d{1,4})[\s_\-\.]/,
      /^(\d{1,4})[\s_\-\.]/,
      /[\s_\-\.](\d{1,4})$/,
    ];
    for (const pat of patterns) {
      const m = base.match(pat);
      if (m) return parseInt(m[1], 10);
    }
    return null;
  }

  // Auto-match files across categories by episode number, then lexicographic
  function autoMatchFiles(
    targetFiles: string[],
    nativeFiles: string[],
    mediaFiles: string[],
  ) {
    // Extract episode numbers and sort
    type FileWithEp = { path: string; ep: number | null; name: string };
    const toEntries = (files: string[]): FileWithEp[] =>
      files.map((f) => {
        const name = f.split("/").pop() || f;
        return { path: f, ep: extractEpisodeNumber(name), name };
      });

    const targets = toEntries(targetFiles);
    const natives = toEntries(nativeFiles);
    const medias = toEntries(mediaFiles);

    // Try episode-number matching first
    const allHaveEps = targets.every((t) => t.ep !== null);
    if (allHaveEps) {
      targets.sort((a, b) => (a.ep ?? 0) - (b.ep ?? 0));
    } else {
      targets.sort((a, b) =>
        a.name.localeCompare(b.name, undefined, { numeric: true }),
      );
    }

    // Match natives and medias by episode number or index
    const newEpisodes: EpisodeEntry[] = targets.map((t, idx) => {
      let nativePath = "";
      let mediaPath = "";
      let mediaType: "none" | "video" | "audio" = "none";

      // Find matching native by episode number
      if (t.ep !== null) {
        const matchNative = natives.find((n) => n.ep === t.ep);
        if (matchNative) nativePath = matchNative.path;
        const matchMedia = medias.find((m) => m.ep === t.ep);
        if (matchMedia) {
          mediaPath = matchMedia.path;
          mediaType = detectMediaType(matchMedia.name);
        }
      }

      // Fall back to index matching
      if (!nativePath && idx < natives.length) {
        const sorted = [...natives].sort((a, b) =>
          a.name.localeCompare(b.name, undefined, { numeric: true }),
        );
        nativePath = sorted[idx]?.path || "";
      }
      if (!mediaPath && idx < medias.length) {
        const sorted = [...medias].sort((a, b) =>
          a.name.localeCompare(b.name, undefined, { numeric: true }),
        );
        if (sorted[idx]) {
          mediaPath = sorted[idx].path;
          mediaType = detectMediaType(sorted[idx].name);
        }
      }

      return {
        id: idx + 1,
        targetSubsPath: t.path,
        nativeSubsPath: nativePath,
        mediaPath,
        mediaType,
      };
    });

    episodes = newEpisodes;
  }

  async function addSeriesTargetSubs() {
    try {
      const selected = await open({
        multiple: true,
        filters: [
          {
            name: t("flashcards.subtitleFiles"),
            extensions: ["srt", "ass", "ssa", "vtt"],
          },
        ],
      });
      if (selected && Array.isArray(selected) && selected.length > 0) {
        autoMatchFiles(
          selected as string[],
          episodes.map((e) => e.nativeSubsPath).filter(Boolean),
          episodes.map((e) => e.mediaPath).filter(Boolean),
        );

        // Infer language from first file if needed
        if (!noteTypeLanguage) {
          const inferred = inferLanguageFromPath(selected[0] as string);
          if (inferred) {
            noteTypeLanguage = inferred;
            localStorage.setItem(NOTE_TYPE_LANGUAGE_KEY, inferred);
          }
        }

        addLog(
          `${episodes.length} ${t("flashcards.seriesEpisodesAdded")}`,
          "target-subs",
        );
      }
    } catch (e) {
      error = `${t("flashcards.errorSelectingFile")}: ${e}`;
    }
  }

  async function addSeriesNativeSubs() {
    try {
      const selected = await open({
        multiple: true,
        filters: [
          {
            name: t("flashcards.subtitleFiles"),
            extensions: ["srt", "ass", "ssa", "vtt"],
          },
        ],
      });
      if (selected && Array.isArray(selected) && selected.length > 0) {
        autoMatchFiles(
          episodes.map((e) => e.targetSubsPath),
          selected as string[],
          episodes.map((e) => e.mediaPath).filter(Boolean),
        );
        addLog(
          `${(selected as string[]).length} ${t("flashcards.seriesNativeSubsAdded")}`,
          "native-subs",
        );
      }
    } catch (e) {
      error = `${t("flashcards.errorSelectingFile")}: ${e}`;
    }
  }

  async function addSeriesMedia() {
    try {
      const selected = await open({
        multiple: true,
        filters: [
          {
            name: t("flashcards.mediaFiles"),
            extensions: [...VIDEO_EXTENSIONS, ...AUDIO_EXTENSIONS],
          },
        ],
      });
      if (selected && Array.isArray(selected) && selected.length > 0) {
        autoMatchFiles(
          episodes.map((e) => e.targetSubsPath),
          episodes.map((e) => e.nativeSubsPath).filter(Boolean),
          selected as string[],
        );
        addLog(
          `${(selected as string[]).length} ${t("flashcards.seriesMediaAdded")}`,
          "media",
        );
      }
    } catch (e) {
      error = `${t("flashcards.errorSelectingFile")}: ${e}`;
    }
  }

  function removeEpisode(idx: number) {
    episodes = episodes
      .filter((_, i) => i !== idx)
      .map((e, i) => ({ ...e, id: i + 1 }));
  }

  function clearAllEpisodes() {
    episodes = [];
  }

  let hasMedia = $derived(mediaType !== "none");
  let hasVideo = $derived(mediaType === "video");
  let hasAudio = $derived(hasMedia);

  let useTimingsFrom = $state<"target" | "native">("target");
  let spanStart = $state("");
  let spanEnd = $state("");
  let timeShiftTarget = $state(0);
  let timeShiftNative = $state(0);

  let showSubtitleOptions = $state(false);
  let showContextLines = $state(false);
  let showFilters = $state(false);
  let hasAnyFiles = $derived(targetSubsPath !== "");
  let includeWords = $state("");
  let excludeWords = $state("");
  let excludeDuplicatesSubs1 = $state(false);
  let excludeDuplicatesSubs2 = $state(false);
  let minChars = $state<number | null>(null);
  let maxChars = $state<number | null>(null);
  let minDurationMs = $state<number | null>(null);
  let maxDurationMs = $state<number | null>(null);
  let excludeStyled = $state(false);
  let actorFilter = $state("");
  let onlyCjk = $state(false);
  let removeNoMatch = $state(false);

  let contextLeading = $state(0);
  let contextTrailing = $state(0);
  let contextMaxGap = $state(15.0);

  let combineSentences = $state(false);
  let continuationChars = $state(",、→");

  let generateAudio = $state(true);
  let audioBitrate = $state(128);
  let audioPadStart = $state(250);
  let audioPadEnd = $state(250);
  let normalizeAudio = $state(false);

  let generateSnapshots = $state(true);
  let snapshotWidth = $state(384);
  let snapshotHeight = $state(216);
  let cropBottom = $state(0);

  let generateVideoClips = $state(false);
  let videoCodec = $state("h264");
  let h264Preset = $state("medium");
  let videoBitrate = $state(800);
  let videoAudioBitrate = $state(128);
  let videoPadStart = $state(250);
  let videoPadEnd = $state(50);

  let exportFormat = $state<"tsv" | "apkg">("apkg");

  let systemCpuCount = $state(4);
  let cpuCores = $state(2); // will be set properly onMount
  let minCpuCores = $derived(2);
  let maxCpuCores = $derived(Math.max(2, systemCpuCount - 1));

  // CPU preset definitions (evenly spaced between min and max cores)
  let cpuPresets = $derived([
    { id: "eco", threads: minCpuCores },
    {
      id: "balanced",
      threads: minCpuCores + Math.ceil((maxCpuCores - minCpuCores) / 3),
    },
    {
      id: "performance",
      threads: minCpuCores + Math.ceil(((maxCpuCores - minCpuCores) * 2) / 3),
    },
    { id: "full", threads: maxCpuCores },
  ] as const);

  let activeCpuPreset = $derived(
    cpuPresets.find((p) => p.threads === cpuCores)?.id ?? null,
  );

  function setCpuPreset(presetId: string) {
    const preset = cpuPresets.find((p) => p.id === presetId);
    if (preset) cpuCores = preset.threads;
  }

  const PANEL_IDS = [
    "files",
    "subtitleOptions",
    "filters",
    "contextLines",
    "audioClips",
    "snapshots",
    "videoClips",
    "ankiFields",
    "exportFormat",
    "naming",
    "cpuCores",
    "actions",
    "progressResult",
    "logs",
  ] as const;

  type PanelId = (typeof PANEL_IDS)[number];

  interface ColumnLayout {
    col1: PanelId[];
    col2: PanelId[];
    col3: PanelId[];
  }

  const DEFAULT_LAYOUT: ColumnLayout = {
    col1: ["files", "subtitleOptions", "contextLines", "filters"],
    col2: ["naming", "audioClips", "snapshots", "videoClips", "ankiFields"],
    col3: ["exportFormat", "cpuCores", "actions", "progressResult", "logs"],
  };

  function loadLayout(): ColumnLayout {
    try {
      const saved = localStorage.getItem("vesta-flashcards-layout-v2");
      if (saved) {
        const parsed = JSON.parse(saved) as ColumnLayout;
        // Validate: all panel IDs must be present exactly once
        const all = [...parsed.col1, ...parsed.col2, ...parsed.col3];
        const valid =
          PANEL_IDS.every((id) => all.includes(id)) &&
          all.length === PANEL_IDS.length;
        if (valid) return parsed;
      }
    } catch {}
    return { ...DEFAULT_LAYOUT };
  }

  function saveLayout(layout: ColumnLayout) {
    localStorage.setItem("vesta-flashcards-layout-v2", JSON.stringify(layout));
  }

  let panelLayout = $state<ColumnLayout>(loadLayout());

  // Column count (1, 2, or 3)
  const COLUMN_COUNT_KEY = "vesta-flashcards-column-count";
  function loadColumnCount(): 1 | 2 | 3 {
    try {
      const saved = localStorage.getItem(COLUMN_COUNT_KEY);
      if (saved) {
        const n = parseInt(saved, 10);
        if (n === 1 || n === 2 || n === 3) return n;
      }
    } catch {}
    return 3;
  }
  let columnCount = $state<1 | 2 | 3>(loadColumnCount());

  function setColumnCount(count: 1 | 2 | 3) {
    columnCount = count;
    localStorage.setItem(COLUMN_COUNT_KEY, String(count));
    // Redistribute panels: merge hidden columns into the last visible one
    if (count === 1) {
      panelLayout = {
        col1: [...panelLayout.col1, ...panelLayout.col2, ...panelLayout.col3],
        col2: [],
        col3: [],
      };
    } else if (count === 2) {
      panelLayout = {
        col1: [...panelLayout.col1],
        col2: [...panelLayout.col2, ...panelLayout.col3],
        col3: [],
      };
    }
    // For count === 3, if col2/col3 are empty, redistribute from col1
    if (count === 3) {
      const all = [
        ...panelLayout.col1,
        ...panelLayout.col2,
        ...panelLayout.col3,
      ];
      if (panelLayout.col2.length === 0 && panelLayout.col3.length === 0) {
        const third = Math.ceil(all.length / 3);
        const twoThirds = Math.ceil((all.length * 2) / 3);
        panelLayout = {
          col1: all.slice(0, third),
          col2: all.slice(third, twoThirds),
          col3: all.slice(twoThirds),
        };
      } else if (panelLayout.col3.length === 0) {
        // Coming from 2 columns: split col2
        const col2All = [...panelLayout.col2];
        const half = Math.ceil(col2All.length / 2);
        panelLayout = {
          col1: [...panelLayout.col1],
          col2: col2All.slice(0, half),
          col3: col2All.slice(half),
        };
      }
    }
    saveLayout(panelLayout);
  }

  // Computed column grid class
  let gridColClass = $derived(
    columnCount === 1
      ? "grid-cols-1"
      : columnCount === 2
        ? "grid-cols-2"
        : "grid-cols-3",
  );

  let draggedPanel = $state<PanelId | null>(null);
  let dragOverCol = $state<"col1" | "col2" | "col3" | null>(null);
  let dragOverIdx = $state<number | null>(null);

  function onDragStart(e: DragEvent, panelId: PanelId) {
    // Don't start drag if the user is interacting with a range input (slider)
    const target = e.target as HTMLElement;
    if (
      target?.tagName === "INPUT" &&
      (target as HTMLInputElement).type === "range"
    ) {
      e.preventDefault();
      return;
    }
    draggedPanel = panelId;
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", panelId);
    }
  }

  function onDragOver(
    e: DragEvent,
    col: "col1" | "col2" | "col3",
    idx: number,
  ) {
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
    dragOverCol = col;
    dragOverIdx = idx;
  }

  function onDragOverColumn(e: DragEvent, col: "col1" | "col2" | "col3") {
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
    dragOverCol = col;
    // If dragging over the column whitespace, set idx to end
    if (dragOverIdx === null) {
      dragOverIdx = panelLayout[col].length;
    }
  }

  function onDrop(col: "col1" | "col2" | "col3", idx: number) {
    if (!draggedPanel) return;

    const newLayout = { ...panelLayout };

    for (const c of ["col1", "col2", "col3"] as const) {
      const i = newLayout[c].indexOf(draggedPanel);
      if (i !== -1) {
        newLayout[c] = [...newLayout[c]];
        newLayout[c].splice(i, 1);
        // Adjust index if we're moving within the same column and removing from before
        if (c === col && i < idx) {
          idx--;
        }
        break;
      }
    }

    newLayout[col] = [...newLayout[col]];
    newLayout[col].splice(idx, 0, draggedPanel);

    panelLayout = newLayout;
    saveLayout(panelLayout);
    draggedPanel = null;
    dragOverCol = null;
    dragOverIdx = null;
  }

  function onDropColumn(col: "col1" | "col2" | "col3") {
    onDrop(col, panelLayout[col].length);
  }

  function onDragEnd() {
    draggedPanel = null;
    dragOverCol = null;
    dragOverIdx = null;
  }

  function resetLayout() {
    panelLayout = {
      ...DEFAULT_LAYOUT,
      col1: [...DEFAULT_LAYOUT.col1],
      col2: [...DEFAULT_LAYOUT.col2],
      col3: [...DEFAULT_LAYOUT.col3],
    };
    saveLayout(panelLayout);
    columnCount = 3;
    localStorage.setItem(COLUMN_COUNT_KEY, "3");
  }

  let helpSection = $state<string | null>(null);

  let noteTypeLanguage = $state("");
  let noteTypeName = $state("");
  let includeTag = $state(true);

  // Auto-update noteTypeName when language changes
  $effect(() => {
    if (noteTypeLanguage) {
      const lang = languages.find((l) => l.code === noteTypeLanguage);
      if (lang) {
        noteTypeName = `${lang.nameEn}_vesta`;
      }
    } else {
      noteTypeName = "";
    }
  });
  let includeSequence = $state(true);
  let includeAudioField = $state(true);
  let includeSnapshotField = $state(true);
  let includeVideoField = $state(true);
  let includeSubs1Field = $state(true);
  let includeSubs2Field = $state(true);

  let deckName = $state("");
  let firstEpisode = $state(1);

  let isProcessing = $state(false);
  let progress = $state(0);
  let progressMessage = $state("");
  let progressStage = $state("");

  interface LogEntry {
    id: number;
    timestamp: string;
    message: string;
    type:
      | "info"
      | "success"
      | "warning"
      | "error"
      | "target-subs"
      | "native-subs"
      | "media"
      | "output"
      | "progress";
    details?: string;
  }
  let logIdCounter = 0;
  let logs = $state<LogEntry[]>([]);
  let error = $state<string | null>(null);
  let result = $state<{
    success: boolean;
    cardsGenerated: number;
    audioClips: number;
    snapshots: number;
    videoClips: number;
    tsvPath: string | null;
    apkgPath: string | null;
  } | null>(null);

  let targetSubsInfo = $state<{
    count: number;
    first_text: string;
    format: string;
    actors: string[];
    duration_ms: number;
  } | null>(null);
  let nativeSubsInfo = $state<{
    count: number;
    first_text: string;
    format: string;
  } | null>(null);
  let ffmpegAvailable = $state<boolean | null>(null);

  let showPreview = $state(false);
  let previewLines = $state<any[]>([]);
  let previewLoading = $state(false);
  let previewFilter = $state<"all" | "active" | "inactive">("all");
  let previewSearch = $state("");
  let previewPage = $state(1);
  let expandedPathField = $state<string | null>(null);
  const previewPerPage = 50;

  let unlisten: (() => void) | null = null;
  let canRunFlashcards = $derived(
    seriesMode
      ? Boolean(
          episodes.length > 0 && outputDir && deckName && noteTypeLanguage,
        )
      : Boolean(targetSubsPath && outputDir && deckName && noteTypeLanguage),
  );

  function inferLanguageFromPath(filePath: string): string | null {
    const filename = filePath.split("/").pop()?.toLowerCase() || "";
    const base = filename.replace(/\.[^/.]+$/, "");
    const tokens = base.split(/[^a-z0-9-]+/).filter(Boolean);
    const tokenSet = new Set(tokens);

    for (const lang of languages) {
      const code = lang.code.toLowerCase();
      if (code.includes("-") && tokenSet.has(code)) return lang.code;
    }

    for (const lang of languages) {
      const code = lang.code.toLowerCase();
      if (code.length !== 2) continue;
      const index = tokens.lastIndexOf(code);
      if (index !== -1 && index >= tokens.length - 2) return lang.code;
    }

    const normalized = ` ${base.replace(/[^a-z0-9]+/g, " ")} `;
    for (const lang of languages) {
      const languageName = lang.nameEn
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, " ")
        .trim();
      if (languageName && normalized.includes(` ${languageName} `)) {
        return lang.code;
      }
    }

    return null;
  }

  onMount(async () => {
    try {
      const savedNoteTypeLanguage = localStorage.getItem(
        NOTE_TYPE_LANGUAGE_KEY,
      );
      if (
        savedNoteTypeLanguage &&
        languages.some((l) => l.code === savedNoteTypeLanguage)
      ) {
        noteTypeLanguage = savedNoteTypeLanguage;
      }
    } catch {}

    try {
      const savedDir = localStorage.getItem(OUTPUT_DIR_KEY);
      if (savedDir) {
        const exists = await invoke<boolean>("flashcard_check_dir_exists", {
          path: savedDir,
        });
        if (exists) {
          outputDir = savedDir;
        } else {
          localStorage.removeItem(OUTPUT_DIR_KEY);
        }
      }
    } catch {}

    try {
      ffmpegAvailable = await invoke<boolean>("flashcard_check_deps");
    } catch {
      ffmpegAvailable = false;
    }

    try {
      systemCpuCount = await invoke<number>("flashcard_get_cpu_count");
      const startupMaxCores = Math.max(2, systemCpuCount - 1);
      cpuCores = 2 + Math.ceil(((startupMaxCores - 2) * 2) / 3);
    } catch {
      systemCpuCount = 4;
      cpuCores = 3;
    }

    unlisten = await listen<{
      stage: string;
      message: string;
      current: number;
      total: number;
      percentage: number;
      params: Record<string, string>;
    }>("flashcard-progress", (event) => {
      const p = event.payload;
      progress = Math.round(p.percentage);
      // Translate the i18n key with params from the backend
      const translated = t(p.message, p.params || {});
      progressMessage = translated;
      progressStage = p.stage;
      if (p.stage !== "done") {
        addLog(translated, "progress", undefined, p.message);
      }
    });
  });

  onDestroy(() => {
    if (unlisten) unlisten();
  });

  // Track the i18n key of the last progress log so sequential updates
  // (e.g. "Extracting media… 1/100", "2/100", …) replace the previous
  // entry instead of appending thousands of lines.
  let lastProgressKey: string | null = null;

  function addLog(
    message: string,
    type: LogEntry["type"] = "info",
    details?: string,
    progressKey?: string,
  ) {
    const timestamp = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    // For sequential progress messages with the same key, update in-place
    if (
      type === "progress" &&
      progressKey &&
      progressKey === lastProgressKey &&
      logs.length > 0
    ) {
      const last = logs[logs.length - 1];
      if (last.type === "progress") {
        const updated = { ...last, timestamp, message };
        logs = [...logs.slice(0, -1), updated];
        return;
      }
    }

    if (type === "progress" && progressKey) {
      lastProgressKey = progressKey;
    } else if (type !== "progress") {
      lastProgressKey = null;
    }

    logs = [...logs, { id: ++logIdCounter, timestamp, message, type, details }];
  }

  function parseTimeToMs(time: string): number | null {
    if (!time || !time.trim()) return null;
    const parts = time.split(":").map(Number);
    if (parts.length === 3 && parts.every((p) => !isNaN(p))) {
      return (parts[0] * 3600 + parts[1] * 60 + parts[2]) * 1000;
    }
    return null;
  }

  function buildConfig() {
    return {
      target_subs_path: targetSubsPath,
      native_subs_path: nativeSubsPath || null,
      video_path: hasVideo ? mediaPath : null,
      audio_path: hasAudio && !hasVideo ? mediaPath : null,
      output_dir: outputDir,
      use_timings_from: useTimingsFrom,
      span_start_ms: parseTimeToMs(spanStart),
      span_end_ms: parseTimeToMs(spanEnd),
      time_shift_target_ms: timeShiftTarget,
      time_shift_native_ms: timeShiftNative,
      filters: {
        include_words: includeWords || null,
        exclude_words: excludeWords || null,
        exclude_duplicates_subs1: excludeDuplicatesSubs1,
        exclude_duplicates_subs2: excludeDuplicatesSubs2,
        min_chars: minChars,
        max_chars: maxChars,
        min_duration_ms: minDurationMs,
        max_duration_ms: maxDurationMs,
        exclude_styled: excludeStyled,
        actor_filter: actorFilter || null,
        only_cjk: onlyCjk,
        remove_no_match: removeNoMatch,
      },
      context: {
        leading: contextLeading,
        trailing: contextTrailing,
        max_gap_seconds: contextMaxGap,
      },
      combine_sentences: combineSentences,
      continuation_chars: continuationChars,
      generate_audio: generateAudio,
      audio_bitrate: audioBitrate,
      normalize_audio: normalizeAudio,
      audio_pad_start_ms: audioPadStart,
      audio_pad_end_ms: audioPadEnd,
      generate_snapshots: generateSnapshots,
      snapshot_width: snapshotWidth,
      snapshot_height: snapshotHeight,
      crop_bottom: cropBottom,
      generate_video_clips: generateVideoClips,
      video_codec: videoCodec,
      h264_preset: h264Preset,
      video_bitrate: videoBitrate,
      video_audio_bitrate: videoAudioBitrate,
      video_pad_start_ms: videoPadStart,
      video_pad_end_ms: videoPadEnd,
      deck_name: deckName,
      episode_number: 1,
      export_format: exportFormat,
      note_type_name: noteTypeName,
      output_fields: {
        include_tag: includeTag,
        include_sequence: includeSequence,
        include_audio: includeAudioField,
        include_snapshot: includeSnapshotField,
        include_video: includeVideoField,
        include_subs1: includeSubs1Field,
        include_subs2: includeSubs2Field,
      },
      cpu_cores: cpuCores,
    };
  }

  async function selectTargetSubs() {
    try {
      const selected = await open({
        multiple: false,
        filters: [
          {
            name: t("flashcards.subtitleFiles"),
            extensions: ["srt", "ass", "ssa", "vtt"],
          },
        ],
      });
      if (selected) {
        targetSubsPath = selected as string;
        const filename = targetSubsPath.split("/").pop() || "";

        if (!noteTypeLanguage) {
          const inferredLanguage = inferLanguageFromPath(targetSubsPath);
          if (inferredLanguage) {
            noteTypeLanguage = inferredLanguage;
            localStorage.setItem(NOTE_TYPE_LANGUAGE_KEY, inferredLanguage);
          }
        }

        try {
          const info = await invoke<any>("flashcard_load_subs", {
            path: targetSubsPath,
          });
          targetSubsInfo = info;
          addLog(
            `${info.count} ${t("flashcards.subtitlesLoaded")} (${info.format.toUpperCase()})`,
            "target-subs",
            filename,
          );

          if (!deckName) {
            deckName = filename.replace(/\.[^/.]+$/, "").replace(/_/g, " ");
          }
        } catch (e) {
          error = `Error parsing subtitles: ${e}`;
        }
      }
    } catch (e) {
      error = `${t("flashcards.errorSelectingFile")}: ${e}`;
    }
  }

  async function selectNativeSubs() {
    try {
      const selected = await open({
        multiple: false,
        filters: [
          {
            name: t("flashcards.subtitleFiles"),
            extensions: ["srt", "ass", "ssa", "vtt"],
          },
        ],
      });
      if (selected) {
        nativeSubsPath = selected as string;
        const filename = nativeSubsPath.split("/").pop() || "";

        if (!noteTypeLanguage) {
          const inferredLanguage = inferLanguageFromPath(nativeSubsPath);
          if (inferredLanguage) {
            noteTypeLanguage = inferredLanguage;
            localStorage.setItem(NOTE_TYPE_LANGUAGE_KEY, inferredLanguage);
          }
        }

        try {
          const info = await invoke<any>("flashcard_load_subs", {
            path: nativeSubsPath,
          });
          nativeSubsInfo = info;
          addLog(
            `${info.count} ${t("flashcards.subtitlesLoaded")} (${info.format.toUpperCase()})`,
            "native-subs",
            filename,
          );
        } catch (e) {
          error = `Error parsing native subtitles: ${e}`;
        }
      }
    } catch (e) {
      error = `${t("flashcards.errorSelectingFile")}: ${e}`;
    }
  }

  const VIDEO_EXTENSIONS = [
    "mp4",
    "mkv",
    "avi",
    "webm",
    "mov",
    "flv",
    "ogm",
    "vob",
  ];
  const AUDIO_EXTENSIONS = ["mp3", "aac", "flac", "m4a", "ogg", "wav", "wma"];

  function detectMediaType(filename: string): "video" | "audio" | "none" {
    const ext = filename.split(".").pop()?.toLowerCase() || "";
    if (VIDEO_EXTENSIONS.includes(ext)) return "video";
    if (AUDIO_EXTENSIONS.includes(ext)) return "audio";
    return "none";
  }

  async function selectMedia() {
    try {
      const selected = await open({
        multiple: false,
        filters: [
          {
            name: t("flashcards.mediaFiles"),
            extensions: [...VIDEO_EXTENSIONS, ...AUDIO_EXTENSIONS],
          },
        ],
      });
      if (selected) {
        mediaPath = selected as string;
        const filename = mediaPath.split("/").pop() || "";
        mediaType = detectMediaType(filename);

        if (mediaType === "video") {
          generateAudio = true;
          generateSnapshots = true;
          addLog(`${t("flashcards.mediaTypeVideo")}`, "media", filename);
        } else if (mediaType === "audio") {
          generateAudio = true;
          generateSnapshots = false;
          generateVideoClips = false;
          addLog(`${t("flashcards.mediaTypeAudio")}`, "media", filename);
        }
      }
    } catch (e) {
      error = `${t("flashcards.errorSelectingFile")}: ${e}`;
    }
  }

  async function selectOutputDir() {
    try {
      const selected = await open({ directory: true });
      if (selected) {
        outputDir = selected as string;
        localStorage.setItem(OUTPUT_DIR_KEY, outputDir);
        addLog(`${t("flashcards.outputDirSet")}`, "output", outputDir);
      }
    } catch (e) {
      error = `${t("flashcards.errorSelectingDir")}: ${e}`;
    }
  }

  async function loadPreview() {
    if (!canRunFlashcards) {
      error = t("flashcards.requiredFieldsMissing");
      return;
    }

    previewLoading = true;
    showPreview = true;
    error = null;

    try {
      const config = buildConfig();
      previewLines = await invoke<any[]>("flashcard_preview", { config });
      addLog(
        `Preview: ${previewLines.length} total, ${previewLines.filter((l: any) => l.active).length} active`,
        "info",
      );
    } catch (e) {
      error = `Preview error: ${e}`;
    } finally {
      previewLoading = false;
    }
  }

  let filteredPreview = $derived(
    previewLines.filter((line: any) => {
      const matchFilter =
        previewFilter === "all" ||
        (previewFilter === "active" && line.active) ||
        (previewFilter === "inactive" && !line.active);
      const matchSearch =
        !previewSearch ||
        line.subs1_text.toLowerCase().includes(previewSearch.toLowerCase()) ||
        (line.subs2_text &&
          line.subs2_text.toLowerCase().includes(previewSearch.toLowerCase()));
      return matchFilter && matchSearch;
    }),
  );

  let previewTotalPages = $derived(
    Math.max(1, Math.ceil(filteredPreview.length / previewPerPage)),
  );
  let previewPaged = $derived(
    filteredPreview.slice(
      (previewPage - 1) * previewPerPage,
      previewPage * previewPerPage,
    ),
  );

  $effect(() => {
    // reactive dependencies: previewFilter, previewSearch
    void previewFilter;
    void previewSearch;
    previewPage = 1;
  });

  async function startSeriesGeneration() {
    error = null;
    result = null;
    progress = 0;
    isProcessing = true;
    seriesTotalEpisodes = episodes.length;
    seriesCurrentEpisode = 0;

    addLog(
      `${t("flashcards.starting")}... (${t("flashcards.modeSeries")}: ${episodes.length} ${t("flashcards.seriesEpisodes")})`,
      "info",
    );
    addLog(`${t("flashcards.deckName")}: ${deckName}`, "info");

    const startTime = Date.now();
    let totalCards = 0;
    let totalAudio = 0;
    let totalSnapshots = 0;
    let totalVideoClips = 0;
    const apkgPaths: string[] = [];
    let hadError = false;

    try {
      for (let i = 0; i < episodes.length; i++) {
        seriesCurrentEpisode = i + 1;
        const ep = episodes[i];
        const epNum = i + 1;

        addLog(
          `${t("flashcards.processingEpisode", { current: String(epNum), total: String(episodes.length) })}`,
          "info",
        );

        // Determine media availability for this episode
        const epMediaType = ep.mediaType;
        const epHasVideo = epMediaType === "video";
        const epHasMedia = epMediaType !== "none";

        const epConfig = {
          target_subs_path: ep.targetSubsPath,
          native_subs_path: ep.nativeSubsPath || null,
          video_path: epHasVideo ? ep.mediaPath : null,
          audio_path: epHasMedia && !epHasVideo ? ep.mediaPath : null,
          output_dir: outputDir,
          use_timings_from: useTimingsFrom,
          span_start_ms: parseTimeToMs(spanStart),
          span_end_ms: parseTimeToMs(spanEnd),
          time_shift_target_ms: timeShiftTarget,
          time_shift_native_ms: timeShiftNative,
          filters: {
            include_words: includeWords || null,
            exclude_words: excludeWords || null,
            exclude_duplicates_subs1: excludeDuplicatesSubs1,
            exclude_duplicates_subs2: excludeDuplicatesSubs2,
            min_chars: minChars,
            max_chars: maxChars,
            min_duration_ms: minDurationMs,
            max_duration_ms: maxDurationMs,
            exclude_styled: excludeStyled,
            actor_filter: actorFilter || null,
            only_cjk: onlyCjk,
            remove_no_match: removeNoMatch,
          },
          context: {
            leading: contextLeading,
            trailing: contextTrailing,
            max_gap_seconds: contextMaxGap,
          },
          combine_sentences: combineSentences,
          continuation_chars: continuationChars,
          generate_audio: ep.mediaPath ? generateAudio : false,
          audio_bitrate: audioBitrate,
          normalize_audio: normalizeAudio,
          audio_pad_start_ms: audioPadStart,
          audio_pad_end_ms: audioPadEnd,
          generate_snapshots: epHasVideo ? generateSnapshots : false,
          snapshot_width: snapshotWidth,
          snapshot_height: snapshotHeight,
          crop_bottom: cropBottom,
          generate_video_clips: epHasVideo ? generateVideoClips : false,
          video_codec: videoCodec,
          h264_preset: h264Preset,
          video_bitrate: videoBitrate,
          video_audio_bitrate: videoAudioBitrate,
          video_pad_start_ms: videoPadStart,
          video_pad_end_ms: videoPadEnd,
          deck_name: deckName,
          episode_number: epNum,
          export_format: exportFormat,
          note_type_name: noteTypeName,
          output_fields: {
            include_tag: includeTag,
            include_sequence: includeSequence,
            include_audio: includeAudioField,
            include_snapshot: includeSnapshotField,
            include_video: includeVideoField,
            include_subs1: includeSubs1Field,
            include_subs2: includeSubs2Field,
          },
          cpu_cores: cpuCores,
        };

        try {
          const res = await invoke<any>("flashcard_generate", {
            config: epConfig,
          });
          if (res.success) {
            totalCards += res.cards_generated;
            totalAudio += res.audio_clips;
            totalSnapshots += res.snapshots;
            totalVideoClips += res.video_clips;
            if (res.apkg_path) apkgPaths.push(res.apkg_path);
            addLog(
              `✓ Ep ${epNum}: ${res.cards_generated} ${t("flashcards.cardsGenerated")}`,
              "success",
            );
          } else {
            addLog(`⚠ Ep ${epNum}: ${res.message}`, "warning");
          }
        } catch (e) {
          addLog(`✗ Ep ${epNum}: ${e}`, "error");
          hadError = true;
        }
      }

      // Merge APKGs if single mode selected
      if (
        seriesOutputMode === "single" &&
        apkgPaths.length > 1 &&
        exportFormat === "apkg"
      ) {
        addLog(t("flashcards.mergingApkg"), "info");
        try {
          const mergedPath = await invoke<string>("flashcard_merge_apkg", {
            apkgPaths,
            outputPath: `${outputDir}/${deckName.replace(/[^a-zA-Z0-9_\-\. ]/g, "_")}.apkg`,
          });
          addLog(`APKG: ${mergedPath}`, "success");
        } catch (e) {
          addLog(`${t("flashcards.mergeFailed")}: ${e}`, "error");
          hadError = true;
        }
      }

      result = {
        success: !hadError,
        cardsGenerated: totalCards,
        audioClips: totalAudio,
        snapshots: totalSnapshots,
        videoClips: totalVideoClips,
        tsvPath: null,
        apkgPath: apkgPaths.length > 0 ? apkgPaths[apkgPaths.length - 1] : null,
      };

      addLog(
        `${t("flashcards.seriesComplete", { total: String(episodes.length) })}`,
        "success",
      );
    } catch (e) {
      error = `${t("flashcards.errorGenerating")}: ${e}`;
      addLog(`${error}`, "error");
    } finally {
      isProcessing = false;
      seriesCurrentEpisode = 0;
      seriesTotalEpisodes = 0;
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const hh = String(Math.floor(elapsed / 3600)).padStart(2, "0");
      const mm = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
      const ss = String(elapsed % 60).padStart(2, "0");
      addLog(`⏱ ${hh}:${mm}:${ss}`, "info");
    }
  }

  async function startGeneration() {
    if (!canRunFlashcards) {
      error = t("flashcards.requiredFieldsMissing");
      return;
    }

    if (seriesMode) {
      await startSeriesGeneration();
      return;
    }

    error = null;
    result = null;
    progress = 0;
    isProcessing = true;
    addLog(`${t("flashcards.starting")}...`, "info");
    addLog(`${t("flashcards.deckName")}: ${deckName}`, "info");

    const startTime = Date.now();

    try {
      const config = buildConfig();
      const res = await invoke<any>("flashcard_generate", { config });
      result = {
        success: res.success,
        cardsGenerated: res.cards_generated,
        audioClips: res.audio_clips,
        snapshots: res.snapshots,
        videoClips: res.video_clips,
        tsvPath: res.tsv_path,
        apkgPath: res.apkg_path,
      };

      if (res.success) {
        addLog(
          `${res.cards_generated} ${t("flashcards.cardsGenerated")}`,
          "success",
        );
        if (res.tsv_path) {
          addLog(`TSV: ${res.tsv_path}`, "success");
        }
        if (res.apkg_path) {
          addLog(`APKG: ${res.apkg_path}`, "success");
        }
      } else {
        addLog(res.message, "warning");
      }
    } catch (e) {
      error = `${t("flashcards.errorGenerating")}: ${e}`;
      addLog(`${error}`, "error");
    } finally {
      isProcessing = false;
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const hh = String(Math.floor(elapsed / 3600)).padStart(2, "0");
      const mm = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
      const ss = String(elapsed % 60).padStart(2, "0");
      addLog(`⏱ ${hh}:${mm}:${ss}`, "info");
    }
  }

  async function cancelGeneration() {
    try {
      await invoke("flashcard_cancel");
      isProcessing = false;
      progress = 0;
      progressMessage = "";
      addLog(`${t("flashcards.cancelled")}`, "warning");
    } catch (e) {
      addLog(`Error cancelling: ${e}`, "error");
    }
  }

  function clearLogs() {
    logs = [];
    lastProgressKey = null;
  }

  function resetGeneration() {
    result = null;
    error = null;
    progress = 0;
    progressMessage = "";
    progressStage = "";
    logs = [];
    logIdCounter = 0;
    lastProgressKey = null;
  }

  function logStyle(type: LogEntry["type"]): {
    bg: string;
    border: string;
    text: string;
    icon: string;
  } {
    switch (type) {
      case "target-subs":
        return {
          bg: "bg-emerald-500/10",
          border: "border-emerald-500/30",
          text: "text-emerald-300",
          icon: "📄",
        };
      case "native-subs":
        return {
          bg: "bg-blue-500/10",
          border: "border-blue-500/30",
          text: "text-blue-300",
          icon: "📄",
        };
      case "media":
        return {
          bg: "bg-purple-500/10",
          border: "border-purple-500/30",
          text: "text-purple-300",
          icon: "🎬",
        };
      case "output":
        return {
          bg: "bg-amber-500/10",
          border: "border-amber-500/30",
          text: "text-amber-300",
          icon: "📁",
        };
      case "success":
        return {
          bg: "bg-green-500/10",
          border: "border-green-500/30",
          text: "text-green-300",
          icon: "✅",
        };
      case "warning":
        return {
          bg: "bg-amber-500/10",
          border: "border-amber-500/30",
          text: "text-amber-300",
          icon: "⚠️",
        };
      case "error":
        return {
          bg: "bg-red-500/10",
          border: "border-red-500/30",
          text: "text-red-300",
          icon: "❌",
        };
      case "progress":
        return {
          bg: "bg-gray-500/5",
          border: "border-gray-700/30",
          text: "text-gray-400",
          icon: "⚙️",
        };
      default:
        return {
          bg: "bg-gray-500/5",
          border: "border-gray-700/30",
          text: "text-gray-400",
          icon: "ℹ️",
        };
    }
  }
</script>

<div
  class="h-full flex flex-col p-6 overflow-hidden bg-gradient-to-br from-gray-900 via-gray-900 to-gray-950"
>
  {#if ffmpegAvailable === false}
    <div
      class="mb-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-center gap-3"
    >
      <svg
        class="w-5 h-5 text-amber-400 flex-shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
        />
      </svg>
      <p class="text-amber-300 text-sm">
        {t("flashcards.ffmpegMissing")}
      </p>
    </div>
  {/if}

  {#if showPreview}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      onclick={() => (showPreview = false)}
      onkeydown={(e) => {
        if (e.key === "Escape") showPreview = false;
      }}
    >
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-5xl max-h-[85vh] flex flex-col"
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => e.stopPropagation()}
      >
        <div
          class="flex items-center justify-between p-4 border-b border-gray-700"
        >
          <div class="flex items-center gap-3">
            <h2 class="text-lg font-bold text-emerald-400">
              {t("flashcards.preview")}
            </h2>
          </div>
          <div class="flex items-center gap-3">
            <div class="relative">
              <svg
                class="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                type="text"
                bind:value={previewSearch}
                class="input-modern text-xs w-48 pl-8"
                placeholder={t("flashcards.previewSearch")}
                style="text-indent: 0;"
              />
            </div>
            <button
              onclick={() => (showPreview = false)}
              class="text-gray-400 hover:text-white text-xl leading-none p-1"
            >
              ✕
            </button>
          </div>
        </div>

        <div
          class="px-4 py-2 border-b border-gray-700 flex items-center justify-between"
        >
          <div class="flex items-center gap-2">
            <div class="flex rounded-lg overflow-hidden border border-gray-700">
              {#each [["all", t("flashcards.previewAll"), "All subtitle lines"], ["active", t("flashcards.previewActive"), "Lines that will become flashcards"], ["inactive", t("flashcards.previewInactive"), "Lines excluded by your filters"]] as [val, label, tooltip]}
                <button
                  class="px-3 py-1 text-xs font-medium transition-colors {previewFilter ===
                  val
                    ? 'bg-emerald-500/20 text-emerald-300'
                    : 'text-gray-400 hover:bg-gray-800'}"
                  onclick={() => (previewFilter = val as any)}
                  title={tooltip}
                >
                  {label}
                </button>
              {/each}
            </div>
            <span class="text-xs text-gray-500">
              {filteredPreview.length}
              {t("flashcards.linesShown")}
            </span>
          </div>
          {#if previewTotalPages > 1}
            <div class="flex items-center gap-1">
              <button
                disabled={previewPage <= 1}
                onclick={() => (previewPage = 1)}
                class="px-2 py-1 text-xs rounded text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
                >«</button
              >
              <button
                disabled={previewPage <= 1}
                onclick={() => previewPage--}
                class="px-2 py-1 text-xs rounded text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
                >‹</button
              >
              <span class="text-xs text-gray-400 px-2">
                {previewPage} / {previewTotalPages}
              </span>
              <button
                disabled={previewPage >= previewTotalPages}
                onclick={() => previewPage++}
                class="px-2 py-1 text-xs rounded text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
                >›</button
              >
              <button
                disabled={previewPage >= previewTotalPages}
                onclick={() => (previewPage = previewTotalPages)}
                class="px-2 py-1 text-xs rounded text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
                >»</button
              >
            </div>
          {/if}
        </div>

        <div class="flex-1 overflow-y-auto p-2">
          {#if previewLoading}
            <div class="flex items-center justify-center h-32">
              <div
                class="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full"
              ></div>
            </div>
          {:else}
            <table class="w-full text-xs">
              <thead class="sticky top-0 z-10">
                <tr class="text-gray-400 bg-gray-800 shadow-sm">
                  <th class="p-2 text-left w-12">#</th>
                  <th class="p-2 text-left w-20"
                    >{t("flashcards.previewTime")}</th
                  >
                  <th class="p-2 text-left">{t("flashcards.subs1")}</th>
                  {#if nativeSubsPath}
                    <th class="p-2 text-left">{t("flashcards.subs2")}</th>
                  {/if}
                  <th class="p-2 text-center w-16"
                    >{t("flashcards.previewStatus")}</th
                  >
                </tr>
              </thead>
              <tbody>
                {#each previewPaged as line, i}
                  <tr
                    class="border-t border-gray-800 {line.active
                      ? 'bg-emerald-500/5 hover:bg-emerald-500/10'
                      : 'bg-red-500/5 opacity-60 hover:bg-red-500/10'}"
                  >
                    <td class="p-2 text-gray-500 font-mono">{line.index + 1}</td
                    >
                    <td class="p-2 text-gray-400 font-mono">
                      {Math.floor(line.start_ms / 60000)}:{String(
                        Math.floor((line.start_ms % 60000) / 1000),
                      ).padStart(2, "0")}
                    </td>
                    <td class="p-2">
                      <span
                        contenteditable="true"
                        class="text-gray-200 outline-none focus:bg-gray-800/50 focus:ring-1 focus:ring-emerald-500/30 rounded px-1 -mx-1 block"
                        onblur={(e) => {
                          line.subs1_text =
                            (e.target as HTMLElement).textContent || "";
                        }}>{line.subs1_text}</span
                      >
                    </td>
                    {#if nativeSubsPath}
                      <td class="p-2">
                        <span
                          contenteditable="true"
                          class="text-gray-300 outline-none focus:bg-gray-800/50 focus:ring-1 focus:ring-emerald-500/30 rounded px-1 -mx-1 block"
                          onblur={(e) => {
                            line.subs2_text =
                              (e.target as HTMLElement).textContent || "";
                          }}>{line.subs2_text || "—"}</span
                        >
                      </td>
                    {/if}
                    <td class="p-2 text-center">
                      {#if line.active}
                        <span
                          class="inline-block w-2 h-2 bg-emerald-400 rounded-full"
                        ></span>
                      {:else}
                        <span
                          class="inline-block w-2 h-2 bg-red-400 rounded-full"
                        ></span>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>
      </div>
    </div>
  {/if}

  {#snippet panelContent(panelId: PanelId)}
    {#if panelId === "files"}
      <div class="glass-card p-4">
        <h3
          class="text-sm font-semibold mb-3 flex items-center gap-2 text-emerald-400"
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
              d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
            />
          </svg>
          {t("flashcards.files")}
          <button
            type="button"
            onclick={() => (helpSection = "files")}
            title="Info"
            class="ml-auto text-gray-500 hover:text-emerald-300 transition-colors"
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
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
        </h3>

        {#if !seriesMode}
          <div class="space-y-2.5">
            <div>
              <span class="block text-xs text-gray-400 mb-1">
                {t("flashcards.targetLangSubs")}
                <span class="text-red-400">*</span>
              </span>
              <span class="block text-[10px] text-gray-500 mb-1"
                >{t("flashcards.targetLangSubsDesc")}</span
              >
              <div class="flex gap-2">
                <button
                  type="button"
                  onclick={() => {
                    if (targetSubsPath) expandedPathField = "targetSubs";
                  }}
                  class="input-modern flex-1 text-xs text-left transition-colors truncate {targetSubsPath
                    ? 'cursor-pointer hover:bg-white/10'
                    : 'cursor-default hover:bg-transparent'}"
                  style="direction: rtl; text-align: left;"
                  title={targetSubsPath || t("flashcards.selectFile")}
                >
                  <span
                    class={targetSubsPath ? "text-white" : "text-gray-500"}
                    style="unicode-bidi: plaintext;"
                  >
                    {targetSubsPath || t("flashcards.selectFile")}
                  </span>
                </button>
                <button
                  onclick={selectTargetSubs}
                  class="btn-primary py-1.5 px-3 text-xs flex-shrink-0 flex items-center gap-1"
                >
                  <svg
                    class="w-3.5 h-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    ><path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                    /></svg
                  >
                  {t("flashcards.browse")}
                </button>
              </div>
            </div>

            <div>
              <span class="block text-xs text-gray-400 mb-1">
                {t("flashcards.outputDir")} <span class="text-red-400">*</span>
              </span>
              <div class="flex gap-2">
                <button
                  type="button"
                  onclick={() => {
                    if (outputDir) expandedPathField = "output";
                  }}
                  class="input-modern flex-1 text-xs text-left transition-colors truncate {outputDir
                    ? 'cursor-pointer hover:bg-white/10'
                    : 'cursor-default hover:bg-transparent'}"
                  style="direction: rtl; text-align: left;"
                  title={outputDir || t("flashcards.selectDir")}
                >
                  <span
                    class={outputDir ? "text-white" : "text-gray-500"}
                    style="unicode-bidi: plaintext;"
                  >
                    {outputDir || t("flashcards.selectDir")}
                  </span>
                </button>
                <button
                  onclick={selectOutputDir}
                  class="btn-primary py-1.5 px-3 text-xs flex-shrink-0 flex items-center gap-1"
                >
                  <svg
                    class="w-3.5 h-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    ><path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                    /></svg
                  >
                  {t("flashcards.browse")}
                </button>
              </div>
            </div>

            <div>
              <span class="block text-xs text-gray-400 mb-1"
                >{t("flashcards.nativeLangSubs")}</span
              >
              <span class="block text-[10px] text-gray-500 mb-1"
                >{t("flashcards.nativeLangSubsDesc")}</span
              >
              <div class="flex gap-2">
                <button
                  type="button"
                  onclick={() => {
                    if (nativeSubsPath) expandedPathField = "nativeSubs";
                  }}
                  class="input-modern flex-1 text-xs text-left transition-colors truncate {nativeSubsPath
                    ? 'cursor-pointer hover:bg-white/10'
                    : 'cursor-default hover:bg-transparent'}"
                  style="direction: rtl; text-align: left;"
                  title={nativeSubsPath || t("flashcards.optional")}
                >
                  <span
                    class={nativeSubsPath ? "text-white" : "text-gray-500"}
                    style="unicode-bidi: plaintext;"
                  >
                    {nativeSubsPath || t("flashcards.optional")}
                  </span>
                </button>
                <button
                  onclick={selectNativeSubs}
                  class="btn-secondary py-1.5 px-3 text-xs flex-shrink-0 flex items-center gap-1"
                >
                  <svg
                    class="w-3.5 h-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    ><path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                    /></svg
                  >
                  {t("flashcards.browse")}
                </button>
              </div>
            </div>

            <div>
              <span class="block text-xs text-gray-400 mb-1"
                >{t("flashcards.mediaFile")}</span
              >
              <span class="block text-[10px] text-gray-500 mb-1"
                >{t("flashcards.mediaFileDesc")}</span
              >
              <div class="flex gap-2">
                <button
                  type="button"
                  onclick={() => {
                    if (mediaPath) expandedPathField = "media";
                  }}
                  class="input-modern flex-1 text-xs text-left transition-colors truncate {mediaPath
                    ? 'cursor-pointer hover:bg-white/10'
                    : 'cursor-default hover:bg-transparent'}"
                  style="direction: rtl; text-align: left;"
                  title={mediaPath || t("flashcards.mediaPlaceholder")}
                >
                  <span
                    class={mediaPath ? "text-white" : "text-gray-500"}
                    style="unicode-bidi: plaintext;"
                  >
                    {mediaPath || t("flashcards.mediaPlaceholder")}
                  </span>
                </button>
                <button
                  onclick={selectMedia}
                  class="btn-secondary py-1.5 px-3 text-xs flex-shrink-0 flex items-center gap-1"
                >
                  <svg
                    class="w-3.5 h-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    ><path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                    /></svg
                  >
                  {t("flashcards.browse")}
                </button>
              </div>
            </div>
          </div>
        {:else}
          <!-- Series mode: batch file management -->
          <div class="space-y-3">
            <!-- Add files buttons -->
            <div class="flex flex-wrap gap-2">
              <button
                onclick={addSeriesTargetSubs}
                class="btn-primary py-1.5 px-3 text-xs flex items-center gap-1.5"
              >
                <svg
                  class="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 4v16m8-8H4"
                  /></svg
                >
                {t("flashcards.addTargetSubs")}
              </button>
              <button
                onclick={addSeriesNativeSubs}
                class="btn-secondary py-1.5 px-3 text-xs flex items-center gap-1.5"
                disabled={episodes.length === 0}
              >
                <svg
                  class="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 4v16m8-8H4"
                  /></svg
                >
                {t("flashcards.addNativeSubs")}
              </button>
              <button
                onclick={addSeriesMedia}
                class="btn-secondary py-1.5 px-3 text-xs flex items-center gap-1.5"
                disabled={episodes.length === 0}
              >
                <svg
                  class="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 4v16m8-8H4"
                  /></svg
                >
                {t("flashcards.addMedia")}
              </button>
              {#if episodes.length > 0}
                <button
                  onclick={clearAllEpisodes}
                  class="ml-auto text-xs text-red-400 hover:text-red-300 transition-colors flex items-center gap-1"
                >
                  <svg
                    class="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    ><path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    /></svg
                  >
                  {t("flashcards.clearAll")}
                </button>
              {/if}
            </div>

            <!-- Episode table -->
            {#if episodes.length === 0}
              <div
                class="p-6 text-center text-gray-500 text-xs border border-dashed border-gray-700 rounded-lg"
              >
                <svg
                  class="w-8 h-8 mx-auto mb-2 text-gray-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.5"
                    d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                  /></svg
                >
                {t("flashcards.noFilesAdded")}
              </div>
            {:else}
              <div class="border border-gray-700/50 rounded-lg overflow-hidden">
                <div class="overflow-y-auto max-h-[300px]">
                  <table class="w-full text-xs">
                    <thead class="bg-gray-800/80 sticky top-0">
                      <tr>
                        <th class="p-1.5 text-left text-gray-400 w-8">#</th>
                        <th class="p-1.5 text-left text-gray-400"
                          >{t("flashcards.targetLangSubs")}</th
                        >
                        <th class="p-1.5 text-left text-gray-400"
                          >{t("flashcards.nativeLangSubs")}</th
                        >
                        <th class="p-1.5 text-left text-gray-400"
                          >{t("flashcards.mediaFile")}</th
                        >
                        <th class="p-1.5 w-8"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each episodes as ep, idx}
                        <tr
                          class="border-t border-gray-800 {idx % 2 === 0
                            ? 'bg-gray-900/30'
                            : 'bg-gray-800/20'} hover:bg-gray-700/20"
                        >
                          <td class="p-1.5 text-gray-500 font-mono">{ep.id}</td>
                          <td
                            class="p-1.5 text-emerald-300 truncate max-w-[150px]"
                            title={ep.targetSubsPath}
                          >
                            {ep.targetSubsPath.split("/").pop()}
                          </td>
                          <td
                            class="p-1.5 truncate max-w-[150px] {ep.nativeSubsPath
                              ? 'text-blue-300'
                              : 'text-gray-600'}"
                            title={ep.nativeSubsPath || "—"}
                          >
                            {ep.nativeSubsPath
                              ? ep.nativeSubsPath.split("/").pop()
                              : "—"}
                          </td>
                          <td
                            class="p-1.5 truncate max-w-[150px] {ep.mediaPath
                              ? 'text-purple-300'
                              : 'text-gray-600'}"
                            title={ep.mediaPath || "—"}
                          >
                            {ep.mediaPath ? ep.mediaPath.split("/").pop() : "—"}
                          </td>
                          <td class="p-1.5">
                            <button
                              onclick={() => removeEpisode(idx)}
                              class="text-gray-600 hover:text-red-400 transition-colors"
                              title={t("flashcards.removeEpisode")}
                            >
                              <svg
                                class="w-3.5 h-3.5"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                                ><path
                                  stroke-linecap="round"
                                  stroke-linejoin="round"
                                  stroke-width="2"
                                  d="M6 18L18 6M6 6l12 12"
                                /></svg
                              >
                            </button>
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
                <div
                  class="bg-gray-800/40 px-2 py-1 text-[10px] text-gray-500 flex items-center justify-between border-t border-gray-700/50"
                >
                  <span>{episodes.length} {t("flashcards.seriesEpisodes")}</span
                  >
                  <span class="text-gray-600"
                    >{t("flashcards.autoMatched")}</span
                  >
                </div>
              </div>

              <!-- Output dir (shared with movie mode) -->
              <div>
                <span class="block text-xs text-gray-400 mb-1">
                  {t("flashcards.outputDir")}
                  <span class="text-red-400">*</span>
                </span>
                <div class="flex gap-2">
                  <button
                    type="button"
                    onclick={() => {
                      if (outputDir) expandedPathField = "output";
                    }}
                    class="input-modern flex-1 text-xs text-left transition-colors truncate {outputDir
                      ? 'cursor-pointer hover:bg-white/10'
                      : 'cursor-default hover:bg-transparent'}"
                    style="direction: rtl; text-align: left;"
                    title={outputDir || t("flashcards.selectDir")}
                  >
                    <span
                      class={outputDir ? "text-white" : "text-gray-500"}
                      style="unicode-bidi: plaintext;"
                    >
                      {outputDir || t("flashcards.selectDir")}
                    </span>
                  </button>
                  <button
                    onclick={selectOutputDir}
                    class="btn-primary py-1.5 px-3 text-xs flex-shrink-0 flex items-center gap-1"
                  >
                    <svg
                      class="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                      /></svg
                    >
                    {t("flashcards.browse")}
                  </button>
                </div>
              </div>
            {/if}
          </div>
        {/if}
      </div>
    {:else if panelId === "subtitleOptions"}
      <div
        class="glass-card p-4 {!hasAnyFiles
          ? 'opacity-40 pointer-events-none'
          : ''}"
      >
        <div class="flex items-center gap-2">
          <button
            onclick={() => {
              if (hasAnyFiles) showSubtitleOptions = !showSubtitleOptions;
            }}
            class="flex-1 flex items-center justify-between text-sm font-semibold text-teal-400"
          >
            <span class="flex items-center gap-2">
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
                  d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
                />
              </svg>
              {t("flashcards.subtitleOptions")}
            </span>
            <svg
              class="w-4 h-4 transition-transform {showSubtitleOptions
                ? 'rotate-180'
                : ''}"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
          <button
            type="button"
            onclick={() => (helpSection = "subtitleOptions")}
            title="Info"
            class="text-gray-500 hover:text-teal-300 flex-shrink-0 transition-colors"
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
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
        </div>
        {#if showSubtitleOptions}
          <div class="mt-3 space-y-2.5 animate-fade-in">
            <div class="flex items-center gap-4">
              <span class="text-xs text-gray-400"
                >{t("flashcards.useTimingsFrom")}:</span
              >
              <label class="flex items-center gap-1.5">
                <input
                  type="radio"
                  bind:group={useTimingsFrom}
                  value="target"
                  class="text-emerald-500"
                />
                <span class="text-xs text-gray-300"
                  >{t("flashcards.subs1")}</span
                >
              </label>
              <label class="flex items-center gap-1.5">
                <input
                  type="radio"
                  bind:group={useTimingsFrom}
                  value="native"
                  class="text-emerald-500"
                  disabled={!nativeSubsPath}
                />
                <span
                  class="text-xs text-gray-300 {!nativeSubsPath
                    ? 'opacity-50'
                    : ''}">{t("flashcards.subs2")}</span
                >
              </label>
            </div>

            <div class="grid grid-cols-2 gap-2">
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.spanStart")}</span
                >
                <input
                  type="text"
                  bind:value={spanStart}
                  class="input-modern w-full text-xs"
                  placeholder="h:mm:ss"
                />
              </div>
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.spanEnd")}</span
                >
                <input
                  type="text"
                  bind:value={spanEnd}
                  class="input-modern w-full text-xs"
                  placeholder="h:mm:ss"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-2">
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.timeShift")} {t("flashcards.subs1")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={timeShiftTarget}
                    class="input-modern w-full text-xs"
                  />
                  <span class="text-xs text-gray-500">ms</span>
                </div>
              </div>
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.timeShift")} {t("flashcards.subs2")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={timeShiftNative}
                    class="input-modern w-full text-xs"
                    disabled={!nativeSubsPath}
                  />
                  <span class="text-xs text-gray-500">ms</span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-3 pt-1">
              <label class="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  bind:checked={combineSentences}
                  class="rounded text-emerald-500"
                />
                <span class="text-xs text-gray-300"
                  >{t("flashcards.combineSentences")}</span
                >
              </label>
              {#if combineSentences}
                <input
                  type="text"
                  bind:value={continuationChars}
                  class="input-modern w-28 text-xs"
                  placeholder=",、→"
                  title={t("flashcards.continuationCharsHint")}
                />
              {/if}
            </div>
          </div>
        {/if}
      </div>
    {:else if panelId === "filters"}
      <div
        class="glass-card p-4 {!hasAnyFiles
          ? 'opacity-40 pointer-events-none'
          : ''}"
      >
        <div class="flex items-center gap-2">
          <button
            onclick={async (e) => {
              if (!hasAnyFiles) return;
              showFilters = !showFilters;
              const column = e.currentTarget.closest(".overflow-y-auto");
              await tick();
              if (column) {
                if (showFilters) {
                  column.scrollTo({
                    top: column.scrollHeight,
                    behavior: "smooth",
                  });
                } else {
                  column.scrollTo({ top: 0, behavior: "smooth" });
                }
              }
            }}
            class="flex-1 flex items-center justify-between text-sm font-semibold text-orange-400"
          >
            <span class="flex items-center gap-2">
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
                  d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
                />
              </svg>
              {t("flashcards.filters")}
            </span>
            <svg
              class="w-4 h-4 transition-transform {showFilters
                ? 'rotate-180'
                : ''}"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
          <button
            onclick={() => (helpSection = "filters")}
            class="text-gray-500 hover:text-orange-400 flex-shrink-0"
            title="Info"
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
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
        </div>

        {#if showFilters}
          <div class="mt-3 space-y-2.5 animate-fade-in">
            <div>
              <span class="block text-xs text-gray-500 mb-1"
                >{t("flashcards.includeWords")}</span
              >
              <input
                type="text"
                bind:value={includeWords}
                class="input-modern w-full text-xs"
                placeholder={t("flashcards.includeWordsHint")}
              />
            </div>
            <div>
              <span class="block text-xs text-gray-500 mb-1"
                >{t("flashcards.excludeWords")}</span
              >
              <input
                type="text"
                bind:value={excludeWords}
                class="input-modern w-full text-xs"
                placeholder={t("flashcards.excludeWordsHint")}
              />
            </div>

            <div class="flex flex-wrap gap-3">
              <label class="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  bind:checked={excludeDuplicatesSubs1}
                  class="rounded text-orange-500"
                />
                <span class="text-xs text-gray-300"
                  >{t("flashcards.excludeDupSubs1")}</span
                >
              </label>
              <label class="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  bind:checked={excludeDuplicatesSubs2}
                  class="rounded text-orange-500"
                  disabled={!nativeSubsPath}
                />
                <span
                  class="text-xs text-gray-300 {!nativeSubsPath
                    ? 'opacity-50'
                    : ''}">{t("flashcards.excludeDupSubs2")}</span
                >
              </label>
            </div>

            <div class="grid grid-cols-2 gap-2">
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.minChars")}</span
                >
                <input
                  type="number"
                  bind:value={minChars}
                  class="input-modern w-full text-xs"
                  min="0"
                  placeholder="—"
                />
              </div>
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.maxChars")}</span
                >
                <input
                  type="number"
                  bind:value={maxChars}
                  class="input-modern w-full text-xs"
                  min="0"
                  placeholder="—"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-2">
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.minDuration")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={minDurationMs}
                    class="input-modern w-full text-xs"
                    min="0"
                    placeholder="—"
                  />
                  <span class="text-xs text-gray-500">ms</span>
                </div>
              </div>
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.maxDuration")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={maxDurationMs}
                    class="input-modern w-full text-xs"
                    min="0"
                    placeholder="—"
                  />
                  <span class="text-xs text-gray-500">ms</span>
                </div>
              </div>
            </div>

            <div class="space-y-1.5">
              <label class="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  bind:checked={excludeStyled}
                  class="rounded text-orange-500"
                />
                <span class="text-xs text-gray-300"
                  >{t("flashcards.excludeStyled")}</span
                >
              </label>
              <label class="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  bind:checked={onlyCjk}
                  class="rounded text-orange-500"
                />
                <span class="text-xs text-gray-300"
                  >{t("flashcards.onlyCjk")}</span
                >
              </label>
              <label class="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  bind:checked={removeNoMatch}
                  class="rounded text-orange-500"
                  disabled={!nativeSubsPath}
                />
                <span
                  class="text-xs text-gray-300 {!nativeSubsPath
                    ? 'opacity-50'
                    : ''}">{t("flashcards.removeNoMatch")}</span
                >
              </label>
            </div>

            {#if targetSubsInfo && targetSubsInfo.actors.length > 0}
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.actorFilter")}</span
                >
                <input
                  type="text"
                  bind:value={actorFilter}
                  class="input-modern w-full text-xs"
                  placeholder={targetSubsInfo.actors.join(", ")}
                />
              </div>
            {/if}
          </div>
        {/if}
      </div>
    {:else if panelId === "contextLines"}
      <div
        class="glass-card p-4 {!hasAnyFiles
          ? 'opacity-40 pointer-events-none'
          : ''}"
      >
        <div class="flex items-center gap-2">
          <button
            onclick={() => {
              if (hasAnyFiles) showContextLines = !showContextLines;
            }}
            class="flex-1 flex items-center justify-between text-sm font-semibold text-indigo-400"
          >
            <span class="flex items-center gap-2">
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
                  d="M4 6h16M4 10h16M4 14h16M4 18h16"
                />
              </svg>
              {t("flashcards.contextLines")}
            </span>
            <svg
              class="w-4 h-4 transition-transform {showContextLines
                ? 'rotate-180'
                : ''}"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
          <button
            type="button"
            onclick={() => (helpSection = "contextLines")}
            title="Info"
            class="text-gray-500 hover:text-indigo-300 flex-shrink-0 transition-colors"
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
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
        </div>
        {#if showContextLines}
          <div class="mt-3 grid grid-cols-3 gap-2 animate-fade-in">
            <div>
              <span class="block text-xs text-gray-500 mb-1"
                >{t("flashcards.leading")}</span
              >
              <input
                type="number"
                bind:value={contextLeading}
                class="input-modern w-full text-xs"
                min="0"
                max="10"
              />
            </div>
            <div>
              <span class="block text-xs text-gray-500 mb-1"
                >{t("flashcards.trailing")}</span
              >
              <input
                type="number"
                bind:value={contextTrailing}
                class="input-modern w-full text-xs"
                min="0"
                max="10"
              />
            </div>
            <div>
              <span class="block text-xs text-gray-500 mb-1"
                >{t("flashcards.maxGap")}</span
              >
              <div class="flex items-center gap-1">
                <input
                  type="number"
                  bind:value={contextMaxGap}
                  class="input-modern w-full text-xs"
                  min="0"
                  step="0.5"
                />
                <span class="text-xs text-gray-500">s</span>
              </div>
            </div>
          </div>
        {/if}
      </div>
    {:else if panelId === "audioClips"}
      <div
        class="glass-card p-4 {!hasAudio
          ? 'opacity-40 pointer-events-none'
          : ''}"
        style="overflow: visible; position: relative; z-index: 10;"
      >
        <div class="flex items-center justify-between mb-3">
          <h3
            class="text-sm font-semibold flex items-center gap-2 text-cyan-400"
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
                d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
              />
            </svg>
            {t("flashcards.generateAudioClips")}
            <button
              type="button"
              onclick={() => (helpSection = "audioClips")}
              title="Info"
              class="text-gray-500 hover:text-cyan-300 transition-colors"
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
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </button>
          </h3>
          <button
            onclick={() => {
              if (hasAudio) generateAudio = !generateAudio;
            }}
            class="w-10 h-5 rounded-full transition-all duration-200 relative
              {generateAudio && hasAudio ? 'bg-cyan-500' : 'bg-gray-600'}"
            aria-label="Toggle audio clips"
            disabled={!hasAudio}
          >
            <div
              class="absolute w-4 h-4 bg-white rounded-full top-0.5 transition-all duration-200
              {generateAudio && hasAudio ? 'left-5' : 'left-0.5'}"
            ></div>
          </button>
        </div>

        {#if generateAudio && hasAudio}
          <div class="space-y-2 animate-fade-in">
            <div class="grid grid-cols-2 gap-2">
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.bitrate")}</span
                >
                <SearchableSelect
                  noResultsText={t("common.noResults")}
                  options={[
                    { value: "64", label: "64 kb/s" },
                    { value: "128", label: "128 kb/s" },
                    { value: "192", label: "192 kb/s" },
                    { value: "256", label: "256 kb/s" },
                    { value: "320", label: "320 kb/s" },
                  ]}
                  value={String(audioBitrate)}
                  onchange={(v) => (audioBitrate = parseInt(v))}
                  placeholder="Bitrate"
                />
              </div>
              <div class="flex items-end">
                <label class="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    bind:checked={normalizeAudio}
                    class="rounded text-cyan-500"
                  />
                  <span class="text-xs text-gray-300"
                    >{t("flashcards.normalizeAudio")}</span
                  >
                </label>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.padStart")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={audioPadStart}
                    class="input-modern w-full text-xs"
                  />
                  <span class="text-xs text-gray-500">ms</span>
                </div>
              </div>
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.padEnd")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={audioPadEnd}
                    class="input-modern w-full text-xs"
                  />
                  <span class="text-xs text-gray-500">ms</span>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
    {:else if panelId === "snapshots"}
      <div
        class="glass-card p-4 {!hasVideo
          ? 'opacity-40 pointer-events-none'
          : ''}"
      >
        <div class="flex items-center justify-between mb-3">
          <h3
            class="text-sm font-semibold flex items-center gap-2 text-purple-400"
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
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            {t("flashcards.generateSnapshots")}
            <button
              type="button"
              onclick={() => (helpSection = "snapshots")}
              title="Info"
              class="text-gray-500 hover:text-purple-300 transition-colors"
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
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </button>
          </h3>
          <button
            onclick={() => {
              if (hasVideo) {
                generateSnapshots = !generateSnapshots;
                if (generateSnapshots) generateVideoClips = false;
              }
            }}
            class="w-10 h-5 rounded-full transition-all duration-200 relative
              {generateSnapshots && hasVideo ? 'bg-purple-500' : 'bg-gray-600'}"
            aria-label="Toggle snapshots"
            disabled={!hasVideo}
          >
            <div
              class="absolute w-4 h-4 bg-white rounded-full top-0.5 transition-all duration-200
              {generateSnapshots && hasVideo ? 'left-5' : 'left-0.5'}"
            ></div>
          </button>
        </div>

        {#if generateSnapshots && hasVideo}
          <div class="space-y-2 animate-fade-in">
            <div class="grid grid-cols-3 gap-2">
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.width")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={snapshotWidth}
                    class="input-modern w-full text-xs"
                  />
                  <span class="text-xs text-gray-500">px</span>
                </div>
              </div>
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.height")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={snapshotHeight}
                    class="input-modern w-full text-xs"
                  />
                  <span class="text-xs text-gray-500">px</span>
                </div>
              </div>
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.cropBottom")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={cropBottom}
                    class="input-modern w-full text-xs"
                  />
                  <span class="text-xs text-gray-500">px</span>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
    {:else if panelId === "videoClips"}
      <div
        class="glass-card p-4 {!hasVideo
          ? 'opacity-40 pointer-events-none'
          : ''}"
        style="overflow: visible; position: relative; z-index: 5;"
      >
        <div class="flex items-center justify-between mb-3">
          <h3
            class="text-sm font-semibold flex items-center gap-2 text-rose-400"
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
                d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
            {t("flashcards.generateVideoClips")}
            <button
              type="button"
              onclick={() => (helpSection = "videoClips")}
              title="Info"
              class="text-gray-500 hover:text-rose-300 transition-colors"
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
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </button>
          </h3>
          <button
            onclick={() => {
              if (hasVideo) {
                generateVideoClips = !generateVideoClips;
                if (generateVideoClips) generateSnapshots = false;
              }
            }}
            class="w-10 h-5 rounded-full transition-all duration-200 relative
              {generateVideoClips && hasVideo ? 'bg-rose-500' : 'bg-gray-600'}"
            aria-label="Toggle video clips"
            disabled={!hasVideo}
          >
            <div
              class="absolute w-4 h-4 bg-white rounded-full top-0.5 transition-all duration-200
              {generateVideoClips && hasVideo ? 'left-5' : 'left-0.5'}"
            ></div>
          </button>
        </div>

        {#if generateVideoClips && hasVideo}
          <div class="space-y-2 animate-fade-in">
            <div class="grid grid-cols-2 gap-2">
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.videoCodec")}</span
                >
                <SearchableSelect
                  noResultsText={t("common.noResults")}
                  options={[
                    { value: "h264", label: "H.264 (MP4)" },
                    { value: "mpeg4", label: "MPEG-4 (AVI)" },
                  ]}
                  value={videoCodec}
                  onchange={(v) => (videoCodec = v)}
                  placeholder="Codec"
                />
              </div>
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.h264Preset")}</span
                >
                <SearchableSelect
                  noResultsText={t("common.noResults")}
                  options={[
                    { value: "ultrafast", label: "Ultrafast" },
                    { value: "fast", label: "Fast" },
                    { value: "medium", label: "Medium" },
                    { value: "slow", label: "Slow" },
                    { value: "veryslow", label: "Very slow" },
                  ]}
                  value={h264Preset}
                  onchange={(v) => (h264Preset = v)}
                  placeholder="Preset"
                />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.videoBitrate")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={videoBitrate}
                    class="input-modern w-full text-xs"
                  />
                  <span class="text-xs text-gray-500">kb/s</span>
                </div>
              </div>
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.audioBitrate")}</span
                >
                <SearchableSelect
                  noResultsText={t("common.noResults")}
                  options={[
                    { value: "64", label: "64 kb/s" },
                    { value: "128", label: "128 kb/s" },
                    { value: "192", label: "192 kb/s" },
                    { value: "256", label: "256 kb/s" },
                  ]}
                  value={String(videoAudioBitrate)}
                  onchange={(v) => (videoAudioBitrate = parseInt(v))}
                  placeholder="Bitrate"
                />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.padStart")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={videoPadStart}
                    class="input-modern w-full text-xs"
                  />
                  <span class="text-xs text-gray-500">ms</span>
                </div>
              </div>
              <div>
                <span class="block text-xs text-gray-500 mb-1"
                  >{t("flashcards.padEnd")}</span
                >
                <div class="flex items-center gap-1">
                  <input
                    type="number"
                    bind:value={videoPadEnd}
                    class="input-modern w-full text-xs"
                  />
                  <span class="text-xs text-gray-500">ms</span>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
    {:else if panelId === "ankiFields"}
      <div
        class="glass-card p-4 {!hasAnyFiles
          ? 'opacity-50 pointer-events-none'
          : ''}"
      >
        <h3
          class="text-sm font-semibold mb-3 flex items-center gap-2 text-lime-400"
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
              d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
            />
          </svg>
          {t("flashcards.ankiFields")}
          <button
            type="button"
            onclick={() => (helpSection = "ankiFields")}
            title="Info"
            class="ml-auto text-gray-500 hover:text-lime-300 transition-colors"
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
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
        </h3>

        <div class="mb-3">
          <span class="block text-xs text-gray-400 mb-1"
            >{t("flashcards.noteTypeLanguage")}</span
          >
          <SearchableSelect
            noResultsText={t("common.noResults")}
            options={languages.map((lang) => ({
              value: lang.code,
              label:
                lang.nameEn === lang.name
                  ? lang.name
                  : `${lang.nameEn} — ${lang.name}`,
              searchTerms: `${lang.nameEn} ${lang.name}`,
              icon: lang.flag,
            }))}
            value={noteTypeLanguage}
            onchange={(v) => {
              noteTypeLanguage = v;
              if (v) {
                localStorage.setItem(NOTE_TYPE_LANGUAGE_KEY, v);
              } else {
                localStorage.removeItem(NOTE_TYPE_LANGUAGE_KEY);
              }
            }}
            placeholder={t("flashcards.noteTypeLanguagePlaceholder")}
          />
        </div>

        <div class="mb-3 flex items-center gap-1.5">
          <span class="text-xs text-gray-400"
            >{t("flashcards.noteTypeName")}:</span
          >
          <span
            class="text-xs text-white font-mono bg-white/10 px-2 py-0.5 rounded font-medium"
            >{noteTypeName || "—"}</span
          >
        </div>

        <span class="block text-xs text-gray-500 mb-2"
          >{t("flashcards.fieldsLabel")}</span
        >
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            onclick={() => (includeSubs1Field = !includeSubs1Field)}
            class="px-3 py-1.5 rounded-full text-xs font-medium border transition-all {includeSubs1Field
              ? 'bg-lime-500/20 border-lime-500/50 text-lime-300'
              : 'bg-gray-800/50 border-gray-700/50 text-gray-500 hover:border-gray-600'}"
          >
            🗣️ {t("flashcards.subs1")}
          </button>
          <button
            type="button"
            onclick={() => {
              if (nativeSubsPath) includeSubs2Field = !includeSubs2Field;
            }}
            class="px-3 py-1.5 rounded-full text-xs font-medium border transition-all {!nativeSubsPath
              ? 'opacity-40 cursor-not-allowed'
              : ''} {includeSubs2Field && nativeSubsPath
              ? 'bg-lime-500/20 border-lime-500/50 text-lime-300'
              : 'bg-gray-800/50 border-gray-700/50 text-gray-500 hover:border-gray-600'}"
          >
            💬 {t("flashcards.subs2")}
          </button>
          <button
            type="button"
            onclick={() => (includeAudioField = !includeAudioField)}
            class="px-3 py-1.5 rounded-full text-xs font-medium border transition-all {includeAudioField
              ? 'bg-lime-500/20 border-lime-500/50 text-lime-300'
              : 'bg-gray-800/50 border-gray-700/50 text-gray-500 hover:border-gray-600'}"
          >
            🔊 {t("flashcards.audioField")}
          </button>
          <button
            type="button"
            onclick={() => (includeSnapshotField = !includeSnapshotField)}
            class="px-3 py-1.5 rounded-full text-xs font-medium border transition-all {includeSnapshotField
              ? 'bg-lime-500/20 border-lime-500/50 text-lime-300'
              : 'bg-gray-800/50 border-gray-700/50 text-gray-500 hover:border-gray-600'}"
          >
            📸 {t("flashcards.snapshotField")}
          </button>
          <button
            type="button"
            onclick={() => (includeVideoField = !includeVideoField)}
            class="px-3 py-1.5 rounded-full text-xs font-medium border transition-all {includeVideoField
              ? 'bg-lime-500/20 border-lime-500/50 text-lime-300'
              : 'bg-gray-800/50 border-gray-700/50 text-gray-500 hover:border-gray-600'}"
          >
            🎬 {t("flashcards.videoField")}
          </button>
          <button
            type="button"
            onclick={() => (includeTag = !includeTag)}
            class="px-3 py-1.5 rounded-full text-xs font-medium border transition-all {includeTag
              ? 'bg-lime-500/20 border-lime-500/50 text-lime-300'
              : 'bg-gray-800/50 border-gray-700/50 text-gray-500 hover:border-gray-600'}"
          >
            🏷️ {t("flashcards.tagField")}
          </button>
          <button
            type="button"
            onclick={() => (includeSequence = !includeSequence)}
            class="px-3 py-1.5 rounded-full text-xs font-medium border transition-all {includeSequence
              ? 'bg-lime-500/20 border-lime-500/50 text-lime-300'
              : 'bg-gray-800/50 border-gray-700/50 text-gray-500 hover:border-gray-600'}"
          >
            🔢 {t("flashcards.sequenceField")}
          </button>
        </div>
      </div>
    {:else if panelId === "exportFormat"}
      <div class="glass-card p-4">
        <h3
          class="text-sm font-semibold mb-3 flex items-center gap-2 text-sky-400"
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
              d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          {t("flashcards.exportFormat")}
          <button
            type="button"
            onclick={() => (helpSection = "exportFormat")}
            title="Info"
            class="ml-auto text-gray-500 hover:text-sky-300 transition-colors"
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
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
        </h3>
        <div class="space-y-2">
          <label
            class="flex items-start gap-2 p-2 rounded-lg cursor-pointer transition-colors
            {exportFormat === 'apkg'
              ? 'bg-emerald-500/10 border border-emerald-500/30'
              : 'bg-transparent border border-transparent hover:bg-gray-800/50'}"
          >
            <input
              type="radio"
              bind:group={exportFormat}
              value="apkg"
              class="mt-0.5 text-emerald-500"
            />
            <div class="flex-1">
              <span class="text-xs font-medium text-gray-200"
                >{t("flashcards.exportAPKG")}</span
              >
              <span
                class="ml-1.5 text-[9px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded-full font-semibold uppercase"
                >{t("flashcards.exportAPKGBadge")}</span
              >
              <p class="text-[10px] text-gray-500">
                {t("flashcards.exportAPKGDesc")}
              </p>
            </div>
          </label>
          <label
            class="flex items-start gap-2 p-2 rounded-lg cursor-pointer transition-colors
            {exportFormat === 'tsv'
              ? 'bg-sky-500/10 border border-sky-500/30'
              : 'bg-transparent border border-transparent hover:bg-gray-800/50'}"
          >
            <input
              type="radio"
              bind:group={exportFormat}
              value="tsv"
              class="mt-0.5 text-sky-500"
            />
            <div class="flex-1">
              <span class="text-xs font-medium text-gray-200"
                >{t("flashcards.exportTSV")}</span
              >
              <span
                class="ml-1.5 text-[9px] bg-gray-500/20 text-gray-400 px-1.5 py-0.5 rounded-full font-semibold uppercase"
                >{t("flashcards.exportTSVBadge")}</span
              >
              <p class="text-[10px] text-gray-500">
                {t("flashcards.exportTSVDesc")}
              </p>
            </div>
          </label>

          {#if seriesMode && exportFormat === "apkg"}
            <!-- Series output mode (only for APKG) -->
            <div class="mt-4 pt-3 border-t border-gray-700/50">
              <span class="block text-xs text-gray-400 mb-2"
                >{t("flashcards.seriesOutputFormat")}</span
              >
              <div class="flex gap-2">
                <button
                  onclick={() => (seriesOutputMode = "separate")}
                  class="flex-1 py-2 px-3 text-xs rounded-lg border transition-colors {seriesOutputMode ===
                  'separate'
                    ? 'border-violet-500/50 bg-violet-500/10 text-violet-300'
                    : 'border-gray-700/50 text-gray-400 hover:border-gray-600 bg-gray-900/40'}"
                >
                  <div
                    class="font-medium mb-0.5 text-gray-200 {seriesOutputMode ===
                    'separate'
                      ? 'text-violet-200'
                      : ''}"
                  >
                    {t("flashcards.outputPerEpisode")}
                  </div>
                  <div class="text-[10px] opacity-80">
                    {t("flashcards.outputPerEpisodeDesc")}
                  </div>
                </button>
                <button
                  onclick={() => (seriesOutputMode = "single")}
                  class="flex-1 py-2 px-3 text-xs rounded-lg border transition-colors {seriesOutputMode ===
                  'single'
                    ? 'border-violet-500/50 bg-violet-500/10 text-violet-300'
                    : 'border-gray-700/50 text-gray-400 hover:border-gray-600 bg-gray-900/40'}"
                >
                  <div
                    class="font-medium mb-0.5 text-gray-200 {seriesOutputMode ===
                    'single'
                      ? 'text-violet-200'
                      : ''}"
                  >
                    {t("flashcards.outputSingleApkg")}
                  </div>
                  <div class="text-[10px] opacity-80">
                    {t("flashcards.outputSingleApkgDesc")}
                  </div>
                </button>
              </div>
            </div>
          {/if}
        </div>
      </div>
    {:else if panelId === "naming"}
      <div
        class="glass-card p-4 {!hasAnyFiles
          ? 'opacity-50 pointer-events-none'
          : ''}"
      >
        <h3
          class="text-sm font-semibold mb-3 flex items-center gap-2 text-amber-400"
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
              d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
            />
          </svg>
          {t("flashcards.naming")}
          <button
            type="button"
            onclick={() => (helpSection = "naming")}
            title="Info"
            class="ml-auto text-gray-500 hover:text-amber-300 transition-colors"
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
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
        </h3>

        <div class="space-y-3">
          <div>
            <span class="block text-xs text-gray-400 mb-1">
              {t("flashcards.deckNameLabel")}
              <span class="text-red-400">*</span>
            </span>
            <input
              type="text"
              bind:value={deckName}
              class="input-modern w-full text-sm"
              placeholder={t("flashcards.deckNamePlaceholder")}
            />
          </div>
          <div>
            <span class="block text-xs text-gray-400 mb-1"
              >{t("flashcards.firstEpisode")}</span
            >
            <input
              type="number"
              bind:value={firstEpisode}
              min="1"
              class="input-modern w-20 text-sm"
            />
          </div>
        </div>
      </div>
    {:else if panelId === "cpuCores"}
      <div class="glass-card p-4">
        <h3
          class="text-sm font-semibold mb-3 flex items-center gap-2 text-orange-400"
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
              d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
            />
          </svg>
          {t("flashcards.cpuCores")}
          <button
            type="button"
            onclick={() => (helpSection = "cpuCores")}
            class="ml-auto text-gray-500 hover:text-orange-300 transition-colors"
            title="Info"
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
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
        </h3>
        <div class="grid grid-cols-4 gap-2 mb-3">
          <button
            onclick={() => setCpuPreset("eco")}
            class="p-2 rounded-lg text-center transition-all duration-200 border text-xs {activeCpuPreset ===
            'eco'
              ? 'bg-orange-500/20 border-orange-500/50 text-white'
              : 'bg-white/5 hover:bg-white/10 border-transparent text-gray-400 hover:text-white'}"
          >
            <span class="text-base block mb-0.5">🍃</span>
            <span class="font-semibold block">{t("flashcards.cpuEco")}</span>
            <span class="text-[10px] text-gray-500 block"
              >{cpuPresets[0].threads} thread</span
            >
          </button>
          <button
            onclick={() => setCpuPreset("balanced")}
            class="p-2 rounded-lg text-center transition-all duration-200 border text-xs {activeCpuPreset ===
            'balanced'
              ? 'bg-orange-500/20 border-orange-500/50 text-white'
              : 'bg-white/5 hover:bg-white/10 border-transparent text-gray-400 hover:text-white'}"
          >
            <span class="text-base block mb-0.5">⚖️</span>
            <span class="font-semibold block"
              >{t("flashcards.cpuBalanced")}</span
            >
            <span class="text-[10px] text-gray-500 block"
              >{cpuPresets[1].threads} thread</span
            >
          </button>
          <button
            onclick={() => setCpuPreset("performance")}
            class="p-2 rounded-lg text-center transition-all duration-200 border text-xs {activeCpuPreset ===
            'performance'
              ? 'bg-orange-500/20 border-orange-500/50 text-white'
              : 'bg-white/5 hover:bg-white/10 border-transparent text-gray-400 hover:text-white'}"
          >
            <span class="text-base block mb-0.5">🔥</span>
            <span class="font-semibold block"
              >{t("flashcards.cpuPerformance")}</span
            >
            <span class="text-[10px] text-gray-500 block"
              >{cpuPresets[2].threads} thread</span
            >
          </button>
          <button
            onclick={() => setCpuPreset("full")}
            class="p-2 rounded-lg text-center transition-all duration-200 border text-xs {activeCpuPreset ===
            'full'
              ? 'bg-orange-500/20 border-orange-500/50 text-white'
              : 'bg-white/5 hover:bg-white/10 border-transparent text-gray-400 hover:text-white'}"
          >
            <span class="text-base block mb-0.5">💪</span>
            <span class="font-semibold block"
              >{t("flashcards.cpuFullPower")}</span
            >
            <span class="text-[10px] text-gray-500 block"
              >{cpuPresets[3].threads} thread</span
            >
          </button>
        </div>
        <div class="flex items-center justify-between text-xs">
          <span class="text-gray-500">{t("flashcards.cpuCoresUsage")}</span>
          <span
            class="text-white font-mono bg-white/10 px-2 py-0.5 rounded text-sm"
            >{cpuCores} / {systemCpuCount}</span
          >
        </div>
      </div>
    {:else if panelId === "actions"}
      <div class="space-y-3">
        {#if isProcessing}
          <button
            onclick={cancelGeneration}
            class="btn-danger w-full py-4 text-lg"
          >
            <svg
              class="w-5 h-5 inline mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
            {t("flashcards.cancel")}
          </button>
        {:else}
          <button
            onclick={startGeneration}
            disabled={!canRunFlashcards}
            class="btn-success w-full py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg
              class="w-5 h-5 inline mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
            {t("flashcards.generate")}
          </button>

          <button
            class="btn-secondary w-full py-2 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={!canRunFlashcards}
            onclick={loadPreview}
          >
            <svg
              class="w-4 h-4 inline mr-2"
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
            {t("flashcards.preview")}
          </button>
        {/if}

        {#if result}
          <button
            onclick={resetGeneration}
            class="w-full py-2 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 transition-colors text-sm font-medium"
            title={t("flashcards.newGenerationDesc")}
          >
            <svg
              class="w-4 h-4 inline mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            {t("flashcards.newGeneration")}
          </button>
        {/if}
      </div>
    {:else if panelId === "progressResult"}
      <div class="space-y-3">
        {#if isProcessing || progress > 0}
          <div
            class="glass-card p-4 {isProcessing ? 'animate-pulse-glow' : ''}"
          >
            <div class="flex items-center gap-4">
              <div class="flex-1">
                <div class="progress-modern h-2">
                  <div
                    class="progress-modern-bar bg-gradient-to-r from-emerald-500 to-teal-500"
                    style="width: {progress}%"
                  ></div>
                </div>
              </div>
              <span class="text-lg font-bold text-emerald-400">{progress}%</span
              >
            </div>
            {#if progressMessage}
              <p class="text-gray-400 text-xs mt-2">{progressMessage}</p>
            {/if}
            {#if progressStage}
              <div class="flex gap-1.5 mt-2">
                {#each Array(10) as _, i}
                  {@const threshold = (i + 1) * 10}
                  <div
                    class="h-1 flex-1 rounded-full transition-colors duration-300 {progress >=
                    threshold
                      ? 'bg-emerald-700'
                      : progress >= threshold - 10
                        ? 'bg-emerald-400'
                        : 'bg-gray-700'}"
                  ></div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
        {#if result}
          <div
            class="glass-card p-4 border-l-4 {result.success
              ? 'border-green-500 bg-green-500/5'
              : 'border-red-500 bg-red-500/5'}"
          >
            {#if result.success}
              <div class="space-y-2">
                <div class="flex items-center gap-3">
                  <svg
                    class="w-5 h-5 text-green-400"
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
                  <p class="text-green-400 font-medium">
                    {result.cardsGenerated}
                    {t("flashcards.cardsGenerated")}
                  </p>
                </div>
                <div class="flex gap-4 text-xs text-gray-400">
                  {#if result.audioClips > 0}
                    <span>🔊 {result.audioClips} audio</span>
                  {/if}
                  {#if result.snapshots > 0}
                    <span>📸 {result.snapshots} snapshots</span>
                  {/if}
                  {#if result.videoClips > 0}
                    <span>🎬 {result.videoClips} video</span>
                  {/if}
                </div>
                {#if result.tsvPath}
                  <p
                    class="text-xs text-gray-500 break-words"
                    title={result.tsvPath}
                  >
                    📄 {result.tsvPath}
                  </p>
                {/if}
                {#if result.apkgPath}
                  <p
                    class="text-xs text-gray-500 break-words"
                    title={result.apkgPath}
                  >
                    📦 {result.apkgPath}
                  </p>
                {/if}
              </div>
            {:else}
              <div class="flex items-center gap-3">
                <svg
                  class="w-5 h-5 text-red-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p class="text-red-300">{t("flashcards.noActiveLines")}</p>
              </div>
            {/if}
          </div>
        {/if}
        {#if error}
          <div class="glass-card p-4 border border-red-500/30 bg-red-500/10">
            <div class="flex items-center gap-3">
              <svg
                class="w-5 h-5 text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p class="text-red-300 flex-1 text-sm break-words">{error}</p>
              <button
                onclick={() => (error = null)}
                class="text-red-400 hover:text-red-300">✕</button
              >
            </div>
          </div>
        {/if}
      </div>
    {:else if panelId === "logs"}
      <div class="glass-card p-4 flex flex-col min-h-32">
        <div class="flex items-center justify-between mb-2">
          <h4
            class="text-xs font-semibold text-gray-400 flex items-center gap-2"
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
                d="M4 6h16M4 12h16m-7 6h7"
              />
            </svg>
            {t("flashcards.logs")}
          </h4>
          {#if logs.length > 0}
            <button
              onclick={clearLogs}
              class="text-xs text-gray-500 hover:text-gray-400"
            >
              {t("flashcards.clearLog")}
            </button>
          {/if}
        </div>
        <div class="overflow-y-auto space-y-1.5 max-h-48">
          {#if logs.length > 0}
            {#each logs as log (log.id)}
              {@const style = logStyle(log.type)}
              <div
                class="p-2 rounded-lg border {style.bg} {style.border} flex items-start gap-2 animate-fade-in"
              >
                <span class="text-xs flex-shrink-0">{style.icon}</span>
                <div class="flex-1 min-w-0">
                  <p
                    class="text-xs {style.text} leading-tight break-words whitespace-pre-wrap"
                  >
                    {log.message}
                  </p>
                  {#if log.details}
                    <p
                      class="text-[10px] text-gray-500 break-words whitespace-pre-wrap mt-0.5"
                      title={log.details}
                    >
                      {log.details}
                    </p>
                  {/if}
                </div>
                <span class="text-[10px] text-gray-600 flex-shrink-0"
                  >{log.timestamp}</span
                >
              </div>
            {/each}
          {:else}
            <p class="text-gray-600 text-xs p-2">{t("flashcards.noLog")}</p>
          {/if}
        </div>
      </div>
    {/if}
  {/snippet}

  <div class="flex items-center justify-between mb-1">
    <!-- Column count buttons -->
    <div class="flex items-center gap-1">
      <button
        onclick={() => setColumnCount(1)}
        class="p-1 rounded transition-colors {columnCount === 1
          ? 'text-emerald-400 bg-emerald-500/15'
          : 'text-gray-500 hover:text-gray-300'}"
        title={t("flashcards.columns1")}
      >
        <svg
          class="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="2"
        >
          <rect x="4" y="4" width="16" height="16" rx="1" />
        </svg>
      </button>
      <button
        onclick={() => setColumnCount(2)}
        class="p-1 rounded transition-colors {columnCount === 2
          ? 'text-emerald-400 bg-emerald-500/15'
          : 'text-gray-500 hover:text-gray-300'}"
        title={t("flashcards.columns2")}
      >
        <svg
          class="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="2"
        >
          <rect x="4" y="4" width="7" height="16" rx="1" />
          <rect x="13" y="4" width="7" height="16" rx="1" />
        </svg>
      </button>
      <button
        onclick={() => setColumnCount(3)}
        class="p-1 rounded transition-colors {columnCount === 3
          ? 'text-emerald-400 bg-emerald-500/15'
          : 'text-gray-500 hover:text-gray-300'}"
        title={t("flashcards.columns3")}
      >
        <svg
          class="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="2"
        >
          <rect x="3" y="4" width="5" height="16" rx="1" />
          <rect x="9.5" y="4" width="5" height="16" rx="1" />
          <rect x="16" y="4" width="5" height="16" rx="1" />
        </svg>
      </button>
    </div>
    <!-- Movie/Series toggle -->
    <div
      class="flex items-center gap-2 px-3 py-0.5 rounded-full bg-gray-800/60 border border-gray-700/50"
    >
      <button
        onclick={toggleSeriesMode}
        class="flex items-center gap-1 text-xs font-medium transition-colors {!seriesMode
          ? 'text-emerald-400'
          : 'text-gray-500 hover:text-gray-300'}"
        title={t("flashcards.modeMovie")}
      >
        <svg
          class="w-3.5 h-3.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="2"
        >
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="M2 8h20M7 4v4M17 4v4" stroke-linecap="round" />
        </svg>
        {t("flashcards.modeMovie")}
      </button>
      <div
        class="relative w-9 h-5 cursor-pointer"
        onclick={toggleSeriesMode}
        role="switch"
        tabindex="0"
        aria-checked={seriesMode}
        onkeydown={(e) => {
          if (e.key === "Enter" || e.key === " ") toggleSeriesMode();
        }}
      >
        <div
          class="absolute inset-0 rounded-full transition-colors {seriesMode
            ? 'bg-violet-500/40'
            : 'bg-gray-700'}"
        ></div>
        <div
          class="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform {seriesMode
            ? 'translate-x-4'
            : 'translate-x-0.5'}"
        ></div>
      </div>
      <button
        onclick={toggleSeriesMode}
        class="flex items-center gap-1 text-xs font-medium transition-colors {seriesMode
          ? 'text-violet-400'
          : 'text-gray-500 hover:text-gray-300'}"
        title={t("flashcards.modeSeries")}
      >
        <svg
          class="w-3.5 h-3.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="2"
        >
          <rect x="2" y="3" width="20" height="6" rx="1" />
          <rect x="2" y="11" width="20" height="6" rx="1" />
          <line x1="6" y1="3" x2="6" y2="9" />
          <line x1="6" y1="11" x2="6" y2="17" />
        </svg>
        {t("flashcards.modeSeries")}
      </button>
    </div>
    <!-- Reset layout button -->
    <button
      onclick={resetLayout}
      class="text-[10px] text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-1"
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
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
        />
      </svg>
      {t("flashcards.resetLayout")}
    </button>
  </div>

  <div class="flex-1 grid {gridColClass} gap-4 min-h-0 overflow-y-auto">
    <div
      class="space-y-3 overflow-y-auto pr-1 min-h-[100px]"
      ondragover={(e) => onDragOverColumn(e, "col1")}
      ondrop={() => onDropColumn("col1")}
      role="list"
    >
      {#each panelLayout.col1 as panelId, idx (panelId)}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          draggable="true"
          ondragstart={(e) => onDragStart(e, panelId)}
          ondragover={(e) => onDragOver(e, "col1", idx)}
          ondrop={(e) => {
            e.stopPropagation();
            onDrop("col1", idx);
          }}
          ondragend={onDragEnd}
          class="cursor-grab active:cursor-grabbing transition-all duration-150 {draggedPanel ===
          panelId
            ? 'opacity-40 scale-[0.98]'
            : ''} {dragOverCol === 'col1' &&
          dragOverIdx === idx &&
          draggedPanel !== panelId
            ? 'border-t-2 border-emerald-400 pt-1'
            : ''}"
          role="listitem"
        >
          {@render panelContent(panelId)}
        </div>
      {/each}
      {#if draggedPanel && dragOverCol === "col1" && dragOverIdx === panelLayout.col1.length}
        <div class="h-1 bg-emerald-400 rounded-full mx-4 transition-all"></div>
      {/if}
    </div>

    {#if columnCount >= 2}
      <div
        class="space-y-3 overflow-y-auto pr-1 min-h-[100px]"
        ondragover={(e) => onDragOverColumn(e, "col2")}
        ondrop={() => onDropColumn("col2")}
        role="list"
      >
        {#each panelLayout.col2 as panelId, idx (panelId)}
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div
            draggable="true"
            ondragstart={(e) => onDragStart(e, panelId)}
            ondragover={(e) => onDragOver(e, "col2", idx)}
            ondrop={(e) => {
              e.stopPropagation();
              onDrop("col2", idx);
            }}
            ondragend={onDragEnd}
            class="cursor-grab active:cursor-grabbing transition-all duration-150 {draggedPanel ===
            panelId
              ? 'opacity-40 scale-[0.98]'
              : ''} {dragOverCol === 'col2' &&
            dragOverIdx === idx &&
            draggedPanel !== panelId
              ? 'border-t-2 border-emerald-400 pt-1'
              : ''}"
            role="listitem"
          >
            {@render panelContent(panelId)}
          </div>
        {/each}
        {#if draggedPanel && dragOverCol === "col2" && dragOverIdx === panelLayout.col2.length}
          <div
            class="h-1 bg-emerald-400 rounded-full mx-4 transition-all"
          ></div>
        {/if}
      </div>
    {/if}

    {#if columnCount >= 3}
      <div
        class="space-y-3 overflow-y-auto pr-1 min-h-[100px]"
        ondragover={(e) => onDragOverColumn(e, "col3")}
        ondrop={() => onDropColumn("col3")}
        role="list"
      >
        {#each panelLayout.col3 as panelId, idx (panelId)}
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div
            draggable="true"
            ondragstart={(e) => onDragStart(e, panelId)}
            ondragover={(e) => onDragOver(e, "col3", idx)}
            ondrop={(e) => {
              e.stopPropagation();
              onDrop("col3", idx);
            }}
            ondragend={onDragEnd}
            class="cursor-grab active:cursor-grabbing transition-all duration-150 {draggedPanel ===
            panelId
              ? 'opacity-40 scale-[0.98]'
              : ''} {dragOverCol === 'col3' &&
            dragOverIdx === idx &&
            draggedPanel !== panelId
              ? 'border-t-2 border-emerald-400 pt-1'
              : ''}"
            role="listitem"
          >
            {@render panelContent(panelId)}
          </div>
        {/each}
        {#if draggedPanel && dragOverCol === "col3" && dragOverIdx === panelLayout.col3.length}
          <div
            class="h-1 bg-emerald-400 rounded-full mx-4 transition-all"
          ></div>
        {/if}
      </div>
    {/if}
  </div>

  {#if helpSection}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      onclick={() => (helpSection = null)}
      onkeydown={(e) => {
        if (e.key === "Escape") helpSection = null;
      }}
    >
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-lg p-6"
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => e.stopPropagation()}
      >
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-bold text-white">
            {#if helpSection === "files"}{t("flashcards.files")}
            {:else if helpSection === "subtitleOptions"}{t(
                "flashcards.subtitleOptions",
              )}
            {:else if helpSection === "filters"}{t("flashcards.filters")}
            {:else if helpSection === "contextLines"}{t(
                "flashcards.contextLines",
              )}
            {:else if helpSection === "audioClips"}{t(
                "flashcards.generateAudioClips",
              )}
            {:else if helpSection === "snapshots"}{t(
                "flashcards.generateSnapshots",
              )}
            {:else if helpSection === "videoClips"}{t(
                "flashcards.generateVideoClips",
              )}
            {:else if helpSection === "ankiFields"}{t("flashcards.ankiFields")}
            {:else if helpSection === "exportFormat"}{t(
                "flashcards.exportFormat",
              )}
            {:else if helpSection === "cpuCores"}{t("flashcards.cpuCores")}
            {:else if helpSection === "naming"}{t("flashcards.naming")}
            {/if}
          </h2>
          <button
            onclick={() => (helpSection = null)}
            class="text-gray-400 hover:text-white text-xl">✕</button
          >
        </div>
        <div
          class="text-gray-300 text-sm leading-relaxed max-h-[60vh] overflow-y-auto help-content"
        >
          {#if helpSection === "files"}{@html t("flashcards.filesHelp")}
          {:else if helpSection === "subtitleOptions"}{@html t(
              "flashcards.subtitleOptionsHelp",
            )}
          {:else if helpSection === "filters"}{@html t(
              "flashcards.filtersHelp",
            )}
          {:else if helpSection === "contextLines"}{@html t(
              "flashcards.contextLinesHelp",
            )}
          {:else if helpSection === "audioClips"}{@html t(
              "flashcards.generateAudioClipsHelp",
            )}
          {:else if helpSection === "snapshots"}{@html t(
              "flashcards.generateSnapshotsHelp",
            )}
          {:else if helpSection === "videoClips"}{@html t(
              "flashcards.generateVideoClipsHelp",
            )}
          {:else if helpSection === "ankiFields"}{@html t(
              "flashcards.ankiFieldsHelp",
            )}
          {:else if helpSection === "exportFormat"}{@html t(
              "flashcards.exportFormatHelp",
            )}
          {:else if helpSection === "cpuCores"}{@html t(
              "flashcards.cpuCoresHelp",
            )}
          {:else if helpSection === "naming"}{@html t("flashcards.namingHelp")}
          {/if}
        </div>
        <div class="mt-4 flex justify-end">
          <button
            onclick={() => (helpSection = null)}
            class="btn-primary py-1.5 px-4 text-sm">OK</button
          >
        </div>
      </div>
    </div>
  {/if}

  {#if expandedPathField}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-6"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      onclick={() => (expandedPathField = null)}
      onkeydown={(e) => {
        if (e.key === "Escape") expandedPathField = null;
      }}
    >
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl p-5 animate-fade-in"
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => e.stopPropagation()}
      >
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-gray-300">
            {#if expandedPathField === "targetSubs"}{t(
                "flashcards.targetLangSubs",
              )}
            {:else if expandedPathField === "output"}{t("flashcards.outputDir")}
            {:else if expandedPathField === "nativeSubs"}{t(
                "flashcards.nativeLangSubs",
              )}
            {:else if expandedPathField === "media"}{t("flashcards.mediaFile")}
            {/if}
          </h3>
          <button
            onclick={() => (expandedPathField = null)}
            class="text-gray-400 hover:text-white text-lg leading-none"
            >✕</button
          >
        </div>
        <div class="bg-gray-800/80 rounded-lg p-3 border border-gray-700/50">
          <p
            class="text-sm text-white font-mono break-all select-all leading-relaxed"
          >
            {#if expandedPathField === "targetSubs"}{targetSubsPath || "—"}
            {:else if expandedPathField === "output"}{outputDir || "—"}
            {:else if expandedPathField === "nativeSubs"}{nativeSubsPath || "—"}
            {:else if expandedPathField === "media"}{mediaPath || "—"}
            {/if}
          </p>
        </div>
        <div class="mt-3 flex justify-end">
          <button
            onclick={() => (expandedPathField = null)}
            class="btn-primary py-1.5 px-4 text-xs">OK</button
          >
        </div>
      </div>
    </div>
  {/if}
</div>
