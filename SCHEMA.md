# City of Mist Threat/Danger Parsing Schema

**Version:** 1.0 (strict heuristic)
**Source:** SuperGrok analysis of City of Mist rulebook
**Scope:** Mundane Dangers, Mythos Power Sets, and full Rifts

## 1. Threat Structure Pattern

### Sections in EVERY threat (100% consistent):
- **Title line:** `NAME [★ rating]` (★ = 0–5, + for Mythos Power Sets)
- **1–3 paragraph flavor description** (always immediately after title)
- **Spectrum line** (always the very next non-empty line after description)
- **Move list** (bullets + any **bold** blocks)

### Optional sections:
- Collective / Vehicle / Team notes (lines starting with **Collective:**, **Vehicle:**, **Team:**)
- Special/Custom rules (**Bold Name:** blocks)
- Sub-rules
- Background variants
- Mythos Power Set header (no spectrum line; rating is additive +★)

### Guaranteed order:
```
IF title detected → THEN description paragraphs
IF description ends → THEN spectrum line (must parse)
IF spectrum parsed → THEN optional Collective/Vehicle notes
IF notes done → THEN **Custom rules** (if any)
IF custom done → THEN bullet moves list (end of entry)
```

**Edge case:** Mythos Power Sets skip spectrum line entirely (rating = +★ only).

## 2. Move Classification Rules

### Plain-text detectable markers:

| Move Type | Detection Rule | Example | Confidence |
|-----------|----------------|---------|------------|
| **CUSTOM** | Starts with `**NAME:**` (bold markdown) | `**Lawsuit:** When you give...` | 100% |
| **HARD** | Contains "(hard move)" text | `• Disappear (hard move)` | 100% |
| **SOFT** | Bullet (`•` or `-`) WITHOUT "(hard move)" | `• Ask for documents (vexed-2)` | 100% |

### Additional rules:
- IF move contains `(Deny Them Something They Want)` OR `create a new Danger:` → add `effectType: "special"` flag
- IF move marked `(optional)` → `optional: true`
- IF move is under "Choose the members..." list → treat as child moves under `subMoves[]`

### Regex patterns:
- Custom: `^\s*\*\*.*:\s*`
- Hard: `/hard move/i`
- Soft: Default for bullets

**Confidence:** 98%

## 3. Spectrum Rules

### Format variations:
- Slash-separated: `SPECTRUM 3 / SPECTRUM2 5`
- Space-separated: `HURT OR SUBDUE 3 THREATEN -`
- Multi-word names: `HURT OR SUBDUE 1`
- Immune/unlimited: `BRIBE -` (dash = null)

### Parsing algorithm:
1. Take line after description
2. Split on ` / ` or space
3. For each token:
   - Name = everything before last space/token
   - Value = last token (number or `-` → `null`)

### Rules:
- 1–4 spectrums per threat (never 0 except Mythos Power Sets)
- Value range: 1–6 or `-` (null)
- Dash (`-`) means immune/unlimited → `maxTier: null`

### JSON transformation:
```json
"spectrums": [
  { "name": "CORRUPT", "max": 3 },
  { "name": "HURT OR SUBDUE", "max": null }
]
```

**Confidence:** 100%

## 4. Tags and Status Rules

### Detection:
- **Status tags:** Anything in `(hyphenated-lowercase-number)`
  - Examples: `(vexed-by-bureaucracy-2)`, `(legal-trouble-3)`, `(gunshot-wound-3)`
  - Tier is the final digit
- **Story tags:** Plain words without trailing number
  - Examples: `(temporary)`, `*press pass*`, `stone (temporary)`, `keys to the safe`

### Distinction rule:
- IF token ends with `-N` (N=digit) → status tag
- ELSE → story tag

### Auto-generation:
- Scan entire entry (description + moves)
- Extract unique status strings
- Store in `system.statusTags[]` and `system.storyTags[]`

**Edge cases:** `I'm-listening-2`, `pumped-full-of-lead-4` — still status if ends in `-N`

**Confidence:** 95%

## 5. Foundry JSON Field Mapping

### Target structure:
```json
{
  "name": "Corporate Lawyer",
  "type": "danger",
  "img": "icons/...jpg",
  "system": {
    "dangerRating": 3,
    "description": "This slimy corporate legal advisor...",
    "spectrums": [
      { "name": "CORRUPT", "maxTier": 3 },
      { "name": "BRIBE", "maxTier": null }
    ],
    "collective": {
      "sizeFactor": 1,
      "note": "This collective has many members..."
    },
    "customAbilities": [
      {
        "name": "Lawsuit",
        "description": "When you give the Corporate Lawyer...",
        "trigger": "When..."
      }
    ],
    "moves": [
      {
        "type": "soft",
        "description": "Use the court system (legal-trouble-3)",
        "status": "legal-trouble-3",
        "effect": "createDanger"
      }
    ],
    "statusTags": ["legal-trouble-3", "guilty-3"],
    "storyTags": ["press pass"],
    "notes": "You can also use this Danger profile..."
  }
}
```

### Required fields:
- `name`, `dangerRating`, `description`, `spectrums`, `moves[]` (at least one)

### Optional fields:
- `collective`, `customAbilities`, `statusTags`, `storyTags`

### Data transformations:
- Rating: count `★` symbols (each = +1)
- `-` spectrum value → `null`
- Status extraction: regex `/\(([\w-]+-\d+)\)/g`

### Edge cases:
- Mythos Power Sets: `dangerRating` = additive (`+1`), `spectrums: []`
- Heist Team: `moves` array + nested `subMoves[]`
- Time Bomb / House Fire: high-tier explosion moves

**Confidence:** 90% (logical inference from City of Mist conventions)

---

## Implementation Status

### ✅ Completed:
- Move type detection (schema-based)
- Spectrum extraction (slash/space separated)
- Spectrum null handling (dash = null)
- Name extraction with OCR cleanup
- Description extraction
- Tag auto-generation

### ⚠️ Partial:
- Custom abilities (extracted as custom moves, not separate)
- Collective fields (not yet extracted)
- Effect flags (createDanger, optional, etc.)

### ❌ Not Implemented:
- Mythos Power Set special handling
- Sub-moves for Heist Teams
- Vehicle-specific fields
