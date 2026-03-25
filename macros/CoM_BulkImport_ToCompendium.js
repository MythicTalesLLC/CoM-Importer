// ============================================================================
// CoM – Bulk Import from Exported JSON Array File
// ============================================================================
// Imports every item from a multi-item JSON array such as:
//   • city_of_mist_everything_foundry.json   (theme kits)
//   • city-of-mist-compendium-foundry.json   (themebooks)
//   • Any array-format output from the CoM Importer tool
//
// METHODS:
//   • Drag-and-drop the .json file onto the drop zone
//   • Click "Browse…" to select the file
//   • Paste the JSON array in the text area
//
// FILTERING:
//   Optionally filter to only import items of specific types (theme, gmmove, etc.)
//   Leave all checkboxes checked to import everything in the file.
//
// DUPLICATE HANDLING:
//   Items with the same name+type already in the compendium are SKIPPED unless
//   you tick "Overwrite duplicates".
// ============================================================================

(async () => {
    const LEGACY_SYSTEM_ID = "city-of-mist";
    const TARGET_SYSTEM_ID = "city-of-mist-ii";

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

    const ALL_TYPES = ["theme", "themebook", "tag", "gmmove", "move", "status", "spectrum",
        "clue", "juice", "improvement", "ability"];

    const typeCheckboxes = ALL_TYPES.map(t =>
        `<label style="display:inline-block;margin:2px 8px 2px 0;">
       <input type="checkbox" class="com-type-cb" value="${t}" checked> ${t}
     </label>`
    ).join("");

    // ── 2. Render dialog ─────────────────────────────────────────────────────
    const dialogContent = `
<style>
  #com-bulk-wrap { font-family: var(--font-primary); }
  #com-bulk-wrap label.section { display:block; font-weight:bold; margin-top:10px; margin-bottom:3px; }
  #com-bulk-wrap select { width:100%; padding:4px; }
  #com-bulk-dropzone {
    border:2px dashed #888; border-radius:6px; padding:12px; text-align:center;
    color:#666; cursor:pointer; transition:border-color .2s,background .2s;
  }
  #com-bulk-dropzone.drag-over { border-color:#4a90d9; background:rgba(74,144,217,.1); color:#222; }
  #com-bulk-dropzone input[type=file] { display:none; }
  #com-bulk-textarea {
    width:100%; height:140px; font-family:monospace; font-size:11px;
    padding:6px; border:1px solid #ccc; border-radius:4px;
    box-sizing:border-box; resize:vertical; margin-top:4px;
  }
  .com-type-filter { margin-top:4px; line-height:1.9; }
  #com-bulk-progress { font-size:12px; margin-top:6px; min-height:14px; color:#444; }
  #com-bulk-err { color:#c00; font-size:12px; margin-top:4px; min-height:14px; }
  .com-opt-row { display:flex; align-items:center; gap:10px; margin-top:6px; }
</style>
<div id="com-bulk-wrap">
  <label class="section" for="com-bulk-pack">Target Compendium</label>
  <select id="com-bulk-pack">${packOptions}</select>

  <label class="section">JSON File</label>
  <div id="com-bulk-dropzone" title="Drop a .json file here or click Browse">
    Drop a <strong>.json</strong> file here, or
    <br><br>
    <button type="button" id="com-bulk-browse" style="cursor:pointer;">Browse…</button>
    <input type="file" id="com-bulk-file" accept=".json,application/json">
  </div>

  <label class="section" for="com-bulk-textarea">— or paste JSON array —</label>
  <textarea id="com-bulk-textarea" placeholder="[ { &quot;name&quot;:…, &quot;type&quot;:&quot;theme&quot;, … }, … ]"></textarea>

  <label class="section">Import types</label>
  <div class="com-type-filter">
    <button type="button" id="com-all-btn" style="font-size:11px;padding:1px 6px;">All</button>
    <button type="button" id="com-none-btn" style="font-size:11px;padding:1px 6px;">None</button>
    ${typeCheckboxes}
  </div>

  <div class="com-opt-row">
    <label style="cursor:pointer;">
      <input type="checkbox" id="com-overwrite"> Overwrite duplicates (same name + type)
    </label>
  </div>

  <div id="com-bulk-progress"></div>
  <div id="com-bulk-err"></div>
</div>`;

    let parsedItems = null;

    await new Promise(resolve => {
        const d = new Dialog({
            title: "CoM – Bulk Import to Compendium",
            content: dialogContent,
            buttons: {
                preview: {
                    label: "Preview",
                    callback: html => { _parseAndPreview(html); return false; },
                },
                import: {
                    label: "Import All",
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
        }, { width: 580 });
        d.render(true);
    });

    if (!parsedItems) return;

    // ── 3. Gather settings from (now closed) dialog ──────────────────────────
    // We captured the HTML reference; read values before the dialog is garbage-collected.
    // However, since resolve() closes the dialog, we need to read values inside the
    // import callback. Wrap them into parsedItems as metadata.
    const { items, packId, overwrite } = parsedItems;

    const pack = game.packs.get(packId);
    if (!pack) return ui.notifications.error(`Compendium "${packId}" not found.`);
    if (pack.locked) {
        return ui.notifications.warn(`Compendium "${pack.metadata.label}" is locked. Unlock it first.`);
    }

    // Build existing name+type index if overwrite is off
    let existingIndex = null;
    if (!overwrite) {
        await pack.getIndex();
        // Index only has _id/name/type/img – name+type is enough
        existingIndex = new Set(pack.index.map(e => `${e.name}||${e.type}`));
    }

    let imported = 0, skipped = 0, failed = 0;
    const total = items.length;

    for (const itemData of items) {
        const key = `${itemData.name}||${itemData.type}`;

        // Skip duplicates
        if (!overwrite && existingIndex?.has(key)) {
            skipped++;
            continue;
        }

        try {
            const payload = foundry.utils.deepClone(itemData);
            delete payload._id;

            // Overwrite: delete existing item first
            if (overwrite && existingIndex?.has(key)) {
                const existing = pack.index.find(e => `${e.name}||${e.type}` === key);
                if (existing) {
                    const doc = await pack.getDocument(existing._id);
                    if (doc) await doc.delete();
                }
            }

            await Item.create(payload, { pack: packId });
            imported++;
        } catch (err) {
            failed++;
            console.error(`[CoM Bulk Import] Failed "${itemData.name}" (${itemData.type}):`, err);
        }
    }

    const parts = [
        `${imported} imported`,
        skipped ? `${skipped} skipped (duplicate)` : null,
        failed ? `${failed} failed` : null,
    ].filter(Boolean).join(", ");

    if (failed === 0) {
        ui.notifications.info(`✓ Bulk import complete: ${parts} → "${pack.metadata.label}".`);
    } else {
        ui.notifications.warn(`Bulk import done with errors: ${parts} (see console).`);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    function _setupHandlers(html) {
        const dropzone = html[0].querySelector("#com-bulk-dropzone");
        const fileInput = html[0].querySelector("#com-bulk-file");
        const browseBtn = html[0].querySelector("#com-bulk-browse");
        const textarea = html[0].querySelector("#com-bulk-textarea");

        browseBtn.addEventListener("click", e => { e.stopPropagation(); fileInput.click(); });
        dropzone.addEventListener("click", e => { if (e.target !== browseBtn) fileInput.click(); });

        fileInput.addEventListener("change", () => {
            if (fileInput.files[0]) _readFile(fileInput.files[0], textarea, html);
        });

        dropzone.addEventListener("dragover", e => {
            e.preventDefault(); dropzone.classList.add("drag-over");
        });
        dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
        dropzone.addEventListener("drop", e => {
            e.preventDefault(); dropzone.classList.remove("drag-over");
            if (e.dataTransfer.files[0]) _readFile(e.dataTransfer.files[0], textarea, html);
        });
        textarea.addEventListener("dragover", e => e.preventDefault());
        textarea.addEventListener("drop", e => {
            e.preventDefault();
            if (e.dataTransfer.files[0]) _readFile(e.dataTransfer.files[0], textarea, html);
        });

        // Type filter buttons
        html[0].querySelector("#com-all-btn").addEventListener("click", () =>
            html[0].querySelectorAll(".com-type-cb").forEach(cb => cb.checked = true)
        );
        html[0].querySelector("#com-none-btn").addEventListener("click", () =>
            html[0].querySelectorAll(".com-type-cb").forEach(cb => cb.checked = false)
        );
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
        const errEl = html[0].querySelector("#com-bulk-err");
        const progEl = html[0].querySelector("#com-bulk-progress");
        errEl.textContent = "";
        progEl.innerHTML = "";

        const raw = html[0].querySelector("#com-bulk-textarea").value.trim();
        if (!raw) { _setErr(html, "No JSON provided."); return null; }

        let data;
        try { data = JSON.parse(raw); }
        catch (e) { _setErr(html, `JSON parse error: ${e.message}`); return null; }

        const allItems = Array.isArray(data) ? data : [data];

        // Apply type filter
        const checkedTypes = new Set(
            [...html[0].querySelectorAll(".com-type-cb:checked")].map(cb => cb.value)
        );
        const items = allItems
            .map(item => normalizeLegacySystemData(item))
            .filter(i => checkedTypes.has(i?.type));

        const ignored = allItems.length - items.length;
        const typeCount = {};
        for (const i of items) typeCount[i.type] = (typeCount[i.type] || 0) + 1;
        const summary = Object.entries(typeCount).map(([t, n]) => `${n}× ${t}`).join(", ");

        progEl.innerHTML = items.length
            ? `<strong>Will import ${items.length} item${items.length !== 1 ? "s" : ""}</strong>`
            + (summary ? ` (${summary})` : "")
            + (ignored ? `; ${ignored} filtered out` : "")
            : `<span style="color:#c00">No items match the selected types.</span>`;

        if (!items.length) return null;

        // Bundle metadata needed after dialog closes
        const packId = html[0].querySelector("#com-bulk-pack").value;
        const overwrite = html[0].querySelector("#com-overwrite").checked;
        return { items, packId, overwrite };
    }

    function _setErr(html, msg) {
        const el = html[0].querySelector("#com-bulk-err");
        if (el) el.textContent = msg;
    }

    function normalizeLegacySystemData(value) {
        if (Array.isArray(value)) {
            return value.map(entry => normalizeLegacySystemData(entry));
        }

        if (value && typeof value === "object") {
            return Object.fromEntries(
                Object.entries(value).map(([key, entryValue]) => {
                    const normalizedKey = key === LEGACY_SYSTEM_ID ? TARGET_SYSTEM_ID : key;
                    return [normalizedKey, normalizeLegacySystemData(entryValue)];
                })
            );
        }

        if (value === LEGACY_SYSTEM_ID) {
            return TARGET_SYSTEM_ID;
        }

        return value;
    }
})();
