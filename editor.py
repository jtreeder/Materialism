#!/usr/bin/env python3
"""
Materialism Data Editor — lightweight local server for editing the HSP database.

Run:  python editor.py
Then open http://localhost:5555 in your browser.

Edits are saved directly to the processed CSV files. Click "Regenerate HTML"
to propagate changes to materialism.html, solvents.html, and polymers.html.
"""

import csv
import io
import json
import os
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = 5555
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHEM_CSV = os.path.join(BASE_DIR, "data", "processed", "hsp_chemicals.csv")
POLY_CSV = os.path.join(BASE_DIR, "data", "processed", "hsp_polymers.csv")


def read_csv(path):
    """Read a CSV file and return (fieldnames, rows)."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames)
        rows = list(reader)
    return fields, rows


def write_csv(path, fields, rows):
    """Write rows back to a CSV file."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def get_editor_html():
    """Return the full editor HTML page."""
    return EDITOR_HTML


class EditorHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Quieter logging
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send_html(get_editor_html())
        elif path == "/api/solvents":
            fields, rows = read_csv(CHEM_CSV)
            self._send_json({"fields": fields, "rows": rows})
        elif path == "/api/polymers":
            fields, rows = read_csv(POLY_CSV)
            self._send_json({"fields": fields, "rows": rows})
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/solvents/save":
            data = json.loads(self._read_body())
            fields, rows = read_csv(CHEM_CSV)
            row_idx = data["row"]
            if 0 <= row_idx < len(rows):
                for key, val in data["updates"].items():
                    if key in fields:
                        rows[row_idx][key] = val
                write_csv(CHEM_CSV, fields, rows)
                self._send_json({"ok": True})
            else:
                self._send_json({"ok": False, "error": "Invalid row index"}, 400)

        elif path == "/api/polymers/save":
            data = json.loads(self._read_body())
            fields, rows = read_csv(POLY_CSV)
            row_idx = data["row"]
            if 0 <= row_idx < len(rows):
                for key, val in data["updates"].items():
                    if key in fields:
                        rows[row_idx][key] = val
                write_csv(POLY_CSV, fields, rows)
                self._send_json({"ok": True})
            else:
                self._send_json({"ok": False, "error": "Invalid row index"}, 400)

        elif path == "/api/solvents/batch":
            data = json.loads(self._read_body())
            fields, rows = read_csv(CHEM_CSV)
            for edit in data.get("edits", []):
                idx = edit["row"]
                if 0 <= idx < len(rows):
                    for key, val in edit["updates"].items():
                        if key in fields:
                            rows[idx][key] = val
            write_csv(CHEM_CSV, fields, rows)
            self._send_json({"ok": True})

        elif path == "/api/polymers/batch":
            data = json.loads(self._read_body())
            fields, rows = read_csv(POLY_CSV)
            for edit in data.get("edits", []):
                idx = edit["row"]
                if 0 <= idx < len(rows):
                    for key, val in edit["updates"].items():
                        if key in fields:
                            rows[idx][key] = val
            write_csv(POLY_CSV, fields, rows)
            self._send_json({"ok": True})

        elif path == "/api/regenerate":
            try:
                result = subprocess.run(
                    [sys.executable, os.path.join(BASE_DIR, "generate_html.py")],
                    capture_output=True, text=True, timeout=60, cwd=BASE_DIR
                )
                self._send_json({
                    "ok": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                })
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)

        else:
            self.send_error(404)


# ===================== EDITOR HTML =====================
EDITOR_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Materialism — View/Edit Data</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #f5f6fa; color: #2d3436; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

