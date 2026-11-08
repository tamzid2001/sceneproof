/* SceneProof editor. The UI may *propose* counterfactuals (drag/keyboard/form);
   only the deterministic server verifies them. Pending previews are always
   labelled as unverified. Coordinates: x∈[0,1] left→right, y∈[0,1] bottom→top —
   identical to the Python engine (sceneproof.models). */
const $ = id => document.getElementById(id);
const EPS = 0.011; // mirrors sceneproof.constraints.EPS — guides only, truth comes from the API
const COLORS = {crate:"#6d7cff", robot:"#3ddc97", human:"#ffb84d", barrel:"#c792ff", cone:"#ff8fa3", vehicle:"#4dc9ff", shelf:"#5b6b9f"};
let scene = null, lastReport = null, selected = null, baselineViol = [];

function scale(c) { const r = c.getBoundingClientRect(); return [r.width / c.width, r.height / c.height]; }

function drawObjects(c, objects, violations = [], ghost = null) {
  const x = c.getContext("2d"), W = c.width, H = c.height, G = 40; // ground line inset
  x.clearRect(0, 0, W, H);
  const toPx = o => [o.x * W, H - G - (o.y + o.h) * H, o.w * W, o.h * H];
  if ($("overlays") && $("overlays").checked) {
    // bound guide
    x.strokeStyle = "#2b355e"; x.setLineDash([2, 4]);
    x.strokeRect(0.5, 0.5, W - 1, H - G - 1);
    // support guides: vertical link across each real support contact
    x.strokeStyle = "#3a4680";
    for (const o of objects) {
      for (const p of objects) {
        if (p.id === o.id) continue;
        const contact = Math.abs(o.y - p.top) <= EPS;
        const under = Math.min(o.x + o.w, p.x + p.w) - Math.max(o.x, p.x) > 0.05;
        if (contact && under) {
          const lx = ((Math.max(o.x, p.x) + Math.min(o.x + o.w, p.x + p.w)) / 2) * W;
          x.beginPath();
          x.moveTo(lx, H - G - o.y * H);
          x.lineTo(lx, H - G - p.top * H);
          x.stroke();
        }
      }
    }
    x.setLineDash([]);
  }
  // ground
  x.strokeStyle = "#232c4d"; x.beginPath(); x.moveTo(0, H - G); x.lineTo(W, H - G); x.stroke();
  const bad = new Set((violations || []).flatMap(v => v.objects));
  for (const o of objects) {
    const [px, py, pw, ph] = toPx(o);
    x.fillStyle = (COLORS[o.kind] || "#888") + "33";
    x.fillRect(px, py, pw, ph);
    x.strokeStyle = bad.has(o.id) ? "#ff5d7a" : (o.id === selected ? "#ffe27a" : (COLORS[o.kind] || "#888"));
    x.lineWidth = bad.has(o.id) ? 3 : (o.id === selected ? 2.5 : 1.5);
    x.setLineDash([6, 4]); x.strokeRect(px, py, pw, ph); x.setLineDash([]);
    x.fillStyle = "#eef1ff"; x.font = "13px system-ui"; x.fillText(`${o.id} · ${o.kind}`, px + 6, py + 18);
  }
  if (ghost) {
    const [px, py, pw, ph] = toPx(ghost);
    x.strokeStyle = "#7ee0ff"; x.lineWidth = 2; x.setLineDash([3, 3]); x.strokeRect(px, py, pw, ph); x.setLineDash([]);
    x.fillStyle = "#7ee0ff88"; x.fillText("pending · unverified", px + 6, py + ph - 8);
  }
}

function blank(c) {
  const x = c.getContext("2d"), W = c.width, H = c.height, G = 40;
  x.clearRect(0, 0, W, H);
  x.strokeStyle = "#232c4d"; x.beginPath(); x.moveTo(0, H - G); x.lineTo(W, H - G); x.stroke();
}

function pendingMove() {
  const a = $("action").value, oid = $("object").value;
  if (!oid) return null;
  const o = scene && scene.objects.find(x => x.id === oid);
  if (!o) return null;
  if (a === "move")
    return {id: oid, kind: o.kind, x: Math.max(0, Math.min(1 - o.w, o.x + (+$("dx").value || 0))),
            y: Math.max(0, o.y + (+$("dy").value || 0)), w: o.w, h: o.h};
  if (a === "resize")
    return {id: oid, kind: o.kind, x: o.x, y: o.y,
            w: Math.max(0.01, +$("w").value || o.w), h: Math.max(0.01, +$("h").value || o.h)};
  if (a === "remove") return null; // refreshStage draws the scene without the object instead
  if (a === "add") return {id: $("newid").value || "new", kind: $("kind").value,
                           x: Math.max(0, Math.min(1, 0.5 + (+$("dx").value || 0))),
                           y: Math.max(0, +$("dy").value || 0), w: Math.max(0.01, +$("w").value || 0.1),
                           h: Math.max(0.01, +$("h").value || 0.1)};
  return null;
}

