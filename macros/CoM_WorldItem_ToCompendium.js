// ============================================================================
// CoM – Send World Items to Compendium  (drag-and-drop or picker)
// ============================================================================
// Sends existing world items into a compendium of your choice.
//
// METHODS:
//   A) Drag-and-drop items from any Foundry sidebar / character sheet onto the
//      "Drop items here" zone in the dialog.
//   B) Pick from a searchable list of all world items.
//
// Only Items are supported (not Actors, Journals, etc.).
// Duplicate handling: optionally overwrite items with the same name + type.
// ============================================================================

(async () => {
    // ── 1. Build compendium options ──────────────────────────────────────────
    const itemPacks = game.packs.filter(p => p.metadata.type === "Item");
    if (!itemPacks.length) {
        return ui.notifications.error("No Item compendiums found in this world.");
    }

    // Sort: world compendiums first, then modules, then systems
    const sortedPacks = [...itemPacks].sort((a, b) => {
        const rank = s => s === "world" ? 0 : s === "module" ? 1 : 2;
        return rank(a.metadata.packageType) - rank(b.metadata.packageType)
            || a.metadata.label.localeCompare(b.metadata.label);
    });

    const packOptions = sortedPacks
        .map(p => {
            const scope = p.metadata.packageType === "world" ? "🌍" :
                p.metadata.packageType === "module" ? "📦" : "⚙";
            return `<option value="${p.collection}">${scope} ${p.metadata.label} [${p.collection}]</option>`;
        })
        .join("\n");

    // ── 2. Gather world items for the picker ─────────────────────────────────
    const worldItems = [...game.items].sort((a, b) => a.name.localeCompare(b.name));

    const itemOptionRows = worldItems.map(item =>
        `<option value="${item.id}">[${item.type}] ${item.name}</option>`
    ).join("\n");

    // ── 3. Dialog content ────────────────────────────────────────────────────
    const dialogContent = `
<style>
  #com-send-wrap { font-family: var(--font-primary); }
  #com-send-wrap label.section { display:block; font-weight:bold; margin-top:10px; margin-bottom:3px; }
  #com-send-wrap select { width:100%; padding:4px; }
  #com-dropzone {
    border:2px dashed #888; border-radius:6px; padding:16px 10px;
    text-align:center; color:#666; min-height:64px;
    transition:border-color .2s, background .2s;
    margin-top:4px;
  }
  #com-dropzone.drag-over {
    border-color:#4a90d9; background:rgba(74,144,217,.12); color:#222;
  }
  #com-queue { list-style:none; margin:8px 0 0 0; padding:0; }
  #com-queue li {
    display:flex; align-items:center; justify-content:space-between;
    padding:2px 6px; font-size:12px; border-radius:3px;
    background:rgba(0,0,0,.04); margin-bottom:2px;
  }
  #com-queue li button {
    background:none; border:none; cursor:pointer; color:#c00;
    padding:0 4px; font-size:14px; line-height:1;
  }
  #com-picker-row { display:flex; gap:6px; margin-top:4px; }
  #com-item-search { flex:1; padding:4px; border:1px solid #ccc; border-radius:3px; }
  #com-item-select { flex:2; padding:4px; border:1px solid #ccc; border-radius:3px; }
  #com-add-btn { white-space:nowrap; padding:4px 10px; cursor:pointer; }
  .com-opt-row { display:flex; align-items:center; gap:10px; margin-top:8px; }
  #com-send-err { color:#c00; font-size:12px; margin-top:4px; min-height:14px; }
</style>
<div id="com-send-wrap">
  <label class="section" for="com-pack-sel">Target Compendium</label>
  <select id="com-pack-sel">${packOptions}</select>

  <!-- ── Drag-and-drop zone ── -->
  <label class="section">Drag items here to queue them</label>
  <div id="com-dropzone">
    <span id="com-dz-hint">Drag items from the sidebar, a sheet, or any compendium onto this area</span>
    <ul id="com-queue"></ul>
  </div>

  <!-- ── Picker (world items) ── -->
  <label class="section">Or pick from world items</label>
  <div class="com-picker-row" id="com-picker-row">
    <input type="text" id="com-item-search" placeholder="Filter by name…">
    <select id="com-item-select" size="1">
      ${worldItems.length
            ? itemOptionRows
            : '<option disabled>(no world items)</option>'}
    </select>
    <button type="button" id="com-add-btn">Add →</button>
  </div>

  <div class="com-opt-row">
    <label style="cursor:pointer;font-size:12px;">
      <input type="checkbox" id="com-overwrite"> Overwrite duplicates (same name + type)
    </label>
  </div>

  <div id="com-send-err"></div>
</div>`;

    // Queue: Map<itemId → {id, name, type, source: "world"|"compendium", data}>
    const queue = new Map();

    const result = await new Promise(resolve => {
        const d = new Dialog({
            title: "CoM – Send Items to Compendium",
            content: dialogContent,
            buttons: {
                send: {
                    label: `Send to Compendium`,
                    callback: html => {
                        if (!queue.size) {
                            html[0].querySelector("#com-send-err").textContent =
                                "Nothing in the queue yet. Add items first.";
                            return false;
                        }
                        resolve({
                            packId: html[0].querySelector("#com-pack-sel").value,
                            overwrite: html[0].querySelector("#com-overwrite").checked,
                            items: [...queue.values()],
                        });
                    },
                },
                cancel: {
                    label: "Cancel",
                    callback: () => resolve(null),
                },
            },
            default: "send",
            render: html => _setupHandlers(html),
            close: () => resolve(null),
        }, { width: 540 });
        d.render(true);
    });

    if (!result) return;

    // ── 4. Import queued items ────────────────────────────────────────────────
    const { packId, overwrite, items } = result;
    const pack = game.packs.get(packId);
    if (!pack) return ui.notifications.error(`Compendium "${packId}" not found.`);
    if (pack.locked) {
        return ui.notifications.warn(`"${pack.metadata.label}" is locked. Unlock it first.`);
    }

    await pack.getIndex();
    const existingIdx = new Map(pack.index.map(e => [`${e.name}||${e.type}`, e._id]));

    let imported = 0, skipped = 0, failed = 0;

    for (const entry of items) {
        const key = `${entry.name}||${entry.type}`;
        if (!overwrite && existingIdx.has(key)) { skipped++; continue; }

        try {
            if (overwrite && existingIdx.has(key)) {
                const doc = await pack.getDocument(existingIdx.get(key));
                if (doc) await doc.delete();
            }
            // Fetch full item data if we only have a stub
            let payload = entry.data;
            if (!payload) {
                const worldItem = game.items.get(entry.id);
                if (!worldItem) { failed++; continue; }
                payload = worldItem.toObject();
            }
            payload = foundry.utils.deepClone(payload);
            delete payload._id;
            await Item.create(payload, { pack: packId });
            imported++;
        } catch (err) {
            failed++;
            console.error(`[CoM Send] Failed "${entry.name}":`, err);
        }
    }

    const parts = [
        `${imported} sent`,
        skipped ? `${skipped} skipped (duplicate)` : null,
        failed ? `${failed} failed` : null,
    ].filter(Boolean).join(", ");

    if (failed === 0) {
        ui.notifications.info(`✓ ${parts} → "${pack.metadata.label}".`);
    } else {
        ui.notifications.warn(`Done with errors: ${parts} (see console).`);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    function _setupHandlers(html) {
        const dropzone = html[0].querySelector("#com-dropzone");
        const queueEl = html[0].querySelector("#com-queue");
        const searchEl = html[0].querySelector("#com-item-search");
        const selectEl = html[0].querySelector("#com-item-select");
        const addBtn = html[0].querySelector("#com-add-btn");
        const errEl = html[0].querySelector("#com-send-err");

        // ── Drop zone: accept Foundry item drag events ──
        dropzone.addEventListener("dragover", e => {
            e.preventDefault();
            dropzone.classList.add("drag-over");
        });
        dropzone.addEventListener("dragleave", e => {
            if (!dropzone.contains(e.relatedTarget))
                dropzone.classList.remove("drag-over");
        });
        dropzone.addEventListener("drop", async e => {
            e.preventDefault();
            dropzone.classList.remove("drag-over");
            errEl.textContent = "";

            // Foundry encodes drag data as JSON in the text/plain transfer
            let dragData = null;
            try {
                const raw = e.dataTransfer.getData("text/plain");
                if (raw) dragData = JSON.parse(raw);
            } catch (_) { /* not JSON */ }

            // Also try the application/json type
            if (!dragData) {
                try {
                    const raw = e.dataTransfer.getData("application/json");
                    if (raw) dragData = JSON.parse(raw);
                } catch (_) { /* ignore */ }
            }

            if (!dragData) {
                errEl.textContent = "Could not read drag data. Make sure you're dragging a Foundry item.";
                return;
            }

            await _resolveAndQueue(dragData, queueEl, errEl);
        });

        // ── Picker: filter and add ──
        searchEl.addEventListener("input", () => {
            const q = searchEl.value.toLowerCase();
            for (const opt of selectEl.options) {
                opt.hidden = q && !opt.text.toLowerCase().includes(q);
            }
            // Select first visible option
            const firstVisible = [...selectEl.options].find(o => !o.hidden);
            if (firstVisible) selectEl.value = firstVisible.value;
        });

        addBtn.addEventListener("click", () => {
            const id = selectEl.value;
            if (!id) return;
            const item = game.items.get(id);
            if (!item) return;
            _enqueue({ id: item.id, name: item.name, type: item.type, data: null }, queueEl);
        });
    }

    async function _resolveAndQueue(dragData, queueEl, errEl) {
        // dragData may contain: { type, uuid, id, pack, ... }
        const dtype = dragData.type;
        if (dtype && dtype !== "Item") {
            errEl.textContent = `Dropped a "${dtype}" — only Items are supported.`;
            return;
        }

        let item = null;
        let itemData = null;

        // Try UUID first (v10+)
        if (dragData.uuid) {
            try {
                item = await fromUuid(dragData.uuid);
            } catch (_) { /* ignore */ }
        }

        // Fallback: world item by id
        if (!item && dragData.id) {
            item = game.items.get(dragData.id);
        }

        // Fallback: compendium item
        if (!item && dragData.pack && dragData.id) {
            const srcPack = game.packs.get(dragData.pack);
            if (srcPack) {
                try { item = await srcPack.getDocument(dragData.id); } catch (_) { }
            }
        }

        if (!item) {
            errEl.textContent = `Could not resolve dropped item. UUID: ${dragData.uuid ?? "—"}`;
            return;
        }

        itemData = item.toObject ? item.toObject() : { ...item };
        _enqueue({ id: item.id ?? dragData.id, name: item.name, type: item.type, data: itemData }, queueEl);
    }

    function _enqueue(entry, queueEl) {
        if (queue.has(entry.id)) return; // already queued
        queue.set(entry.id, entry);

        const li = document.createElement("li");
        li.dataset.id = entry.id;
        li.innerHTML = `
      <span><em style="color:#888;">[${_esc(entry.type)}]</em> ${_esc(entry.name)}</span>
      <button type="button" title="Remove from queue" data-id="${_esc(entry.id)}">✕</button>`;
        li.querySelector("button").addEventListener("click", () => {
            queue.delete(entry.id);
            li.remove();
        });
        queueEl.appendChild(li);
    }

    function _esc(str) {
        return String(str ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }
})();
