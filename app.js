const csvUrl = new URL("history.csv", window.location.href);
const currency = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });
const dateFormat = new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "long", year: "numeric" });
const dateTimeFormat = new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "Asia/Jakarta" });

function parseCSV(text) {
  const rows = [];
  let row = [], value = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (char === '"' && quoted && text[i + 1] === '"') { value += '"'; i++; }
    else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) { row.push(value); value = ""; }
    else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[i + 1] === "\n") i++;
      row.push(value); if (row.some((cell) => cell !== "")) rows.push(row); row = []; value = "";
    } else value += char;
  }
  if (value || row.length) { row.push(value); rows.push(row); }
  if (!rows.length) return [];
  const headers = rows.shift().map((item) => item.trim());
  return rows.map((cells) => Object.fromEntries(headers.map((key, index) => [key, (cells[index] || "").trim()])));
}

function fmtDate(value) {
  if (!value) return "Tidak tersedia";
  const date = new Date(`${value.slice(0, 10)}T12:00:00+07:00`);
  return Number.isNaN(date.getTime()) ? value : dateFormat.format(date);
}

function setFreshness(priceDate) {
  const badge = document.querySelector("#freshness");
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(new Date());
  const isCurrent = priceDate === today;
  badge.classList.toggle("stale", !isCurrent);
  badge.querySelector("span").textContent = isCurrent ? "DATA HARI INI" : "CEK TANGGAL DATA";
  document.querySelector("#stale-note").hidden = isCurrent;
}

function drawChart(records) {
  const canvas = document.querySelector("#chart");
  const empty = document.querySelector("#empty-state");
  const ctx = canvas.getContext("2d");
  const points = records.map((record) => ({ date: record.price_date, value: Number(record.buyback_rp_per_gram) })).filter((item) => item.date && Number.isFinite(item.value));
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, width * ratio); canvas.height = Math.max(1, height * ratio); ctx.scale(ratio, ratio);
  if (!points.length) { empty.classList.add("visible"); return; }
  empty.classList.remove("visible");
  const values = points.map((item) => item.value);
  const min = Math.min(...values), max = Math.max(...values), span = max - min || Math.max(max * 0.03, 1);
  const pad = { top: 16, right: 8, bottom: 16, left: 8 };
  const chartW = width - pad.left - pad.right, chartH = height - pad.top - pad.bottom;
  const y = (value) => pad.top + chartH - ((value - (min - span * 0.15)) / (span * 1.3)) * chartH;
  const x = (index) => pad.left + (points.length === 1 ? chartW / 2 : index / (points.length - 1) * chartW);
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(220,224,208,.08)"; ctx.lineWidth = 1;
  for (let line = 0; line < 4; line++) { const gy = pad.top + line * chartH / 3; ctx.beginPath(); ctx.moveTo(pad.left, gy); ctx.lineTo(width - pad.right, gy); ctx.stroke(); }
  const gradient = ctx.createLinearGradient(0, pad.top, 0, height);
  gradient.addColorStop(0, "rgba(217,183,108,.24)"); gradient.addColorStop(1, "rgba(217,183,108,0)");
  ctx.beginPath(); points.forEach((point, index) => index ? ctx.lineTo(x(index), y(point.value)) : ctx.moveTo(x(index), y(point.value)));
  ctx.lineTo(x(points.length - 1), height - pad.bottom); ctx.lineTo(x(0), height - pad.bottom); ctx.closePath(); ctx.fillStyle = gradient; ctx.fill();
  ctx.beginPath(); points.forEach((point, index) => index ? ctx.lineTo(x(index), y(point.value)) : ctx.moveTo(x(index), y(point.value)));
  ctx.strokeStyle = "#d9b76c"; ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.lineCap = "round"; ctx.stroke();
  const last = points.at(-1); ctx.beginPath(); ctx.arc(x(points.length - 1), y(last.value), 4, 0, Math.PI * 2); ctx.fillStyle = "#f0d48f"; ctx.fill();
  document.querySelector("#axis-start").textContent = fmtDate(points[0].date);
  document.querySelector("#axis-end").textContent = fmtDate(last.date);
  const first = points[0].value;
  const delta = last.value - first;
  document.querySelector("#change-label").textContent = points.length < 2 ? "1 catatan" : `${delta >= 0 ? "+" : "−"}${currency.format(Math.abs(delta))} sejak awal`;
}

async function loadPrices() {
  try {
    const response = await fetch(`${csvUrl}?v=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Riwayat belum bisa dimuat");
    const records = parseCSV(await response.text()).filter((row) => Number(row.buyback_rp_per_gram) > 0);
    records.sort((a, b) => `${a.fetched_at_wib}`.localeCompare(`${b.fetched_at_wib}`));
    const latest = records.at(-1);
    if (!latest) { document.querySelector("#freshness span").textContent = "MENUNGGU DATA"; drawChart([]); return; }
    document.querySelector("#price").textContent = currency.format(Number(latest.buyback_rp_per_gram));
    document.querySelector("#price-date").textContent = fmtDate(latest.price_date);
    const fetched = latest.fetched_at_wib ? new Date(`${latest.fetched_at_wib.replace(" ", "T")}+07:00`) : null;
    document.querySelector("#fetched-at").textContent = fetched && !Number.isNaN(fetched.getTime()) ? dateTimeFormat.format(fetched) + " WIB" : "Tidak tersedia";
    document.querySelector("#source").textContent = latest.source || "Tidak tersedia";
    setFreshness(latest.price_date);
    drawChart(records);
  } catch (error) {
    document.querySelector("#freshness").classList.add("stale");
    document.querySelector("#freshness span").textContent = "GAGAL MEMUAT";
    document.querySelector("#price-date").textContent = "Coba muat ulang halaman";
    drawChart([]);
  }
}

loadPrices();
window.addEventListener("resize", () => loadPrices());
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) navigator.serviceWorker.register("./sw.js").catch(() => {});
