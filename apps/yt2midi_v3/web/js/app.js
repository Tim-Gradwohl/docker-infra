const form = document.getElementById("form");
const urlEl = document.getElementById("url");
const deviceEl = document.getElementById("device");

const statusBox = document.getElementById("status");
const statusTitle = document.getElementById("statusTitle");
const statusBadge = document.getElementById("statusBadge");
const statusMsg = document.getElementById("statusMsg");
const progressEl = document.getElementById("progress");
const barEl = progressEl.querySelector(".bar");
const pctEl = document.getElementById("pct");
const submitBtn = document.getElementById("submitBtn");
const resultEl = document.getElementById("result");
const logsEl = document.getElementById("logs");
const logWrap = document.getElementById("logWrap");

let pollTimer = null;

function setProgress(pct, indeterminate=false){
  if (indeterminate){
    progressEl.classList.add("indeterminate");
    progressEl.setAttribute("aria-valuenow", "0");
    pctEl.textContent = "…";
    return;
  }
  progressEl.classList.remove("indeterminate");
  const p = Math.max(0, Math.min(100, pct|0));
  progressEl.setAttribute("aria-valuenow", String(p));
  barEl.style.width = `${p}%`;
  pctEl.textContent = `${p}%`;
}

function setStatus({title, badge, msg, kind}){
  statusTitle.textContent = title;
  statusBadge.textContent = badge;
  statusMsg.textContent = msg;

  statusBox.classList.remove("error","ok");
  if (kind === "error") statusBox.classList.add("error");
  if (kind === "ok") statusBox.classList.add("ok");
}

function stopPolling(){
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
}

async function poll(jobId){
  const res = await fetch(`/api/status/${jobId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`status ${res.status}`);
  return await res.json();
}

function renderResult(jobId, files){
  if (!files || files.length === 0) return;
  const links = files.map(f => {
    const safeName = encodeURIComponent(f);
    return `<li><a href="/api/download/${jobId}/${safeName}" download>${f}</a></li>`;
  }).join("");
  resultEl.innerHTML = `<div class="small" style="margin-bottom:6px;">Downloads</div><ul style="margin:0; padding-left:18px;">${links}</ul>`;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  stopPolling();
  resultEl.innerHTML = "";
  logsEl.textContent = "";
  logWrap.hidden = true;

  statusBox.hidden = false;
  submitBtn.disabled = true;

  setStatus({ title: "Working…", badge: "Starting", msg: "Submitting job to the server…" });
  setProgress(0, true);

  const payload = {
    url: urlEl.value.trim(),
    device: deviceEl.value
  };

  try{
    const res = await fetch("/api/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok){
      throw new Error(data?.detail || `process ${res.status}`);
    }

    const jobId = data.job_id;
    setStatus({ title: "Working…", badge: "Queued", msg: `Job created: ${jobId}` });

    // Poll status every 1s
    pollTimer = setInterval(async () => {
      try{
        const st = await poll(jobId);

        statusBadge.textContent = st.status.toUpperCase();
        statusMsg.textContent = st.message || st.stage || "Working…";

        if (st.indeterminate) setProgress(0, true);
        else setProgress(st.progress ?? 0, false);

        if (st.logs){
          logsEl.textContent = st.logs;
          logWrap.hidden = false;
        }

        if (st.status === "done"){
          stopPolling();
          setProgress(100, false);
          setStatus({ title: "Done ✅", badge: "DONE", msg: "Your files are ready.", kind: "ok" });
          renderResult(jobId, st.files || []);
          submitBtn.disabled = false;
        } else if (st.status === "error"){
          stopPolling();
          setProgress(st.progress ?? 0, false);
          setStatus({ title: "Failed ❌", badge: "ERROR", msg: st.message || "Something went wrong.", kind: "error" });
          submitBtn.disabled = false;
        }
      }catch(err){
        // Keep polling; transient errors happen during restarts
      }
    }, 1000);

  }catch(err){
    stopPolling();
    setProgress(0, false);
    setStatus({ title: "Error", badge: "ERROR", msg: String(err?.message || err), kind: "error" });
    submitBtn.disabled = false;
  }
});