function refreshStage() {
  if (!scene) return;
  if (actionActive() && $("action").value === "remove") {
    drawObjects($("stage"), scene.objects.filter(o => o.id !== $("object").value), baselineViol, null);
    return;
  }
  drawObjects($("stage"), scene.objects, baselineViol, actionActive() ? pendingMove() : null);
}

function actionActive() { return !!$("action").value; }

function onControlsChanged() {
  const a = $("action").value;
  const sensitive = a === "remove" || (a === "add" && ["human", "vehicle"].includes($("kind").value));
  $("approval").classList.toggle("hidden", !sensitive);
  $("addfields").classList.toggle("hidden", a !== "add");
  $("sizefields").classList.toggle("hidden", a !== "resize" && a !== "add");
  refreshStage();
  ghostBaseline();
}

/* right pane of the compare card = ghost preview until a run happens */
function ghostBaseline() {
  if (!scene) return;
  const after = $("after");
  const a = $("action").value;
  if (!a) {
    blank(after);
    $("comparenote").textContent = "Choose an intervention to preview it (unverified), then Run to verify both sides.";
    return;
  }
  if (a === "remove") {
    drawObjects(after, scene.objects.filter(o => o.id !== $("object").value), [], null);
  } else {
    const g = pendingMove();
    if (!g) { blank(after); return; }
    const exists = scene.objects.some(o => o.id === g.id);
    // add: mark the pending object as locked (sensitive kinds still need approval)
    drawObjects(after, exists ? scene.objects.map(o => o.id === g.id ? g : o) : scene.objects.concat([{...g, id: g.id + " (pending)"}]), [], null);
  }
  $("comparenote").innerHTML = "Right side is a <b>pending</b> counterfactual preview — <b>not verified</b>. Press Run.";
}

async function load(seed = 7) {
  const r = await (await fetch(`/api/scene?seed=${seed}`)).json();
  if (r.error) { $("status").textContent = r.error; return; }
  scene = r.scene;
  // test hook: geometry bridge for browser E2E (read-only)
  window.__scene_objects__ = () => Object.fromEntries(scene.objects.map(o => [o.id, {...o}]));
  $("empty").classList.add("hidden");
  $("fp").textContent = "· fingerprint " + r.fingerprint;
  $("object").innerHTML = scene.objects.map(o => `<option>${o.id}</option>`).join("");
  selected = scene.objects.length ? scene.objects[0].id : null; baselineViol = [];
  drawObjects($("stage"), scene.objects);
  blank($("after")); blank($("before"));
  $("basefps").textContent = $("afterfp").textContent = $("fp").textContent;
  document.querySelectorAll(".stepper li").forEach((li, i) => li.classList.toggle("on", i === 1));
}

/* ---- draggable entities (pointer) ---- */
const stage = $("stage");
function hit(csx, csy) {
  if (!scene) return null;
  const W = stage.width, H = stage.height, G = 40;
  for (let i = scene.objects.length - 1; i >= 0; i--) {
    const o = scene.objects[i], px = o.x * W, py = H - G - (o.y + o.h) * H, pw = o.w * W, ph = o.h * H;
    if (csx >= px && csx <= px + pw && csy >= py && csy <= py + ph) return o;
  }
  return null;
}
let dragging = null, dragStart = null;
stage.addEventListener("pointerdown", e => {
  if (!scene) return;
  const [sx, sy] = scale(stage);
  const o = hit((e.clientX - stage.getBoundingClientRect().left) / sx,
                (e.clientY - stage.getBoundingClientRect().top) / sy);
  if (!o) return;
  selected = o.id; dragging = o; dragStart = [o.x, o.y];
  if ($("action").value === "" || $("action").value === "add") $("action").value = "move";
  $("object").value = o.id;
  stage.setPointerCapture(e.pointerId);
  stage.focus(); refreshStage();
});
stage.addEventListener("pointermove", e => {
  if (!dragging) return;
  const [sx, sy] = scale(stage), r = stage.getBoundingClientRect();
  const gx = (e.clientX - r.left) / sx, gy = (e.clientY - r.top) / sy;
  const H = stage.height, G = 40;
  const y = Math.max(0, (H - G - gy) / H - dragging.h / 2);
  const nx = Math.max(-1, Math.min(1, gx / stage.width - dragging.w / 2 - dragging.x));
  const nyy = Math.max(-1, Math.min(1, y - dragging.y));
  $("dx").value = (+nx.toFixed(2)); $("dy").value = (+nyy.toFixed(2));
  if ($("action").value !== "move") $("action").value = "move";
  onControlsChanged();
});
stage.addEventListener("pointerup", () => { dragging = null; });

/* ---- keyboard nudging on the canvas (a11y path) ---- */
stage.addEventListener("keydown", e => {
  if (!scene || !selected) return;
  const step = 0.02;
  const map = {ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowDown: [0, -step], ArrowUp: [0, step]};
  if (!map[e.key]) return;
  e.preventDefault();
  $("object").value = selected; $("action").value = "move";
  $("dx").value = ((+$("dx").value || 0) + map[e.key][0]).toFixed(2);
  $("dy").value = ((+$("dy").value || 0) + map[e.key][1]).toFixed(2);
  onControlsChanged();
});

