/* Pauli page (Atlas v2).  Wave functions, densities, conditional densities and
   holes, J/K integrals and the 2x2 CI of the Coulomb hole come from
   quas_atlas.core.pauli (pauli.map, pauli.cond, pauli.orbs, pauli.energy,
   pauli.cimap, pauli.ci); this script draws and animates. */
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const NS='http://www.w3.org/2000/svg';
function el(p,t,a){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);p.appendChild(e);return e}
const fmt=(x,d=2)=>(Math.abs(x)<5e-4?'0':x.toFixed(d)).replace('-','−');
const SUBN=n=>String(n).split('').map(c=>'₀₁₂₃₄₅₆₇₈₉'[+c]).join('');
const f64=s=>new Float64Array(Uint8Array.from(atob(s),c=>c.charCodeAt(0)).buffer);
const MODES=[
 {id:'H',name:'Hartree product'},
 {id:'T',name:'Triplet, S = 1'},
 {id:'S',name:'Singlet, S = 0'},
 {id:'D',name:'Single determinant ↑↓'},
 {id:'B',name:'Bosons (for comparison)'}];
let S={mode:'T',ms:1,a:1,b:2,view:'P',x1:0.3};
try{const s=JSON.parse(localStorage.getItem('pauli-state')||'null');if(s)Object.assign(S,s)}catch(e){}
function pauliZero(){return S.mode==='T'&&S.a===S.b}
const NG=301,XS=Array.from({length:NG},(_,i)=>i/(NG-1));
function condLab(){const ar=S.ms>0?'↑':'↓';if(S.mode==='H')return ['density of all ↑ electrons, ρ↑(x₂)','hole = c − ρ↑'];if(S.mode==='T')return S.ms?['density of all electrons '+ar+', ρ'+ar+'(x₂)','exchange hole = c − ρ'+ar]:['density of the second electron without permutations','difference'];if(S.mode==='D')return ['density of ↓ electrons, ρ↓(x₂)','difference c − ρ↓'];if(S.mode==='B')return ['density of all particles, ρ(x₂)','difference c − ρ'];return ['density of ↓ electrons, ρ↓(x₂)','difference c − ρ↓']}
const liveMap=QC.live('pauli.map'),liveCond=QC.live('pauli.cond'),liveOrbs=QC.live('pauli.orbs'),liveE=QC.live('pauli.energy'),liveCM=QC.live('pauli.cimap'),liveCI=QC.live('pauli.ci');
/* ===== отрисовка ===== */
const M0=34,MS=356;
function mix(c1,c2,t){const p=c=>c.startsWith('#')?[1,3,5].map(i=>parseInt(c.slice(i,i+2),16)):c.match(/\d+/g).slice(0,3).map(Number);const A=p(c1),B=p(c2);return A.map((x,i)=>Math.round(x+(B[i]-x)*t))}
function heat(t){const s=[tok('--heat0'),tok('--heat1'),tok('--heat2'),tok('--heat3')];t=Math.max(0,Math.min(1,t))*3;const k=Math.min(2,Math.floor(t));return mix(s[k],s[k+1],t-k)}
async function drawMap(){let Mp;try{Mp=await liveMap({mode:S.mode,a:S.a,b:S.b,view:S.view})}catch(e){return}const sv=document.getElementById('map');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');
  const R=120;const cv=document.createElement('canvas');cv.width=R;cv.height=R;const cx=cv.getContext('2d');const img=cx.createImageData(R,R);
  const P=S.view==='P';const vals=f64(Mp.f64),mx=Mp.mx;
  const pc=mix(tok('--panel'),tok('--panel'),0),pos=mix(tok('--pos'),tok('--pos'),0),neg=mix(tok('--neg'),tok('--neg'),0);
  for(let k=0;k<R*R;k++){const v=mx>1e-12?vals[k]/mx:0;let c;if(P)c=heat(Math.pow(v,0.8));else{const t=Math.min(1,Math.abs(v));const base=v>=0?pos:neg;c=pc.map((x,i)=>Math.round(x+(base[i]-x)*t))}
    img.data[4*k]=c[0];img.data[4*k+1]=c[1];img.data[4*k+2]=c[2];img.data[4*k+3]=255}
  cx.putImageData(img,0,0);
  if(pauliZero()){el(sv,'rect',{x:M0,y:6,width:MS,height:MS,fill:tok('--panel'),stroke:tok('--line')});const t=el(sv,'text',{x:M0+MS/2,y:6+MS/2-8,'text-anchor':'middle','font-size':22,'font-family':'PT Serif, serif',fill:ink});t.textContent='Ψ ≡ 0';
    const t2=el(sv,'text',{x:M0+MS/2,y:6+MS/2+18,'text-anchor':'middle','font-size':13,fill:mut,'font-family':'Golos Text, sans-serif'});t2.textContent='no such state exists'}
  else{const g=el(sv,'g',{});if(S.flipT>0){const cx0=M0+MS/2,cy0=6+MS/2,sc=Math.cos(Math.PI*S.flipT);g.setAttribute('transform',`translate(${cx0} ${cy0}) rotate(-45) scale(1 ${sc}) rotate(45) translate(${-cx0} ${-cy0})`)}
    el(g,'image',{href:cv.toDataURL(),x:M0,y:6,width:MS,height:MS,preserveAspectRatio:'none',style:'image-rendering:auto'})}
  el(sv,'rect',{x:M0,y:6,width:MS,height:MS,fill:'none',stroke:tok('--line')});
  if(!pauliZero())el(sv,'line',{x1:M0,y1:6+MS,x2:M0+MS,y2:6,stroke:ink,'stroke-width':1.2,'stroke-dasharray':'5 4',opacity:.7});
  const dl=el(sv,'text',{x:M0+MS*0.74,y:6+MS*0.2,'font-size':12,fill:ink,'font-family':'Golos Text, sans-serif',transform:`rotate(-45 ${M0+MS*0.74} ${6+MS*0.2})`,stroke:tok('--panel'),'stroke-width':3,'paint-order':'stroke'});dl.textContent='x₁ = x₂';
  const X=M0+S.x1*MS;if(!pauliZero())el(sv,'line',{x1:X,y1:6,x2:X,y2:6+MS,stroke:acc,'stroke-width':2});
  if(!pauliZero())el(sv,'circle',{cx:X,cy:6+MS-S.x1*MS,r:5,fill:'none',stroke:acc,'stroke-width':2});
  [0,0.5,1].forEach(v=>{el(sv,'text',{x:M0+v*MS,y:6+MS+16,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(v);
    el(sv,'text',{x:M0-6,y:6+MS-v*MS+4,'text-anchor':'end','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(v)});
  el(sv,'text',{x:M0+MS-4,y:6+MS+30,'text-anchor':'end','font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₁';
  el(sv,'text',{x:6,y:20,'font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₂';
  document.getElementById('mapTitle').textContent=S.view==='P'?(S.mode==='D'?'Density |Ψ|² summed over spins':'Probability density |Ψ(x₁, x₂)|²'):(S.mode==='D'?'Ψ: the α(1)β(2) component (sign: orange +, teal −)':'Ψ(x₁, x₂) — spatial part (orange +, teal −)');
  document.getElementById('mapLegend').innerHTML=S.view==='P'?'<span><i class="box" style="background:var(--heat0);border:1px solid var(--line)"></i>0</span><span><i class="box" style="background:linear-gradient(90deg,var(--heat1),var(--heat2),var(--heat3))"></i>higher</span><span>Dashed line — the diagonal x₁ = x₂: electrons at the same point</span>':'<span><i class="box" style="background:var(--pos)"></i>Ψ &gt; 0</span><span><i class="box" style="background:var(--neg)"></i>Ψ &lt; 0</span><span>An antisymmetric Ψ changes color on reflection in the diagonal</span>'}
async function drawCond(){let C;try{C=await liveCond({mode:S.mode,a:S.a,b:S.b,ms:S.ms,x1:S.x1})}catch(e){return}const sv=document.getElementById('cond');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');
  const L=44,T=10,W=500,H=230;const nums=document.getElementById('nums');
  if(!C){el(sv,'text',{x:L+W/2,y:T+H/2,'text-anchor':'middle','font-size':16,fill:ink,'font-family':'Golos Text, sans-serif'}).textContent='Ψ ≡ 0 — the second electron has nowhere to go';nums.innerHTML='';document.getElementById('condLegend').innerHTML='';return}
  [C.refLab,C.holeLab]=condLab();const lo=Math.min(0,...C.h),hi=Math.max(...C.c,...C.ref)*1.08;const sx=x=>L+x*W,sy=v=>T+H-(v-lo)/(hi-lo)*H;
  for(let v=Math.ceil(lo);v<=hi;v+=1){el(sv,'line',{x1:L,x2:L+W,y1:sy(v),y2:sy(v),stroke:tok('--line'),'stroke-width':v===0?1.3:.7});el(sv,'text',{x:L-6,y:sy(v)+4,'text-anchor':'end','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(v).replace('-','−')}
  const pts=a=>a.map((v,i)=>sx(XS[i]).toFixed(1)+','+sy(v).toFixed(1)).join(' ');
  el(sv,'polygon',{points:sx(0)+','+sy(0)+' '+pts(C.h)+' '+sx(1)+','+sy(0),fill:tok('--hole'),stroke:tok('--neg'),'stroke-width':1.2});
  el(sv,'polyline',{points:pts(C.ref),fill:'none',stroke:tok('--ref'),'stroke-width':2,'stroke-dasharray':'6 4'});
  el(sv,'polyline',{points:pts(C.c),fill:'none',stroke:acc,'stroke-width':2.6,'stroke-linejoin':'round'});
  el(sv,'line',{x1:sx(S.x1),x2:sx(S.x1),y1:T,y2:T+H,stroke:ink,'stroke-width':1,'stroke-dasharray':'2 3',opacity:.6});
  const lb=el(sv,'text',{x:sx(S.x1)+4,y:T+H-6,'font-size':12,fill:ink,'font-family':'Golos Text, sans-serif'});lb.textContent='x₁ (first electron)';
  if(S.x1>0.6)lb.setAttribute('text-anchor','end'),lb.setAttribute('x',sx(S.x1)-4);
  [0,0.25,0.5,0.75,1].forEach(v=>el(sv,'text',{x:sx(v),y:T+H+18,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(v));
  el(sv,'text',{x:L+W,y:T+H+36,'text-anchor':'end','font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₂';
  document.getElementById('condLegend').innerHTML='<span><i class="sw" style="border-color:var(--accent)"></i>c(x₂) — where the second electron is</span><span><i class="sw" style="border-color:var(--ref);border-top-style:dashed"></i>'+C.refLab+'</span><span><i class="box" style="background:var(--hole);border:1px solid var(--neg)"></i>'+C.holeLab+'</span>';
  nums.innerHTML='<span>c(x₁) = <b class="'+(Math.abs(C.c0)<1e-6?'zero':'')+'">'+fmt(C.c0)+'</b></span><span>∫ c dx₂ = <b>1</b></span><span>∫ hole dx₂ = <b>'+fmt(C.hint)+'</b></span>'}
async function drawOrbs(){let O;try{O=await liveOrbs({a:S.a,b:S.b})}catch(e){return}const sv=document.getElementById('orbs');sv.innerHTML='';const mut=tok('--muted');const L=44,W=500,T=8,H=96;const sx=x=>L+x*W,sy=v=>T+H/2-v/1.6*H/2;
  el(sv,'line',{x1:L,x2:L+W,y1:sy(0),y2:sy(0),stroke:tok('--line')});
  [[S.a,'--pos','φ'+SUBN(S.a)+' = φa'],[S.b,'--neg','φ'+SUBN(S.b)+' = φb']].forEach(([n,c,l],k)=>{const p=XS.map((x,i)=>sx(x).toFixed(1)+','+sy((k?O.pb:O.pa)[i]).toFixed(1)).join(' ');el(sv,'polyline',{points:p,fill:'none',stroke:tok(c),'stroke-width':2.2,'stroke-dasharray':k&&S.a===S.b?'6 4':'none'});
    el(sv,'text',{x:L+W+4,y:T+14+k*18,'text-anchor':'end','font-size':12.5,fill:tok(c),'font-family':'Golos Text, sans-serif'}).textContent=l});
  el(sv,'line',{x1:sx(S.x1),x2:sx(S.x1),y1:T,y2:T+H,stroke:tok('--accent'),'stroke-width':1,'stroke-dasharray':'2 3'});
  [0,1].forEach(v=>el(sv,'text',{x:sx(v),y:T+H+14,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=v)}
function drawFormula(){const a='φ'+SUBN(S.a),b='φ'+SUBN(S.b);let h='';
  if(S.mode==='H')h='Ψ(1, 2) = '+a+'(1)α(1) · '+b+'(2)α(2)';
  else if(S.mode==='T'){const sp=S.ms>0?'α(1)α(2)':S.ms<0?'β(1)β(2)':'<span class=fr><span>1</span><span>√2</span></span> [ α(1)β(2) + β(1)α(2) ]';
    const det=S.ms?'<span class=fr><span>1</span><span>√2</span></span> <span class="mat"><span>'+a+'(1)'+(S.ms>0?'α':'β')+'(1)</span><span>'+b+'(1)'+(S.ms>0?'α':'β')+'(1)</span><span>'+a+'(2)'+(S.ms>0?'α':'β')+'(2)</span><span>'+b+'(2)'+(S.ms>0?'α':'β')+'(2)</span></span> = ':'<span class=fr><span>1</span><span>√2</span></span> ( |'+a+' <span class="ob">'+b+'</span>| + |<span class="ob">'+a+'</span> '+b+'| ) = ';
    h='<sup style="font-size:13px">3</sup>Ψ<sub style="font-size:12px">M='+(S.ms>0?'+1':S.ms<0?'−1':'0')+'</sub> = '+det+'<span class=fr><span>1</span><span>√2</span></span> [ '+a+'(1)'+b+'(2) − '+b+'(1)'+a+'(2) ] · '+sp}
  else if(S.mode==='B')h=S.a===S.b?'Ψ<sub style="font-size:12px">bosons</sub> = '+a+'(1)'+a+'(2)':'Ψ<sub style="font-size:12px">bosons</sub> = <span class=fr><span>1</span><span>√2</span></span> [ '+a+'(1)'+b+'(2) + '+b+'(1)'+a+'(2) ]';
  else if(S.mode==='D')h='|'+a+' <span class="ob">'+b+'</span>| = <span class=fr><span>1</span><span>√2</span></span> <span class="mat"><span>'+a+'(1)α(1)</span><span>'+b+'(1)β(1)</span><span>'+a+'(2)α(2)</span><span>'+b+'(2)β(2)</span></span>';
  else h=S.a===S.b?'<sup style="font-size:13px">1</sup>Ψ = '+a+'(1)'+a+'(2) · <span class=fr><span>1</span><span>√2</span></span> [ α(1)β(2) − β(1)α(2) ]':'<sup style="font-size:13px">1</sup>Ψ = <span class=fr><span>1</span><span>√2</span></span> ( |'+a+' <span class="ob">'+b+'</span>| − |<span class="ob">'+a+'</span> '+b+'| ) = <span class=fr><span>1</span><span>√2</span></span> [ '+a+'(1)'+b+'(2) + '+b+'(1)'+a+'(2) ] · <span class=fr><span>1</span><span>√2</span></span> [ α(1)β(2) − β(1)α(2) ]';
  document.getElementById('formula').innerHTML='<span>'+h+'</span>'}
function drawExplain(){const a=S.a===S.b;let t='';
  if(S.mode==='H')t='<b>The electrons are distinguishable.</b> The first is always on φ<sub>a</sub> and the second on φ<sub>b</sub>, so the map is not symmetric about the diagonal: swap the electrons and the picture changes. For identical particles this cannot be. On the diagonal the density is not zero: nothing prevents two electrons with the same spin from being at the same point. The “hole” on the right is just the electron’s own orbital crossed out; it does not follow the electron as x₁ moves.';
  else if(S.mode==='T'&&a)t='<b>Pauli exclusion.</b> The spatial part of the triplet φ<sub>a</sub>(1)φ<sub>a</sub>(2) − φ<sub>a</sub>(1)φ<sub>a</sub>(2) is identically zero (for M<sub>S</sub> = ±1, the determinant has two identical columns). A triplet on a single orbital does not exist.';
  else if(S.mode==='T'&&S.ms===0)t='<b>Triplet, M<sub>S</sub> = 0.</b> Here the spins are different, but the spin part is symmetric, so the spatial part is antisymmetric — the same as for M<sub>S</sub> = ±1. Hence in this component, too, the electrons are never at the same point: c(x₁) = 0. This component cannot be written as a single determinant — it needs a sum of two (like the singlet, but with a “+” sign). All three triplet components have the same energy J − K.';
  else if(S.mode==='T')t='<b>Triplet, M<sub>S</sub> = '+(S.ms>0?'+1':'−1')+' — a single determinant.</b> Ψ changes sign when the electrons are swapped (switch to “Ψ”: the color changes on reflection in the diagonal), so Ψ = 0 on the diagonal — electrons with the same spin are never at the same point. Around the first electron there is no second one: this is the <b>exchange (Fermi) hole</b>. Move x₁ — the hole moves together with the electron. Its integral is exactly −1: one electron is “cut out”, the electron itself, so the electron does not repel itself. The Hartree–Fock method describes this hole exactly.';
  else if(S.mode==='B')t='<b>Bosons</b> (photons, ⁴He atoms) — for comparison: their function is symmetric, P₁₂Ψ = +Ψ. '+(a?'Two particles on the same orbital — no problem: there is no prohibition (hence Bose condensation).':'Look at the point x₂ = x₁: the conditional density there is not zero but a maximum. On the diagonal the density is twice that of distinguishable particles (Hartree product) — bosons “bunch together”, while fermions with the same spin “keep apart”.');
  else if(S.mode==='D')t='<b>A single determinant ↑↓ does not have a definite spin:</b> |φ<sub>a</sub>φ̄<sub>b</sub>| = <span class=fr><span>singlet + triplet M<sub>S</sub>=0</span><span>√2</span></span> — this is exactly what “the last two combinations separately have no definite symmetry” means — hence spin contamination in UHF. Antisymmetry is provided by the spin part, and the spatial density on the diagonal does not vanish'+(a?' (here both electrons are on the same orbital, as in the He atom)':'')+'. The ↓ electron “does not know” where the ↑ electron is: the conditional density coincides with the ordinary one, and there is no hole. So in a single determinant — and hence in the Hartree–Fock method — electrons with opposite spins move independently. The missing <b>Coulomb hole</b> is the source of the correlation energy.';
  else t=a?'<b>The singlet on a single orbital</b> coincides with the determinant ↑↓: the spatial part φ<sub>a</sub>(1)φ<sub>a</sub>(2) is symmetric, and the spin part is antisymmetric.':'<b>Singlet.</b> The spatial part is symmetric, and the spin factor is antisymmetric. Such a function cannot be written as a single determinant — it needs a combination of two. On the diagonal the density is even enhanced: the electrons are found close together more often than without symmetry, so the repulsion in the singlet is larger than in the triplet (see below: J + K versus J − K).';
  document.getElementById('explain').innerHTML=t}
async function drawEnergy(){let E;try{E=await liveE({a:S.a,b:S.b})}catch(e){return}const {J,K}=E;const same=S.a===S.b;
  document.getElementById('jk').innerHTML='<span>J<sub>ab</sub> = <b>'+fmt(J,3)+'</b></span><span>K<sub>ab</sub> = <b>'+fmt(K,3)+'</b></span><span class="hint">(arb. units)</span>'+(same?'<span class="hint">For a = b the integrals coincide: K<sub>aa</sub> = J<sub>aa</sub>.</span>':'');
  const rows=[['T','Triplet S = 1 (any M<sub>S</sub>)','J − K',E.rows[0][1]],['H','Hartree product','J',J],['D','Single determinant ↑↓','J',J],['S','Singlet S = 0',same?'J':'J + K',E.rows[3][1]],['B','Bosons',same?'J':'J + K',E.rows[3][1]]];
  const mx=E.mx;
  document.getElementById('bars').innerHTML=rows.map(r=>'<div class="bar'+(r[0]===S.mode?' on':'')+'"><span>'+r[1]+' — '+r[2]+'</span><span class="t"><i style="width:'+(r[3]==null?0:r[3]/mx*100)+'%"></i></span><b>'+(r[3]==null?'none':fmt(r[3],3))+'</b></div>').join('');
  document.getElementById('hund').innerHTML=same?'Two particles in the same orbital can only form a singlet: the triplet is forbidden by the Pauli principle.':'The triplet lies below the singlet by 2K = '+fmt(E.K2,3)+'. The energy of a single ↑↓ determinant lies exactly halfway between: it is half singlet, half triplet. Electrons with the same spin avoid each other (exchange hole), so the repulsion is smaller. This is <b>Hund’s rule</b> (example: the 1s¹2s¹ configuration of the He atom).'}
function drawAll(){drawFormula();drawMap();drawCond();drawOrbs();drawExplain();drawEnergy();document.getElementById('x1v').textContent=fmt(S.x1);
  try{localStorage.setItem('pauli-state',JSON.stringify(S))}catch(e){}}
/* ===== управление ===== */
function chips(id,items,cur,set,cls){const box=document.getElementById(id);box.innerHTML='';items.forEach(([v,l])=>{const b=document.createElement('button');b.type='button';b.className='chip'+(cls?' '+cls:'');b.innerHTML=l;b.setAttribute('aria-pressed',v===cur());b.onclick=()=>{set(v);S.flip=0;S.flipT=0;renderControls();drawAll();flipMsg()};box.appendChild(b)})}
function renderControls(){chips('modes',MODES.map(m=>[m.id,m.name]),()=>S.mode,v=>S.mode=v);
  chips('oa',[1,2,3,4].map(n=>[n,'φ'+SUBN(n)]),()=>S.a,v=>S.a=v,'m');chips('ob',[1,2,3,4].map(n=>[n,'φ'+SUBN(n)]),()=>S.b,v=>S.b=v,'m');
  chips('ms',[[1,'+1 (↑↑)'],[0,'0'],[-1,'−1 (↓↓)']],()=>S.ms,v=>S.ms=v);document.getElementById('msRow').style.display=S.mode==='T'?'':'none';
  chips('views',[['P','|Ψ|²'],['W','Signed Ψ']],()=>S.view,v=>S.view=v)}
S.flip=0;S.flipT=0;
function flipMsg(){const m=document.getElementById('flipMsg');if(S.flipT<1||pauliZero()){m.textContent=S.flipT>0&&S.flipT<1?'reflecting the map in the diagonal x₁ = x₂…':'';return}
  const P=S.view==='P';let t='';
  if(S.mode==='H')t=P?'The picture has changed: |Ψ(2,1)|² ≠ |Ψ(1,2)|², so the particles are distinguishable. This is not allowed for electrons.':'P₁₂Ψ ≠ ±Ψ: the function is neither symmetric nor antisymmetric, so it is unsuitable for identical particles.';
  else if(P)t='|Ψ|² is unchanged: exchanging identical particles changes nothing observable. Switch to “Signed Ψ” to see the difference between fermions and bosons.';
  else if(S.mode==='T')t='P₁₂Ψ = −Ψ: every point has switched to the opposite color. These are fermions; on the diagonal, where Ψ = −Ψ, only Ψ = 0 remains.';
  else if(S.mode==='D')t='For ↑↓ the spins are exchanged together with the coordinates: the component α(1)β(2) turns into β(1)α(2) with a “−” sign, so the determinant as a whole is antisymmetric.';
  else t='P₁₂Ψ = +Ψ: the spatial part is symmetric, the picture is unchanged'+(S.mode==='S'?' (the singlet gets its antisymmetry from the spin factor).':' — this is how bosons behave.');
  m.textContent=t}
function doFlip(){const target=S.flip?0:1;S.flip=target;const t0=performance.now(),from=S.flipT;if(matchMedia('(prefers-reduced-motion: reduce)').matches){S.flipT=target;drawMap();flipMsg();return}
  const stepF=n=>{const u=Math.min(1,(n-t0)/1100);const e=u<.5?2*u*u:1-Math.pow(-2*u+2,2)/2;S.flipT=from+(target-from)*e;drawMap();flipMsg();if(u<1)requestAnimationFrame(stepF)};requestAnimationFrame(stepF)}
document.getElementById('bFlip').onclick=doFlip;
const x1in=document.getElementById('x1');x1in.value=S.x1;x1in.oninput=e=>{S.x1=+e.target.value;drawMap();drawCond();drawOrbs();if(window.drawCI)drawCI();document.getElementById('x1v').textContent=fmt(S.x1)};
(()=>{const sv=document.getElementById('map');let down=false;const set=e=>{const r=sv.getBoundingClientRect();const x=((e.clientX-r.left)/r.width*400-M0)/MS;S.x1=Math.max(0.01,Math.min(0.99,x));x1in.value=S.x1;drawMap();drawCond();drawOrbs();if(window.drawCI)drawCI();document.getElementById('x1v').textContent=fmt(S.x1)};
  sv.addEventListener('pointerdown',e=>{down=true;sv.setPointerCapture(e.pointerId);set(e)});sv.addEventListener('pointermove',e=>{if(down)set(e)});sv.addEventListener('pointerup',()=>{down=false;try{localStorage.setItem('pauli-state',JSON.stringify(S))}catch(e){}});})();
renderControls();drawAll();

/* ===== кулоновская дырка: КВ из двух конфигураций ===== */
S.th=S.th??0;S.lam=S.lam??3;
async function drawCIMap(){let Mp;try{Mp=await liveCM({th:S.th})}catch(e){return}const sv=document.getElementById('ciMap');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');
  const R=110;const cv=document.createElement('canvas');cv.width=R;cv.height=R;const cx=cv.getContext('2d');const img=cx.createImageData(R,R);const v=f64(Mp.f64),mx=Mp.mx;
  for(let k=0;k<R*R;k++){const c=heat(Math.pow(v[k]/mx,0.8));img.data.set([c[0],c[1],c[2],255],4*k)}cx.putImageData(img,0,0);
  el(sv,'image',{href:cv.toDataURL(),x:M0,y:6,width:MS,height:MS,preserveAspectRatio:'none'});el(sv,'rect',{x:M0,y:6,width:MS,height:MS,fill:'none',stroke:tok('--line')});
  el(sv,'line',{x1:M0,y1:6+MS,x2:M0+MS,y2:6,stroke:ink,'stroke-width':1.2,'stroke-dasharray':'5 4',opacity:.7});
  const X=M0+S.x1*MS;el(sv,'line',{x1:X,y1:6,x2:X,y2:6+MS,stroke:acc,'stroke-width':2});
  [0,0.5,1].forEach(q=>{el(sv,'text',{x:M0+q*MS,y:6+MS+16,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(q);
    el(sv,'text',{x:M0-6,y:6+MS-q*MS+4,'text-anchor':'end','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(q)});
  el(sv,'text',{x:M0+MS-4,y:6+MS+30,'text-anchor':'end','font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₁';
  el(sv,'text',{x:6,y:20,'font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₂'}
function drawCICond(Z){const sv=document.getElementById('ciCond');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');
  const c=Z.c,ref=Z.ref,h=Z.h;
  const L=44,T=10,W=500,H=190;const lo=Math.min(-0.5,...h),hi=Math.max(...c,...ref)*1.08;const sx=x=>L+x*W,sy=q=>T+H-(q-lo)/(hi-lo)*H;
  for(let q=Math.ceil(lo);q<=hi;q++){el(sv,'line',{x1:L,x2:L+W,y1:sy(q),y2:sy(q),stroke:tok('--line'),'stroke-width':q===0?1.3:.7});el(sv,'text',{x:L-6,y:sy(q)+4,'text-anchor':'end','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(q).replace('-','−')}
  const pts=a=>a.map((q,i)=>sx(XS[i]).toFixed(1)+','+sy(q).toFixed(1)).join(' ');
  el(sv,'polygon',{points:sx(0)+','+sy(0)+' '+pts(h)+' '+sx(1)+','+sy(0),fill:tok('--hole'),stroke:tok('--neg'),'stroke-width':1.2});
  el(sv,'polyline',{points:pts(ref),fill:'none',stroke:tok('--ref'),'stroke-width':2,'stroke-dasharray':'6 4'});
  el(sv,'polyline',{points:pts(c),fill:'none',stroke:acc,'stroke-width':2.6});
  el(sv,'line',{x1:sx(S.x1),x2:sx(S.x1),y1:T,y2:T+H,stroke:ink,'stroke-width':1,'stroke-dasharray':'2 3',opacity:.6});
  [0,0.5,1].forEach(q=>el(sv,'text',{x:sx(q),y:T+H+18,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(q));
  el(sv,'text',{x:L+W,y:T+H+36,'text-anchor':'end','font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₂';
  return Z.dep}
function drawCIE(Z){const sv=document.getElementById('ciE');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');
  const L=56,T=8,W=480,H=120;const ths=Array.from({length:181},(_,i)=>-45+i*0.5);const Es=Z.Es,lo=Z.lo,hi=Z.hi;
  const sx=t=>L+(t+45)/90*W,sy=e=>T+H-(e-lo)/(hi-lo)*H;
  [lo,(lo+hi)/2,hi].forEach(e=>{el(sv,'line',{x1:L,x2:L+W,y1:sy(e),y2:sy(e),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(e)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=e.toFixed(1)});
  el(sv,'polyline',{points:ths.map((t,i)=>sx(t).toFixed(1)+','+sy(Es[i]).toFixed(1)).join(' '),fill:'none',stroke:mut,'stroke-width':2});
  const to=Z.toDeg;el(sv,'line',{x1:sx(0),x2:sx(0),y1:T,y2:T+H,stroke:mut,'stroke-dasharray':'2 3'});
  el(sv,'circle',{cx:sx(to),cy:sy(Z.Eto),r:4,fill:'none',stroke:tok('--neg'),'stroke-width':2});
  el(sv,'circle',{cx:sx(S.th),cy:sy(Z.Eth),r:6,fill:acc});
  [-45,-30,-15,0,15,30,45].forEach(t=>el(sv,'text',{x:sx(t),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(t).replace('-','−')+'°');
  el(sv,'text',{x:L+W,y:T+H+32,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='θ'}
async function drawCI(){let Z;try{Z=await liveCI({th:S.th,lam:S.lam,x1:S.x1})}catch(e){return}drawCIMap();const dep=drawCICond(Z);drawCIE(Z);const c1=Z.c1,c2=Z.c2,E=Z.E,E0=Z.E0,Em=Z.Em;
  document.getElementById('thv').textContent=(S.th>0?'+':'')+String(S.th).replace('-','−')+'°';document.getElementById('lamv').textContent=S.lam.toFixed(1);
  document.getElementById('ciNums').innerHTML='<span>c₁ = <b>'+fmt(c1,3)+'</b></span><span>c₂ = <b>'+fmt(c2,3)+'</b></span><span>E = <b>'+fmt(E,3)+'</b></span><span>E(θ = 0) = <b>'+fmt(E0,3)+'</b></span><span>E<sub>corr</sub> = E<sub>min</sub> − E(0) = <b>'+fmt(Em-E0,3)+'</b></span><span>'+(dep>=0?'density depletion':'density excess')+' at x₂ = x₁: <b>'+Math.abs(Math.round(dep*100))+' %</b></span>';
  let txt;if(Math.abs(S.th)<0.01)txt='<b>θ = 0: a single determinant.</b> The conditional density of the second electron coincides with the ordinary density: there is no hole, and electrons with opposite spins move independently. Press “Energy minimum”.';
  else if(c2<0)txt='<b>c₂ &lt; 0: a Coulomb hole has appeared.</b> The signs are such that the contributions of the two configurations partly cancel on the diagonal x₁ = x₂, so the electrons are less often close together. The repulsion decreases more than the kinetic energy grows (on φ₂ it is 4 times larger), so E is lower than for a single determinant. '+(Z.atMin?'This is the minimum: the CI solution in the basis of two configurations; the gain E<sub>corr</sub> is exactly the correlation energy that Hartree–Fock misses.':'The energy minimum is marked on the plot with a circle.');
  else txt='<b>c₂ &gt; 0: the “wrong” sign.</b> Now the contributions on the diagonal add up: the electrons are more often close together, the repulsion grows, and the energy is higher than for a single determinant. Nature chooses the sign that creates a hole.';
  document.getElementById('ciText').innerHTML=txt}
const thIn=document.getElementById('th'),lamIn=document.getElementById('lam');thIn.value=S.th;lamIn.value=S.lam;
thIn.oninput=e=>{S.th=+e.target.value;drawCI()};lamIn.oninput=e=>{S.lam=+e.target.value;drawCI()};
document.getElementById('bMin').onclick=async()=>{let Z;try{Z=await QC.api('pauli.ci',{th:S.th,lam:S.lam,x1:S.x1})}catch(e){return}S.th=+Z.toDeg.toFixed(2);thIn.value=S.th;drawCI()};
document.getElementById('bZero').onclick=()=>{S.th=0;thIn.value=0;drawCI()};
(()=>{const sv=document.getElementById('ciMap');let down=false;const set=e=>{const r=sv.getBoundingClientRect();S.x1=Math.max(0.01,Math.min(0.99,((e.clientX-r.left)/r.width*400-M0)/MS));x1in.value=S.x1;drawMap();drawCond();drawOrbs();drawCI();document.getElementById('x1v').textContent=fmt(S.x1)};
  sv.style.touchAction='none';sv.style.cursor='crosshair';sv.addEventListener('pointerdown',e=>{down=true;sv.setPointerCapture(e.pointerId);set(e)});sv.addEventListener('pointermove',e=>{if(down)set(e)});sv.addEventListener('pointerup',()=>down=false)})();
drawCI();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{drawAll();drawCI()});
new MutationObserver(()=>{drawAll();drawCI()}).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
