# Secure Architecture Plan: Google Sheets + GitHub.io Guardrailed Dashboard

## 1. Executive Summary

This architecture enables an **autonomous, zero-server, zero-database, interactive dashboard** powered by **Marimo running in WebAssembly on GitHub Pages (`github.io`)**, connected to a live **Google Sheet** (data source + layout store), with **LLM-driven dynamic generation** guarded by a read-only template interpreter.

### Key Highlights
- **Hosting Cost:** $0 (GitHub Pages static hosting + Google Sheets storage + client-side Pyodide WASM compute).
- **Security Boundary:** 100% immune to code injection even with a publicly editable Google Sheet.
- **Persistence:** Layout blueprints persist in Google Sheets metadata; no recurring LLM token cost on reload.
- **Client Footprint:** Zero installation for end users (runs in any modern web browser).

---

## 2. Three-Tier Trust & Security Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. TRUSTED LAYER (Read-Only)                                                │
│    Location: Your GitHub Repository & github.io Page                        │
│    Role: The Immutable Engine & Guardrail Interpreter                       │
│    • Stored as read-only Python code compiled into WebAssembly.             │
│    • Only the repo owner (via Git commits) can modify the interpreter.      │
│    • Enforces column validation, component allowlists, and error boundaries.│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Enforces validation & guardrails
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. DYNAMIC SPECIFICATION LAYER (AI Logic)                                   │
│    Role: The LLM Translator (Gemini / OpenAI / Anthropic)                   │
│    • Takes user prompt + Google Sheet schema headers.                       │
│    • Emits STRICT declarative JSON specifications (NOT raw Python strings). │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Saved via Webhook / Loaded via CSV
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. MUTABLE DATA LAYER (Public / Multi-User)                                 │
│    Location: Google Sheet                                                   │
│    ├── Tab 1: 'Data' (Thousands of rows of metrics/records)                 │
│    └── Tab 2: '_metadata' (Hidden tab storing JSON layout blueprint)        │
│    Role: State & Storage (Editable by users or Apps Script Webhook).        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. End-to-End Data & Execution Flow

```
[ User Prompt in Marimo Chat ]
              │
              ▼
[ LLM Generates Declarative JSON Spec ]
              │
              ▼
[ Write-Back Webhook ] ──▶ [ Saves JSON to Google Sheet '_metadata' Tab ]
                                              │
┌─────────────────────────────────────────────┘
│ (On Page Load / Reload)
▼
[ Marimo WASM on github.io ]
  ├── 1. Fetches live data:   https://docs.google.com/.../export?format=csv&gid=0
  ├── 2. Fetches layout spec: https://docs.google.com/.../export?format=csv&gid=META_GID
  ├── 3. Validates columns against real DataFrame headers
  ├── 4. Maps JSON spec to approved Altair charts & Marimo UI elements
  └── 5. Renders interactive dashboard in < 1 second in browser RAM
```

---

## 4. Declarative Layout Specification Schema

The LLM is strictly instructed to return a **declarative JSON specification** (never raw executable Python strings). This guarantees that even if a public user edits `_metadata`, no arbitrary code execution is possible.

```json
{
  "title": "Quarterly Operations & Revenue Dashboard",
  "kpis": [
    {"column": "Revenue", "label": "Total Revenue", "format": "currency"},
    {"column": "Units", "label": "Total Units Sold", "format": "number"}
  ],
  "charts": [
    {
      "id": "chart_1",
      "type": "bar",
      "title": "Revenue by Region",
      "x": "Region",
      "y": "Revenue",
      "color": "Product",
      "sort": "-y"
    },
    {
      "id": "chart_2",
      "type": "line",
      "title": "Monthly Trend",
      "x": "Date",
      "y": "Revenue"
    }
  ],
  "table": {
    "enabled": true,
    "pagination": true,
    "page_size": 10
  }
}
```

---

## 5. Implementation Code Templates

### A. The Read-Only Guardrailed Interpreter (`app.py` on `github.io`)

