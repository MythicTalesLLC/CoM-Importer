// ============================================================================
// CoM – Sort Items into Type Subfolders  (Foundry v13+)
// ============================================================================
// Moves world Items into subfolders organised by CoM item type.
//
// Structure created:
//   📁 City of Mist  (parent – name is configurable in the dialog)
//     📁 Theme Kits
//     📁 Themebooks
//     📁 Tags
//     📁 GM Moves
//     📁 Player Moves
//     📁 Statuses
//     📁 Spectrums
//     📁 Clues
//     📁 Juice
//     📁 Improvements
//     📁 Abilities
//     📁 Other          ← anything with an unrecognised type
//
// OPTIONS (in dialog):
//   • Parent folder name
//   • Include items already in a folder, or only root-level items
//   • Dry-run preview mode (shows what WOULD move without touching anything)
// ============================================================================

(async () => {
    // ── Type → Folder name mapping ────────────────────────────────────────────
    const TYPE_MAP = {
        theme: "Theme Kits",
        themebook: "Themebooks",
        tag: "Tags",
        gmmove: "GM Moves",
        move: "Player Moves",
        status: "Statuses",
        spectrum: "Spectrums",
        clue: "Clues",
        juice: "Juice",
        improvement: "Improvements",
        ability: "Abilities",
    };

    // Folder colours (hex) per type — purely cosmetic, tweak freely
    const TYPE_COLORS = {
        theme: "#7b4ea0",
        themebook: "#5a3478",
        tag: "#2e7d32",
        gmmove: "#b71c1c",
        move: "#1565c0",
        status: "#e65100",
        spectrum: "#006064",
        clue: "#4e342e",
        juice: "#f9a825",
        improvement: "#37474f",
        ability: "#880e4f",
        _other: "#424242",
    };

    const PARENT_COLOR = "#1a1a2e";

    // ── 1. Count items by type for the preview ───────────────────────────────
    const allItems = [...game.items];
    const rootItems = allItems.filter(i => !i.folder);
    const anyItems = allItems.length > 0;

    if (!anyItems) {
        return ui.notifications.warn("No items found in the world.");
    }

    function buildTypeSummary(items) {
        const counts = {};
        for (const item of items) {
            const bucket = TYPE_MAP[item.type] ? item.type : "_other";
            counts[bucket] = (counts[bucket] ?? 0) + 1;
        }
        return counts;
    }

    const rootSummary = buildTypeSummary(rootItems);
    const allSummary = buildTypeSummary(allItems);

    function summaryHtml(counts) {
        if (!Object.keys(counts).length) return "<em>none</em>";
        return Object.entries(counts)
            .sort(([a], [b]) => (TYPE_MAP[a] ?? "Other").localeCompare(TYPE_MAP[b] ?? "Other"))
            .map(([t, n]) => {
                const folderName = TYPE_MAP[t] ?? "Other";
                const color = TYPE_COLORS[t] ?? TYPE_COLORS._other;
                return `<li>
          <span style="display:inline-block;width:10px;height:10px;border-radius:2px;
            background:${color};margin-right:5px;vertical-align:middle;"></span>
          <strong>${n}</strong> → <em>${folderName}</em>
        </li>`;
            })
            .join("");
    }

    // ── 2. Dialog ─────────────────────────────────────────────────────────────
    const dialogContent = `
<style>
  #com-sort-wrap { font-family: var(--font-primary); }
  #com-sort-wrap label.section {
    display: block; font-weight: bold; margin-top: 12px; margin-bottom: 4px;
  }
  #com-sort-wrap input[type=text] {
    width: 100%; padding: 4px 6px; border: 1px solid #aaa;
    border-radius: 3px; box-sizing: border-box;
  }
  .com-scope-row { display: flex; gap: 16px; margin-top: 4px; }
  .com-scope-row label { cursor: pointer; font-size: 13px; }
  #com-sort-preview {
    margin-top: 8px; max-height: 180px; overflow-y: auto;
    border: 1px solid #ddd; border-radius: 4px; padding: 6px 10px;
    background: rgba(0,0,0,.03);
  }
  #com-sort-preview ul { list-style: none; margin: 0; padding: 0; line-height: 1.9; }
  #com-dry-row { margin-top: 10px; }
  #com-dry-row label { cursor: pointer; font-size: 12px; color: #555; }
  .com-warn { color: #b55; font-size: 12px; margin-top: 6px; }
</style>
<div id="com-sort-wrap">

  <label class="section" for="com-parent-name">Parent folder name</label>
  <input type="text" id="com-parent-name" value="City of Mist">

  <label class="section">Scope</label>
  <div class="com-scope-row">
    <label>
      <input type="radio" name="com-scope" value="root" checked>
      Root items only <small>(${rootItems.length} items)</small>
    </label>
    <label>
      <input type="radio" name="com-scope" value="all">
      All world items <small>(${allItems.length} items)</small>
    </label>
  </div>

  <label class="section">Preview</label>
  <div id="com-sort-preview">
    <ul id="com-preview-list">${summaryHtml(rootSummary)}</ul>
  </div>

  <div id="com-dry-row">
    <label>
      <input type="checkbox" id="com-dry-run">
      Dry run — log to console only, don't move anything
    </label>
  </div>

  <p class="com-warn">
    ⚠ Items already in the correct type subfolder won't be touched.
    Re-running is safe.
  </p>
</div>`;

    const choice = await new Promise(resolve => {
        const d = new Dialog({
            title: "CoM – Sort Items into Type Folders",
            content: dialogContent,
            buttons: {
                sort: {
                    label: "Sort Items",
                    callback: html => resolve({
                        parentName: html[0].querySelector("#com-parent-name").value.trim() || "City of Mist",
                        scope: html[0].querySelector('input[name="com-scope"]:checked').value,
                        dryRun: html[0].querySelector("#com-dry-run").checked,
                    }),
                },
                cancel: {
                    label: "Cancel",
                    callback: () => resolve(null),
                },
            },
            default: "sort",
            render: html => {
                // Live-update preview when scope changes
                html[0].querySelectorAll('input[name="com-scope"]').forEach(radio => {
                    radio.addEventListener("change", () => {
                        const isAll = radio.value === "all" && radio.checked;
                        html[0].querySelector("#com-preview-list").innerHTML =
                            summaryHtml(isAll ? allSummary : rootSummary);
                    });
                });
            },
            close: () => resolve(null),
        }, { width: 460 });
        d.render(true);
    });

    if (!choice) return;

    const { parentName, scope, dryRun } = choice;
    const targetItems = scope === "all" ? allItems : rootItems;

    if (!targetItems.length) {
        return ui.notifications.warn("No items in the selected scope.");
    }

    // ── 3. Get or create the parent folder ───────────────────────────────────
    async function getOrCreateFolder(name, parentId, color) {
        const existing = game.folders.find(
            f => f.type === "Item" && f.name === name && (f.folder?.id ?? null) === parentId
        );
        if (existing) return existing;
        if (dryRun) {
            console.log(`[CoM Sort | DRY RUN] Would create folder "${name}" (parent: ${parentId ?? "root"})`);
            return { id: `dry-${name}`, name };
        }
        return await Folder.create({
            name,
            type: "Item",
            parent: parentId ?? null,
            color: color ?? "#444444",
            sorting: "a",
        });
    }

    // ── 4. Build / look up all needed folders ────────────────────────────────
    // Determine which types are actually present in targetItems
    const presentTypes = new Set(targetItems.map(i => TYPE_MAP[i.type] ? i.type : "_other"));

    const parentFolder = await getOrCreateFolder(parentName, null, PARENT_COLOR);
    const parentId = dryRun ? `dry-${parentName}` : parentFolder.id;

    const subFolders = {}; // type → folder
    for (const type of presentTypes) {
        const folderName = TYPE_MAP[type] ?? "Other";
        const color = TYPE_COLORS[type] ?? TYPE_COLORS._other;
        subFolders[type] = await getOrCreateFolder(folderName, parentId, color);
    }

    // ── 5. Bucket items and build update payload ──────────────────────────────
    const updates = [];
    const skipped = [];

    for (const item of targetItems) {
        const bucket = TYPE_MAP[item.type] ? item.type : "_other";
        const destFolder = subFolders[bucket];
        if (!destFolder) continue;

        const destId = dryRun ? destFolder.id : destFolder.id;

        // Skip if already in the correct folder
        if (!dryRun && item.folder?.id === destId) {
            skipped.push(item.name);
            continue;
        }

        if (dryRun) {
            console.log(
                `[CoM Sort | DRY RUN] "${item.name}" (${item.type}) → "${destFolder.name}"`
            );
        } else {
            updates.push({ _id: item.id, folder: destId });
        }
    }

    // ── 6. Apply updates in one batch ────────────────────────────────────────
    if (!dryRun && updates.length) {
        await Item.updateDocuments(updates);
    }

    // ── 7. Report ─────────────────────────────────────────────────────────────
    if (dryRun) {
        const n = targetItems.length - skipped.length;
        ui.notifications.info(
            `[Dry Run] Would move ${n} item${n !== 1 ? "s" : ""} into type subfolders under "${parentName}". See console (F12) for details.`
        );
        return;
    }

    const moved = updates.length;
    const already = skipped.length;
    const parts = [
        moved ? `${moved} moved` : null,
        already ? `${already} already sorted` : null,
    ].filter(Boolean).join(", ");

    ui.notifications.info(`✓ Sort complete: ${parts} → "${parentName}".`);
    console.log(`[CoM Sort] ${parts}`, { moved: updates.map(u => u._id), skipped });
})();
