// ==============================================================================
// AegisBank AI - Enterprise Banking Fraud Detection System
// Complete Frontend Client Logic & REST API Integration Engine
// ==============================================================================

let sampleScenarios = [];
let datasetFeatures = [];
let liveStreamInterval = null;
let charts = {
  volumeTrend: null,
  typeDistribution: null,
  riskAmount: null,
  actionsBreakdown: null
};

// --- Application Initialization ---
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initSidebar();
  fetchHealth();
  fetchStats();
  loadTransactions();
  fetchScenarios();
  setupForm();
  setupCsvUpload();
  fetchDatasetOverview();
  fetchModelInsights();
  loadReportData();
  initVisualizationCharts();

  // Periodically check API health
  setInterval(fetchHealth, 15000);
});

// ==============================================================================
// 1. NAVIGATION & SIDEBAR MANAGEMENT
// ==============================================================================

function initTabs() {
  const navLinks = document.querySelectorAll(".sidebar-nav .nav-link");
  navLinks.forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const tabId = link.getAttribute("data-tab");
      activateTab(tabId, link);
    });
  });

  // Handle URL hash routing on initial load
  const hash = window.location.hash.replace("#", "");
  const hashMapping = {
    "dashboard": "tab-dashboard",
    "dataset-overview": "tab-dataset",
    "analytics": "tab-analytics",
    "fraud-detection": "tab-detector",
    "report": "tab-report",
    "visualization": "tab-visualization",
    "workflow": "tab-workflow",
    "about-project": "tab-about",
    "connect-api": "tab-api"
  };

  if (hash && hashMapping[hash]) {
    switchToTab(hashMapping[hash]);
  }
}

function switchToTab(tabId) {
  const link = document.querySelector(`.sidebar-nav .nav-link[data-tab="${tabId}"]`);
  activateTab(tabId, link);
}

function activateTab(tabId, activeLink) {
  // Update sidebar active link
  document.querySelectorAll(".sidebar-nav .nav-link").forEach(l => l.classList.remove("active"));
  if (activeLink) {
    activeLink.classList.add("active");
  } else {
    const matching = document.querySelector(`.sidebar-nav .nav-link[data-tab="${tabId}"]`);
    if (matching) matching.classList.add("active");
  }

  // Update visible pane
  document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
  const targetPane = document.getElementById(tabId);
  if (targetPane) {
    targetPane.classList.add("active");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // Update header breadcrumb title
  const titleMap = {
    "tab-dashboard": "Dashboard & Surveillance",
    "tab-dataset": "Dataset Overview & Benchmark",
    "tab-analytics": "Machine Learning Diagnostics",
    "tab-detector": "Real-Time Fraud Detection Engine",
    "tab-report": "Audit & Compliance Report",
    "tab-visualization": "Interactive Visualizations",
    "tab-workflow": "System Architecture & Decision Flow",
    "tab-about": "About Project & Model Specs",
    "tab-api": "Connect Fraud Detection API"
  };

  const titleEl = document.getElementById("header-active-title");
  if (titleEl && titleMap[tabId]) {
    titleEl.innerText = titleMap[tabId];
  }

  // Close mobile sidebar if open
  const sidebar = document.getElementById("app-sidebar");
  if (sidebar && window.innerWidth <= 900) {
    sidebar.classList.remove("mobile-open");
  }

  // Trigger lazy-load actions per tab
  if (tabId === "tab-visualization") {
    setTimeout(refreshVisualizationCharts, 150);
  } else if (tabId === "tab-report") {
    loadReportData();
    loadTransactions();
  } else if (tabId === "tab-dataset") {
    fetchDatasetOverview();
  } else if (tabId === "tab-analytics") {
    fetchModelInsights();
  }
}

function initSidebar() {
  const toggleBtn = document.getElementById("sidebar-toggle-btn");
  const sidebar = document.getElementById("app-sidebar");
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      toggleSidebar();
    });
  }
}

function toggleSidebar() {
  const sidebar = document.getElementById("app-sidebar");
  if (!sidebar) return;
  if (window.innerWidth <= 900) {
    sidebar.classList.toggle("mobile-open");
  } else {
    sidebar.classList.toggle("collapsed");
  }
}

// ==============================================================================
// 2. SYSTEM HEALTH & METRICS
// ==============================================================================

async function fetchHealth() {
  const start = performance.now();
  try {
    const res = await fetch("/api/health");
    const latency = Math.round(performance.now() - start);
    const pill = document.getElementById("health-pill");
    const statusText = document.getElementById("health-status-text");

    if (res.ok) {
      if (pill) pill.className = "health-pill online";
      if (statusText) statusText.innerHTML = `API Online (<span id="health-latency">${latency}ms</span>)`;
    } else {
      if (pill) pill.className = "health-pill error";
      if (statusText) statusText.innerText = "API Degraded";
    }
  } catch (err) {
    const pill = document.getElementById("health-pill");
    const statusText = document.getElementById("health-status-text");
    if (pill) pill.className = "health-pill offline";
    if (statusText) statusText.innerText = "API Offline";
  }
}

async function fetchStats() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) return;
    const stats = await res.json();

    const elTotal = document.getElementById("kpi-total");
    const elGen = document.getElementById("kpi-genuine");
    const elFraud = document.getElementById("kpi-fraud");
    const elBadge = document.getElementById("kpi-rate-badge");
    const elPrevented = document.getElementById("kpi-prevented");

    if (elTotal) elTotal.innerText = Number(stats.total_transactions).toLocaleString();
    if (elGen) elGen.innerText = Number(stats.genuine_count).toLocaleString();
    if (elFraud) elFraud.innerText = Number(stats.fraud_count).toLocaleString();
    if (elBadge) elBadge.innerText = `${stats.fraud_rate_percentage}% Rate`;
    if (elPrevented) {
      elPrevented.innerText = "$" + Number(stats.total_fraud_amount_prevented).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
    }
  } catch (err) {
    console.error("Failed to fetch system stats:", err);
  }
}

// ==============================================================================
// 3. TRANSACTION AUDIT LOG & LIVE FEED
// ==============================================================================

