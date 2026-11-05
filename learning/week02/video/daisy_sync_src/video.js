// Drives the Cyton + Daisy explorer frame by frame and dumps JPEG frames + label positions into the DOM.
(function(){
const Q = new URLSearchParams(location.search);
const SC = +Q.get("scene"), DUR = +Q.get("dur"), F0 = +Q.get("f0"), F1 = +Q.get("f1"), FPS = 15;
let fakeT = 0;
const V = (x, y, z) => new THREE.Vector3(x, y, z);

Object.assign(TOURS, {
  vsig:{col:"#4fd1ff", paths:[["HEAD","Daisy PL1","Daisy D2","Daisy R2","Daisy C12","Daisy U1"]], steps:[["HEAD",""]]},
  vclock:{col:"#f0e04a", paths:[["U6","J1","Daisy J1","Daisy U1"]], steps:[["U6",""]]},
  vstart:{col:"#7aa2ff", paths:[["U7","U6"],["U7","J1","Daisy J1","Daisy U1"]], steps:[["U7",""]]},
  vdrdy:{col:"#ff8a5c", paths:[["U6","U7"]], steps:[["U6",""]]},
  vread:{col:"#4fd1ff", paths:[["Daisy U1","Daisy J1","J1","U7"]], steps:[["U7",""]]},
  vradio:{col:"#2ec4a0", paths:[["U7","BLE1","PC"]], steps:[["BLE1",""]]},
});

function camPart(n, k = 1){
  const info = byName[n], w = wpos(n), s = info.p.virtual ? info.side : info.up;
  const off = n === "HEAD" ? V(30, 22, 40) : n === "PC" ? V(30, -22, 40) : V(20, s * 52, 44);
  return {pos:w.clone().add(off.multiplyScalar(k)), tgt:w};
}
const camOver = a => ({pos:V(112 * Math.sin(a), 74, 112 * Math.cos(a)), tgt:V(0, 13, 0)});
const camSide = () => ({pos:V(62, 78, 100), tgt:V(-4, 12, 0)});
function camJ1(){ const a = wpos("J1"), b = wpos("Daisy J1"), m = a.clone().lerp(b, 0.5); return {pos:m.clone().add(V(-46, 22, 50)), tgt:m}; }
function camPair(){ const a = wpos("U6"), b = wpos("Daisy U1"), m = a.clone().lerp(b, 0.5); return {pos:m.clone().add(V(60, 62, 70)), tgt:m}; }

// shot: at (fraction of the scene), cam(t) -> {pos,tgt}, focus, keep (highlight without fading), flows, labels [[part, text]]
const SCENES = [
  [{at:0, cam:t => camOver(0.5 + t * 0.03), focus:null, flows:[], labels:[["U7","Cyton: channels 1–8"]], lift:true},
   {at:0.55, cam:t => camOver(0.5 + t * 0.03), focus:null, flows:[], labels:[["U7","Cyton: channels 1–8"],["Daisy U1","Daisy: channels 9–16"]]}],
  [{at:0, cam:camPair, focus:null, fadeD:0.35, keep:["U6","Daisy U1"], flows:[], labels:[["U6","Cyton ADS1299 · ch 1–8"],["Daisy U1","Daisy ADS1299 · ch 9–16"]]},
   {at:0.36, cam:() => camPart("U6", 0.9), focus:"U6", flows:[], labels:[["U6","Cyton ADS1299 · ch 1–8"]]},
   {at:0.62, cam:() => camPart("Daisy U1", 0.9), focus:"Daisy U1", flows:[], labels:[["Daisy U1","Daisy ADS1299 · ch 9–16"]]}],
  [{at:0, cam:() => camPart("HEAD"), focus:"HEAD", flows:["vsig"], labels:[["HEAD","8 more electrodes"]]},
   {at:0.12, cam:() => camPart("Daisy PL1"), focus:"Daisy PL1", flows:["vsig"], labels:[["Daisy PL1","Daisy header (on top of the Cyton's)"]]},
   {at:0.37, cam:() => camPart("Daisy D2"), focus:"Daisy D2", flows:["vsig"], labels:[["Daisy D2","TVS diode · underneath"]]},
   {at:0.53, cam:() => camPart("Daisy R2"), focus:"Daisy R2", flows:["vsig"], labels:[["Daisy R2","2.2 kΩ · on top"]]},
   {at:0.68, cam:() => camPart("Daisy C12"), focus:"Daisy C12", flows:["vsig"], labels:[["Daisy C12","1 nF · underneath"]]},
   {at:0.84, cam:() => camPart("Daisy U1"), focus:"Daisy U1", flows:["vsig"], labels:[["Daisy U1","Daisy ADS1299"]]}],
  [{at:0, cam:camJ1, focus:null, keep:["J1","Daisy J1"], flows:["daisybus"], labels:[["J1","Cyton J1 · 8 pins"],["Daisy J1","Daisy socket"]]}],
  [{at:0, cam:camSide, focus:null, fadeD:0.35, flows:["vclock"], labels:[["U6","Cyton ADS1299"],["Daisy U1","Daisy ADS1299"]]},
   {at:0.17, cam:() => camPart("Daisy U1", 0.9), focus:"Daisy U1", flows:["vclock"], labels:[["Daisy U1","CLKSEL tied to ground: no own clock"]]},
   {at:0.36, cam:() => camPart("U6", 0.9), focus:"U6", flows:["vclock"], labels:[["U6","2.048 MHz out on CLK"]]},
   {at:0.58, cam:camSide, focus:null, fadeD:0.35, keep:["U6","Daisy U1"], flows:["vclock"], labels:[["U6","counts the same ticks"],["Daisy U1","counts the same ticks"]]}],
  [{at:0, cam:() => camPart("U7", 0.9), focus:"U7", flows:["vstart"], labels:[["U7","PIC32: CS1 + CS2 low, then START"]]},
   {at:0.38, cam:camSide, focus:null, fadeD:0.35, keep:["U6","Daisy U1"], flows:["vstart"], labels:[["U6","START"],["Daisy U1","START"]]}],
  [{at:0, cam:() => camPart("U6", 0.9), focus:"U6", flows:["vdrdy"], labels:[["U6","DRDY rings"]]},
   {at:0.24, cam:camSide, focus:null, fadeD:0.35, keep:["Daisy U1"], flows:["vdrdy"], labels:[["Daisy U1","its DRDY: not connected"]]},
   {at:0.5, cam:camSide, focus:null, fadeD:0.35, keep:["U7"], flows:["vdrdy","vread"], labels:[["U7","CS1: 27 bytes, then CS2: 27 bytes"]]}],
  [{at:0, cam:() => camPart("U7", 0.9), focus:"U7", flows:["vradio"], labels:[["U7","averages each pair of samples"]]},
   {at:0.3, cam:() => camPart("BLE1"), focus:"BLE1", flows:["vradio"], labels:[["BLE1","odd: ch 1–8 · even: ch 9–16"]]},
   {at:0.68, cam:() => camPart("PC"), focus:"PC", flows:["vradio"], labels:[["PC","16 channels, 125 per second each"]]}],
  [{at:0, cam:t => camOver(0.2 + t * 0.04), focus:null, flows:["vclock","vstart","vread"], labels:[]},
   {at:0.62, cam:() => camPart("Daisy PL1", 1.1), focus:"Daisy PL1", flows:["vclock","vstart","vread"], labels:[["Daisy PL1","SRB: join both with a Y-splitter"]]}],
];

let applied = -1;
function applyShot(sh){
  for (const k of Object.keys(TOURS)){
    if (sh.flows.includes(k)) buildTour(k).g.visible = true; else if (tourGroups[k]) tourGroups[k].g.visible = false;
  }
  const L = fadeMats(); setFadeList(L.d, 1); setFadeList(L.c, 1); fadedD = fadedC = false;
  if (sh.focus){ selectPart(sh.focus, false); fly = null; }
  else { setSel(null); focusName = null; applyFade(null); }
  if (sh.keep){ lit = null; for (const n of sh.keep) byName[n].mats.forEach(m => m.emissive && m.emissive.setHex(0x8a7d10)); if (!sh.focus) focusName = sh.keep[0]; }
  if (sh.fadeD){ setFadeList(L.d, sh.fadeD); fadedD = true; }
}
function clearKeep(){ for (const info of Object.values(byName)) info.mats.forEach(m => m.emissive && m.emissive.setHex(0x000000)); }
const ease = u => u < 0 ? 0 : u > 1 ? 1 : u * u * (3 - 2 * u);

function run(){
  setDaisyMode("lifted"); setSpin(false); renderer.setClearColor(0x0d1311, 1); showLabels = false; labelLayer.hidden = true;
  const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0;
  performance.now = () => fakeT * 1000;
  const shots = SCENES[SC], out = [];
  const cv = renderer.domElement;
  const STILLS = Q.get("stills") ? shots.map(s => Math.round((s.at * DUR + 1.8) * FPS)) : null;
  const frames = STILLS || Array.from({length:F1 - F0}, (_, i) => F0 + i);
  for (const f of frames){
    const t = f / FPS; fakeT = t + SC * 100;
    let k = 0; for (let i = 0; i < shots.length; i++) if (t >= shots[i].at * DUR) k = i;
    if (k !== applied || STILLS){ clearKeep(); applyShot(shots[k]); applied = k; }
    if (shots[k].lift || SC === 0){ const u = ease((t - 0.2 * DUR) / (0.35 * DUR)); daisy.position.z = DZ_LIFT.stacked + (DZ_LIFT.lifted - DZ_LIFT.stacked) * u; scene.updateMatrixWorld(true); }
    const st = shots[k].at * DUR, cur = shots[k].cam(t), prev = k > 0 ? shots[k - 1].cam(st) : cur;
    const u = ease((t - st) / 1.4);
    camera.position.copy(prev.pos).lerp(cur.pos, u); controls.target.copy(prev.tgt).lerp(cur.tgt, u);
    camera.lookAt(controls.target); camera.updateMatrixWorld(true);
    fly = null; updateFlows(); renderer.render(scene, camera);
    const labels = [];
    for (const [n, text] of shots[k].labels){
      const info = byName[n], v = wpos(n), s = info.p.virtual ? 1 : info.up;
      if (!info.p.virtual) v.y += s * ((info.h || 1) / 2 + 1.2);
      v.project(camera); if (v.z < 1) labels.push([Math.round((v.x + 1) / 2 * cv.width), Math.round((1 - v.y) / 2 * cv.height), text]);
    }
    out.push({f, img:cv.toDataURL("image/jpeg", 0.86), labels});
  }
  const pre = document.createElement("pre"); pre.id = "vout"; pre.textContent = "VOUT_BEGIN" + JSON.stringify(out) + "VOUT_END"; document.body.prepend(pre);
  window.requestAnimationFrame = raf;
}
window.addEventListener("load", () => setTimeout(run, 1500));
})();
