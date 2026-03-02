import { mount } from "svelte";
import "./app.css";
import App from "./App.svelte";

// Prevent WebKit from handling dropped files (triggers GStreamer errors).
// Only intercept OS file drops (dataTransfer contains "Files"); internal DOM
// drags (panel rearrangement) are left untouched.
// Must use capture phase to intercept before WebKit's native media handling.
for (const evt of ["dragenter", "dragover", "drop"] as const) {
  document.addEventListener(
    evt,
    (e) => {
      if ((e as DragEvent).dataTransfer?.types?.includes("Files")) {
        e.preventDefault();
        e.stopPropagation();
      }
    },
    { capture: true },
  );
}

// Debug: global error handler
window.onerror = (msg, src, line, col, err) => {
  document.body.innerHTML = `<pre style="color:red;padding:2em;white-space:pre-wrap">ERROR: ${msg}\nSource: ${src}:${line}:${col}\n${err?.stack || ''}</pre>`;
};
window.onunhandledrejection = (e) => {
  document.body.innerHTML += `<pre style="color:orange;padding:2em;white-space:pre-wrap">UNHANDLED REJECTION: ${e.reason}\n${e.reason?.stack || ''}</pre>`;
};

try {
  const app = mount(App, {
    target: document.getElementById("app")!,
  });
  // @ts-ignore
  window.__app = app;
} catch (e: any) {
  document.body.innerHTML = `<pre style="color:red;padding:2em;white-space:pre-wrap">MOUNT ERROR: ${e.message}\n${e.stack}</pre>`;
}

export default {};