async function loadTransactions() {
  const tbody = document.getElementById("transactions-body");
  const feedList = document.getElementById("dashboard-feed-list");
  const filterEl = document.getElementById("filter-verdict");
  const filter = filterEl ? filterEl.value : "";

  let url = "/api/transactions?limit=50";
  if (filter) {
    url += `&verdict=${encodeURIComponent(filter)}`;
  }

  try {
    const res = await fetch(url);
    if (!res.ok) return;
    const items = await res.json();

    // 1. Populate Report Audit Trail Table
    if (tbody) {
      if (items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" class="text-center" style="padding: 2.5rem; color: var(--text-muted);">No transactions recorded yet. Run a test scenario or trigger simulation traffic!</td></tr>`;
      } else {
        tbody.innerHTML = items.map(tx => {
          const isFraud = tx.verdict === "FRAUD" || tx.is_fraud;
          const badgeClass = isFraud ? "badge-fraud" : "badge-genuine";
          const scorePct = (tx.risk_score * 100).toFixed(1) + "%";
          const timeFormatted = new Date(tx.timestamp).toLocaleString();

          return `
            <tr>
              <td style="font-weight: 700; font-family: 'JetBrains Mono', monospace;">${escapeHtml(tx.transaction_id)}</td>
              <td><span class="type-pill">${escapeHtml(tx.transaction_type)}</span></td>
              <td style="font-weight: 700;">$${parseFloat(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
              <td style="font-family: 'JetBrains Mono', monospace;">${escapeHtml(tx.account_id)}</td>
              <td style="font-family: 'JetBrains Mono', monospace;">${escapeHtml(tx.recipient_id)}</td>
              <td><span style="color: ${isFraud ? 'var(--accent-red)' : 'var(--accent-green)'}; font-weight: 700;">${scorePct}</span></td>
              <td><span class="badge ${badgeClass}">${escapeHtml(tx.verdict)}</span></td>
              <td><span class="action-tag action-${tx.action}">${escapeHtml(tx.action)}</span></td>
              <td style="color: var(--text-muted); font-size: 0.8rem;">${timeFormatted}</td>
            </tr>
          `;
        }).join("");
      }
    }

    // 2. Populate Dashboard Live Feed (Top 6 latest)
    if (feedList) {
      if (items.length === 0) {
        feedList.innerHTML = `<div class="feed-empty">No transactions logged yet. Click "Simulate 5 Txns" or test a benchmark scenario!</div>`;
      } else {
        const topRecent = items.slice(0, 6);
        feedList.innerHTML = topRecent.map(tx => {
          const isFraud = tx.verdict === "FRAUD" || tx.is_fraud;
          const icon = isFraud ? "🚨" : "✅";
          const borderClass = isFraud ? "feed-fraud" : "feed-genuine";
          const scorePct = (tx.risk_score * 100).toFixed(1);
          let reasonSnippet = "Normal transaction pattern";
          try {
            const reasons = typeof tx.reasons === "string" ? JSON.parse(tx.reasons) : tx.reasons;
            if (reasons && reasons.length > 0) {
              reasonSnippet = reasons[0];
            }
          } catch (e) {
            if (tx.reasons) reasonSnippet = String(tx.reasons);
          }

          return `
            <div class="feed-item ${borderClass}">
              <div class="feed-item-icon">${icon}</div>
              <div class="feed-item-info">
                <div class="feed-item-top">
                  <span class="feed-item-id">${escapeHtml(tx.transaction_id)}</span>
                  <span class="feed-item-amount">$${parseFloat(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
                <div class="feed-item-sub">
                  <span>${escapeHtml(tx.transaction_type)} &bull; ${escapeHtml(tx.account_id)} &rarr; ${escapeHtml(tx.recipient_id)}</span>
                  <span class="feed-item-action ${isFraud ? 'text-red' : 'text-green'}">${escapeHtml(tx.action)} (${scorePct}%)</span>
                </div>
                <div class="feed-item-reason">${escapeHtml(reasonSnippet)}</div>
              </div>
            </div>
          `;
        }).join("");
      }
    }
  } catch (err) {
    console.error("Failed to load transactions:", err);
  }
}

async function clearAuditLog() {
  if (!confirm("Are you sure you want to clear all records from the database audit log?")) return;
  try {
    const res = await fetch("/api/transactions", { method: "DELETE" });
    if (res.ok) {
      showToast("Audit database cleared successfully.", "success");
      loadTransactions();
      fetchStats();
      loadReportData();
      if (document.getElementById("tab-visualization").classList.contains("active")) {
        refreshVisualizationCharts();
      }
    }
  } catch (err) {
    showToast("Error clearing audit log: " + err.message, "error");
  }
}

// ==============================================================================
// 4. TRAFFIC SIMULATOR & STREAMING
// ==============================================================================

async function triggerSimulation(count = 5) {
  try {
    const res = await fetch(`/api/simulate?count=${count}`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      showToast(`Injected ${count} simulated transactions into pipeline.`, "info");
      fetchStats();
      loadTransactions();
      if (data.results && data.results.length > 0) {
        displayResult(data.results[data.results.length - 1]);
      }
      if (document.getElementById("tab-visualization").classList.contains("active")) {
        refreshVisualizationCharts();
      }
    }
  } catch (err) {
    showToast("Simulation failed: " + err.message, "error");
  }
}

function toggleLiveStream() {
  const btn = document.getElementById("btn-live-stream");
  const label = document.getElementById("live-stream-label");

  if (liveStreamInterval) {
    clearInterval(liveStreamInterval);
    liveStreamInterval = null;
    if (btn) btn.classList.remove("streaming");
    if (label) label.innerText = "Live Stream: OFF";
    showToast("Live streaming stopped.", "info");
  } else {
    if (btn) btn.classList.add("streaming");
    if (label) label.innerText = "Live Stream: ACTIVE";
    showToast("Live transaction stream started (every 3s).", "success");
    triggerSimulation(1);
    liveStreamInterval = setInterval(() => {
      triggerSimulation(1);
    }, 3200);
  }
}

// ==============================================================================
// 5. FRAUD DETECTION INTERACTIVE ENGINE
// ==============================================================================

async function fetchScenarios() {
  try {
    const res = await fetch("/api/sample-scenarios");
    if (res.ok) {
      sampleScenarios = await res.json();
    }
  } catch (err) {
    console.error("Failed to load sample scenarios:", err);
  }
}

function loadScenario(index) {
  if (!sampleScenarios || !sampleScenarios[index]) return;
  const p = sampleScenarios[index].payload;

  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = val;
  };

  setVal("transaction_id", "TXN-" + Math.floor(100000 + Math.random() * 900000));
  setVal("transaction_type", p.transaction_type);
  setVal("account_id", p.account_id);
  setVal("recipient_id", p.recipient_id);
  setVal("amount", p.amount);
  setVal("old_balance_orig", p.old_balance_orig);
  setVal("new_balance_orig", p.new_balance_orig !== null ? p.new_balance_orig : "");
  setVal("velocity_1h", p.velocity_1h);
  setVal("distance_from_home_km", p.distance_from_home_km);
  setVal("device_trust_score", p.device_trust_score);

  const trustDisp = document.getElementById("trust-display");
  if (trustDisp) trustDisp.innerText = p.device_trust_score;

  const foreignEl = document.getElementById("is_foreign");
  if (foreignEl) foreignEl.checked = !!p.is_foreign;

  const highRiskEl = document.getElementById("is_high_risk_merchant");
  if (highRiskEl) highRiskEl.checked = !!p.is_high_risk_merchant;
}

