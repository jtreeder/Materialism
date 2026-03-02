IMPORT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Materialism — Import</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #f0f2f5; color: #2d3436; font-family: 'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height: 100vh; display: flex; flex-direction: column; }
.header { background: #1a1a2e; padding: 14px 28px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
.header h1 { font-size: 1.35rem; color: #fff; font-weight: 700; letter-spacing: 0.01em; }
.header h1 span { color: #e94560; }
.header .nav-links { display: flex; align-items: center; gap: 18px; font-size: 0.88rem; }
.header .nav-links a { color: #adb5bd; text-decoration: none; transition: color 0.2s; }
.header .nav-links a:hover { color: #fff; }
.header .nav-links .sep { color: #4a4a6a; }
.page-body { display: flex; flex: 1; min-height: 0; }
.sidebar { width: 260px; flex-shrink: 0; background: #fff; border-right: 1px solid #dfe6e9; padding: 18px 14px; overflow-y: auto; }
.sidebar h2 { font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.08em; color: #636e72; margin-bottom: 14px; font-weight: 600; }
.sidebar .step-item { display: flex; align-items: flex-start; gap: 10px; padding: 8px 6px; border-radius: 5px; margin-bottom: 2px; font-size: 0.82rem; color: #636e72; transition: background 0.15s; }
.sidebar .step-item.active { background: #fff5f7; color: #e94560; font-weight: 600; }
.sidebar .step-item.done { color: #27ae60; }
.sidebar .step-item .step-num { width: 22px; height: 22px; border-radius: 50%; background: #f0f2f5; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 700; flex-shrink: 0; color: #636e72; }
.sidebar .step-item.active .step-num { background: #e94560; color: #fff; }
.sidebar .step-item.done .step-num { background: #27ae60; color: #fff; }
.main-content { flex: 1; padding: 24px 28px; overflow-y: auto; }
.card { background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); padding: 24px; margin-bottom: 20px; }
.card h2 { font-size: 1.05rem; color: #2d3436; margin-bottom: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
.card h2 .badge { font-size: 0.72rem; background: #e94560; color: #fff; padding: 2px 7px; border-radius: 10px; font-weight: 600; }
.upload-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.upload-zone { border: 2px dashed #dfe6e9; border-radius: 8px; padding: 32px 20px; text-align: center; cursor: pointer; transition: all 0.2s; position: relative; }
.upload-zone:hover, .upload-zone.drag-over { border-color: #e94560; background: #fff5f7; }
.upload-zone.has-file { border-color: #27ae60; background: #f0faf4; }
.upload-zone .uz-icon { font-size: 2rem; margin-bottom: 10px; }
.upload-zone .uz-title { font-size: 0.95rem; font-weight: 600; color: #2d3436; margin-bottom: 6px; }
.upload-zone .uz-hint { font-size: 0.78rem; color: #636e72; }
.upload-zone .uz-filename { font-size: 0.82rem; color: #27ae60; margin-top: 8px; font-weight: 600; }
.upload-zone input[type=file] { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.meta-form { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.meta-form .full-row { grid-column: 1 / -1; }
.form-group label { display: block; font-size: 0.8rem; font-weight: 600; color: #636e72; margin-bottom: 5px; }
.form-group input { width: 100%; padding: 8px 11px; border: 1px solid #dfe6e9; border-radius: 5px; font-size: 0.87rem; font-family: inherit; transition: border-color 0.2s; }
.form-group input:focus { outline: none; border-color: #e94560; box-shadow: 0 0 0 2px rgba(233,69,96,0.1); }
.form-group input.invalid { border-color: #e74c3c; }
.form-group .hint { font-size: 0.72rem; color: #b2bec3; margin-top: 4px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 9px 20px; border: none; border-radius: 6px; font-size: 0.88rem; font-family: inherit; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.btn-primary { background: #e94560; color: #fff; }
.btn-primary:hover { background: #d63851; }
.btn-primary:disabled { background: #b2bec3; cursor: not-allowed; }
.btn-secondary { background: #fff; color: #636e72; border: 1px solid #dfe6e9; }
.btn-secondary:hover { background: #f0f2f5; }
.btn-success { background: #27ae60; color: #fff; }
.btn-success:hover { background: #219653; }
.btn-warning { background: #f39c12; color: #fff; }
.btn-warning:hover { background: #d68910; }
.btn-danger { background: #e74c3c; color: #fff; }
.btn-danger:hover { background: #c0392b; }
.btn-sm { padding: 5px 12px; font-size: 0.78rem; }
.btn-row { display: flex; align-items: center; gap: 10px; margin-top: 18px; flex-wrap: wrap; }
#section-upload { display: block; }
#section-meta { display: none; }
#section-progress { display: none; }
#section-results { display: none; }
.audit-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; margin-top: 10px; }
.audit-table th { background: #f0f2f5; padding: 6px 10px; text-align: left; font-weight: 600; color: #636e72; border-bottom: 2px solid #dfe6e9; }
.audit-table td { padding: 5px 10px; border-bottom: 1px solid #f0f2f5; }
.audit-table .ok { color: #27ae60; }
.audit-table .warn { color: #f39c12; }
.audit-table .err { color: #e74c3c; }
.progress-section { }
.step-tracker { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 14px; }
.step-chip { padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; background: #f0f2f5; color: #636e72; transition: all 0.3s; }
.step-chip.active { background: #fff3cd; color: #856404; }
.step-chip.done { background: #d5f5e3; color: #1a7a45; }
.step-chip.error { background: #fde8e8; color: #c0392b; }
.progress-bar-wrap { background: #eee; border-radius: 6px; height: 12px; margin: 12px 0; overflow: hidden; }
.progress-bar-fill { height: 100%; background: linear-gradient(90deg, #27ae60, #2ecc71); border-radius: 6px; transition: width 0.4s ease; width: 0%; }
.progress-label { font-size: 0.8rem; color: #636e72; margin-bottom: 8px; }
.log-box { background: #0d1117; border-radius: 6px; padding: 12px 14px; height: 200px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 0.75rem; color: #39d353; }
.log-box .log-line { line-height: 1.5; }
.log-box .log-warn { color: #f39c12; }
.log-box .log-err { color: #e74c3c; }
.log-box .log-info { color: #58a6ff; }
.log-box .log-gray { color: #6e7681; }
.ctrl-row { display: flex; gap: 8px; margin-top: 12px; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; margin-bottom: 18px; }
.stat-box { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 14px; text-align: center; }
.stat-box .stat-val { font-size: 1.8rem; font-weight: 700; color: #e94560; line-height: 1; }
.stat-box .stat-label { font-size: 0.75rem; color: #636e72; margin-top: 4px; }
.tabs { display: flex; border-bottom: 2px solid #dfe6e9; margin-bottom: 16px; }
.tab { padding: 8px 20px; cursor: pointer; font-size: 0.88rem; color: #636e72; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.2s; }
.tab:hover { color: #2d3436; }
.tab.active { color: #e94560; border-bottom-color: #e94560; font-weight: 600; }
.tab-content { display: none; }
.tab-content.active { display: block; }
.results-table-wrap { overflow: auto; max-height: 420px; border: 1px solid #dfe6e9; border-radius: 6px; }
.results-table { width: max-content; min-width: 100%; border-collapse: collapse; font-size: 0.78rem; }
.results-table th { background: #f0f2f5; padding: 7px 10px; text-align: left; font-weight: 600; color: #636e72; position: sticky; top: 0; z-index: 2; cursor: pointer; white-space: nowrap; border-bottom: 2px solid #dfe6e9; }
.results-table th:hover { background: #e8eaed; }
.results-table th.sort-asc::after { content: ' ▲'; font-size: 0.65em; color: #e94560; }
.results-table th.sort-desc::after { content: ' ▼'; font-size: 0.65em; color: #e94560; }
.results-table td { padding: 5px 10px; border-bottom: 1px solid #f0f2f5; white-space: nowrap; }
.results-table tr:hover td { background: #f8f9fa; }
.conf-pill { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 0.72rem; font-weight: 700; }
.conf-high { background: #d5f5e3; color: #1a7a45; }
.conf-med { background: #fef3cd; color: #856404; }
.conf-low { background: #fde3d0; color: #9c4a00; }
.conf-vlow { background: #fde8e8; color: #c0392b; }
.flag-icon { display: inline-block; width: 14px; height: 14px; border-radius: 50%; background: #e74c3c; color: #fff; font-size: 0.6rem; text-align: center; line-height: 14px; font-weight: 700; cursor: help; margin-left: 2px; }
.flag-warn { background: #f39c12; }
.review-row td { background: #fff8e1 !important; }
.review-override { width: 14px; height: 14px; cursor: pointer; }
.commit-section { padding: 16px 0 0; border-top: 1px solid #dfe6e9; margin-top: 18px; }
.commit-section h3 { font-size: 0.9rem; font-weight: 700; color: #2d3436; margin-bottom: 10px; }
.commit-options { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }
.commit-options label { display: flex; align-items: center; gap: 8px; font-size: 0.83rem; color: #2d3436; cursor: pointer; }
.commit-options input[type=checkbox] { width: 15px; height: 15px; accent-color: #e94560; cursor: pointer; }
.commit-msg { display: none; margin-top: 14px; padding: 14px; background: #d5f5e3; border-radius: 6px; color: #1a7a45; font-size: 0.88rem; }
.commit-msg a { color: #1a7a45; font-weight: 700; }
.quality-report { display: none; }
.quality-report .qr-section { margin-bottom: 18px; }
.quality-report .qr-section h4 { font-size: 0.85rem; font-weight: 700; color: #2d3436; margin-bottom: 8px; }
.quality-report table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.quality-report table th { background: #f0f2f5; padding: 6px 10px; text-align: left; }
.quality-report table td { padding: 5px 10px; border-bottom: 1px solid #f0f2f5; }
.issues-list { list-style: none; }
.issues-list li { padding: 5px 0; font-size: 0.82rem; border-bottom: 1px solid #f0f2f5; display: flex; gap: 10px; }
.issues-list li .issue-type { font-weight: 700; min-width: 80px; }
.issues-list li .issue-type.err { color: #e74c3c; }
.issues-list li .issue-type.warn { color: #f39c12; }
.hidden { display: none !important; }
.tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 0.68rem; font-weight: 600; margin-right: 3px; }
.tag-carcinogen { background: #fde8e8; color: #c0392b; }
.tag-repro { background: #fde8e8; color: #9b1c31; }
.tag-flam { background: #fff3cd; color: #856404; }
.tag-toxic { background: #fef0e0; color: #8a4800; }
.ich-1 { background: #fde8e8; color: #c0392b; font-size: 0.68rem; padding: 1px 5px; border-radius: 3px; font-weight: 600; }
.ich-2a { background: #fef0e0; color: #8a4800; font-size: 0.68rem; padding: 1px 5px; border-radius: 3px; font-weight: 600; }
.ich-2b { background: #fef3cd; color: #856404; font-size: 0.68rem; padding: 1px 5px; border-radius: 3px; font-weight: 600; }
.ich-3 { background: #d5f5e3; color: #1a7a45; font-size: 0.68rem; padding: 1px 5px; border-radius: 3px; font-weight: 600; }
.spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #dfe6e9; border-top-color: #e94560; border-radius: 50%; animation: spin 0.7s linear infinite; vertical-align: middle; margin-right: 6px; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="header">
  <h1>Materialism &mdash; <span>Import</span></h1>
  <div class="nav-links">
    <a href="database.html">Database</a>
    <span class="sep">|</span>
    <a href="materialism.html">Visualization</a>
  </div>
</div>
<div class="page-body">
  <div class="sidebar">
    <h2>Pipeline Steps</h2>
    <div class="step-item" id="sbar-upload"><div class="step-num">1</div>Upload Files</div>
    <div class="step-item" id="sbar-audit"><div class="step-num">2</div>Load &amp; Audit</div>
    <div class="step-item" id="sbar-meta"><div class="step-num">3</div>Dataset Metadata</div>
    <div class="step-item" id="sbar-names"><div class="step-num">4</div>Name Cleaning</div>
    <div class="step-item" id="sbar-cas"><div class="step-num">5</div>CAS Validation</div>
    <div class="step-item" id="sbar-pubchem"><div class="step-num">6</div>PubChem Lookup</div>
    <div class="step-item" id="sbar-props"><div class="step-num">7</div>Physical Props</div>
    <div class="step-item" id="sbar-ghs"><div class="step-num">8</div>GHS Hazard</div>
    <div class="step-item" id="sbar-ich"><div class="step-num">9</div>ICH Q3C Class</div>
    <div class="step-item" id="sbar-classyfire"><div class="step-num">10</div>ClassyFire</div>
    <div class="step-item" id="sbar-confidence"><div class="step-num">11</div>Confidence Score</div>
    <div class="step-item" id="sbar-verify"><div class="step-num">12</div>Verification</div>
    <div class="step-item" id="sbar-results"><div class="step-num">13</div>Results &amp; Commit</div>
  </div>

  <div class="main-content">
    <!-- UPLOAD SECTION -->
    <div id="section-upload">
      <div class="card">
        <h2>Upload Data Files</h2>
        <div class="upload-grid">
          <div>
            <div style="font-size:0.82rem;font-weight:600;color:#636e72;margin-bottom:8px;">Solvents CSV</div>
            <div class="upload-zone" id="zone-solvents" ondragover="handleDragOver(event,'solvents')" ondragleave="handleDragLeave(event,'solvents')" ondrop="handleDrop(event,'solvents')">
              <div class="uz-icon">&#128196;</div>
              <div class="uz-title">Solvents / Chemicals</div>
              <div class="uz-hint">CSV, XLSX, TSV &bull; rows with dd, dp, dh columns</div>
              <div class="uz-filename" id="fn-solvents" style="display:none"></div>
              <input type="file" id="file-solvents" accept=".csv,.xlsx,.xls,.tsv,.txt" onchange="handleFileSelect('solvents')">
            </div>
          </div>
          <div>
            <div style="font-size:0.82rem;font-weight:600;color:#636e72;margin-bottom:8px;">Polymers CSV <span style="font-weight:400;color:#b2bec3;">(optional)</span></div>
            <div class="upload-zone" id="zone-polymers" ondragover="handleDragOver(event,'polymers')" ondragleave="handleDragLeave(event,'polymers')" ondrop="handleDrop(event,'polymers')">
              <div class="uz-icon">&#129520;</div>
              <div class="uz-title">Polymers</div>
              <div class="uz-hint">CSV, XLSX, TSV &bull; rows with dd, dp, dh, r (radius)</div>
              <div class="uz-filename" id="fn-polymers" style="display:none"></div>
              <input type="file" id="file-polymers" accept=".csv,.xlsx,.xls,.tsv,.txt" onchange="handleFileSelect('polymers')">
            </div>
          </div>
        </div>
        <div class="btn-row">
          <button class="btn btn-primary" id="btn-audit" onclick="runAudit()" disabled>Audit Files</button>
          <span id="upload-hint" style="font-size:0.8rem;color:#b2bec3;">Upload at least one file to continue</span>
        </div>
      </div>
    </div>

    <!-- METADATA / AUDIT SECTION -->
    <div id="section-meta" style="display:none">
      <div class="card">
        <h2>Audit Results</h2>
        <table class="audit-table" id="audit-table">
          <thead><tr><th>File</th><th>Rows</th><th>Detected Columns</th><th>Missing</th><th>Status</th></tr></thead>
          <tbody id="audit-tbody"></tbody>
        </table>
      </div>
      <div class="card">
        <h2>Dataset Metadata</h2>
        <div class="meta-form">
          <div class="form-group">
            <label>Dataset ID <span style="color:#e94560">*</span></label>
            <input type="text" id="meta-id" placeholder="e.g. my_solvents_2024" oninput="validateMetaId()">
            <div class="hint">Lowercase letters, digits, underscores only. Auto-generated from filename.</div>
          </div>
          <div class="form-group">
            <label>Display Name <span style="color:#e94560">*</span></label>
            <input type="text" id="meta-name" placeholder="e.g. My Solvents Dataset 2024">
          </div>
          <div class="form-group full-row">
            <label>Source URL <span style="color:#b2bec3;">(optional)</span></label>
            <input type="url" id="meta-url" placeholder="https://...">
          </div>
        </div>
        <div class="btn-row">
          <button class="btn btn-primary" id="btn-process" onclick="startPipeline()" disabled>Process Dataset</button>
          <button class="btn btn-secondary" onclick="resetToUpload()">&#8592; Back</button>
          <span id="meta-hint" style="font-size:0.8rem;color:#b2bec3;"></span>
        </div>
      </div>
    </div>

    <!-- PROGRESS SECTION -->
    <div id="section-progress" style="display:none">
      <div class="card">
        <h2>Processing <span id="prog-title"></span> <span class="badge" id="prog-badge"></span></h2>
        <div class="step-tracker" id="step-tracker"></div>
        <div class="progress-label" id="progress-label">Starting&hellip;</div>
        <div class="progress-bar-wrap"><div class="progress-bar-fill" id="progress-bar"></div></div>
        <div class="log-box" id="log-box"></div>
        <div class="ctrl-row">
          <button class="btn btn-secondary btn-sm" id="btn-pause" onclick="togglePause()">Pause</button>
          <button class="btn btn-danger btn-sm" id="btn-cancel" onclick="cancelPipeline()">Cancel</button>
        </div>
      </div>
    </div>

    <!-- RESULTS SECTION -->
    <div id="section-results" style="display:none">
      <div class="card">
        <h2>Results Summary</h2>
        <div class="stats-grid" id="stats-grid"></div>
        <div class="tabs">
          <div class="tab active" onclick="showTab('solvents')" id="tab-solvents">Solvents/Chemicals</div>
          <div class="tab" onclick="showTab('polymers')" id="tab-polymers">Polymers</div>
          <div class="tab" onclick="showTab('report')" id="tab-report">Quality Report</div>
        </div>
        <div class="tab-content active" id="tabcontent-solvents">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
            <input type="text" id="filter-solvents" placeholder="Filter by name, CAS, class..." oninput="filterResults('solvents')" style="padding:6px 10px;border:1px solid #dfe6e9;border-radius:5px;font-size:0.82rem;width:260px;">
            <label style="font-size:0.8rem;display:flex;align-items:center;gap:5px;cursor:pointer;">
              <input type="checkbox" id="show-review-only" onchange="filterResults('solvents')"> Show review-needed only
            </label>
          </div>
          <div class="results-table-wrap">
            <table class="results-table" id="tbl-solvents">
              <thead id="thead-solvents"></thead>
              <tbody id="tbody-solvents"></tbody>
            </table>
          </div>
        </div>
        <div class="tab-content" id="tabcontent-polymers">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
            <input type="text" id="filter-polymers" placeholder="Filter by name, CAS..." oninput="filterResults('polymers')" style="padding:6px 10px;border:1px solid #dfe6e9;border-radius:5px;font-size:0.82rem;width:260px;">
          </div>
          <div class="results-table-wrap">
            <table class="results-table" id="tbl-polymers">
              <thead id="thead-polymers"></thead>
              <tbody id="tbody-polymers"></tbody>
            </table>
          </div>
        </div>
        <div class="tab-content" id="tabcontent-report">
          <div class="quality-report" id="quality-report-content" style="display:block"></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:14px;flex-wrap:wrap;">
          <button class="btn btn-secondary btn-sm" onclick="downloadCSV('solvents')">&#8595; Download Solvents CSV</button>
          <button class="btn btn-secondary btn-sm" onclick="downloadCSV('polymers')">&#8595; Download Polymers CSV</button>
          <button class="btn btn-secondary btn-sm" onclick="showTab('report')">Quality Report</button>
        </div>
        <div class="commit-section">
          <h3>Commit to Database</h3>
          <div class="commit-options">
            <label><input type="checkbox" id="opt-skip-low-conf" checked> Skip rows with confidence &lt; 0.60</label>
            <label><input type="checkbox" id="opt-skip-review" checked> Skip rows needing manual review</label>
            <label><input type="checkbox" id="opt-skip-dupe"> Skip rows already in database</label>
          </div>
          <div class="btn-row">
            <button class="btn btn-success" onclick="commitToDatabase()">Commit to Database</button>
            <button class="btn btn-secondary" onclick="resetToUpload()">&#8592; Start Over</button>
          </div>
          <div class="commit-msg" id="commit-msg"></div>
        </div>
      </div>
    </div>

  </div><!-- end main-content -->
</div><!-- end page-body -->
<script>
// ============================================================
// CONSTANTS & STATE
// ============================================================
const ABBREV_SOLVENTS = {
  DCM: 'dichloromethane', THF: 'tetrahydrofuran', MeOH: 'methanol',
  EtOH: 'ethanol', DMF: 'N,N-dimethylformamide', DMSO: 'dimethyl sulfoxide',
  ACN: 'acetonitrile', MeCN: 'acetonitrile', EtOAc: 'ethyl acetate',
  IPA: 'isopropanol', NMP: 'N-methyl-2-pyrrolidone', CHCl3: 'chloroform',
  MEK: 'methyl ethyl ketone', MIBK: 'methyl isobutyl ketone',
  DMAc: 'N,N-dimethylacetamide', DMAC: 'N,N-dimethylacetamide',
  DBE: 'dibutyl ether', DEE: 'diethyl ether', Et2O: 'diethyl ether',
  MeTHF: '2-methyltetrahydrofuran', '2-MeTHF': '2-methyltetrahydrofuran',
  GBL: 'gamma-butyrolactone', NBS: 'N-bromosuccinimide', DME: 'dimethoxyethane',
  MTBE: 'methyl tert-butyl ether', nBuOH: '1-butanol', iBuOH: 'isobutanol',
  tBuOH: 'tert-butanol', nHexane: 'n-hexane', nHeptane: 'n-heptane',
  iPrOH: 'isopropanol', BuOH: '1-butanol', AmOH: '1-pentanol',
  PrOH: '1-propanol', HOAc: 'acetic acid', AcOH: 'acetic acid',
};

const ABBREV_POLYMERS = {
  PS: 'polystyrene', PE: 'polyethylene', PP: 'polypropylene',
  PVC: 'poly(vinyl chloride)', PMMA: 'poly(methyl methacrylate)',
  PET: 'poly(ethylene terephthalate)', PDMS: 'poly(dimethylsiloxane)',
  PLA: 'poly(lactic acid)', PC: 'polycarbonate', PAN: 'polyacrylonitrile',
  PVA: 'poly(vinyl alcohol)', PAA: 'polyacrylic acid',
  PEG: 'poly(ethylene glycol)', PPO: 'poly(phenylene oxide)',
  PEEK: 'poly(ether ether ketone)', PI: 'polyimide', PA6: 'polyamide 6',
  PA66: 'polyamide 6,6', POM: 'polyoxymethylene', PTT: 'poly(trimethylene terephthalate)',
  PBS: 'poly(butylene succinate)', PCL: 'polycaprolactone',
  PVDF: 'poly(vinylidene fluoride)', PTFE: 'polytetrafluoroethylene',
  PPS: 'poly(phenylene sulfide)', PSU: 'polysulfone', PES: 'polyethersulfone',
  PEI: 'polyetherimide', NBR: 'nitrile butadiene rubber',
  SBR: 'styrene-butadiene rubber', EPDM: 'ethylene propylene diene monomer',
  EVA: 'ethylene-vinyl acetate', PVAC: 'poly(vinyl acetate)',
  PVB: 'poly(vinyl butyral)', PVAL: 'poly(vinyl alcohol)',
};

// ICH Q3C classification table (CAS -> class)
const ICH_Q3C = {
  '67-56-1': 'Class 2', // methanol
  '64-17-5': 'Class 3', // ethanol
  '67-63-0': 'Class 3', // IPA
  '71-36-3': 'Class 3', // 1-butanol
  '78-83-1': 'Class 3', // isobutanol
  '71-23-8': 'Class 3', // 1-propanol
  '67-64-1': 'Class 3', // acetone
  '78-93-3': 'Class 3', // MEK
  '108-10-1': 'Class 3', // MIBK
  '108-88-3': 'Class 2', // toluene
  '71-43-2': 'Class 1', // benzene
  '110-82-7': 'Class 2', // cyclohexane
  '110-54-3': 'Class 2', // n-hexane
  '109-66-0': 'Class 3', // n-pentane
  '142-82-5': 'Class 3', // n-heptane
  '75-09-2': 'Class 2', // DCM
  '67-66-3': 'Class 2', // CHCl3
  '56-23-5': 'Class 1', // CCl4
  '75-05-8': 'Class 2', // acetonitrile
  '68-12-2': 'Class 2', // DMF
  '872-50-4': 'Class 2', // NMP
  '67-68-5': 'Class 3', // DMSO
  '109-99-9': 'Class 2', // THF
  '60-29-7': 'Class 3', // diethyl ether
  '141-78-6': 'Class 3', // ethyl acetate
  '107-21-1': 'Class 2', // ethylene glycol
  '56-81-5': 'Class 3', // glycerol
  '7732-18-5': 'Class 3', // water
  '64-19-7': 'Class 3', // acetic acid
  '79-20-9': 'Class 3', // methyl acetate
  '100-61-8': 'Class 2', // N-methylaniline
  '1330-20-7': 'Class 2', // xylenes
  '100-41-4': 'Class 2', // ethylbenzene
  '98-82-8': 'Class 3', // cumene
  '123-91-1': 'Class 2', // 1,4-dioxane
  '96-33-3': 'Class 2', // methyl acrylate
  '107-98-2': 'Class 3', // propylene glycol monomethyl ether
  '111-76-2': 'Class 3', // 2-butoxyethanol
  '584-84-9': 'Class 2', // toluene 2,4-diisocyanate - note: not ICH actually
  '108-94-1': 'Class 3', // cyclohexanone
  '872-50-4': 'Class 2', // NMP
  '96-47-9': 'Class 3', // 2-methyltetrahydrofuran
  '616-38-6': 'Class 2', // dimethyl carbonate
};

const PIPELINE_STEPS = [
  'Load & Audit', 'Name Cleaning', 'CAS Validation',
  'PubChem Identity', 'Physical Props', 'GHS Hazard',
  'ICH Q3C', 'ClassyFire', 'Confidence Score', 'Verification'
];

let state = {
  solventFile: null, polymerFile: null,
  solventRows: [], polymerRows: [],
  processedSolvents: [], processedPolymers: [],
  paused: false, cancelled: false,
  dsId: '', dsName: '', dsUrl: '',
  sortCol: {solvents: null, polymers: null},
  sortDir: {solvents: 1, polymers: 1},
};

let checkpointData = null;

// ============================================================
// FILE UPLOAD & DRAG-DROP
// ============================================================
function handleDragOver(e, type) {
  e.preventDefault();
  document.getElementById('zone-' + type).classList.add('drag-over');
}
function handleDragLeave(e, type) {
  document.getElementById('zone-' + type).classList.remove('drag-over');
}
function handleDrop(e, type) {
  e.preventDefault();
  document.getElementById('zone-' + type).classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) {
    if (type === 'solvents') state.solventFile = file;
    else state.polymerFile = file;
    showFileName(type, file.name);
    checkUploadReady();
  }
}
function handleFileSelect(type) {
  const el = document.getElementById('file-' + type);
  const file = el.files[0];
  if (file) {
    if (type === 'solvents') state.solventFile = file;
    else state.polymerFile = file;
    showFileName(type, file.name);
    checkUploadReady();
  }
}
function showFileName(type, name) {
  const zone = document.getElementById('zone-' + type);
  zone.classList.add('has-file');
  const fn = document.getElementById('fn-' + type);
  fn.textContent = name;
  fn.style.display = 'block';
}
function checkUploadReady() {
  const btn = document.getElementById('btn-audit');
  btn.disabled = !(state.solventFile || state.polymerFile);
  if (!btn.disabled) document.getElementById('upload-hint').textContent = 'Ready to audit';
}

// ============================================================
// CSV / TSV / XLSX PARSING
// ============================================================
function parseFileToRows(file) {
  return new Promise((resolve, reject) => {
    const name = file.name.toLowerCase();
    if (name.endsWith('.xlsx') || name.endsWith('.xls')) {
      readXLSX(file).then(resolve).catch(reject);
    } else {
      const reader = new FileReader();
      reader.onload = e => {
        try {
          const text = e.target.result;
          const rows = parseDelimited(text, name.endsWith('.tsv') ? '\t' : null);
          resolve(rows);
        } catch(ex) { reject(ex); }
      };
      reader.onerror = () => reject(new Error('File read error'));
      reader.readAsText(file);
    }
  });
}

function parseDelimited(text, forcedDelim) {
  const lines = text.split(/\r?\n/).filter(l => l.trim());
  if (!lines.length) return [];
  // Detect delimiter
  const delim = forcedDelim || detectDelimiter(lines[0]);
  const headers = parseCSVLine(lines[0], delim).map(h => h.trim().toLowerCase());
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue;
    const vals = parseCSVLine(lines[i], delim);
    const row = {};
    headers.forEach((h, idx) => { row[h] = vals[idx] !== undefined ? vals[idx].trim() : ''; });
    rows.push(row);
  }
  return rows;
}

function detectDelimiter(line) {
  const counts = {',': 0, '\t': 0, ';': 0, '|': 0};
  for (const c of line) if (counts[c] !== undefined) counts[c]++;
  return Object.entries(counts).sort((a,b) => b[1]-a[1])[0][0];
}

function parseCSVLine(line, delim) {
  const result = [];
  let cur = '', inQ = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') {
      if (inQ && line[i+1] === '"') { cur += '"'; i++; }
      else inQ = !inQ;
    } else if (c === delim && !inQ) {
      result.push(cur); cur = '';
    } else cur += c;
  }
  result.push(cur);
  return result;
}

function readXLSX(file) {
  // Simple XLSX reader using fetch + ArrayBuffer
  // We use a lightweight approach without external libs
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = e => {
      try {
        // Attempt to parse as CSV if text readable, else fail gracefully
        const buf = e.target.result;
        const uint8 = new Uint8Array(buf);
        // Check magic bytes for ZIP (XLSX)
        if (uint8[0] === 0x50 && uint8[1] === 0x4B) {
          reject(new Error('XLSX files require a converter. Please save as CSV and re-upload.'));
        } else {
          // Try as text
          const text = new TextDecoder().decode(buf);
          resolve(parseDelimited(text, null));
        }
      } catch(ex) { reject(ex); }
    };
    reader.onerror = () => reject(new Error('File read error'));
    reader.readAsArrayBuffer(file);
  });
}

// ============================================================
// COLUMN AUTO-DETECTION
// ============================================================
const COL_PATTERNS = {
  name: [/^name$/i, /^chemical.*name/i, /^compound/i, /^solvent/i, /^material/i, /^substance/i],
  cas: [/^cas$/i, /^cas.?no/i, /^cas.?number/i, /^cas.?rn/i],
  dd: [/^d_?d$/i, /^delta.?d$/i, /^\u03b4d$/i, /^dd$/i, /^disp/i, /^hd$/i, /^\bfd\b/i, /^vd$/i],
  dp: [/^d_?p$/i, /^delta.?p$/i, /^\u03b4p$/i, /^dp$/i, /^polar/i, /^hp$/i, /^\bfp\b/i, /^vp$/i],
  dh: [/^d_?h$/i, /^delta.?h$/i, /^\u03b4h$/i, /^dh$/i, /^h.?bond/i, /^hh$/i, /^\bfh\b/i, /^vh$/i],
  mw: [/^mw$/i, /^mol.?wt/i, /^molecular.?weight/i, /^mass$/i],
  bp: [/^bp$/i, /^boiling.?point/i, /^b\.p\./i, /^tbp/i],
  density: [/^density/i, /^rho/i, /^\u03c1/i, /^dens$/i],
  smiles: [/^smiles/i, /^canonical/i, /^smi$/i],
  radius: [/^r$/i, /^radius/i, /^r0$/i, /^interaction.?radius/i, /^ra$/i],
};

function detectColumns(headers) {
  const mapping = {};
  const used = new Set();
  for (const [field, patterns] of Object.entries(COL_PATTERNS)) {
    for (const pat of patterns) {
      const found = headers.find(h => pat.test(h) && !used.has(h));
      if (found) { mapping[field] = found; used.add(found); break; }
    }
  }
  return mapping;
}

function extractRow(rawRow, mapping) {
  const r = {};
  for (const [field, col] of Object.entries(mapping)) {
    r[field] = rawRow[col] !== undefined ? rawRow[col] : '';
  }
  // Fill original keys for reference
  r._raw = rawRow;
  return r;
}

// Normalize numeric
function toNum(v) {
  if (v === null || v === undefined || v === '') return null;
  const s = String(v).replace(/[^\d.\-+eE]/g, '');
  const n = parseFloat(s);
  return isNaN(n) ? null : n;
}


// ============================================================
// AUDIT
// ============================================================
async function runAudit() {
  const btn = document.getElementById('btn-audit');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Auditing...';

  try {
    if (state.solventFile) {
      state.solventRows = await parseFileToRows(state.solventFile);
    }
    if (state.polymerFile) {
      state.polymerRows = await parseFileToRows(state.polymerFile);
    }
  } catch(ex) {
    alert('Error reading file: ' + ex.message);
    btn.disabled = false;
    btn.textContent = 'Audit Files';
    return;
  }

  // Build audit table
  const tbody = document.getElementById('audit-tbody');
  tbody.innerHTML = '';

  function auditFile(rows, filename, isPolymer) {
    if (!rows.length) return;
    const headers = rows.length ? Object.keys(rows[0]).filter(k => k !== '_raw') : [];
    const mapping = detectColumns(headers);
    const required = ['name', 'dd', 'dp', 'dh'];
    const missing = required.filter(f => !mapping[f]);
    const status = missing.length ? 'warn' : 'ok';
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${filename}</td>
      <td>${rows.length}</td>
      <td>${Object.entries(mapping).map(([k,v]) => `<span style="color:#0984e3">${k}</span>=${v}`).join(', ') || '<em>none detected</em>'}</td>
      <td class="${missing.length ? 'err' : 'ok'}">${missing.length ? missing.join(', ') : '&#10003; All present'}</td>
      <td class="${status}">${status === 'ok' ? '&#10003; Ready' : '&#9888; Missing required cols'}</td>`;
    tbody.appendChild(tr);
  }

  if (state.solventRows.length) {
    const headers = Object.keys(state.solventRows[0]);
    const mapping = detectColumns(headers);
    state.solventMapping = mapping;
    auditFile(state.solventRows, state.solventFile.name, false);
  }
  if (state.polymerRows.length) {
    const headers = Object.keys(state.polymerRows[0]);
    const mapping = detectColumns(headers);
    state.polymerMapping = mapping;
    auditFile(state.polymerRows, state.polymerFile.name, true);
  }

  // Auto-fill metadata from filename
  const fname = (state.solventFile || state.polymerFile).name;
  const autoId = fname.replace(/\.[^.]+$/, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  document.getElementById('meta-id').value = autoId;
  document.getElementById('meta-name').value = fname.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' ');
  validateMetaId();

  document.getElementById('section-upload').style.display = 'none';
  document.getElementById('section-meta').style.display = 'block';
  setSidebarActive('sbar-audit');
}

function validateMetaId() {
  const v = document.getElementById('meta-id').value;
  const ok = /^[a-z0-9_]+$/.test(v) && v.length > 0;
  document.getElementById('meta-id').classList.toggle('invalid', !ok);
  document.getElementById('btn-process').disabled = !ok || !document.getElementById('meta-name').value.trim();
  const hint = document.getElementById('meta-hint');
  if (!ok && v.length > 0) hint.textContent = 'ID must be lowercase letters, digits, underscores only';
  else hint.textContent = '';
  return ok;
}

function resetToUpload() {
  state = { ...state, processedSolvents: [], processedPolymers: [], paused: false, cancelled: false };
  document.getElementById('section-upload').style.display = 'block';
  document.getElementById('section-meta').style.display = 'none';
  document.getElementById('section-progress').style.display = 'none';
  document.getElementById('section-results').style.display = 'none';
  document.getElementById('btn-audit').disabled = false;
  document.getElementById('btn-audit').textContent = 'Audit Files';
  setSidebarActive('sbar-upload');
}

// ============================================================
// PIPELINE ORCHESTRATOR
// ============================================================
async function startPipeline() {
  if (!validateMetaId()) return;
  const name = document.getElementById('meta-name').value.trim();
  if (!name) { document.getElementById('meta-hint').textContent = 'Dataset name required'; return; }

  state.dsId = document.getElementById('meta-id').value.trim();
  state.dsName = name;
  state.dsUrl = document.getElementById('meta-url').value.trim();
  state.paused = false;
  state.cancelled = false;
  state.processedSolvents = [];
  state.processedPolymers = [];

  document.getElementById('section-meta').style.display = 'none';
  document.getElementById('section-progress').style.display = 'block';
  document.getElementById('prog-title').textContent = state.dsName;
  setSidebarActive('sbar-names');

  buildStepTracker();
  logMsg('Pipeline started for dataset: ' + state.dsId);

  // Process solvents
  if (state.solventRows.length) {
    logMsg('Processing ' + state.solventRows.length + ' solvents/chemicals...', 'info');
    const mapping = state.solventMapping || detectColumns(Object.keys(state.solventRows[0]));
    await processBatch(state.solventRows, mapping, false);
  }

  // Process polymers
  if (state.polymerRows.length) {
    logMsg('Processing ' + state.polymerRows.length + ' polymers...', 'info');
    const mapping = state.polymerMapping || detectColumns(Object.keys(state.polymerRows[0]));
    await processBatch(state.polymerRows, mapping, true);
  }

  if (!state.cancelled) {
    logMsg('Pipeline complete!', 'info');
    showResults();
  }
}

function buildStepTracker() {
  const wrap = document.getElementById('step-tracker');
  wrap.innerHTML = PIPELINE_STEPS.map((s, i) =>
    `<span class="step-chip" id="step-chip-${i}">${s}</span>`
  ).join('');
}

function setStepActive(idx) {
  PIPELINE_STEPS.forEach((_, i) => {
    const chip = document.getElementById('step-chip-' + i);
    if (!chip) return;
    chip.className = 'step-chip' + (i < idx ? ' done' : i === idx ? ' active' : '');
  });
}

function togglePause() {
  state.paused = !state.paused;
  document.getElementById('btn-pause').textContent = state.paused ? 'Resume' : 'Pause';
  if (state.paused) logMsg('Paused. Click Resume to continue.', 'warn');
  else logMsg('Resumed.', 'info');
}

function cancelPipeline() {
  if (!confirm('Cancel the import pipeline?')) return;
  state.cancelled = true;
  logMsg('Cancelled by user.', 'err');
  setTimeout(() => resetToUpload(), 1500);
}

let _logCount = 0;
function logMsg(msg, cls) {
  const box = document.getElementById('log-box');
  const div = document.createElement('div');
  div.className = 'log-line' + (cls ? ' log-' + cls : '');
  const ts = new Date().toISOString().slice(11,19);
  div.textContent = '[' + ts + '] ' + msg;
  box.appendChild(div);
  if (++_logCount % 20 === 0) {
    // Keep last 500 lines
    while (box.children.length > 500) box.removeChild(box.firstChild);
  }
  box.scrollTop = box.scrollHeight;
}

function updateProgress(done, total, label) {
  const pct = total > 0 ? Math.round(100 * done / total) : 0;
  document.getElementById('progress-bar').style.width = pct + '%';
  document.getElementById('progress-label').textContent =
    label || ('Processing row ' + done + ' of ' + total + ' (' + pct + '%)');
}

function setSidebarActive(id) {
  document.querySelectorAll('.step-item').forEach(el => el.classList.remove('active'));
  const el = document.getElementById(id);
  if (el) el.classList.add('active');
}

// Wait while paused
async function waitIfPaused() {
  while (state.paused && !state.cancelled) {
    await sleep(300);
  }
}
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ============================================================
// API HELPERS
// ============================================================
let _lastApiCall = 0;
async function apiDelay() {
  const now = Date.now();
  const elapsed = now - _lastApiCall;
  if (elapsed < 200) await sleep(200 - elapsed);
  _lastApiCall = Date.now();
}

async function fetchWithRetry(url, retries = 3) {
  let delay = 1000;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      await apiDelay();
      const resp = await fetch(url);
      if (resp.status === 429) {
        logMsg('Rate limited (429). Waiting 10s...', 'warn');
        await sleep(10000);
        continue;
      }
      if (resp.status === 404) return { status: 404, data: null };
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();
      return { status: resp.status, data };
    } catch(ex) {
      if (attempt === retries) return { status: -1, data: null, error: ex.message };
      await sleep(delay);
      delay *= 2;
    }
  }
  return { status: -1, data: null };
}

// ============================================================
// STEP 1: NAME CLEANING
// ============================================================
function cleanName(name, isPolymer) {
  if (!name) return name;
  const abbrevTable = isPolymer ? ABBREV_POLYMERS : ABBREV_SOLVENTS;
  let s = name.trim();
  // Check exact abbrev match (case-sensitive)
  if (abbrevTable[s]) return abbrevTable[s];
  // Check case-insensitive
  const lower = s.toLowerCase();
  for (const [abbr, full] of Object.entries(abbrevTable)) {
    if (abbr.toLowerCase() === lower) return full;
  }
  // Remove extra whitespace
  s = s.replace(/\s+/g, ' ');
  return s;
}

// ============================================================
// STEP 2: CAS VALIDATION
// ============================================================
function validateCAS(cas) {
  if (!cas || !cas.trim()) return { valid: false, formatted: null, reason: 'empty' };
  const s = cas.trim();
  // Format check
  if (!/^\d{2,7}-\d{2}-\d$/.test(s)) {
    return { valid: false, formatted: null, reason: 'format' };
  }
  // Checksum
  const digits = s.replace(/-/g, '');
  const check = parseInt(digits[digits.length - 1]);
  let sum = 0;
  for (let i = 0; i < digits.length - 1; i++) {
    sum += parseInt(digits[digits.length - 2 - i]) * (i + 1);
  }
  const valid = (sum % 10) === check;
  return { valid, formatted: s, reason: valid ? null : 'checksum' };
}

// Extract CAS from synonyms list
function extractCASFromSynonyms(synonyms) {
  if (!synonyms) return null;
  for (const s of synonyms) {
    if (/^\d{2,7}-\d{2}-\d$/.test(s.trim())) {
      const v = validateCAS(s.trim());
      if (v.valid) return s.trim();
    }
  }
  return null;
}


// ============================================================
// STEP 3: PUBCHEM IDENTITY RESOLUTION
// ============================================================
async function pubchemLookupByName(name) {
  const encoded = encodeURIComponent(name);
  const url = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encoded}/property/MolecularWeight,MolecularFormula,CanonicalSMILES,IsomericSMILES,IUPACName/JSON`;
  const res = await fetchWithRetry(url);
  if (res.status === 404 || !res.data) return null;
  try {
    const props = res.data.PropertyTable.Properties[0];
    return { cid: props.CID, mw: props.MolecularWeight, formula: props.MolecularFormula,
      smiles_canonical: props.CanonicalSMILES, smiles_isomeric: props.IsomericSMILES,
      name_iupac: props.IUPACName };
  } catch(e) { return null; }
}

async function pubchemLookupByCAS(cas) {
  if (!cas) return null;
  return await pubchemLookupByName(cas);
}

async function pubchemGetInChIKey(cid) {
  const url = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/property/InChIKey/JSON`;
  const res = await fetchWithRetry(url);
  if (res.status === 404 || !res.data) return null;
  try {
    return res.data.PropertyTable.Properties[0].InChIKey;
  } catch(e) { return null; }
}

async function pubchemGetSynonyms(cid) {
  const url = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/synonyms/JSON`;
  const res = await fetchWithRetry(url);
  if (res.status === 404 || !res.data) return [];
  try {
    return res.data.InformationList.Information[0].Synonym || [];
  } catch(e) { return []; }
}

async function pubchemGetExtraProps(cid) {
  const url = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/property/BoilingPoint,MeltingPoint,Density,FlashPoint,XLogP,HBondDonorCount,HBondAcceptorCount,Complexity/JSON`;
  const res = await fetchWithRetry(url);
  if (res.status === 404 || !res.data) return {};
  try {
    const p = res.data.PropertyTable.Properties[0];
    return {
      bp_pubchem: p.BoilingPoint, mp_pubchem: p.MeltingPoint,
      density_pubchem: p.Density, fp_pubchem: p.FlashPoint,
      xlogp: p.XLogP, hbd: p.HBondDonorCount, hba: p.HBondAcceptorCount,
      complexity: p.Complexity
    };
  } catch(e) { return {}; }
}

// ============================================================
// STEP 4: GHS HAZARD
// ============================================================
async function fetchGHSHazard(cid) {
  if (!cid) return {};
  const url = `https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/${cid}/JSON?heading=GHS+Classification`;
  const res = await fetchWithRetry(url);
  if (res.status === 404 || !res.data) return {};
  try {
    const root = res.data.Record;
    const sections = root.Section || [];
    let ghsCodes = [], signalWord = '', pictograms = [];
    function walkSections(sects) {
      for (const s of sects) {
        if (s.Section) walkSections(s.Section);
        if (s.Information) {
          for (const info of s.Information) {
            const name = (info.Name || '').toLowerCase();
            if (name.includes('ghs hazard')) {
              const vals = info.Value && info.Value.StringWithMarkup;
              if (vals) vals.forEach(v => {
                const m = v.String.match(/H\d{3}/g);
                if (m) ghsCodes.push(...m);
              });
            }
            if (name.includes('signal')) {
              const sv = info.Value && info.Value.StringWithMarkup;
              if (sv && sv[0]) signalWord = sv[0].String;
            }
            if (name.includes('pictogram') || name.includes('ghs symbol')) {
              const mv = info.Value && info.Value.StringWithMarkup;
              if (mv) mv.forEach(v => pictograms.push(v.String));
            }
          }
        }
      }
    }
    walkSections(sections);
    ghsCodes = [...new Set(ghsCodes)];
    return {
      ghs_hazard_codes: ghsCodes.join(';'),
      ghs_signal_word: signalWord,
      ghs_pictograms: pictograms.join(';'),
      flag_carcinogen: ghsCodes.some(c => ['H350','H351'].includes(c)),
      flag_reproductive_toxin: ghsCodes.some(c => ['H360','H361'].includes(c)),
      flag_flammable: ghsCodes.some(c => ['H224','H225','H226','H228'].includes(c)),
      flag_acutely_toxic: ghsCodes.some(c => ['H300','H301','H310','H311','H330','H331'].includes(c)),
    };
  } catch(e) {
    return { ghs_parse_error: e.message };
  }
}

// ============================================================
// STEP 5: CLASSYFIRE
// ============================================================
async function fetchClassyFire(inchikey) {
  if (!inchikey) return { cf_status: 'no_inchikey' };
  const url = `https://cfb.fiehnlab.ucdavis.edu/entities/${inchikey}.json`;
  try {
    const res = await fetchWithRetry(url, 1);
    if (res.status === 404) return { cf_status: 'not_found' };
    if (res.status === -1) return { cf_status: 'proxy_required' };
    const d = res.data;
    return {
      cf_status: 'ok',
      cf_kingdom: d.kingdom && d.kingdom.name,
      cf_superclass: d.superclass && d.superclass.name,
      cf_class: d['class'] && d['class'].name,
      cf_subclass: d.subclass && d.subclass.name,
      cf_direct_parent: d.direct_parent && d.direct_parent.name,
    };
  } catch(e) {
    return { cf_status: 'proxy_required', cf_error: e.message };
  }
}

// ============================================================
// STEP 6: CONFIDENCE SCORING
// ============================================================
function computeConfidence(row) {
  // score_cas: 0.25
  let score_cas = 0;
  if (row.cas_validated && row.cas_final) score_cas = 0.25;
  else if (row.cas_final && row.cas_pubchem_match) score_cas = 0.20;
  else if (row.cas_final && !row.cas_validated) score_cas = 0.10;
  // score_name_match: 0.20
  let score_name_match = 0;
  if (row.name_iupac && row.name_cleaned) {
    const sim = nameSimilarity(row.name_cleaned.toLowerCase(), row.name_iupac.toLowerCase());
    score_name_match = sim * 0.20;
  } else if (row.pubchem_cid) {
    score_name_match = 0.10;
  }
  // score_pubchem: 0.20
  let score_pubchem = 0;
  if (row.pubchem_cid && row.pubchem_confirmed) score_pubchem = 0.20;
  else if (row.pubchem_cid) score_pubchem = 0.15;
  // score_smiles: 0.15
  let score_smiles = 0;
  if (row.smiles_canonical && row.smiles_canonical.length > 2) score_smiles = 0.15;
  else if (row.smiles_input && row.smiles_input.length > 2) score_smiles = 0.08;
  // score_crossref: 0.15
  let score_crossref = 0;
  if (row.cas_from_pubchem && row.cas_final && row.cas_from_pubchem === row.cas_final) score_crossref = 0.15;
  else if (row.cas_name_lookup_matches_cas_lookup) score_crossref = 0.10;
  else if (row.pubchem_cid) score_crossref = 0.05;
  // score_properties: 0.05
  let score_properties = 0;
  const propCount = ['bp', 'density', 'xlogp'].filter(p => row[p] !== null && row[p] !== undefined && row[p] !== '').length;
  score_properties = Math.min(0.05, propCount * 0.017);

  const confidence_score = score_cas + score_name_match + score_pubchem + score_smiles + score_crossref + score_properties;
  const clamped = Math.min(1.0, Math.max(0, confidence_score));
  let confidence_label;
  if (clamped >= 0.85) confidence_label = 'High';
  else if (clamped >= 0.60) confidence_label = 'Medium';
  else if (clamped >= 0.30) confidence_label = 'Low';
  else confidence_label = 'Very Low';

  return { confidence_score: +clamped.toFixed(3), confidence_label,
    score_cas: +score_cas.toFixed(3), score_name_match: +score_name_match.toFixed(3),
    score_pubchem: +score_pubchem.toFixed(3), score_smiles: +score_smiles.toFixed(3),
    score_crossref: +score_crossref.toFixed(3), score_properties: +score_properties.toFixed(3) };
}

function nameSimilarity(a, b) {
  if (!a || !b) return 0;
  if (a === b) return 1;
  if (a.includes(b) || b.includes(a)) return 0.8;
  // Simple bigram similarity
  function bigrams(s) {
    const bg = new Set();
    for (let i = 0; i < s.length - 1; i++) bg.add(s.slice(i, i+2));
    return bg;
  }
  const bg1 = bigrams(a), bg2 = bigrams(b);
  let common = 0;
  bg1.forEach(g => { if (bg2.has(g)) common++; });
  return (2 * common) / (bg1.size + bg2.size);
}

// ============================================================
// STEP 7: VERIFICATION
// ============================================================
function runVerification(row, batchInChIKeys, existingInChIKeys) {
  const notes = [];
  let needs_review = false;
  // V1: InChIKey cross-check
  const verify_inchikey_mismatch = !!(row.inchikey_from_smiles && row.inchikey && row.inchikey_from_smiles !== row.inchikey);
  if (verify_inchikey_mismatch) { notes.push('InChIKey mismatch between SMILES and PubChem'); needs_review = true; }
  // V2: CAS re-verification
  const verify_cas_conflict = !!(row.cas_final && row.cas_from_pubchem && row.cas_final !== row.cas_from_pubchem);
  if (verify_cas_conflict) { notes.push('CAS from input conflicts with PubChem CAS'); needs_review = true; }
  // V3: Name sanity
  let verify_name_warning = false;
  if (row.name_cleaned && row.name_iupac) {
    const nc = row.name_cleaned.toLowerCase();
    const ni = row.name_iupac.toLowerCase();
    const sim = nameSimilarity(nc, ni);
    if (sim < 0.15 && !row.cas_final) { verify_name_warning = true; notes.push('Name similarity very low: "' + row.name_cleaned + '" vs "' + row.name_iupac + '"'); needs_review = true; }
  }
  // V4: Formula consistency (basic)
  let verify_formula_warning = false;
  if (row.mol_formula && row.smiles_canonical) {
    const fC = (row.mol_formula.match(/C(\d+)?/) || [''])[0];
    const sC = (row.smiles_canonical.match(/C/g) || []).length;
    const formulaC = fC ? parseInt(fC.replace('C','') || '1') : 0;
    if (formulaC > 0 && Math.abs(formulaC - sC) > Math.max(3, formulaC * 0.3)) {
      verify_formula_warning = true; notes.push('Carbon count mismatch between formula and SMILES');
    }
  }
  // V5: HSP plausibility
  const dd = toNum(row.dd), dp = toNum(row.dp), dh = toNum(row.dh);
  let verify_hsp_outlier = false;
  if (dd !== null && dp !== null && dh !== null) {
    if (dd < 10 || dd > 22 || dp < 0 || dp > 30 || dh < 0 || dh > 40) {
      verify_hsp_outlier = true;
      notes.push(`HSP values out of typical range: dD=${dd}, dP=${dp}, dH=${dh}`);
    }
  }
  // V7: Duplicate InChIKey
  let already_in_database = false;
  let duplicate_in_batch = false;
  if (row.inchikey) {
    if (existingInChIKeys && existingInChIKeys.has(row.inchikey)) {
      already_in_database = true; notes.push('Already in database (InChIKey match)');
    }
    if (batchInChIKeys.has(row.inchikey)) {
      duplicate_in_batch = true; needs_review = true; notes.push('Duplicate InChIKey in batch');
    } else {
      batchInChIKeys.add(row.inchikey);
    }
  }
  return {
    verify_inchikey_mismatch, verify_cas_conflict, verify_hsp_outlier,
    verify_name_warning, verify_formula_warning,
    already_in_database, duplicate_in_batch,
    needs_manual_review: needs_review,
    processing_notes: notes.join(' | '),
  };
}

// Get existing InChIKeys from localStorage
function getExistingInChIKeys() {
  const keys = new Set();
  try {
    const datasets = JSON.parse(localStorage.getItem('materialism_imported_datasets') || '{}');
    for (const ds of Object.values(datasets)) {
      if (ds.chemicals) ds.chemicals.forEach(c => { if (c.inchikey) keys.add(c.inchikey); });
      if (ds.polymers) ds.polymers.forEach(p => { if (p.inchikey) keys.add(p.inchikey); });
    }
    // Also check built-in database placeholder
    const builtIn = JSON.parse(localStorage.getItem('materialism_builtin_inchikeys') || '[]');
    builtIn.forEach(k => keys.add(k));
  } catch(e) {}
  return keys;
}


// ============================================================
// MAIN BATCH PROCESSOR
// ============================================================
async function processBatch(rows, mapping, isPolymer) {
  const existingInChIKeys = getExistingInChIKeys();
  const batchInChIKeys = new Set();
  const total = rows.length;
  const results = isPolymer ? state.processedPolymers : state.processedSolvents;

  // Check for checkpoint
  const cpKey = 'materialism_checkpoint_' + state.dsId + (isPolymer ? '_poly' : '_chem');
  let startFrom = 0;
  try {
    const cp = JSON.parse(sessionStorage.getItem(cpKey) || 'null');
    if (cp && cp.results && cp.results.length > 0) {
      logMsg('Resuming from checkpoint at row ' + cp.results.length, 'info');
      cp.results.forEach(r => results.push(r));
      startFrom = cp.results.length;
      cp.inchikeys.forEach(k => batchInChIKeys.add(k));
    }
  } catch(e) {}

  const typeLabel = isPolymer ? 'Polymer' : 'Chemical';

  for (let i = startFrom; i < rows.length; i++) {
    if (state.cancelled) break;
    await waitIfPaused();
    if (state.cancelled) break;

    const rawRow = rows[i];
    const result = { src: state.dsId, dsId: state.dsId };

    try {
      // Extract mapped fields
      const mapped = extractRow(rawRow, mapping);
      result.dd = toNum(mapped.dd);
      result.dp = toNum(mapped.dp);
      result.dh = toNum(mapped.dh);
      result.mw = toNum(mapped.mw) || null;
      result.bp = toNum(mapped.bp) || null;
      result.density = toNum(mapped.density) || null;
      if (isPolymer) result.r = toNum(mapped.radius) || null;
      result.smiles_input = mapped.smiles || '';

      // --- STEP 1: Name Cleaning ---
      setStepActive(1);
      result.name_original = mapped.name || '';
      result.name_cleaned = cleanName(result.name_original, isPolymer);

      // --- STEP 2: CAS Validation ---
      setStepActive(2);
      const casRaw = mapped.cas || '';
      const casVal = validateCAS(casRaw);
      result.cas_input = casRaw;
      result.cas_validated = casVal.valid;
      result.cas_final = casVal.valid ? casVal.formatted : (casRaw.trim() || null);
      if (casRaw && !casVal.valid) {
        result.processing_notes = (result.processing_notes || '') + 'CAS invalid (' + casVal.reason + '); ';
      }

      updateProgress(i + 1, total, typeLabel + ' ' + (i+1) + '/' + total + ': ' + (result.name_cleaned || '?'));
      logMsg((i+1) + '/' + total + ' ' + typeLabel + ': ' + (result.name_cleaned || 'unnamed'));

      // --- STEP 3: PubChem Identity ---
      setStepActive(3);
      let pcByName = null, pcByCAS = null;

      if (result.name_cleaned) {
        pcByName = await pubchemLookupByName(result.name_cleaned);
      }
      if (result.cas_final) {
        pcByCAS = await pubchemLookupByCAS(result.cas_final);
      }

      // Cross-reference
      if (pcByName && pcByCAS && pcByName.cid === pcByCAS.cid) {
        result.cas_name_lookup_matches_cas_lookup = true;
      }

      // Pick best result
      const pc = pcByName || pcByCAS;
      if (pc) {
        result.pubchem_cid = pc.cid;
        result.mw = result.mw || toNum(pc.mw);
        result.mol_formula = pc.formula || null;
        result.smiles_canonical = pc.smiles_canonical || result.smiles_input || null;
        result.smiles_isomeric = pc.smiles_isomeric || null;
        result.name_iupac = pc.name_iupac || null;
        result.pubchem_confirmed = true;

        // Get InChIKey
        result.inchikey = await pubchemGetInChIKey(pc.cid);

        // Get synonyms to find CAS
        const synonyms = await pubchemGetSynonyms(pc.cid);
        result.cas_from_pubchem = extractCASFromSynonyms(synonyms);
        if (result.cas_from_pubchem && !result.cas_final) {
          result.cas_final = result.cas_from_pubchem;
          result.cas_validated = validateCAS(result.cas_final).valid;
          logMsg('  CAS from PubChem: ' + result.cas_final, 'gray');
        }
        // pubchem CAS match
        if (result.cas_final && result.cas_from_pubchem === result.cas_final) {
          result.cas_pubchem_match = true;
        }
      } else {
        result.pubchem_cid = null;
        result.lookup_failed = true;
        logMsg('  PubChem not found for: ' + result.name_cleaned, 'warn');
        // Use input SMILES if available
        result.smiles_canonical = result.smiles_input || null;
      }

      // --- STEP 4: Physical Properties ---
      setStepActive(4);
      if (result.pubchem_cid) {
        const extraProps = await pubchemGetExtraProps(result.pubchem_cid);
        // Prefer input values, fall back to PubChem
        result.bp = result.bp !== null ? result.bp : (toNum(extraProps.bp_pubchem) || null);
        result.density = result.density !== null ? result.density : (toNum(extraProps.density_pubchem) || null);
        result.xlogp = extraProps.xlogp !== undefined ? extraProps.xlogp : null;
        result.hbd = extraProps.hbd !== undefined ? extraProps.hbd : null;
        result.hba = extraProps.hba !== undefined ? extraProps.hba : null;
        result.complexity = extraProps.complexity !== undefined ? extraProps.complexity : null;
        result.mp = toNum(extraProps.mp_pubchem) || null;
        result.fp = result.fp || (toNum(extraProps.fp_pubchem) || null);
      }

      // --- STEP 5: GHS Hazard (skip for polymers) ---
      if (!isPolymer) {
        setStepActive(5);
        const ghs = await fetchGHSHazard(result.pubchem_cid);
        Object.assign(result, ghs);
      } else {
        result.ghs_hazard_codes = null;
        result.ghs_signal_word = null;
      }

      // --- STEP 6: ICH Q3C ---
      setStepActive(6);
      if (!isPolymer && result.cas_final) {
        result.ich_q3c_class = ICH_Q3C[result.cas_final] || null;
      } else {
        result.ich_q3c_class = null;
      }

      // --- STEP 7: ClassyFire ---
      setStepActive(7);
      const cfResult = await fetchClassyFire(result.inchikey);
      Object.assign(result, cfResult);

      // --- STEP 8: Confidence Scoring ---
      setStepActive(8);
      const conf = computeConfidence(result);
      Object.assign(result, conf);

      // --- STEP 9: Verification ---
      setStepActive(9);
      const verif = runVerification(result, batchInChIKeys, existingInChIKeys);
      Object.assign(result, verif);

      // Final name
      result.name = result.name_cleaned || result.name_original || 'Unknown';

    } catch(ex) {
      result.processing_notes = (result.processing_notes || '') + 'Row error: ' + ex.message;
      result.needs_manual_review = true;
      result.confidence_score = 0;
      result.confidence_label = 'Very Low';
      logMsg('  ERROR row ' + (i+1) + ': ' + ex.message, 'err');
    }

    // Ensure required fields have defaults
    result.needs_manual_review = result.needs_manual_review || false;
    result.already_in_database = result.already_in_database || false;
    result.confidence_score = result.confidence_score || 0;
    result.confidence_label = result.confidence_label || 'Very Low';
    results.push(result);

    // Checkpoint every 25 rows
    if ((i + 1) % 25 === 0) {
      try {
        sessionStorage.setItem(cpKey, JSON.stringify({
          results: results.slice(),
          inchikeys: [...batchInChIKeys],
          timestamp: Date.now()
        }));
        logMsg('Checkpoint saved at row ' + (i+1), 'gray');
      } catch(e) {}
    }
  }

  // Clear checkpoint on completion
  try { sessionStorage.removeItem(cpKey); } catch(e) {}
  setStepActive(PIPELINE_STEPS.length);
}


// ============================================================
// RESULTS DISPLAY
// ============================================================
function showResults() {
  document.getElementById('section-progress').style.display = 'none';
  document.getElementById('section-results').style.display = 'block';
  setSidebarActive('sbar-results');

  renderStats();
  renderSolventsTable();
  renderPolymersTable();
  renderQualityReport();
  showTab('solvents');
}

function renderStats() {
  const solvents = state.processedSolvents;
  const polymers = state.processedPolymers;
  const allItems = [...solvents, ...polymers];
  const highConf = allItems.filter(r => r.confidence_score >= 0.85).length;
  const medConf = allItems.filter(r => r.confidence_score >= 0.60 && r.confidence_score < 0.85).length;
  const lowConf = allItems.filter(r => r.confidence_score < 0.60).length;
  const needsReview = allItems.filter(r => r.needs_manual_review).length;

  const grid = document.getElementById('stats-grid');
  grid.innerHTML = `
    <div class="stat-box"><div class="stat-val">${solvents.length}</div><div class="stat-label">Chemicals</div></div>
    <div class="stat-box"><div class="stat-val">${polymers.length}</div><div class="stat-label">Polymers</div></div>
    <div class="stat-box"><div class="stat-val" style="color:#27ae60">${highConf}</div><div class="stat-label">High Confidence</div></div>
    <div class="stat-box"><div class="stat-val" style="color:#f39c12">${medConf}</div><div class="stat-label">Med Confidence</div></div>
    <div class="stat-box"><div class="stat-val" style="color:#e74c3c">${lowConf}</div><div class="stat-label">Low Confidence</div></div>
    <div class="stat-box"><div class="stat-val" style="color:#e67e22">${needsReview}</div><div class="stat-label">Needs Review</div></div>
  `;
}

const SOLVENT_COLS = [
  {key:'_idx', label:'#', sortable:false},
  {key:'name', label:'Name'},
  {key:'cas_final', label:'CAS'},
  {key:'dd', label:'dD'},
  {key:'dp', label:'dP'},
  {key:'dh', label:'dH'},
  {key:'mw', label:'MW'},
  {key:'pubchem_cid', label:'CID'},
  {key:'mol_formula', label:'Formula'},
  {key:'confidence_score', label:'Confidence'},
  {key:'ghs_hazard_codes', label:'GHS Codes'},
  {key:'ich_q3c_class', label:'ICH Q3C'},
  {key:'cf_class', label:'ClassyFire'},
  {key:'flag_carcinogen', label:'Carc'},
  {key:'flag_flammable', label:'Flam'},
  {key:'needs_manual_review', label:'Review'},
  {key:'already_in_database', label:'In DB'},
  {key:'processing_notes', label:'Notes'},
  {key:'_override', label:'Override', sortable:false},
];

const POLYMER_COLS = [
  {key:'_idx', label:'#', sortable:false},
  {key:'name', label:'Name'},
  {key:'cas_final', label:'CAS'},
  {key:'dd', label:'dD'},
  {key:'dp', label:'dP'},
  {key:'dh', label:'dH'},
  {key:'r', label:'Radius'},
  {key:'pubchem_cid', label:'CID'},
  {key:'confidence_score', label:'Confidence'},
  {key:'cf_class', label:'ClassyFire'},
  {key:'needs_manual_review', label:'Review'},
  {key:'processing_notes', label:'Notes'},
  {key:'_override', label:'Override', sortable:false},
];

function renderSolventsTable() {
  const data = getFilteredSolvents();
  renderTable('solvents', SOLVENT_COLS, data);
}
function renderPolymersTable() {
  const data = getFilteredPolymers();
  renderTable('polymers', POLYMER_COLS, data);
}

function getFilteredSolvents() {
  const query = (document.getElementById('filter-solvents') && document.getElementById('filter-solvents').value || '').toLowerCase();
  const reviewOnly = document.getElementById('show-review-only') && document.getElementById('show-review-only').checked;
  let data = state.processedSolvents;
  if (reviewOnly) data = data.filter(r => r.needs_manual_review);
  if (query) data = data.filter(r => {
    return (r.name || '').toLowerCase().includes(query) ||
      (r.cas_final || '').includes(query) ||
      (r.mol_formula || '').toLowerCase().includes(query) ||
      (r.cf_class || '').toLowerCase().includes(query) ||
      (r.ich_q3c_class || '').toLowerCase().includes(query);
  });
  return data;
}
function getFilteredPolymers() {
  const query = (document.getElementById('filter-polymers') && document.getElementById('filter-polymers').value || '').toLowerCase();
  let data = state.processedPolymers;
  if (query) data = data.filter(r => {
    return (r.name || '').toLowerCase().includes(query) ||
      (r.cas_final || '').includes(query);
  });
  return data;
}

function filterResults(type) {
  if (type === 'solvents') renderSolventsTable();
  else renderPolymersTable();
}

function renderTable(type, cols, data) {
  const thead = document.getElementById('thead-' + type);
  const tbody = document.getElementById('tbody-' + type);

  // Header
  thead.innerHTML = '<tr>' + cols.map(c => {
    const sortable = c.sortable !== false;
    const cls = state.sortCol[type] === c.key ? (state.sortDir[type] > 0 ? 'sort-asc' : 'sort-desc') : '';
    return `<th class="${cls}" ${sortable ? `onclick="sortTable('${type}','${c.key}')"` : ''}>${c.label}</th>`;
  }).join('') + '</tr>';

  // Sort
  let sorted = [...data];
  if (state.sortCol[type] && state.sortCol[type] !== '_idx' && state.sortCol[type] !== '_override') {
    sorted.sort((a, b) => {
      const av = a[state.sortCol[type]], bv = b[state.sortCol[type]];
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * state.sortDir[type];
      return String(av).localeCompare(String(bv)) * state.sortDir[type];
    });
  }

  tbody.innerHTML = '';
  sorted.forEach((row, idx) => {
    const tr = document.createElement('tr');
    if (row.needs_manual_review && !row._override) tr.classList.add('review-row');
    cols.forEach(c => {
      const td = document.createElement('td');
      td.appendChild(renderCell(row, c.key, idx));
      tbody.appendChild(tr.appendChild(td) && tr) || tr.appendChild(td);
    });
    // Re-do: build td cells
    tr.innerHTML = '';
    cols.forEach(c => {
      const td = document.createElement('td');
      const cell = renderCellContent(row, c.key, idx);
      td.innerHTML = cell;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

function renderCellContent(row, key, idx) {
  if (key === '_idx') return String(idx + 1);
  if (key === '_override') {
    const checked = row._override ? 'checked' : '';
    const rowKey = (row.name || '') + idx;
    return `<input type="checkbox" class="review-override" ${checked}
      title="Override: include this row despite review flag"
      onchange="setOverride(${idx},'${key}',this.checked,'${row.src || ''}')" >`;
  }
  if (key === 'confidence_score') {
    const score = row.confidence_score || 0;
    const cls = score >= 0.85 ? 'conf-high' : score >= 0.60 ? 'conf-med' : score >= 0.30 ? 'conf-low' : 'conf-vlow';
    const label = row.confidence_label || 'Very Low';
    return `<span class="conf-pill ${cls}">${score.toFixed(2)} ${label}</span>`;
  }
  if (key === 'flag_carcinogen' || key === 'flag_reproductive_toxin' || key === 'flag_flammable' || key === 'flag_acutely_toxic') {
    return row[key] ? '<span class="flag-icon flag-warn">!</span>' : '';
  }
  if (key === 'needs_manual_review') {
    return row[key] ? '<span class="flag-icon">R</span>' : '';
  }
  if (key === 'already_in_database') {
    return row[key] ? '<span class="flag-icon" style="background:#8e44ad">D</span>' : '';
  }
  if (key === 'ich_q3c_class') {
    const v = row[key];
    if (!v) return '';
    const cls = v === 'Class 1' ? 'ich-1' : v === 'Class 2A' ? 'ich-2a' : v === 'Class 2B' ? 'ich-2b' : v === 'Class 2' ? 'ich-2a' : 'ich-3';
    return `<span class="${cls}">${v}</span>`;
  }
  if (key === 'pubchem_cid' && row[key]) {
    return `<a href="https://pubchem.ncbi.nlm.nih.gov/compound/${row[key]}" target="_blank" rel="noopener">${row[key]}</a>`;
  }
  if (key === 'cas_final' && row[key]) {
    return `<a href="https://www.chemspider.com/Search.aspx?q=${row[key]}" target="_blank" rel="noopener">${row[key]}</a>`;
  }
  if (key === 'ghs_hazard_codes') {
    if (!row[key]) return '';
    return row[key].split(';').map(c => `<span class="tag tag-toxic" title="${c}">${c}</span>`).join('');
  }
  if (key === 'processing_notes') {
    const v = row[key];
    if (!v) return '';
    return `<span title="${escHtml(v)}" style="font-size:0.7rem;color:#636e72;max-width:160px;display:inline-block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(v)}</span>`;
  }
  const v = row[key];
  if (v === null || v === undefined || v === '') return '';
  if (typeof v === 'number') return v.toFixed ? v.toFixed(2) : String(v);
  return escHtml(String(v));
}

function renderCell() { return document.createTextNode(''); } // placeholder

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function sortTable(type, key) {
  if (state.sortCol[type] === key) state.sortDir[type] *= -1;
  else { state.sortCol[type] = key; state.sortDir[type] = 1; }
  if (type === 'solvents') renderSolventsTable();
  else renderPolymersTable();
}

function showTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name) && document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('tabcontent-' + name) && document.getElementById('tabcontent-' + name).classList.add('active');
}

function setOverride(idx, key, val, src) {
  // Find the row in processed solvents or polymers by index
  const allData = [...getFilteredSolvents(), ...getFilteredPolymers()];
  if (allData[idx]) allData[idx]._override = val;
  renderSolventsTable();
  renderPolymersTable();
}

// ============================================================
// QUALITY REPORT
// ============================================================
function renderQualityReport() {
  const el = document.getElementById('quality-report-content');
  const solvents = state.processedSolvents;
  const polymers = state.processedPolymers;
  const all = [...solvents, ...polymers];

  // Confidence distribution
  const confDist = [
    {label:'High (>=0.85)', count: all.filter(r=>r.confidence_score>=0.85).length, color:'#27ae60'},
    {label:'Medium (0.60-0.84)', count: all.filter(r=>r.confidence_score>=0.60&&r.confidence_score<0.85).length, color:'#f39c12'},
    {label:'Low (0.30-0.59)', count: all.filter(r=>r.confidence_score>=0.30&&r.confidence_score<0.60).length, color:'#e67e22'},
    {label:'Very Low (<0.30)', count: all.filter(r=>r.confidence_score<0.30).length, color:'#e74c3c'},
  ];

  // Issues
  const issues = [];
  all.forEach((r, i) => {
    if (r.verify_inchikey_mismatch) issues.push({type:'err', name:r.name||'?', msg:'InChIKey mismatch'});
    if (r.verify_cas_conflict) issues.push({type:'err', name:r.name||'?', msg:'CAS conflict'});
    if (r.verify_hsp_outlier) issues.push({type:'warn', name:r.name||'?', msg:`HSP out of range: dD=${r.dd},dP=${r.dp},dH=${r.dh}`});
    if (r.already_in_database) issues.push({type:'warn', name:r.name||'?', msg:'Already in database'});
    if (r.duplicate_in_batch) issues.push({type:'err', name:r.name||'?', msg:'Duplicate in batch'});
    if (r.lookup_failed) issues.push({type:'warn', name:r.name||'?', msg:'PubChem lookup failed'});
    if (r.cf_status === 'proxy_required') issues.push({type:'warn', name:r.name||'?', msg:'ClassyFire requires proxy'});
  });

  // PubChem coverage
  const withCID = all.filter(r=>r.pubchem_cid).length;
  const withCAS = all.filter(r=>r.cas_final).length;
  const withSMILES = all.filter(r=>r.smiles_canonical).length;
  const withInChIKey = all.filter(r=>r.inchikey).length;
  const withGHS = solvents.filter(r=>r.ghs_hazard_codes).length;
  const withICH = solvents.filter(r=>r.ich_q3c_class).length;
  const withCF = all.filter(r=>r.cf_status==='ok').length;

  el.innerHTML = `
    <div class="qr-section">
      <h4>Confidence Distribution</h4>
      <table>
        <thead><tr><th>Level</th><th>Count</th><th>%</th><th>Bar</th></tr></thead>
        <tbody>
          ${confDist.map(d => `<tr>
            <td><span style="color:${d.color};font-weight:700">${d.label}</span></td>
            <td>${d.count}</td>
            <td>${all.length ? (100*d.count/all.length).toFixed(1) : 0}%</td>
            <td><div style="background:${d.color};height:10px;border-radius:3px;width:${all.length?Math.round(200*d.count/all.length):0}px;min-width:2px"></div></td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
    <div class="qr-section">
      <h4>Data Coverage</h4>
      <table>
        <thead><tr><th>Field</th><th>Count</th><th>Coverage</th></tr></thead>
        <tbody>
          ${[
            ['PubChem CID', withCID, all.length],
            ['CAS Number', withCAS, all.length],
            ['SMILES', withSMILES, all.length],
            ['InChIKey', withInChIKey, all.length],
            ['GHS Hazard (solvents)', withGHS, solvents.length],
            ['ICH Q3C (solvents)', withICH, solvents.length],
            ['ClassyFire', withCF, all.length],
          ].map(([lbl, cnt, tot]) => `<tr>
            <td>${lbl}</td>
            <td>${cnt} / ${tot}</td>
            <td>
              <div style="background:#eee;border-radius:3px;height:8px;width:120px;overflow:hidden">
                <div style="background:#27ae60;height:8px;width:${tot?Math.round(120*cnt/tot):0}px"></div>
              </div>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
    <div class="qr-section">
      <h4>Issues &amp; Warnings (${issues.length})</h4>
      ${issues.length ? `<ul class="issues-list">
        ${issues.slice(0,100).map(iss => `<li>
          <span class="issue-type ${iss.type}">${iss.type === 'err' ? 'ERROR' : 'WARN'}</span>
          <strong>${escHtml(iss.name)}</strong>: ${escHtml(iss.msg)}
        </li>`).join('')}
        ${issues.length > 100 ? `<li style="color:#636e72">... and ${issues.length-100} more</li>` : ''}
      </ul>` : '<p style="color:#27ae60;font-size:0.88rem">No issues found!</p>'}
    </div>
  `;
}


// ============================================================
// DOWNLOAD CSV
// ============================================================
function downloadCSV(type) {
  const data = type === 'solvents' ? state.processedSolvents : state.processedPolymers;
  if (!data.length) { alert('No ' + type + ' data to download.'); return; }
  const cols = type === 'solvents' ? SOLVENT_COLS : POLYMER_COLS;
  const keys = cols.filter(c => c.key !== '_idx' && c.key !== '_override').map(c => c.key);
  const header = keys.join(',');
  const rows = data.map(row => keys.map(k => {
    const v = row[k];
    if (v === null || v === undefined) return '';
    const s = String(v);
    if (s.includes(',') || s.includes('"') || s.includes('\n')) return '"' + s.replace(/"/g,'""') + '"';
    return s;
  }).join(','));
  const csv = header + '\n' + rows.join('\n');
  const blob = new Blob([csv], {type:'text/csv'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = state.dsId + '_' + type + '_processed.csv';
  a.click(); URL.revokeObjectURL(url);
}

// ============================================================
// COMMIT TO DATABASE
// ============================================================
function commitToDatabase() {
  const skipLowConf = document.getElementById('opt-skip-low-conf').checked;
  const skipReview = document.getElementById('opt-skip-review').checked;
  const skipDupe = document.getElementById('opt-skip-dupe').checked;

  let chemicals = state.processedSolvents.filter(r => {
    if (skipLowConf && r.confidence_score < 0.60 && !r._override) return false;
    if (skipReview && r.needs_manual_review && !r._override) return false;
    if (skipDupe && r.already_in_database) return false;
    return true;
  });
  let polymers = state.processedPolymers.filter(r => {
    if (skipLowConf && r.confidence_score < 0.60 && !r._override) return false;
    if (skipReview && r.needs_manual_review && !r._override) return false;
    if (skipDupe && r.already_in_database) return false;
    return true;
  });

  // Build final chemical records matching localStorage schema
  const chemRecords = chemicals.map(r => ({
    name: r.name || r.name_cleaned || r.name_original || '',
    cas_final: r.cas_final || '',
    dd: r.dd, dp: r.dp, dh: r.dh,
    mw: r.mw || null,
    bp: r.bp || null,
    density: r.density || null,
    smiles_canonical: r.smiles_canonical || r.smiles_input || null,
    smiles_isomeric: r.smiles_isomeric || null,
    mol_formula: r.mol_formula || null,
    name_iupac: r.name_iupac || null,
    pubchem_cid: r.pubchem_cid || null,
    inchikey: r.inchikey || null,
    ghs_hazard_codes: r.ghs_hazard_codes || null,
    ghs_signal_word: r.ghs_signal_word || null,
    ich_q3c_class: r.ich_q3c_class || null,
    flag_carcinogen: r.flag_carcinogen || false,
    flag_reproductive_toxin: r.flag_reproductive_toxin || false,
    flag_flammable: r.flag_flammable || false,
    flag_acutely_toxic: r.flag_acutely_toxic || false,
    cf_superclass: r.cf_superclass || null,
    cf_class: r.cf_class || null,
    confidence_score: r.confidence_score,
    confidence_label: r.confidence_label,
    score_cas: r.score_cas, score_name_match: r.score_name_match,
    score_pubchem: r.score_pubchem, score_smiles: r.score_smiles,
    score_crossref: r.score_crossref, score_properties: r.score_properties,
    verify_inchikey_mismatch: r.verify_inchikey_mismatch || false,
    verify_cas_conflict: r.verify_cas_conflict || false,
    verify_hsp_outlier: r.verify_hsp_outlier || false,
    already_in_database: r.already_in_database || false,
    needs_manual_review: r.needs_manual_review || false,
    processing_notes: r.processing_notes || null,
    src: r.src || state.dsId,
    dsId: state.dsId,
  }));

  const polyRecords = polymers.map(r => ({
    name: r.name || r.name_cleaned || r.name_original || '',
    cas_final: r.cas_final || '',
    dd: r.dd, dp: r.dp, dh: r.dh, r: r.r || null,
    smiles_repeat_unit: r.smiles_canonical || r.smiles_input || null,
    name_iupac: r.name_iupac || null,
    pubchem_cid: r.pubchem_cid || null,
    inchikey: r.inchikey || null,
    cf_superclass: r.cf_superclass || null,
    cf_class: r.cf_class || null,
    confidence_score: r.confidence_score,
    confidence_label: r.confidence_label,
    needs_manual_review: r.needs_manual_review || false,
    processing_notes: r.processing_notes || null,
    src: r.src || state.dsId,
    dsId: state.dsId,
  }));

  // Load existing datasets
  let datasets = {};
  try {
    datasets = JSON.parse(localStorage.getItem('materialism_imported_datasets') || '{}');
  } catch(e) {}

  // Build dataset entry
  datasets[state.dsId] = {
    chemicals: chemRecords,
    polymers: polyRecords,
    meta: {
      id: state.dsId,
      name: state.dsName,
      source_url: state.dsUrl || '',
      imported_at: new Date().toISOString(),
      chemical_count: chemRecords.length,
      polymer_count: polyRecords.length,
    },
    _imported: true,
  };

  try {
    localStorage.setItem('materialism_imported_datasets', JSON.stringify(datasets));
  } catch(e) {
    if (e.name === 'QuotaExceededError') {
      alert('localStorage quota exceeded. Try reducing the dataset size or clearing old datasets in database.html.');
      return;
    }
    alert('Error saving to localStorage: ' + e.message);
    return;
  }

  const msg = document.getElementById('commit-msg');
  msg.style.display = 'block';
  msg.innerHTML = `
    <strong>Committed successfully!</strong><br>
    Saved <strong>${chemRecords.length}</strong> chemical${chemRecords.length !== 1 ? 's' : ''}
    and <strong>${polyRecords.length}</strong> polymer${polyRecords.length !== 1 ? 's' : ''}
    under dataset ID <code>${escHtml(state.dsId)}</code>.<br>
    <a href="database.html" style="color:#1a7a45;font-weight:700">&#10140; Go to Database</a>
    &nbsp;&nbsp;
    <a href="materialism.html" style="color:#1a7a45;font-weight:700">&#10140; View Visualization</a>
  `;
  msg.scrollIntoView({behavior:'smooth'});
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  setSidebarActive('sbar-upload');
  // Mark all sidebar steps as not-done initially
  document.querySelectorAll('.step-item').forEach(el => el.classList.remove('done','active'));
  document.getElementById('sbar-upload').classList.add('active');
  // Watch meta fields for enable/disable of process button
  document.getElementById('meta-name').addEventListener('input', () => {
    const ok = /^[a-z0-9_]+$/.test(document.getElementById('meta-id').value) &&
               document.getElementById('meta-id').value.length > 0 &&
               document.getElementById('meta-name').value.trim().length > 0;
    document.getElementById('btn-process').disabled = !ok;
  });
  // Try to restore progress from sessionStorage on load
  // (User refreshed during pipeline - offer resume)
  const savedKeys = Object.keys(sessionStorage).filter(k => k.startsWith('materialism_checkpoint_'));
  if (savedKeys.length > 0) {
    const restore = confirm('A previous import session was interrupted. Resume it?');
    if (!restore) {
      savedKeys.forEach(k => sessionStorage.removeItem(k));
    }
    // If restore=true, the pipeline will pick up checkpoints when re-started
  }
});
</script>
</body>
</html>

"""