.header { background: #fff; padding: 15px 30px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #dfe6e9; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.header h1 { font-size: 1.5rem; color: #e94560; }
.header h1 a { color: #e94560; text-decoration: none; }
.header .actions { display: flex; align-items: center; gap: 12px; }

.toolbar { background: #fff; padding: 10px 30px; display: flex; align-items: center; gap: 14px; border-bottom: 1px solid #dfe6e9; flex-wrap: wrap; }
.toolbar .tabs { display: flex; gap: 0; }
.toolbar .tab { padding: 8px 20px; cursor: pointer; border: none; background: transparent; color: #636e72; font-size: 0.9rem; transition: all 0.2s; border-bottom: 2px solid transparent; }
.toolbar .tab:hover { color: #2d3436; background: #f5f6fa; }
.toolbar .tab.active { color: #e94560; border-bottom-color: #e94560; }
.toolbar input[type="text"] { background: #f5f6fa; border: 2px solid #dfe6e9; color: #2d3436; padding: 8px 14px; border-radius: 6px; width: 300px; font-size: 0.9rem; outline: none; }
.toolbar input[type="text"]:focus { border-color: #e94560; }

.btn { padding: 8px 18px; font-size: 0.85rem; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.2s; }
.btn-primary { background: #e94560; color: white; }
.btn-primary:hover { background: #c73652; }
.btn-secondary { background: #dfe6e9; color: #2d3436; }
.btn-secondary:hover { background: #c8d6db; }
.btn-sm { padding: 4px 10px; font-size: 0.8rem; }

.status { font-size: 0.8rem; color: #636e72; display: flex; align-items: center; gap: 6px; }
.status .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot-saved { background: #00b894; }
.dot-saving { background: #fdcb6e; }
.dot-dirty { background: #e94560; }

.content { padding: 0; }
.table-wrapper { overflow: auto; max-height: calc(100vh - 160px); }

table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
thead { position: sticky; top: 0; z-index: 10; }
th { background: #f0f2f5; color: #e94560; padding: 8px 10px; text-align: left; font-weight: 600; border-bottom: 2px solid #dfe6e9; cursor: pointer; white-space: nowrap; user-select: none; }
th:hover { background: #e8eaed; }
th.sort-asc::after { content: ' ▲'; font-size: 0.7em; }
th.sort-desc::after { content: ' ▼'; font-size: 0.7em; }

td { padding: 0; border-bottom: 1px solid #eee; position: relative; }
td .cell { padding: 6px 8px; min-height: 32px; cursor: text; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 250px; }
td .cell:focus { outline: 2px solid #e94560; outline-offset: -2px; background: #fff8f0; white-space: normal; overflow: visible; }
td .cell.dirty { background: #ffeaa7; }

tr:hover { background: #f8f9fa; }
tr.hidden-row { opacity: 0.45; }
tr.hidden-row:hover { opacity: 0.7; }

.vis-btn { cursor: pointer; border: none; background: transparent; font-size: 1rem; padding: 4px 8px; transition: opacity 0.2s; }
.vis-btn:hover { opacity: 0.6; }

.col-idx { color: #b2bec3; font-size: 0.75rem; font-variant-numeric: tabular-nums; text-align: right; padding: 6px 6px 6px 10px; width: 40px; }

.regen-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 999; justify-content: center; align-items: center; }
.regen-overlay.visible { display: flex; }
.regen-box { background: white; border-radius: 12px; padding: 30px; text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
.regen-box .spinner { width: 30px; height: 30px; border: 3px solid #dfe6e9; border-top-color: #e94560; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 12px; }
@keyframes spin { to { transform: rotate(360deg); } }

.stats-bar { padding: 6px 30px; background: #fff; border-bottom: 1px solid #eee; font-size: 0.8rem; color: #636e72; display: flex; gap: 20px; }
</style>
</head>
<body>

<div class="header">
    <h1><a href="materialism.html">Materialism</a> — View/Edit Data</h1>
    <div class="actions">
        <div class="status" id="save-status"><span class="dot dot-saved"></span> All saved</div>
        <button class="btn btn-primary" onclick="regenerate()">Regenerate HTML</button>
    </div>
</div>

<div class="toolbar">
    <div class="tabs">
        <button class="tab active" onclick="switchTab('solvents')">Solvents</button>
        <button class="tab" onclick="switchTab('polymers')">Polymers</button>
    </div>
    <input type="text" id="filter-input" placeholder="Filter by name, CAS, category..." oninput="applyFilter()">
    <label style="font-size:0.82rem;color:#636e72;display:flex;align-items:center;gap:4px;">
        <input type="checkbox" id="show-hidden" checked onchange="applyFilter()"> Show hidden
    </label>
    <span style="flex:1"></span>
    <span class="stats-info" id="stats-info"></span>
</div>

<div class="content">
    <div class="table-wrapper" id="table-wrapper">
        <table id="data-table">
            <thead id="data-thead"></thead>
            <tbody id="data-tbody"></tbody>
        </table>
    </div>
</div>

<div class="regen-overlay" id="regen-overlay">
    <div class="regen-box">
        <div class="spinner"></div>
        <div id="regen-msg">Regenerating HTML files...</div>
    </div>
</div>

<script>
// ===================== STATE =====================
var activeTab = 'solvents';
var data = { solvents: null, polymers: null };
var dirtyEdits = { solvents: {}, polymers: {} }; // { "rowIdx:field": newValue }
var saveTimer = null;
var sortState = { col: null, asc: true };

// Column configs
var SOLVENT_COLS = [
    { key: 'name', label: 'Name', width: '200px' },
    { key: 'cas_number', label: 'CAS', width: '110px' },
    { key: 'smiles', label: 'SMILES', width: '160px' },
    { key: 'molecular_formula', label: 'Formula', width: '100px' },
    { key: 'delta_d', label: '\u03B4D', width: '60px' },
    { key: 'delta_p', label: '\u03B4P', width: '60px' },
    { key: 'delta_h', label: '\u03B4H', width: '60px' },
    { key: 'molecular_weight', label: 'MW', width: '70px' },
    { key: 'boiling_point', label: 'BP \u00B0C', width: '70px' },
    { key: 'density', label: 'Density', width: '70px' },
    { key: 'molar_volume', label: 'Vm', width: '70px' },
    { key: 'category', label: 'Category', width: '100px' },
    { key: 'ghs_hazard', label: 'GHS', width: '100px' },
    { key: 'source', label: 'Source', width: '80px' },
];

var POLYMER_COLS = [
    { key: 'name', label: 'Name', width: '250px' },
    { key: 'cas_number', label: 'CAS', width: '110px' },
    { key: 'delta_d', label: '\u03B4D', width: '60px' },
    { key: 'delta_p', label: '\u03B4P', width: '60px' },
    { key: 'delta_h', label: '\u03B4H', width: '60px' },
    { key: 'radius', label: 'R\u2080', width: '60px' },
    { key: 'type', label: 'Type', width: '120px' },
    { key: 'source', label: 'Source', width: '80px' },
];

function getCols() {
    return activeTab === 'solvents' ? SOLVENT_COLS : POLYMER_COLS;
}

function getRows() {
    return data[activeTab] ? data[activeTab].rows : [];
}

// ===================== DATA LOADING =====================
function loadData(tab) {
    fetch('/api/' + tab)
        .then(function(r) { return r.json(); })
        .then(function(d) {
            data[tab] = d;
            if (tab === activeTab) renderTable();
        });
}

function switchTab(tab) {
    activeTab = tab;
    sortState = { col: null, asc: true };
    document.querySelectorAll('.toolbar .tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelector('.toolbar .tab[onclick*="' + tab + '"]').classList.add('active');
    renderTable();
}

// ===================== RENDERING =====================
function renderTable() {
    var cols = getCols();
    var rows = getRows();

    // Header
    var thead = document.getElementById('data-thead');
    var hdr = '<tr><th style="width:40px">#</th><th style="width:40px">Vis</th>';
    cols.forEach(function(c) {
        var cls = '';
        if (sortState.col === c.key) cls = sortState.asc ? 'sort-asc' : 'sort-desc';
        hdr += '<th class="' + cls + '" style="width:' + c.width + '" onclick="sortBy(\'' + c.key + '\')">' + c.label + '</th>';
    });
    hdr += '</tr>';
    thead.innerHTML = hdr;

    // Build sorted index
    var indices = [];
    for (var i = 0; i < rows.length; i++) indices.push(i);

    if (sortState.col) {
        var key = sortState.col;
        var dir = sortState.asc ? 1 : -1;
        indices.sort(function(a, b) {
            var va = rows[a][key] || '';
            var vb = rows[b][key] || '';
            var na = parseFloat(va), nb = parseFloat(vb);
            if (!isNaN(na) && !isNaN(nb)) return (na - nb) * dir;
            return va.localeCompare(vb) * dir;
        });
    }

    // Filter
    var filterText = (document.getElementById('filter-input').value || '').toLowerCase();
    var showHidden = document.getElementById('show-hidden').checked;

    var filtered = indices.filter(function(idx) {
        var row = rows[idx];
        var isHidden = (row.hidden || '').toLowerCase();
        isHidden = isHidden === '1' || isHidden === 'true' || isHidden === 'yes';
        if (!showHidden && isHidden) return false;
        if (!filterText) return true;
        var text = '';
        for (var k in row) text += (row[k] || '') + ' ';
        return text.toLowerCase().indexOf(filterText) !== -1;
    });

    // Stats
    var totalHidden = rows.filter(function(r) {
        var h = (r.hidden || '').toLowerCase();
        return h === '1' || h === 'true' || h === 'yes';
    }).length;
    document.getElementById('stats-info').textContent =
        'Showing ' + filtered.length + ' of ' + rows.length +
        (totalHidden > 0 ? ' (' + totalHidden + ' hidden)' : '');

    // Body — render in chunks to stay responsive
    var tbody = document.getElementById('data-tbody');
    tbody.innerHTML = '';

    var CHUNK = 200;
    var pos = 0;

    function renderChunk() {
        var frag = document.createDocumentFragment();
        var end = Math.min(pos + CHUNK, filtered.length);
        for (var fi = pos; fi < end; fi++) {
            var idx = filtered[fi];
            var row = rows[idx];
            var isHidden = (row.hidden || '').toLowerCase();
            isHidden = isHidden === '1' || isHidden === 'true' || isHidden === 'yes';

            var tr = document.createElement('tr');
            tr.dataset.rowIdx = idx;
            if (isHidden) tr.className = 'hidden-row';

            // Row number
            var tdNum = document.createElement('td');
            tdNum.className = 'col-idx';
            tdNum.textContent = idx + 1;
            tr.appendChild(tdNum);

            // Visibility toggle
            var tdVis = document.createElement('td');
            tdVis.style.textAlign = 'center';
            var btn = document.createElement('button');
            btn.className = 'vis-btn';
            btn.textContent = isHidden ? '\uD83D\uDEAB' : '\uD83D\uDC41';
            btn.title = isHidden ? 'Hidden from search — click to unhide' : 'Visible in search — click to hide';
            btn.dataset.rowIdx = idx;
            btn.onclick = function() { toggleHidden(parseInt(this.dataset.rowIdx)); };
            tdVis.appendChild(btn);
            tr.appendChild(tdVis);

            // Data cells
            cols.forEach(function(c) {
                var td = document.createElement('td');
                var div = document.createElement('div');
                div.className = 'cell';
                div.contentEditable = 'true';
                div.spellcheck = false;
                div.textContent = row[c.key] || '';
                div.dataset.rowIdx = idx;
                div.dataset.field = c.key;
                div.style.maxWidth = c.width;
                div.addEventListener('focus', onCellFocus);
                div.addEventListener('blur', onCellBlur);
                div.addEventListener('keydown', onCellKeydown);
                td.appendChild(div);
                tr.appendChild(td);
            });

            frag.appendChild(tr);
        }
        tbody.appendChild(frag);
        pos = end;
        if (pos < filtered.length) requestAnimationFrame(renderChunk);
    }

    renderChunk();
}

// ===================== CELL EDITING =====================
var originalValue = '';

function onCellFocus(e) {
    originalValue = e.target.textContent;
}

function onCellBlur(e) {
    var cell = e.target;
    var newVal = cell.textContent.trim();
    if (newVal !== originalValue) {
        var idx = parseInt(cell.dataset.rowIdx);
        var field = cell.dataset.field;
        // Update local data
        data[activeTab].rows[idx][field] = newVal;
        // Track dirty edit
        var editKey = idx + ':' + field;
        dirtyEdits[activeTab][editKey] = { row: idx, field: field, value: newVal };
        cell.classList.add('dirty');
        scheduleSave();
    }
}

function onCellKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        e.target.blur();
    }
    if (e.key === 'Escape') {
        e.target.textContent = originalValue;
        e.target.blur();
    }
    if (e.key === 'Tab') {
        e.preventDefault();
        e.target.blur();
        // Move to next/prev cell
        var cells = Array.from(document.querySelectorAll('.cell[contenteditable]'));
        var ci = cells.indexOf(e.target);
        var next = e.shiftKey ? ci - 1 : ci + 1;
        if (next >= 0 && next < cells.length) cells[next].focus();
    }
}

// ===================== HIDE/UNHIDE =====================
function toggleHidden(rowIdx) {
    var rows = getRows();
    var current = (rows[rowIdx].hidden || '').toLowerCase();
    var isHidden = current === '1' || current === 'true' || current === 'yes';
    var newVal = isHidden ? '' : '1';
    rows[rowIdx].hidden = newVal;

    var editKey = rowIdx + ':hidden';
    dirtyEdits[activeTab][editKey] = { row: rowIdx, field: 'hidden', value: newVal };
    scheduleSave();
    renderTable();
}

// ===================== AUTO-SAVE =====================
function scheduleSave() {
    setStatus('dirty', 'Unsaved changes');
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(flushSave, 1500);
}

function flushSave() {
    // Batch all dirty edits for each tab
    ['solvents', 'polymers'].forEach(function(tab) {
        var edits = dirtyEdits[tab];
        var keys = Object.keys(edits);
        if (keys.length === 0) return;

        // Build batch payload
        var byRow = {};
        keys.forEach(function(k) {
            var e = edits[k];
            if (!byRow[e.row]) byRow[e.row] = {};
            byRow[e.row][e.field] = e.value;
        });
        var batch = [];
        for (var r in byRow) batch.push({ row: parseInt(r), updates: byRow[r] });

        setStatus('saving', 'Saving...');
        fetch('/api/' + tab + '/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ edits: batch })
        }).then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.ok) {
                // Clear dirty indicators
                document.querySelectorAll('.cell.dirty').forEach(function(c) { c.classList.remove('dirty'); });
                setStatus('saved', 'All saved');
            } else {
                setStatus('dirty', 'Save error');
            }
        }).catch(function() {
            setStatus('dirty', 'Save failed');
        });

        dirtyEdits[tab] = {};
    });
}

function setStatus(state, msg) {
    var el = document.getElementById('save-status');
    var dotCls = state === 'saved' ? 'dot-saved' : state === 'saving' ? 'dot-saving' : 'dot-dirty';
    el.innerHTML = '<span class="dot ' + dotCls + '"></span> ' + msg;
}

// ===================== SORTING =====================
function sortBy(col) {
    if (sortState.col === col) {
        sortState.asc = !sortState.asc;
    } else {
        sortState.col = col;
        sortState.asc = true;
    }
    renderTable();
}

// ===================== FILTER =====================
function applyFilter() {
    renderTable();
}

// ===================== REGENERATE =====================
function regenerate() {
    // Flush any pending saves first
    if (saveTimer) { clearTimeout(saveTimer); flushSave(); }

    var overlay = document.getElementById('regen-overlay');
    var msg = document.getElementById('regen-msg');
    overlay.classList.add('visible');
    msg.textContent = 'Regenerating HTML files...';

    setTimeout(function() {
        fetch('/api/regenerate', { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.ok) {
                msg.innerHTML = '<span style="color:#00b894;font-size:1.3rem">&#10003;</span> Done!<br><small style="color:#636e72">' +
                    (d.stdout || '').replace(/\n/g, '<br>') + '</small>';
            } else {
                msg.innerHTML = '<span style="color:#d63031">Error</span><br><small>' +
                    (d.stderr || d.error || '').replace(/\n/g, '<br>') + '</small>';
            }
            setTimeout(function() { overlay.classList.remove('visible'); }, 2000);
        }).catch(function(err) {
            msg.innerHTML = '<span style="color:#d63031">Network error</span>';
            setTimeout(function() { overlay.classList.remove('visible'); }, 2000);
        });
    }, 100);
}

// ===================== INIT =====================
loadData('solvents');
loadData('polymers');
</script>
</body>
</html>"""


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), EditorHandler)
    print(f"Materialism Data Editor running at http://localhost:{PORT}")
    print(f"  Solvents CSV: {CHEM_CSV}")
    print(f"  Polymers CSV: {POLY_CSV}")
    print(f"  Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
