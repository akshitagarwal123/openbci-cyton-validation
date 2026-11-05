// Renders course scenes from the Cyton + Daisy explorer, frame by frame, into the DOM (JPEG + label positions).
(function(){
const Q = new URLSearchParams(location.search);
const SC = +Q.get("scene"), F0 = +Q.get("f0"), F1 = +Q.get("f1"), FPS = 15;
const SCENE = window.COURSE[SC], DUR = window.DURS[SC].dur, LEAD = window.DURS[SC].lead;
let fakeT = 0;
const V = (x, y, z) => new THREE.Vector3(x, y, z);

Object.assign(TOURS, {
  vsig:{col:"#4fd1ff", paths:[["HEAD","Daisy PL1","Daisy D2","Daisy R2","Daisy C12","Daisy U1"]], steps:[["HEAD",""]]},
  vclock:{col:"#f0e04a", paths:[["U6","J1","Daisy J1","Daisy U1"]], steps:[["U6",""]]},
  vstart:{col:"#7aa2ff", paths:[["U7","U6"],["U7","J1","Daisy J1","Daisy U1"]], steps:[["U7",""]]},
  vdrdy:{col:"#ff8a5c", paths:[["U6","U7"]], steps:[["U6",""]]},
  vread1:{col:"#4fd1ff", paths:[["U7","U6"]], steps:[["U7",""]]},
  vread:{col:"#4fd1ff", paths:[["Daisy U1","Daisy J1","J1","U7"]], steps:[["U7",""]]},
  vradio:{col:"#2ec4a0", paths:[["U7","BLE1","PC"]], steps:[["BLE1",""]]},
});

function camPart(n, k = 1){
  const info = byName[n], w = wpos(n), s = info.p.virtual ? info.side : info.up;
  const off = n === "HEAD" ? V(30, 22, 40) : n === "PC" ? V(30, -22, 40) : V(20, s * 52, 44);
  return {pos:w.clone().add(off.multiplyScalar(k)), tgt:w};
}
const orbit = (r, y, a, ty) => ({pos:V(r * Math.sin(a), y, r * Math.cos(a)), tgt:V(0, ty, 0)});
function camFor(sh, t){
  switch (sh.cam){
    case "overC": return orbit(88, 56, 0.55 + t * 0.035, 0);
    case "over": return orbit(100, 68, 0.5 + t * 0.03, 13);
    case "all": return orbit(150, 112, 0.6 + t * 0.03, 14);
    case "top": return {pos:V(0, 118, 26), tgt:V(0, 0, 2)};
    case "bot": return {pos:V(0, -112, 28), tgt:V(0, 0, 2)};
    case "side": return daisyMode === "off" ? {pos:V(58, 64, 92), tgt:V(0, 0, 0)} : {pos:V(62, 78, 100), tgt:V(-4, 12, 0)};
    case "pair": { const a = wpos("U6"), b = wpos("Daisy U1"), m = a.clone().lerp(b, 0.5); return {pos:m.clone().add(V(60, 62, 70)), tgt:m}; }
    case "j1": { const a = wpos("J1"), b = wpos("Daisy J1"), m = a.clone().lerp(b, 0.5); return {pos:m.clone().add(V(-46, 22, 50)), tgt:m}; }
    case "part": return camPart(sh.focus);
  }
  return orbit(104, 66, 0.6, 0);
}
function clearKeep(){ for (const info of Object.values(byName)) info.mats.forEach(m => m.emissive && m.emissive.setHex(0x000000)); }
function applyShot(sh){
  const mode = sh.daisy === "lift" ? "lifted" : (sh.daisy || "off");
  if (mode !== daisyMode) setDaisyMode(mode);
  const wantReal = !sh.copper; if (wantReal !== real) setFinish(wantReal);
  clearKeep();
  for (const k of Object.keys(TOURS)){
    if ((sh.flows || []).includes(k)) buildTour(k).g.visible = true; else if (tourGroups[k]) tourGroups[k].g.visible = false;
  }
  const L = fadeMats(); setFadeList(L.d, 1); setFadeList(L.c, 1); fadedD = fadedC = false;
  if (sh.focus){ selectPart(sh.focus, false); fly = null; }
  else { setSel(null); focusName = null; }
  if (sh.keep){ lit = null; for (const n of sh.keep) byName[n].mats.forEach(m => m.emissive && m.emissive.setHex(0x8a7d10)); if (!sh.focus) focusName = sh.keep[0]; }
  if (sh.fadeD){ setFadeList(L.d, sh.fadeD); fadedD = true; }
}
const ease = u => u < 0 ? 0 : u > 1 ? 1 : u * u * (3 - 2 * u);

function run(){
  setSpin(false); renderer.setClearColor(0x0d1311, 1); showLabels = false; labelLayer.hidden = true;
  window.requestAnimationFrame = () => 0;
  performance.now = () => fakeT * 1000;
  const shots = SCENE.shots, out = [], cv = renderer.domElement;
  const STILLS = Q.get("stills") ? shots.map(s => Math.round((s.at * (DUR - LEAD) + LEAD + 1.8) * FPS)) : null;
  const frames = STILLS || Array.from({length:F1 - F0}, (_, i) => F0 + i);
  let applied = -1;
  for (const f of frames){
    const t = f / FPS, ts = Math.max(0, t - LEAD); fakeT = t + SC * 100;
    let k = 0; for (let i = 0; i < shots.length; i++) if (ts >= shots[i].at * (DUR - LEAD)) k = i;
    if (k !== applied || STILLS){ applyShot(shots[k]); applied = k; }
    if (shots[k].daisy === "lift"){ const u = ease((ts - 0.15 * DUR) / (0.35 * DUR)); daisy.position.z = DZ_LIFT.stacked + (DZ_LIFT.lifted - DZ_LIFT.stacked) * u; scene.updateMatrixWorld(true); }
    const st = shots[k].at * (DUR - LEAD), cur = camFor(shots[k], ts), prev = k > 0 ? camFor(shots[k - 1], st) : cur;
    const u = ease((ts - st) / 1.4);
    camera.position.copy(prev.pos).lerp(cur.pos, u); controls.target.copy(prev.tgt).lerp(cur.tgt, u);
    camera.lookAt(controls.target); camera.updateMatrixWorld(true);
    fly = null; updateFlows(); renderer.render(scene, camera);
    const labels = [];
    for (const [n, text] of shots[k].labels || []){
      const info = byName[n]; if (!info) continue;
      if (info.daisy && daisyMode === "off") continue;
      const v = wpos(n), s = info.p.virtual ? 1 : info.up;
      if (!info.p.virtual) v.y += s * ((info.h || 1) / 2 + 1.2);
      v.project(camera); if (v.z < 1) labels.push([Math.round((v.x + 1) / 2 * cv.width), Math.round((1 - v.y) / 2 * cv.height), text]);
    }
    out.push({f, img:cv.toDataURL("image/jpeg", 0.86), labels, shot:k});
  }
  const pre = document.createElement("pre"); pre.id = "vout"; pre.textContent = "VOUT_BEGIN" + JSON.stringify(out) + "VOUT_END"; document.body.prepend(pre);
}
window.addEventListener("load", () => setTimeout(run, 1500));
})();