$("start").onclick = () => load(7);
$("action").onchange = onControlsChanged;
$("kind").onchange = onControlsChanged;
$("object").addEventListener("change", () => { selected = $("object").value; refreshStage(); ghostBaseline(); });
$("overlays").onchange = refreshStage;
for (const id of ["dx", "dy", "w", "h", "newid"]) $(id).addEventListener("input", onControlsChanged);

/* ---- run the deterministic verifier ---- */
$("run").onclick = async () => {
  if (!scene) await load(7);
  $("status").textContent = "Verifying deterministically…";
  const body = {seed: scene.seed, action: $("action").value || null,
                object: ($("action").value === "add" ? ($("newid").value || "") : $("object").value),
                dx: +$("dx").value, dy: +$("dy").value, kind: $("kind").value,
                approver: $("approver").value, approved: $("approved").checked};
  if ($("action").value === "" ) delete body.object;
  if (["resize", "add"].includes($("action").value)) { body.w = +$("w").value; body.h = +$("h").value; }
  if (["move", "remove"].includes($("action").value)) { delete body.kind; }
  const res = await fetch("/api/run", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  const r = await res.json();
  if (r.status === "APPROVAL_REQUIRED") {
    $("approval").classList.remove("hidden");
    $("status").textContent = "Approval required — a named human must approve above, then verify again.";
    return;
  }
  if (r.error) { $("status").textContent = "Rejected: " + r.error; return; }
  lastReport = r.report;
  const v = r.report.intervened || r.report.baseline;
  $("score").textContent = Math.round(v.score);
  $("arc").style.strokeDashoffset = 327 - 327 * v.score / 100;
  $("arc").style.stroke = v.feasible ? "#3ddc97" : "#ff5d7a";
  $("verdict").textContent = (v.feasible ? "FEASIBLE" : "INFEASIBLE") + (r.report.effect != null ? ` · counterfactual effect ${r.report.effect >= 0 ? "+" : ""}${r.report.effect.toFixed(1)} pts` : "");
  $("violations").innerHTML = v.violations.length ? v.violations.map(x => `<li><b>[${x.rule}]</b> ${x.detail}</li>`).join("") : '<li class="dim">No violations. This world holds together.</li>';
  $("explain").textContent = r.report.explanation; $("src").textContent = r.report.explanation_source;
  $("head").textContent = r.report.ledger_head.slice(0, 16) + "…"; $("chain").textContent = r.chain_valid ? "valid ✓" : "BROKEN";
  baselineViol = r.report.baseline.violations;
  if (scene) drawObjects($("stage"), scene.objects, baselineViol, actionActive() ? pendingMove() : null);
  if (r.report.baseline) drawObjects($("before"), r.scene.objects, r.report.baseline.violations);
  if (r.after_scene) drawObjects($("after"), r.after_scene.objects, v.violations), $("afterfp").textContent = "";
  document.querySelectorAll(".stepper li").forEach((li, i) => li.classList.toggle("on", i === 3));
  $("status").textContent = v.feasible ? "Verified: world holds together." : "Verified: infeasible world (see violations).";
};

/* ---- shareable outcome: seed + counterfactual encoded in the URL ---- */
function shareUrl() {
  const p = new URLSearchParams();
  p.set("seed", scene ? scene.seed : 7);
  if (actionActive()) {
    p.set("act", $("action").value);
    p.set("obj", $("action").value === "add" ? ($("newid").value || "new") : $("object").value);
    p.set("dx", $("dx").value); p.set("dy", $("dy").value);
    if (["resize", "add"].includes($("action").value)) { p.set("w", $("w").value); p.set("h", $("h").value); p.set("kind", $("kind").value); }
  }
  return location.origin + location.pathname + "?" + p.toString();
}
$("share").onclick = async () => {
  try { await navigator.clipboard.writeText(shareUrl()); $("status").textContent = "Share link copied — it replays this exact verification."; }
  catch { $("status").textContent = "Copy failed — " + shareUrl(); }
};

/* ---- auto-replay a shared link, honestly (runs the same POST) ---- */
(function replayFromUrl() {
  const q = new URLSearchParams(location.search);
  if (!q.get("act") || [...q.keys()].length === 0) return;
  window.addEventListener("DOMContentLoaded", async () => {
    await load(parseInt(q.get("seed") || "7", 10) || 7);
    const act = q.get("act");
    if (["move", "remove", "resize", "add"].includes(act)) {
      $("action").value = act;
      if (act === "add") { $("newid").value = q.get("obj") || "new"; if (q.get("kind")) $("kind").value = q.get("kind"); }
      else { if (q.get("obj")) $("object").value = q.get("obj"); }
      $("dx").value = q.get("dx") || 0; $("dy").value = q.get("dy") || 0;
      $("w").value = q.get("w") || 0.1; $("h").value = q.get("h") || 0.1;
      onControlsChanged();
      $("run").click();
      $("status").textContent = "Shared link replayed — this ran the same deterministic verification.";
    }
  });
})();

$("export").onclick = () => {
  const b = new Blob([JSON.stringify(lastReport || {note: "run a verification first"}, null, 2)], {type: "application/json"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = "sceneproof-report.json"; a.click();
};
