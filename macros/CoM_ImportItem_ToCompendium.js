// ============================================================================
// CoM – Import Item(s) to Compendium
// ============================================================================
// Imports individual City of Mist items (themes, tags, moves, statuses,
// spectrums, themebooks) into any compendium you choose.
//
// METHODS:
//   • Paste JSON directly into the text area
//   • Click "Browse…" to pick a .json file from your filesystem
//   • Drag-and-drop a .json file onto the drop zone
//
// The JSON may be a single item object { "name":…, "type":…, "system":… }
// or an array of items.  All items are buffered for review before import.
//
// SETUP:  Create a new Script macro in Foundry, paste this file, and save.
// ============================================================================

(async () => {
    // ── 1. Build compendium options ──────────────────────────────────────────
    const itemPacks = game.packs.filter(p => p.metadata.type === "Item");
    if (!itemPacks.length) {
        return ui.notifications.error("No Item compendiums found in this world.");
    }

    const packOptions = itemPacks
        .map(p => {
            const label = `${p.metadata.label} [${p.collection}]`;
            return `<option value="${p.collection}">${label}</option>`;
        })
        .join("\n");

    // Supported CoM item types for display labelling only
    const TYPE_LABELS = {
        theme: "Theme Kit",
        themebook: "Themebook",
        tag: "Tag",
        gmmove: "GM Move",
        move: "Player Move",
        status: "Status",
        spectrum: "Spectrum",
        clue: "Clue",
        juice: "Juice",
        improvement: "Improvement",
        ability: "Ability",
    };

    // ── 2. Render dialog ─────────────────────────────────────────────────────
    const dialogContent = `
<style>
  #com-import-wrap { font-family: var(--font-primary); }
  #com-import-wrap label { display:block; font-weight:bold; margin-top:10px; margin-bottom:3px; }
  #com-import-wrap select { width:100%; padding:4px; }
  #com-import-dropzone {
    border: 2px dashed #888; border-radius:6px; padding:14px; text-align:center;
    color:#666; cursor:pointer; transition: border-color .2s, background .2s;
    margin-top:6px;
  }
  #com-import-dropzone.drag-over {
    border-color: #4a90d9; background: rgba(74,144,217,.1); color:#222;
  }
  #com-import-dropzone input[type=file] { display:none; }
  #com-json-area {
    width:100%; height:200px; font-family:monospace; font-size:11px;
    padding:6px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box;
    margin-top:4px; resize:vertical;
  }
  #com-preview { margin-top:8px; font-size:12px; color:#333; }
  #com-preview ul { max-height:100px; overflow-y:auto; margin:4px 0 0 16px; padding:0; }
  #com-import-err { color:#c00; font-size:12px; margin-top:4px; min-height:16px; }
</style>
<div id="com-import-wrap">
  <label for="com-pack-select">Target Compendium</label>
  <select id="com-pack-select">${packOptions}</select>

  <label>JSON Source</label>
  <div id="com-import-dropzone" title="Drop a .json file here or click Browse">
    <span id="com-dz-text">Drop a <strong>.json</strong> file here, or</span>
    <br><br>
    <button type="button" id="com-browse-btn" style="cursor:pointer;">Browse…</button>
    <input type="file" id="com-file-input" accept=".json,application/json">
  </div>

  <label for="com-json-area">— or paste JSON here —</label>
  <textarea id="com-json-area" placeholder='{ "name":"…","type":"theme","system":{…} }  or  [ {…}, {…} ]'></textarea>

  <div id="com-preview"></div>
  <div id="com-import-err"></div>
</div>`;

    let parsedItems = null; // validated item array, set before import

    await new Promise(resolve => {
        const d = new Dialog({
            title: "CoM – Import Item(s) to Compendium",
            content: dialogContent,
            buttons: {
                preview: {
                    label: "Preview",
                    callback: html => {
                        _parseAndPreview(html);
                        return false; // keep dialog open
                    },
                },
                import: {
                    label: "Import",
                    callback: async html => {
                        const items = _parseAndPreview(html);
                        if (!items) return false;
                        parsedItems = items;
                        resolve(html);
                    },
                },
                cancel: {
                    label: "Cancel",
                    callback: () => resolve(null),
                },
            },
            default: "import",
            render: html => _setupHandlers(html),
            close: () => resolve(null),
        }, { width: 520 });
        d.render(true);
    });

    if (!parsedItems) return;

    // ── 3. Import ─────────────────────────────────────────────────────────────
    const packId = document.getElementById("com-pack-select")?.value;
    if (!packId) return ui.notifications.error("No compendium selected.");
    const pack = game.packs.get(packId);
    if (!pack) return ui.notifications.error(`Compendium "${packId}" not found.`);
    if (pack.locked) {
        ui.notifications.warn(`Compendium "${pack.metadata.label}" is locked. Unlock it first.`);
        return;
    }

    let imported = 0;
    let failed = 0;
    for (const itemData of parsedItems) {
        try {
            const payload = foundry.utils.deepClone(itemData);
            delete payload._id; // let Foundry assign a fresh ID
            await Item.create(payload, { pack: packId });
            imported++;
        } catch (err) {
            failed++;
            console.error(`[CoM Import] Failed to create "${itemData.name}":`, err);
        }
    }

    const total = parsedItems.length;
    if (failed === 0) {
        ui.notifications.info(
            `✓ Imported ${imported} item${imported !== 1 ? "s" : ""} into "${pack.metadata.label}".`
        );
    } else {
        ui.notifications.warn(
            `Imported ${imported}/${total} items into "${pack.metadata.label}" — ${failed} failed (see console).`
        );
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    function _setupHandlers(html) {
        const dropzone = html[0].querySelector("#com-import-dropzone");
        const fileInput = html[0].querySelector("#com-file-input");
        const browseBtn = html[0].querySelector("#com-browse-btn");
        const textarea = html[0].querySelector("#com-json-area");

        // Browse button → open file picker
        browseBtn.addEventListener("click", e => {
            e.stopPropagation();
            fileInput.click();
        });

        // Clicking the dropzone also opens file picker
        dropzone.addEventListener("click", e => {
            if (e.target !== browseBtn) fileInput.click();
        });

        // File selected via browser
        fileInput.addEventListener("change", () => {
            const file = fileInput.files[0];
            if (file) _readFile(file, textarea, html);
        });

        // Drag-and-drop events on drop zone
        dropzone.addEventListener("dragover", e => {
            e.preventDefault();
            dropzone.classList.add("drag-over");
            html[0].querySelector("#com-dz-text").textContent = "Release to load file…";
        });
        dropzone.addEventListener("dragleave", () => {
            dropzone.classList.remove("drag-over");
            html[0].querySelector("#com-dz-text").innerHTML =
                "Drop a <strong>.json</strong> file here, or";
        });
        dropzone.addEventListener("drop", e => {
            e.preventDefault();
            dropzone.classList.remove("drag-over");
            html[0].querySelector("#com-dz-text").innerHTML =
                "Drop a <strong>.json</strong> file here, or";
            const file = e.dataTransfer.files[0];
            if (file) _readFile(file, textarea, html);
        });

        // Also allow dropping directly onto the textarea
        textarea.addEventListener("dragover", e => e.preventDefault());
        textarea.addEventListener("drop", e => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if (file) _readFile(file, textarea, html);
        });
    }

    function _readFile(file, textarea, html) {
        if (!file.name.endsWith(".json") && file.type !== "application/json") {
            _setErr(html, "Only .json files are supported.");
            return;
        }
        const reader = new FileReader();
        reader.onload = ev => {
            textarea.value = ev.target.result;
            _parseAndPreview(html);
        };
        reader.readAsText(file);
    }

    function _parseAndPreview(html) {
        const errEl = html[0].querySelector("#com-import-err");
        const previewEl = html[0].querySelector("#com-preview");
        const raw = html[0].querySelector("#com-json-area").value.trim();

        errEl.textContent = "";
        previewEl.innerHTML = "";

        if (!raw) {
            _setErr(html, "No JSON provided.");
            return null;
        }

        let data;
        try { data = JSON.parse(raw); }
        catch (e) {
            _setErr(html, `JSON parse error: ${e.message}`);
            return null;
        }

        const items = Array.isArray(data) ? data : [data];

        // Basic validation: each entry must have name + type
        const bad = items.filter(i => !i?.name || !i?.type);
        if (bad.length) {
            _setErr(html, `${bad.length} item(s) missing "name" or "type" field.`);
            return null;
        }

        // Build preview list
        const typeCount = {};
        for (const i of items) typeCount[i.type] = (typeCount[i.type] || 0) + 1;
        const summary = Object.entries(typeCount)
            .map(([t, n]) => `${n}× ${TYPE_LABELS[t] ?? t}`)
            .join(", ");

        const listItems = items
            .slice(0, 30)
            .map(i => `<li>${_esc(i.name)} <em style="color:#888">[${_esc(i.type)}]</em></li>`)
            .join("");
        const more = items.length > 30 ? `<li>… and ${items.length - 30} more</li>` : "";

        previewEl.innerHTML = `
      <strong>Ready to import: ${items.length} item${items.length !== 1 ? "s" : ""}</strong>
      (${summary})
      <ul>${listItems}${more}</ul>`;

        return items;
    }

    function _setErr(html, msg) {
        const el = html[0].querySelector("#com-import-err");
        if (el) el.textContent = msg;
    }

    function _esc(str) {
        return String(str ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }
})();