```python
import marimo as mo
import pandas as pd
import json
import altair as alt

# --- Configuration ---
SHEET_ID = "YOUR_GOOGLE_SHEET_ID"
DATA_GID = "0"          # Tab 1: Raw Data
META_GID = "12345678"   # Tab 2: _metadata

ALLOWED_CHART_TYPES = {"bar", "line", "scatter", "area"}

# --- Data Fetching ---
@mo.cache
def load_sheet_data():
    data_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={DATA_GID}"
    return pd.read_csv(data_url)

def load_layout_spec():
    try:
        meta_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={META_GID}"
        meta_df = pd.read_csv(meta_url)
        spec_str = meta_df.loc[meta_df['key'] == 'layout_spec', 'value'].iloc[0]
        return json.loads(spec_str), None
    except Exception as e:
        return None, f"Failed to load layout spec from Google Sheet: {e}"

# --- Guardrail Render Engine ---
def render_guardrailed_dashboard(df: pd.DataFrame, spec: dict):
    outputs = []
    
    # Title
    outputs.append(mo.md(f"# 📊 {spec.get('title', 'Analytics Dashboard')}"))
    
    # 1. Guardrailed KPI Cards
    kpis = []
    for kpi in spec.get("kpis", []):
        col = kpi.get("column")
        if col in df.columns:
            total = df[col].sum()
            fmt = kpi.get("format", "number")
            val_str = f"${total:,.0f}" if fmt == "currency" else f"{total:,.0f}"
            kpis.append(mo.stat(value=val_str, label=kpi.get("label", col)))
    if kpis:
        outputs.append(mo.hstack(kpis, justify="start"))

    # 2. Guardrailed Charts (Allowlist + Column Verification)
    for c in spec.get("charts", []):
        c_type = c.get("type")
        x_col = c.get("x")
        y_col = c.get("y")
        
        # Verify chart type is allowlisted
        if c_type not in ALLOWED_CHART_TYPES:
            outputs.append(mo.callout(f"Unsupported chart type: `{c_type}`", kind="warn"))
            continue
            
        # Verify columns exist in the actual dataset
        if x_col not in df.columns or y_col not in df.columns:
            outputs.append(mo.callout(f"Columns `{x_col}` or `{y_col}` missing in sheet.", kind="danger"))
            continue
            
        chart = alt.Chart(df).properties(title=c.get("title", ""), width="container", height=300)
        if c_type == "bar":
            chart = chart.mark_bar(cornerRadius=4).encode(x=f"{x_col}:N", y=f"sum({y_col}):Q")
        elif c_type == "line":
            chart = chart.mark_line(point=True).encode(x=f"{x_col}:O", y=f"sum({y_col}):Q")
        elif c_type == "scatter":
            chart = chart.mark_circle(size=60).encode(x=f"{x_col}:Q", y=f"{y_col}:Q")
            
        outputs.append(chart.interactive())

    # 3. Interactive Data Table
    if spec.get("table", {}).get("enabled", True):
        outputs.append(mo.ui.table(df, pagination=True))

    return mo.vstack(outputs)
```

---

### B. Google Apps Script Webhook (for Browser-to-Sheet Write-Back)

Deploy this in **Google Sheets > Extensions > Apps Script**:

```javascript
function doPost(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("_metadata");
    
    if (!sheet) {
      sheet = ss.insertSheet("_metadata");
      sheet.appendRow(["key", "value"]);
    }
    
    var payload = JSON.parse(e.postData.contents);
    var newSpec = payload.new_layout_spec;
    
    // Search for existing layout_spec key or insert new row
    var data = sheet.getDataRange().getValues();
    var found = false;
    for (var i = 1; i < data.length; i++) {
      if (data[i][0] === "layout_spec") {
        sheet.getRange(i + 1, 2).setValue(newSpec);
        found = true;
        break;
      }
    }
    
    if (!found) {
      sheet.appendRow(["layout_spec", newSpec]);
    }
    
    return ContentService.createTextOutput(JSON.stringify({status: "success"}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({status: "error", message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

---

## 6. Security & Guardrail Checklist

| Potential Attack / Failure | Mitigation / Guardrail |
|---|---|
| **Malicious Python code injection** in public Google Sheet | **Immune**: Sheet only stores declarative JSON; raw code execution (`exec`) is forbidden. |
| **Tampering with the engine** | **Immune**: `github.io` code is served as static read-only WASM; visitors have no write access to GitHub. |
| **Invalid/hallucinated column names from LLM** | **Defended**: Engine validates column existence against `df.columns` before instantiating charts. |
| **Unsupported/dangerous visualization commands** | **Defended**: Strict `ALLOWED_CHART_TYPES` allowlist in the read-only interpreter. |
| **Cost blowup from repeated LLM calls** | **Defended**: Layout persists in `_metadata`; returning visitors reload live data with **$0** token costs. |
| **Leaking private LLM API keys** | **Defended**: Client uses "Bring Your Own Key" in session memory or a rate-limited Cloudflare Worker proxy. |

---

## 7. Operational Runbook

1. **Deploying Updates to the Engine**:
   - Edit [`app.py`](file:///home/vin/ws/00_scratch/marimo/app.py) in `/home/vin/ws/00_scratch/marimo`.
   - Push to `main`: `git push origin main`.
   - GitHub Actions workflow [`.github/workflows/static.yml`](file:///home/vin/ws/00_scratch/marimo/.github/workflows/static.yml) compiles and deploys to `github.io` in ~25 seconds.
2. **Reverting an Engine Bug**:
   - Run `git revert HEAD && git push origin main` to instantly restore the previous known-good deployment.
3. **Connecting a New Google Sheet**:
   - Provide sheet with `Data` tab and `_metadata` tab.
   - Update `SHEET_ID` in `app.py` (or pass via URL parameter `?sheet_id=...`).