function loadScenarioAndEvaluate(index) {
  switchToTab("tab-detector");
  loadScenario(index);
  const form = document.getElementById("fraud-form");
  if (form) {
    setTimeout(() => {
      form.dispatchEvent(new Event("submit", { cancelable: true }));
    }, 100);
  }
}

function autoComputeBalance() {
  const amtEl = document.getElementById("amount");
  const oldBalEl = document.getElementById("old_balance_orig");
  const newBalEl = document.getElementById("new_balance_orig");
  if (!amtEl || !oldBalEl || !newBalEl) return;

  const amt = parseFloat(amtEl.value) || 0;
  const oldBal = parseFloat(oldBalEl.value) || 0;
  if (oldBal >= amt) {
    newBalEl.value = (oldBal - amt).toFixed(2);
  } else {
    newBalEl.value = "0.00";
  }
}

function setupForm() {
  const form = document.getElementById("fraud-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const submitBtn = document.getElementById("btn-submit");
    const spinner = document.getElementById("btn-spinner");
    const btnText = document.getElementById("btn-text");

    if (submitBtn) submitBtn.disabled = true;
    if (spinner) spinner.style.display = "inline-block";
    if (btnText) btnText.innerText = "Evaluating AI Models...";

    const payload = {
      transaction_id: document.getElementById("transaction_id").value.trim() || undefined,
      account_id: document.getElementById("account_id").value.trim(),
      recipient_id: document.getElementById("recipient_id").value.trim(),
      transaction_type: document.getElementById("transaction_type").value,
      amount: parseFloat(document.getElementById("amount").value),
      old_balance_orig: parseFloat(document.getElementById("old_balance_orig").value),
      new_balance_orig: document.getElementById("new_balance_orig").value ? parseFloat(document.getElementById("new_balance_orig").value) : null,
      velocity_1h: parseInt(document.getElementById("velocity_1h").value) || 1,
      distance_from_home_km: parseFloat(document.getElementById("distance_from_home_km").value) || 0.0,
      device_trust_score: parseFloat(document.getElementById("device_trust_score").value) || 1.0,
      is_foreign: document.getElementById("is_foreign").checked,
      is_high_risk_merchant: document.getElementById("is_high_risk_merchant").checked
    };

    try {
      const response = await fetch("/api/fraud-detection", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const result = await response.json();
      displayResult(result);
      fetchStats();
      loadTransactions();
      showToast(result.is_fraud ? "Alert: Fraud detected & intercepted!" : "Success: Genuine transaction approved.", result.is_fraud ? "error" : "success");
    } catch (error) {
      showToast("Evaluation error: " + error.message, "error");
    } finally {
      if (submitBtn) submitBtn.disabled = false;
      if (spinner) spinner.style.display = "none";
      if (btnText) btnText.innerText = "Detect Fraud Status";
    }
  });
}

