// Automated test for the Cyton 3D explorer. Results go into <pre id="testout"> for --dump-dom.
const ERRS = [];
window.addEventListener("error", e => ERRS.push("window error: " + e.message));
const origErr = console.error; console.error = (...a) => { ERRS.push("console.error: " + a.join(" ")); origErr(...a); };
function report(lines, extra){
  const pre = document.createElement("pre"); pre.id = "testout";
  pre.textContent = "TESTREPORT_BEGIN\n" + lines.concat(ERRS.map(e => "ERR " + e)).join("\n") + "\nTESTREPORT_END";
  document.body.prepend(pre);
  if (extra) extra();
}
function clickAt(name){
  const v = wpos(name).project(camera), r = renderer.domElement.getBoundingClientRect();
  const x = r.left + (v.x + 1) / 2 * r.width, y = r.top + (1 - v.y) / 2 * r.height;
  const opts = {clientX:x, clientY:y, bubbles:true, pointerId:1, pointerType:"mouse", button:0, isPrimary:true};
  renderer.domElement.dispatchEvent(new PointerEvent("pointerdown", opts));
  renderer.domElement.dispatchEvent(new PointerEvent("pointerup", opts));
  return [Math.round(x), Math.round(y)];
}
function setView(pos){
  fly = null; controls.autoRotate = false;
  camera.position.copy(pos); controls.target.set(0, 0, 0); controls.update(); camera.updateMatrixWorld(true);
}
function run(){
  const out = [], fail = [];
  const c = window.cyton;
  if (!c){ report(["FAIL window.cyton missing"]); return; }
  // 1. every part selectable, has real info
  let n = 0; const generic = [];
  for (const name of Object.keys(c.byName)){
    try {
      c.selectPart(name, false); n++;
      const html = document.getElementById("partbox").innerHTML;
      if (!html.includes("<h3>")) fail.push("no title for " + name);
      if (c.infoFor(name).b === "misc") generic.push(name);
    } catch (e){ fail.push("select " + name + " threw " + e.message); }
  }
  out.push(`parts selectable: ${n}`); out.push(`parts with generic info: ${generic.join(",") || "none"}`);
  // 2. every link target exists
  let links = 0;
  for (const [name, inf] of Object.entries(c.INFO)) for (const [m] of inf.i.concat(inf.o)){ links++; if (!c.byName[m]) fail.push(`link target missing ${name} -> ${m}`); }
  out.push(`links checked: ${links}`);
  // 3. every tour, every step
  let steps = 0;
  for (const [k, t] of Object.entries(c.TOURS)){
    for (const path of t.paths) for (const p of path) if (!c.byName[p]) fail.push(`path part missing ${k}:${p}`);
    for (let i = 0; i < t.steps.length; i++){
      try {
        c.startTour(k, i); steps++;
        const st = c.state();
        if (st.activeTour !== k || st.stepIdx !== i || st.focusName !== t.steps[i][0]) fail.push(`tour state wrong ${k} ${i}`);
        if (!document.querySelector("#tourbox .tb-text").textContent.length) fail.push(`empty tour text ${k} ${i}`);
      } catch (e){ fail.push(`tour ${k} step ${i} threw ${e.message}`); }
    }
    const g = tourGroups[k];
    out.push(`tour ${k}: ${t.steps.length} steps, ${g ? g.edges.length : 0} flow lines, ${g ? g.edges.reduce((a, e) => a + e.dots.length, 0) : 0} particles`);
  }
  out.push(`tour steps run: ${steps}`);
  // 4. panel buttons
  c.startTour("signal", 0);
  document.querySelector("[data-nav=next]").click(); if (c.state().stepIdx !== 1) fail.push("Next button");
  document.querySelector("[data-nav=back]").click(); if (c.state().stepIdx !== 0) fail.push("Back button");
  document.querySelectorAll(".tb-dots .dot")[4].click(); if (c.state().stepIdx !== 4) fail.push("step dot");
  document.dispatchEvent(new KeyboardEvent("keydown", {key:"ArrowRight"})); if (c.state().stepIdx !== 5) fail.push("ArrowRight key");
  document.dispatchEvent(new KeyboardEvent("keydown", {key:"ArrowLeft"})); if (c.state().stepIdx !== 4) fail.push("ArrowLeft key");
  const chip = document.querySelector("#partbox .chip[data-go]"); const tgt = chip.dataset.go; chip.click();
  if (c.state().focusName !== tgt) fail.push("part link chip");
  const tchip = document.querySelector("#partbox .chip[data-tour]"); if (tchip){ tchip.click(); if (c.state().activeTour !== tchip.dataset.tour) fail.push("flow chip"); }
  document.querySelector(".tourbtn[data-tour=power]").click(); if (c.state().activeTour !== "power") fail.push("tour button start");
  document.querySelector(".tourbtn[data-tour=power]").click(); if (c.state().activeTour !== null) fail.push("tour button toggle off");
  c.startTour("bias", 5); document.querySelector("[data-nav=next]").click(); if (c.state().activeTour !== null) fail.push("Finish button");
  c.startTour("motion", 1); document.dispatchEvent(new KeyboardEvent("keydown", {key:"Escape"})); if (c.state().activeTour !== null) fail.push("Escape key");
  document.getElementById("allflows").click(); const vis = Object.values(tourGroups).filter(g => g.g.visible).length;
  if (vis !== Object.keys(c.TOURS).length) fail.push(`all flows shows ${vis}`); out.push(`"show every flow" visible groups: ${vis}`);
  document.getElementById("allflows").click();
  find.value = "U3"; find.dispatchEvent(new Event("change")); if (c.state().focusName !== "U3") fail.push("find dropdown");
  // 5. click on the 3D board itself (Cyton alone first)
  c.exitTour();
  const clicks = [];
  c.setDaisyMode("off");
  setView(new THREE.Vector3(0, 125, 0.01));
  for (const name of ["U6", "U7", "X1", "PL1", "U1", "R2", "SW1"]){ c.selectPart("HEAD", false); const xy = clickAt(name); const ok = c.state().focusName === name; clicks.push(`${name}@${xy}:${ok ? "ok" : "got " + c.state().focusName}`); if (!ok) fail.push("3D click top " + name); }
  setView(new THREE.Vector3(0, -125, 0.01));
  for (const name of ["BLE1", "U5", "U3", "VR1", "CONN1", "D3", "B1"]){ c.selectPart("HEAD", false); const xy = clickAt(name); const ok = c.state().focusName === name; clicks.push(`${name}@${xy}:${ok ? "ok" : "got " + c.state().focusName}`); if (!ok) fail.push("3D click bottom " + name); }
  out.push("3D clicks: " + clicks.join(" "));
  // 6. Daisy
  const st = () => c.state();
  c.setDaisyMode("lifted"); if (st().daisyMode !== "lifted" || !c.daisy.visible) fail.push("daisy lifted");
  c.selectPart("U6", false); if (!st().fadedD || st().fadedC) fail.push("fade daisy for U6");
  c.selectPart("D3", false); if (st().fadedD) fail.push("no fade for Cyton bottom part");
  c.selectPart("Daisy C14", false); if (!st().fadedC || st().fadedD) fail.push("fade cyton for Daisy C14");
  c.selectPart("Daisy U1", false); if (st().fadedC || st().fadedD) fail.push("no fade for Daisy U1");
  c.setDaisyMode("off"); if (st().focusName !== null || c.daisy.visible) fail.push("hide daisy clears Daisy focus");
  c.selectPart("Daisy R3", false); if (st().daisyMode !== "lifted") fail.push("selecting a Daisy part shows the Daisy");
  c.startTour("daisy", 0); c.setDaisyMode("off"); if (st().activeTour !== null) fail.push("hiding daisy ends a Daisy tour");
  for (const mode of ["lifted", "stacked"]){
    c.setDaisyMode(mode);
    let ok = true;
    for (const k of ["daisy", "daisybus", "daisypower", "daisybias", "signal", "bias"]){
      c.startTour(k, 0); const g = tourGroups[k];
      if (!g || !g.edges.length) { ok = false; fail.push(`no flow lines ${k} ${mode}`); continue; }
      for (const e of g.edges) for (let u = 0; u <= 1; u += 0.05){ const v = e.curve.getPointAt(u); if (!isFinite(v.x + v.y + v.z)) { ok = false; fail.push(`bad curve ${k} ${e.a}>${e.b}`); break; } }
    }
    const e = tourGroups.daisy.edges.find(x => x.a === "Daisy J1" && x.b === "J1"), A = e.curve.getPointAt(0), B = e.curve.getPointAt(1);
    if (Math.hypot(A.x - B.x, A.z - B.z) > 0.5) fail.push(`Daisy J1 -> J1 not straight down (${mode})`);
    out.push(`daisy ${mode}: flows ok=${ok}, Daisy J1 at y ${A.y.toFixed(1)} -> J1 at y ${B.y.toFixed(1)}`);
  }
  c.exitTour();
  c.setDaisyMode("lifted");
  document.getElementById("allflows").click(); const vis2 = Object.values(tourGroups).filter(g => g.g.visible).length;
  if (vis2 !== Object.keys(c.TOURS).length) fail.push(`all flows with daisy shows ${vis2}`); document.getElementById("allflows").click();
  c.setDaisyMode("off"); document.getElementById("allflows").click(); const vis3 = Object.values(tourGroups).filter(g => g.g.visible).length;
  if (vis3 !== Object.keys(c.TOURS).length - 4) fail.push(`all flows without daisy shows ${vis3}`); document.getElementById("allflows").click();
  out.push(`all flows: ${vis2} with Daisy, ${vis3} without`);
  c.setDaisyMode("lifted");
  const dclicks = [];
  setView(new THREE.Vector3(0, 125, 0.01));
  for (const name of ["Daisy U1", "Daisy PL1", "Daisy R2", "Daisy C2", "Daisy R5"]){ c.selectPart("HEAD", false); const xy = clickAt(name); const ok = st().focusName === name; dclicks.push(`${name}@${xy}:${ok ? "ok" : "got " + st().focusName}`); if (!ok) fail.push("3D click Daisy top " + name); }
  c.selectPart("HEAD", false); clickAt("U6"); if (st().focusName === "U6") fail.push("Daisy should block a click on U6 from above"); else dclicks.push("U6 under Daisy blocked:ok");
  c.selectPart("U6", false); { const xy = clickAt("U7"); const ok = st().focusName === "U7"; dclicks.push(`U7 through faded Daisy@${xy}:${ok ? "ok" : "got " + st().focusName}`); if (!ok) fail.push("click through faded Daisy"); }
  setView(new THREE.Vector3(0, -125, 0.01));
  for (const name of ["Daisy D3", "Daisy C12", "Daisy J1", "Daisy C16"]){ c.selectPart("Daisy C14", false); const xy = clickAt(name); const ok = st().focusName === name; dclicks.push(`${name}@${xy}:${ok ? "ok" : "got " + st().focusName}`); if (!ok) fail.push("3D click Daisy bottom " + name); }
  out.push("Daisy clicks: " + dclicks.join(" "));
  c.exitTour(); c.selectPart("HEAD", false);
  // 7. finish switch still works
  document.getElementById("finish").click(); document.getElementById("finish").click();
  out.push(fail.length ? "RESULT FAIL" : "RESULT PASS"); fail.forEach(f => out.push("FAIL " + f));
  // optional screenshot state from ?shot=tour,step
  const q = new URLSearchParams(location.search).get("shot");
  report(out, () => {
    document.getElementById("testout").style.display = q ? "none" : "block";
    if (q){
      const [k, i, all] = q.split(","); const md = new URLSearchParams(location.search).get("mode"); if (md) c.setDaisyMode(md);
      if (new URLSearchParams(location.search).get("copper")) document.getElementById("finish").click();
      if (all) document.getElementById("allflows").click();
      if (k === "cam"){ c.exitTour(); const P = new URLSearchParams(location.search); setView(new THREE.Vector3(+P.get("cx"), +P.get("cy"), +P.get("cz"))); controls.target.set(0, +P.get("ty") || 0, 0); controls.update(); }
      else if (k === "top"){ c.exitTour(); setView(new THREE.Vector3(0, 125, 0.01)); }
      else if (k === "none"){ c.exitTour(); setView(VIEWS.iso()); controls.target.set(0, c.state().daisyMode === "lifted" ? 12 : 0, 0); controls.update(); }
      else c.startTour(k, +i);
      const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0;
      for (let f = 0; f < 400 && fly; f++) loop();
      window.requestAnimationFrame = raf; requestAnimationFrame(loop);
    }
  });
}
window.addEventListener("load", () => setTimeout(run, 1200));