function displayResult(res) {
  const placeholder = document.getElementById("verdict-placeholder");
  const resultCard = document.getElementById("verdict-result");
  const banner = document.getElementById("verdict-banner");
  const icon = document.getElementById("verdict-icon");
  const statusText = document.getElementById("verdict-text");
  const actionText = document.getElementById("verdict-action");
  const badge = document.getElementById("risk-badge");
  const riskPct = document.getElementById("risk-percentage");
  const barFill = document.getElementById("risk-bar-fill");
  const reasonsList = document.getElementById("reasons-list");
  const jsonOutput = document.getElementById("json-output");

  if (placeholder) placeholder.style.display = "none";
  if (resultCard) resultCard.classList.remove("hidden");

  const isFraud = res.verdict === "FRAUD" || res.is_fraud;

  if (banner) {
    banner.className = isFraud ? "verdict-banner banner-fraud" : "verdict-banner banner-genuine";
  }
  if (icon) icon.innerText = isFraud ? "🚨" : "✅";
  if (statusText) statusText.innerText = isFraud ? "FRAUD DETECTED - TRANSACTION INTERCEPTED" : "GENUINE TRANSACTION - APPROVED";
  if (actionText) actionText.innerText = `Action Directive: ${res.action} (${res.risk_level} RISK)`;
  if (badge) {
    badge.innerText = `${res.risk_level} RISK`;
    badge.className = `verdict-badge badge-${res.risk_level.toLowerCase()}`;
  }

  // Risk Bar
  const pct = Math.min(100, Math.max(0, res.risk_percentage || (res.risk_score * 100)));
  if (riskPct) riskPct.innerText = `${pct.toFixed(1)}%`;
  if (barFill) {
    barFill.style.width = `${pct}%`;
    barFill.className = `risk-bar-fill ${pct > 60 ? 'risk-high' : pct > 30 ? 'risk-medium' : 'risk-low'}`;
  }

  // Explanations List
  if (reasonsList) {
    reasonsList.innerHTML = "";
    if (res.reasons && res.reasons.length > 0) {
      res.reasons.forEach(r => {
        const li = document.createElement("li");
        li.innerText = r;
        reasonsList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.innerText = "All behavioral heuristics and XGBoost thresholds satisfied.";
      reasonsList.appendChild(li);
    }
  }

  // Metadata
  const resTx = document.getElementById("res-tx-id");
  const resAmt = document.getElementById("res-amount");
  const resTime = document.getElementById("res-time");
  if (resTx) resTx.innerText = res.transaction_id;
  if (resAmt) resAmt.innerText = "$" + res.amount.toLocaleString(undefined, { minimumFractionDigits: 2 });
  if (resTime) resTime.innerText = new Date(res.timestamp).toLocaleTimeString();

  // Raw JSON
  if (jsonOutput) {
    jsonOutput.innerText = JSON.stringify(res, null, 2);
  }
}

// ==============================================================================
// 6. DATASET OVERVIEW & EXPLORER
// ==============================================================================

async function fetchDatasetOverview() {
  try {
    const res = await fetch("/api/dataset/overview");
    if (!res.ok) return;
    const data = await res.json();

    // Summary Stat Cards
    const dsName = document.getElementById("ds-name");
    const dsTotal = document.getElementById("ds-total");
    const dsFeatures = document.getElementById("ds-features");
    const dsRatio = document.getElementById("ds-ratio");

    if (dsName) dsName.innerText = data.dataset_name || "PaySim Banking Benchmark";
    if (dsTotal) dsTotal.innerText = Number(data.total_records || 30000).toLocaleString();
    if (dsFeatures) dsFeatures.innerText = `${data.features_count || 18} Features`;
    if (dsRatio) dsRatio.innerText = (data.class_distribution && data.class_distribution.class_imbalance_ratio) || "10.76 : 1";

    // Feature Dictionary
    datasetFeatures = data.features_dictionary || [];
    renderFeatureDictionary(datasetFeatures);

    // Sample Benchmark Records
    const sampleTbody = document.getElementById("sample-dataset-tbody");
    if (sampleTbody && data.sample_records && data.sample_records.length > 0) {
      sampleTbody.innerHTML = data.sample_records.map((row, idx) => {
        return `
          <tr>
            <td style="font-family: 'JetBrains Mono', monospace; font-weight: 700;">${escapeHtml(row.transaction_id)}</td>
            <td><span class="type-pill">${escapeHtml(row.transaction_type)}</span></td>
            <td style="font-weight: 700;">$${parseFloat(row.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
            <td style="font-family: 'JetBrains Mono', monospace;">${escapeHtml(row.account_id)}</td>
            <td style="font-family: 'JetBrains Mono', monospace;">${escapeHtml(row.recipient_id)}</td>
            <td>$${parseFloat(row.old_balance_orig || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
            <td>${escapeHtml(row.velocity_1h)}/hr</td>
            <td>${escapeHtml(row.distance_from_home_km)} km</td>
            <td>${row.is_foreign == "1" || row.is_foreign === true ? '<span class="text-red">Yes</span>' : 'No'}</td>
            <td>${escapeHtml(row.device_trust_score)}</td>
            <td>
              <button class="btn-sm" onclick="evaluateSingleSampleRecord(${idx})">Test &rarr;</button>
            </td>
          </tr>
        `;
      }).join("");
    }
  } catch (err) {
    console.error("Failed to load dataset overview:", err);
  }
}

function renderFeatureDictionary(features) {
  const tbody = document.getElementById("features-tbody");
  if (!tbody) return;

  if (!features || features.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No matching features found.</td></tr>`;
    return;
  }

  tbody.innerHTML = features.map(f => {
    return `
      <tr>
        <td style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-blue);">${escapeHtml(f.name)}</td>
        <td><span class="badge badge-purple">${escapeHtml(f.category)}</span></td>
        <td><code>${escapeHtml(f.type)}</code></td>
        <td style="color: var(--text-secondary); font-size: 0.88rem;">${escapeHtml(f.description)}</td>
      </tr>
    `;
  }).join("");
}

function filterFeatureDictionary() {
  const query = (document.getElementById("feature-search")?.value || "").toLowerCase();
  if (!query) {
    renderFeatureDictionary(datasetFeatures);
    return;
  }
  const filtered = datasetFeatures.filter(f => 
    f.name.toLowerCase().includes(query) ||
    f.description.toLowerCase().includes(query) ||
    f.category.toLowerCase().includes(query)
  );
  renderFeatureDictionary(filtered);
}

async function evaluateSingleSampleRecord(index) {
  try {
    const res = await fetch("/api/dataset/overview");
    const data = await res.json();
    if (data.sample_records && data.sample_records[index]) {
      const row = data.sample_records[index];
      switchToTab("tab-detector");

      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val;
      };

      setVal("transaction_id", row.transaction_id || "TXN-TEST");
      setVal("transaction_type", row.transaction_type);
      setVal("account_id", row.account_id);
      setVal("recipient_id", row.recipient_id);
      setVal("amount", row.amount);
      setVal("old_balance_orig", row.old_balance_orig);
      setVal("new_balance_orig", row.new_balance_orig || "");
      setVal("velocity_1h", row.velocity_1h || 1);
      setVal("distance_from_home_km", row.distance_from_home_km || 0);
      setVal("device_trust_score", row.device_trust_score || 1.0);

      const trustDisp = document.getElementById("trust-display");
      if (trustDisp) trustDisp.innerText = row.device_trust_score || "1.0";

      const foreignEl = document.getElementById("is_foreign");
      if (foreignEl) foreignEl.checked = row.is_foreign == "1" || row.is_foreign === true;

      const highRiskEl = document.getElementById("is_high_risk_merchant");
      if (highRiskEl) highRiskEl.checked = row.is_high_risk_merchant == "1" || row.is_high_risk_merchant === true;

      const form = document.getElementById("fraud-form");
      if (form) {
        setTimeout(() => {
          form.dispatchEvent(new Event("submit", { cancelable: true }));
        }, 100);
      }
    }
  } catch (err) {
    showToast("Failed to load sample record: " + err.message, "error");
  }
}

// ==============================================================================
// 7. BULK CSV UPLOAD & PROCESSING
// ==============================================================================

function setupCsvUpload() {
  const dropArea = document.getElementById("csv-drop-area");
  if (!dropArea) return;

  ["dragenter", "dragover"].forEach(name => {
    dropArea.addEventListener(name, (e) => {
      e.preventDefault();
      dropArea.classList.add("dragover");
    }, false);
  });

  ["dragleave", "drop"].forEach(name => {
    dropArea.addEventListener(name, (e) => {
      e.preventDefault();
      dropArea.classList.remove("dragover");
    }, false);
  });

  dropArea.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    if (dt && dt.files.length > 0) {
      uploadCsvFile(dt.files[0]);
    }
  });
}

function handleCsvFileSelected(event) {
  const file = event.target.files[0];
  if (file) {
    uploadCsvFile(file);
  }
}

async function uploadCsvFile(file) {
  const statusDiv = document.getElementById("upload-status");
  if (statusDiv) {
    statusDiv.innerHTML = `<span class="loading-spinner"></span> Uploading and evaluating ${escapeHtml(file.name)} across models...`;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/fraud-detection/upload-csv", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || `Upload failed with status ${res.status}`);
    }

    const data = await res.json();
    if (statusDiv) {
      statusDiv.innerHTML = `<span class="text-green">✓ Successfully evaluated ${data.total_rows} transactions from ${escapeHtml(file.name)}. Fraud rate: ${data.fraud_rate_percentage}%</span>`;
    }

    // Render Batch metrics
    const container = document.getElementById("batch-metrics-container");
    if (container) container.classList.remove("hidden");

    const elTotal = document.getElementById("batch-total");
    const elGen = document.getElementById("batch-genuine");
    const elFraud = document.getElementById("batch-fraud");
    const elPrev = document.getElementById("batch-prevented");

    if (elTotal) elTotal.innerText = data.total_rows;
    if (elGen) elGen.innerText = data.genuine_detected;
    if (elFraud) elFraud.innerText = data.fraud_detected;
    if (elPrev) elPrev.innerText = "$" + data.total_fraud_amount_prevented.toLocaleString(undefined, { minimumFractionDigits: 2 });

    // Render Batch Table
    const tbody = document.getElementById("batch-results-body");
    if (tbody && data.evaluated_records) {
      tbody.innerHTML = data.evaluated_records.map(rec => {
        const isFraud = rec.verdict === "FRAUD" || rec.is_fraud;
        const reasonsSummary = rec.reasons && rec.reasons.length > 0 ? rec.reasons.join("; ") : "Normal baseline";

        return `
          <tr>
            <td style="font-weight: 700; font-family: 'JetBrains Mono', monospace;">${escapeHtml(rec.transaction_id)}</td>
            <td><span class="type-pill">${escapeHtml(rec.transaction_type)}</span></td>
            <td style="font-weight: 700;">$${parseFloat(rec.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
            <td style="font-family: 'JetBrains Mono', monospace;">${escapeHtml(rec.account_id)}</td>
            <td style="font-family: 'JetBrains Mono', monospace;">${escapeHtml(rec.recipient_id)}</td>
            <td><span style="color: ${isFraud ? 'var(--accent-red)' : 'var(--accent-green)'}; font-weight: 700;">${rec.risk_percentage}%</span></td>
            <td><span class="badge ${isFraud ? 'badge-fraud' : 'badge-genuine'}">${escapeHtml(rec.verdict)}</span></td>
            <td><span class="action-tag action-${rec.action}">${escapeHtml(rec.action)}</span></td>
            <td style="font-size: 0.78rem; color: var(--text-secondary); max-width: 250px;">${escapeHtml(reasonsSummary)}</td>
          </tr>
        `;
      }).join("");
    }

    fetchStats();
    loadTransactions();
    showToast(`Evaluated ${data.total_rows} transactions. Prevented $${data.total_fraud_amount_prevented.toLocaleString()} in fraud!`, "success");
  } catch (err) {
    if (statusDiv) statusDiv.innerHTML = `<span class="text-red">Error: ${escapeHtml(err.message)}</span>`;
    showToast("CSV Upload Error: " + err.message, "error");
  }
}

async function loadSampleCsvFile() {
  const sampleContent = `transaction_id,account_id,recipient_id,transaction_type,amount,old_balance_orig,new_balance_orig,old_balance_dest,new_balance_dest,velocity_1h,distance_from_home_km,is_foreign,is_high_risk_merchant,device_trust_score
TXN-10001,ACC-883192,MCH-SUPERMARKET,PAYMENT,42.50,1450.00,1407.50,54000.00,54042.50,1,1.5,0,0,0.98
TXN-10002,ACC-992104,REC-ANON-881,TRANSFER,75000.00,75000.00,0.00,0.00,0.00,5,320.0,0,1,0.18
TXN-10003,ACC-449102,ATM-FOREIGN-99,CASH_OUT,12000.00,15000.00,3000.00,0.00,12000.00,6,4500.0,1,1,0.15
TXN-10004,CORP-PAYROLL,ACC-331092,CASH_IN,3800.00,195000.00,191200.00,850.00,4650.00,1,0.0,0,0,1.0
TXN-10005,ACC-221094,MCH-COFFEE-01,PAYMENT,4.80,620.00,615.20,12000.00,12004.80,1,0.8,0,0,0.95
TXN-10006,ACC-771923,REC-CRYPTO-EX,TRANSFER,32000.00,32000.00,0.00,0.00,0.00,4,850.0,0,1,0.22
TXN-10007,ACC-661028,MCH-ELECTRONICS,PAYMENT,249.99,3200.00,2950.01,220000.00,220249.99,1,8.4,0,0,0.89
TXN-10008,ACC-551029,REC-UNKNOWN-44,TRANSFER,49000.00,50000.00,1000.00,0.00,0.00,7,1200.0,1,1,0.10`;

  const blob = new Blob([sampleContent], { type: "text/csv" });
  const file = new File([blob], "sample_transactions.csv");
  uploadCsvFile(file);
}

// ==============================================================================
// 8. MACHINE LEARNING ANALYTICS & THRESHOLD SANDBOX
// ==============================================================================

async function fetchModelInsights() {
  try {
    const res = await fetch("/api/model/info");
    if (!res.ok) return;
    const info = await res.json();

    if (info.metrics) {
      const elAuc = document.getElementById("metric-auc");
      const elPrec = document.getElementById("metric-prec");
      const elRec = document.getElementById("metric-rec");
      const elF1 = document.getElementById("metric-f1");

      if (elAuc) elAuc.innerText = (info.metrics.roc_auc || 1.0).toFixed(3);
      if (elPrec) elPrec.innerText = (info.metrics.precision || 1.0).toFixed(3);
      if (elRec) elRec.innerText = (info.metrics.recall || 1.0).toFixed(3);
      if (elF1) elF1.innerText = (info.metrics.f1_score || 1.0).toFixed(3);
    }

    // Render Feature Importance Bars
    const container = document.getElementById("feature-importance-bars");
    if (container && info.feature_importance) {
      const sorted = Object.entries(info.feature_importance)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8);

      const maxImp = sorted[0][1] || 1.0;

      container.innerHTML = sorted.map(([feat, imp]) => {
        const pctWidth = Math.max(4, Math.round((imp / maxImp) * 100));
        return `
          <div class="feat-bar-row">
            <span class="feat-bar-label" title="${escapeHtml(feat)}">${escapeHtml(feat)}</span>
            <div class="feat-bar-track">
              <div class="feat-bar-value-fill" style="width: ${pctWidth}%;"></div>
            </div>
            <span class="feat-bar-pct">${(imp * 100).toFixed(1)}%</span>
          </div>
        `;
      }).join("");
    }

    // Fetch and populate detailed analytics & risk buckets
    fetchRiskBuckets();
  } catch (err) {
    console.error("Failed to load model insights:", err);
  }
}

async function fetchRiskBuckets() {
  try {
    const res = await fetch("/api/analytics/detailed");
    if (!res.ok) return;
    const analytics = await res.json();

    const grid = document.getElementById("risk-buckets-grid");
    if (grid && analytics.risk_buckets) {
      const buckets = analytics.risk_buckets;
      grid.innerHTML = `
        <div class="bucket-card bucket-low">
          <div class="bucket-header">
            <span class="bucket-name">Low Risk (0-25%)</span>
            <span class="bucket-pct">${buckets.low_0_25.percentage}%</span>
          </div>
          <div class="bucket-count">${buckets.low_0_25.count} Txns</div>
          <div class="bucket-bar"><div class="bucket-bar-fill" style="width: ${buckets.low_0_25.percentage}%;"></div></div>
        </div>
        <div class="bucket-card bucket-guarded">
          <div class="bucket-header">
            <span class="bucket-name">Guarded (25-50%)</span>
            <span class="bucket-pct">${buckets.guarded_25_50.percentage}%</span>
          </div>
          <div class="bucket-count">${buckets.guarded_25_50.count} Txns</div>
          <div class="bucket-bar"><div class="bucket-bar-fill" style="width: ${buckets.guarded_25_50.percentage}%;"></div></div>
        </div>
        <div class="bucket-card bucket-elevated">
          <div class="bucket-header">
            <span class="bucket-name">Elevated (50-75%)</span>
            <span class="bucket-pct">${buckets.elevated_50_75.percentage}%</span>
          </div>
          <div class="bucket-count">${buckets.elevated_50_75.count} Txns</div>
          <div class="bucket-bar"><div class="bucket-bar-fill" style="width: ${buckets.elevated_50_75.percentage}%;"></div></div>
        </div>
        <div class="bucket-card bucket-critical">
          <div class="bucket-header">
            <span class="bucket-name">Critical (75-100%)</span>
            <span class="bucket-pct">${buckets.critical_75_100.percentage}%</span>
          </div>
          <div class="bucket-count">${buckets.critical_75_100.count} Txns</div>
          <div class="bucket-bar"><div class="bucket-bar-fill" style="width: ${buckets.critical_75_100.percentage}%;"></div></div>
        </div>
      `;
    }
  } catch (err) {
    console.error("Failed to load risk buckets:", err);
  }
}

function updateThresholdSandbox(value) {
  const val = parseFloat(value);
  const disp = document.getElementById("thresh-display");
  const badge = document.getElementById("mode-badge");
  const explanation = document.getElementById("mode-explanation");

  if (disp) disp.innerText = val.toFixed(2);

  if (val < 0.35) {
    if (badge) {
      badge.innerText = "PARANOID / ULTRA-STRICT DEFENSE MODE";
      badge.className = "mode-badge badge-strict";
    }
    if (explanation) {
      explanation.innerText = "Highest fraud interception rate. Any mild anomaly triggers 2FA challenge or account hold. Recommended for high-value corporate treasury accounts.";
    }
  } else if (val > 0.65) {
    if (badge) {
      badge.innerText = "HIGH-THROUGHPUT / LOW-FRICTION MODE";
      badge.className = "mode-badge badge-lenient";
    }
    if (explanation) {
      explanation.innerText = "Minimizes consumer friction for e-commerce checkout speed. Only blatant, indisputable fraud patterns (>65% probability) are frozen.";
    }
  } else {
    if (badge) {
      badge.innerText = "BALANCED PRODUCTION MODE (RECOMMENDED)";
      badge.className = "mode-badge badge-balanced";
    }
    if (explanation) {
      explanation.innerText = "Institutional standard configuration. Blends XGBoost ML predictions with financial heuristics for optimal trade-off of risk prevention and customer satisfaction.";
    }
  }
}

// ==============================================================================
// 9. AUDIT & REGULATORY REPORT
// ==============================================================================

async function loadReportData() {
  try {
    const res = await fetch("/api/report/summary");
    if (!res.ok) return;
    const report = await res.json();

    const genTime = document.getElementById("report-gen-time");
    const healthGrade = document.getElementById("report-health-grade");
    const repVol = document.getElementById("rep-total-vol");
    const repPrev = document.getElementById("rep-fraud-vol");
    const repCount = document.getElementById("rep-total-count");
    const repRate = document.getElementById("rep-fraud-rate");

    if (genTime) genTime.innerText = new Date(report.generated_at).toLocaleString();
    if (healthGrade) healthGrade.innerText = report.health_grade;

    if (report.stats) {
      if (repVol) repVol.innerText = "$" + Number(report.stats.total_amount_processed || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
      if (repPrev) repPrev.innerText = "$" + Number(report.stats.total_fraud_amount_prevented || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
      if (repCount) repCount.innerText = Number(report.stats.total_transactions || 0).toLocaleString();
      if (repRate) repRate.innerText = `${report.stats.fraud_rate_percentage || 0}%`;
    }

    // Critical Incidents Table
    const tbody = document.getElementById("report-incidents-body");
    if (tbody) {
      if (!report.critical_incidents || report.critical_incidents.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding: 1.5rem;">No critical fraud incidents logged in current audit window.</td></tr>`;
      } else {
        tbody.innerHTML = report.critical_incidents.map(inc => {
          const reasonsStr = Array.isArray(inc.reasons) ? inc.reasons.join("; ") : String(inc.reasons || "High risk anomaly");
          return `
            <tr>
              <td style="font-family: 'JetBrains Mono', monospace; font-weight: 700;">${escapeHtml(inc.transaction_id)}</td>
              <td style="font-family: 'JetBrains Mono', monospace;">${escapeHtml(inc.account_id)}</td>
              <td style="font-family: 'JetBrains Mono', monospace;">${escapeHtml(inc.recipient_id)}</td>
              <td><span class="type-pill">${escapeHtml(inc.transaction_type)}</span></td>
              <td style="font-weight: 700; color: var(--accent-red);">$${parseFloat(inc.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
              <td><span style="font-weight: 700; color: var(--accent-red);">${(inc.risk_score * 100).toFixed(1)}%</span></td>
              <td><span class="badge badge-fraud">${escapeHtml(inc.action)}</span></td>
              <td style="font-size: 0.8rem; color: var(--text-secondary); max-width: 280px;">${escapeHtml(reasonsStr)}</td>
            </tr>
          `;
        }).join("");
      }
    }
  } catch (err) {
    console.error("Failed to load report data:", err);
  }
}

function printReport() {
  window.print();
}

// ==============================================================================
// 10. INTERACTIVE VISUALIZATION CHARTS
// ==============================================================================

function initVisualizationCharts() {
  if (typeof Chart === "undefined") {
    console.warn("Chart.js not loaded. Visualizations will be disabled.");
    return;
  }

  // Chart defaults for modern fintech dark theme
  Chart.defaults.color = "#94a3b8";
  Chart.defaults.borderColor = "#26354d";
  Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";

  // 1. Volume Trend Chart
  const ctxVolume = document.getElementById("chart-volume-trend");
  if (ctxVolume) {
    charts.volumeTrend = new Chart(ctxVolume, {
      type: "line",
      data: {
        labels: ["T-6", "T-5", "T-4", "T-3", "T-2", "T-1", "Current"],
        datasets: [
          {
            label: "Evaluated Volume",
            data: [12, 19, 15, 25, 22, 30, 40],
            borderColor: "#3b82f6",
            backgroundColor: "rgba(59, 130, 246, 0.15)",
            fill: true,
            tension: 0.35,
            borderWidth: 2
          },
          {
            label: "Fraud Intercepted",
            data: [2, 3, 1, 4, 3, 5, 8],
            borderColor: "#ef4444",
            backgroundColor: "rgba(239, 68, 68, 0.15)",
            fill: true,
            tension: 0.35,
            borderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top" }
        },
        scales: {
          y: { beginAtZero: true }
        }
      }
    });
  }

  // 2. Type Distribution Chart
  const ctxType = document.getElementById("chart-type-distribution");
  if (ctxType) {
    charts.typeDistribution = new Chart(ctxType, {
      type: "doughnut",
      data: {
        labels: ["TRANSFER", "CASH_OUT", "PAYMENT", "CASH_IN", "DEBIT"],
        datasets: [{
          data: [45, 35, 12, 5, 3],
          backgroundColor: ["#ef4444", "#f59e0b", "#3b82f6", "#10b981", "#8b5cf6"],
          borderWidth: 1,
          borderColor: "#151f32"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "right" }
        }
      }
    });
  }

  // 3. Risk Score vs Amount Chart
  const ctxRisk = document.getElementById("chart-risk-amount");
  if (ctxRisk) {
    charts.riskAmount = new Chart(ctxRisk, {
      type: "bar",
      data: {
        labels: ["<$100", "$100-$1K", "$1K-$10K", "$10K-$50K", "$50K+"],
        datasets: [
          {
            label: "Average Risk Score (%)",
            data: [4.2, 8.5, 24.0, 78.5, 96.2],
            backgroundColor: ["#10b981", "#10b981", "#f59e0b", "#ef4444", "#ef4444"],
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { max: 100, beginAtZero: true }
        }
      }
    });
  }

  // 4. Action Directives Breakdown
  const ctxActions = document.getElementById("chart-actions-breakdown");
  if (ctxActions) {
    charts.actionsBreakdown = new Chart(ctxActions, {
      type: "bar",
      data: {
        labels: ["ALLOW", "CHALLENGE_2FA", "FLAG_REVIEW", "BLOCK"],
        datasets: [{
          label: "Policy Enforcement Count",
          data: [35, 8, 4, 18],
          backgroundColor: ["#10b981", "#3b82f6", "#f59e0b", "#ef4444"],
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        plugins: {
          legend: { display: false }
        }
      }
    });
  }

  // Load live chart data from server
  refreshVisualizationCharts();
}

async function refreshVisualizationCharts() {
  if (typeof Chart === "undefined") return;

  try {
    const res = await fetch("/api/analytics/detailed");
    if (!res.ok) return;
    const data = await res.json();

    // Update Type Distribution
    if (charts.typeDistribution && data.by_type) {
      const labels = Object.keys(data.by_type);
      const values = labels.map(l => data.by_type[l].fraud_count || 1);
      charts.typeDistribution.data.labels = labels;
      charts.typeDistribution.data.datasets[0].data = values;
      charts.typeDistribution.update();
    }

    // Update Actions Breakdown
    if (charts.actionsBreakdown && data.by_action) {
      const labels = ["ALLOW", "CHALLENGE_2FA", "FLAG_REVIEW", "BLOCK"];
      const values = labels.map(a => data.by_action[a] || 0);
      charts.actionsBreakdown.data.datasets[0].data = values;
      charts.actionsBreakdown.update();
    }

    // Update Volume Trend
    if (charts.volumeTrend && data.recent_trend && data.recent_trend.length > 0) {
      charts.volumeTrend.data.labels = data.recent_trend.map(r => r.period);
      charts.volumeTrend.data.datasets[0].data = data.recent_trend.map(r => r.total);
      charts.volumeTrend.data.datasets[1].data = data.recent_trend.map(r => r.fraud);
      charts.volumeTrend.update();
    }
  } catch (err) {
    console.error("Failed to refresh visualization charts:", err);
  }
}

// ==============================================================================
// 11. WORKFLOW INTERACTIVE DEEP DIVE
// ==============================================================================

const workflowDetails = {
  1: {
    title: "Stage 01: Transaction Ingress & Validation",
    subtitle: "High-throughput asynchronous payload intake and schema validation",
    content: `
      <div class="wf-explanation">
        <p>Incoming payment transactions are ingested via <code>POST /api/fraud-detection</code>. The payload is checked using Pydantic v2 schemas in less than 0.2ms, ensuring strong typing, positive numeric constraints, and UUID / account validation.</p>
        <div class="wf-features-tag-list mt-3">
          <span class="step-tag">FastAPI ASGI</span>
          <span class="step-tag">Pydantic v2 Validation</span>
          <span class="step-tag">Sub-millisecond Ingress</span>
          <span class="step-tag">CORS Enabled</span>
        </div>
      </div>
      <div class="code-preview mt-3">
<pre><code># FastAPI Endpoint Definition:
@app.post("/api/fraud-detection", response_model=FraudDetectionResponse)
async def analyze_transaction(payload: TransactionRequest, threshold: float = 0.50):
    # Immediate validation & dispatch to hybrid ensemble
    response = detector.evaluate(payload, threshold=threshold)
    save_transaction(response.model_dump())
    return response</code></pre>
      </div>
    `
  },
  2: {
    title: "Stage 02: Real-Time Feature Engineering",
    subtitle: "Mathematical transformation of balances, velocity counters, and device trust telemetry",
    content: `
      <div class="wf-explanation">
        <p>Raw transaction vectors are transformed into 18 predictive features. Key financial discrepancy formulas reveal hidden fraud signatures:</p>
        <div class="wf-equations-box mt-2">
          <code>balance_error_orig = amount - (old_balance_orig - new_balance_orig)</code><br>
          <code>balance_error_dest = (new_balance_dest - old_balance_dest) - amount</code>
        </div>
        <p class="mt-2 text-sm text-secondary">A non-zero <code>balance_error_orig</code> frequently pinpoints identity theft or unauthorized balance draining before the bank's core ledger updates.</p>
      </div>
    `
  },
  3: {
    title: "Stage 03: Dual-Engine Defense Layer (Ensemble)",
    subtitle: "Parallel evaluation combining Domain Heuristic Financial Rules with XGBoost ML",
    content: `
      <div class="wf-explanation">
        <p>Transactions are simultaneously evaluated by two independent defense systems:</p>
        <ul class="styled-list mt-2">
          <li><strong>XGBoost Gradient Tree Model:</strong> Evaluates nonlinear feature interactions over 30,000 transaction topologies with <code>scale_pos_weight=10.76</code>.</li>
          <li><strong>Heuristic Financial Defense Rules:</strong> Zero-tolerance checks for complete balance liquidation, high-frequency velocity bursts (&gt;4/hr), foreign unverified mobile devices, and off-hour withdrawals.</li>
        </ul>
      </div>
      <div class="code-preview mt-3">
<pre><code># Dual-Engine Risk Synthesis:
ml_prob = xgboost_model.predict_proba(features)[1]
rule_score, rule_reasons = evaluate_heuristics(transaction)

# Calibrated Ensemble Weighted Score:
combined_risk = (0.65 * ml_prob) + (0.35 * rule_score)</code></pre>
      </div>
    `
  },
  4: {
    title: "Stage 04: Risk Score Calibration & Explainability",
    subtitle: "Converting probability into calibrated risk percentage and human-readable audit reasons",
    content: `
      <div class="wf-explanation">
        <p>The system computes an exact risk score (0.00 to 1.00) and categorizes it into risk tiers (<code>LOW</code>, <code>MEDIUM</code>, <code>HIGH</code>, <code>CRITICAL</code>). Every flagged event generates explicit explanation statements for compliance analysts.</p>
      </div>
      <div class="wf-risk-breakdown mt-3">
        <div class="risk-tier-pill low">0.00 - 0.24 &bull; LOW RISK</div>
        <div class="risk-tier-pill medium">0.25 - 0.49 &bull; MEDIUM RISK</div>
        <div class="risk-tier-pill high">0.50 - 0.74 &bull; HIGH RISK</div>
        <div class="risk-tier-pill critical">0.75 - 1.00 &bull; CRITICAL RISK</div>
      </div>
    `
  },
  5: {
    title: "Stage 05: Policy Enforcement & Action Dispatch",
    subtitle: "Enforcing concrete operational actions to halt fraudulent money movement",
    content: `
      <div class="wf-explanation">
        <p>Rather than simply returning a raw score, the engine issues clear operational directives to the payment switch:</p>
        <div class="action-cards-grid mt-3">
          <div class="action-card card-allow">
            <h4>ALLOW</h4>
            <p>Frictionless approval. Transaction executed instantly.</p>
          </div>
          <div class="action-card card-challenge">
            <h4>CHALLENGE_2FA</h4>
            <p>Interim step-up security. Prompts SMS or Biometric OTP.</p>
          </div>
          <div class="action-card card-flag">
            <h4>FLAG_REVIEW</h4>
            <p>Queued for secondary inspection by fraud investigation team.</p>
          </div>
          <div class="action-card card-block">
            <h4>BLOCK</h4>
            <p>Immediate payment termination. Account frozen from capital loss.</p>
          </div>
        </div>
      </div>
    `
  },
  6: {
    title: "Stage 06: Immutable Audit Trail & Feedback Loop",
    subtitle: "Persisting transaction telemetry in SQLite for compliance, reporting, and model retraining",
    content: `
      <div class="wf-explanation">
        <p>Every transaction evaluated is recorded in SQLite with full forensic attributes, risk scores, rule triggers, and timestamps. Compliance officers can stream audit logs directly via <code>GET /api/transactions/export-csv</code>.</p>
      </div>
    `
  }
};

function showWorkflowDetail(step) {
  document.querySelectorAll(".workflow-step-card").forEach(c => c.classList.remove("active"));
  const clickedCard = document.querySelectorAll(".workflow-step-card")[step - 1];
  if (clickedCard) clickedCard.classList.add("active");

  const detail = workflowDetails[step];
  if (!detail) return;

  const titleEl = document.getElementById("wf-detail-title");
  const subEl = document.getElementById("wf-detail-subtitle");
  const contentEl = document.getElementById("wf-detail-content");

  if (titleEl) titleEl.innerText = detail.title;
  if (subEl) subEl.innerText = detail.subtitle;
  if (contentEl) contentEl.innerHTML = detail.content;
}

// ==============================================================================
// 12. CONNECT WITH API PLAYGROUND & SNIPPETS
// ==============================================================================

async function sendLiveApiTest() {
  const reqText = document.getElementById("api-request-json")?.value;
  const statusEl = document.getElementById("api-res-status");
  const latencyEl = document.getElementById("api-res-latency");
  const outputEl = document.getElementById("api-res-output");
  const btn = document.getElementById("btn-send-api");

  let payload;
  try {
    payload = JSON.parse(reqText);
  } catch (e) {
    showToast("Invalid JSON syntax in request payload.", "error");
    return;
  }

  if (btn) btn.disabled = true;
  if (outputEl) outputEl.innerText = "// Sending API request to POST /api/fraud-detection...";

  const startTime = performance.now();
  try {
    const res = await fetch("/api/fraud-detection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const elapsed = (performance.now() - startTime).toFixed(1);
    const data = await res.json();

    if (statusEl) {
      statusEl.innerText = `${res.status} ${res.statusText || "OK"}`;
      statusEl.style.color = res.ok ? "var(--accent-green)" : "var(--accent-red)";
    }
    if (latencyEl) {
      latencyEl.innerText = `${elapsed}ms`;
    }
    if (outputEl) {
      outputEl.innerText = JSON.stringify(data, null, 2);
    }

    fetchStats();
    loadTransactions();
    showToast(`API Response received in ${elapsed}ms: ${data.verdict} (${data.action})`, res.ok ? "success" : "error");
  } catch (err) {
    if (statusEl) {
      statusEl.innerText = "Error";
      statusEl.style.color = "var(--accent-red)";
    }
    if (outputEl) {
      outputEl.innerText = "// Network or Server Error:\n" + err.message;
    }
    showToast("API Call Error: " + err.message, "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

function resetApiJson(type) {
  const area = document.getElementById("api-request-json");
  if (!area) return;

  if (type === "fraud") {
    area.value = JSON.stringify({
      account_id: "ACC-904128",
      recipient_id: "REC-UNKNOWN-719",
      transaction_type: "TRANSFER",
      amount: 89500.0,
      old_balance_orig: 89500.0,
      new_balance_orig: 0.0,
      velocity_1h: 5,
      distance_from_home_km: 185.0,
      is_foreign: false,
      is_high_risk_merchant: true,
      device_trust_score: 0.18
    }, null, 2);
  } else {
    area.value = JSON.stringify({
      account_id: "ACC-100249",
      recipient_id: "MCH-STARBUCKS-88",
      transaction_type: "PAYMENT",
      amount: 6.50,
      old_balance_orig: 3420.50,
      new_balance_orig: 3414.00,
      velocity_1h: 1,
      distance_from_home_km: 2.3,
      is_foreign: false,
      is_high_risk_merchant: false,
      device_trust_score: 0.98
    }, null, 2);
  }
}

function copyApiResponse() {
  const outputEl = document.getElementById("api-res-output");
  if (!outputEl) return;
  const text = outputEl.innerText;
  navigator.clipboard.writeText(text).then(() => {
    showToast("API Response copied to clipboard!", "success");
  }).catch(() => {
    showToast("Failed to copy response.", "error");
  });
}

function switchCodeSnippet(lang) {
  document.querySelectorAll(".code-tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".snippet-box").forEach(box => box.classList.remove("active"));

  if (window.event && window.event.currentTarget) {
    window.event.currentTarget.classList.add("active");
  } else {
    const btn = Array.from(document.querySelectorAll(".code-tab-btn")).find(b => b.innerText.toLowerCase().includes(lang));
    if (btn) btn.classList.add("active");
  }

  const target = document.getElementById(`snippet-${lang}`);
  if (target) {
    target.classList.add("active");
  }
}

// ==============================================================================
// 13. UTILITY FUNCTIONS & TOAST NOTIFICATIONS
// ==============================================================================

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === "success" ? "✓" : type === "error" ? "⚠️" : "ℹ️"}</span>
    <span class="toast-msg">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add("show");
  }, 10);

  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
