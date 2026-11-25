/* Density-functional page (Atlas v2).  The functionals (LSDA, B88, PBE, PW92), the
   radial and Becke quadratures, the self-interaction table, E(N) and the H2+
   curves come from quas_atlas.core.dft (endpoints dft.meta, dft.sie, dft.en,
   dft.h2; the precomputed arrays are core/data/dft.json); this script draws. */
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=3)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const fsig=(x,d=3)=>(x>0.5*Math.pow(10,-d)?'+':'')+fmt(x,d);
const KJ=2625.5;
function axes(svg,o){const X=x=>o.L+(x-o.x0)/(o.x1-o.x0)*(o.W-o.L-o.R),Y=y=>o.H-o.B-(y-o.y0)/(o.y1-o.y0)*(o.H-o.T-o.B);
  o.yt.forEach(v=>{el('line',{x1:o.L,x2:o.W-o.R,y1:Y(v),y2:Y(v),stroke:Math.abs(v)<1e-12?'var(--muted)':'var(--line)','stroke-width':1},svg);el('text',{x:o.L-6,y:Y(v)+4,'text-anchor':'end','font-size':11.5,fill:'var(--muted)'},svg,fmt(v,o.yd??2))});
  o.xt.forEach(v=>{el('line',{x1:X(v),x2:X(v),y1:o.H-o.B,y2:o.H-o.B+4,stroke:'var(--muted)','stroke-width':1},svg);el('text',{x:X(v),y:o.H-o.B+17,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,fmt(v,o.xd??0))});
  el('line',{x1:o.L,x2:o.W-o.R,y1:o.H-o.B,y2:o.H-o.B,stroke:'var(--muted)','stroke-width':1},svg);
  if(o.xl)el('text',{x:(o.L+o.W-o.R)/2,y:o.H-2,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,o.xl);return {X,Y}}
const line=(pts,X,Y,lo=-1e9,hi=1e9)=>{let s='',pen=false;pts.forEach(p=>{if(!(p[1]>=lo&&p[1]<=hi)){pen=false;return}s+=(pen?'L':'M')+X(p[0]).toFixed(1)+','+Y(p[1]).toFixed(1);pen=true});return s};
// ---------- 1. самодействие ----------
const FUNCS=[{n:'Hartree–Fock (exact exchange)',x:'hf',c:null},{n:'Spin-unpolarized LDA',x:'xlda',c:'clda'},{n:'LSDA',x:'xlsda',c:'clsda'},{n:'B88 exchange + LSDA correlation',x:'xb88',c:'clsda'},{n:'PBE exchange + LSDA correlation',x:'xpbe',c:'clsda'}];
async function sec1(){let Z;try{Z=await QC.api('dft.sie',{})}catch(e){return}const rows=FUNCS.map((f,i)=>({...f,...Z.rows[i]}));
  $('sieTab').innerHTML='<table class="mtab bt"><thead><tr><th class="n">functional</th><th>E<sub>x</sub></th><th>E<sub>c</sub></th><th>J + E<sub>x</sub> + E<sub>c</sub></th><th>E at best ζ</th></tr></thead><tbody>'+
    rows.map(r=>`<tr><td class="n">${r.n}</td><td>${fmt(r.Ex,4)}</td><td>${fmt(r.Ec,4)}</td><td>${fsig(r.s,4)}</td><td>${fmt(r.Eo,4)} <span class="hint">(ζ = ${fmt(r.zo,3)})</span></td></tr>`).join('')+'</tbody></table>';
  const svg=$('sieBar');svg.innerHTML='';const L=150,W=540,Rr=14,T=20,rowH=(300-T-30)/rows.length,x0=-0.4,x1=0.4,X=v=>L+(v-x0)/(x1-x0)*(W-L-Rr);
  [-0.4,-0.2,0,0.2,0.4].forEach(v=>{el('line',{x1:X(v),x2:X(v),y1:T-6,y2:300-24,stroke:v===0?'var(--muted)':'var(--line)','stroke-width':1},svg);el('text',{x:X(v),y:296,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,fmt(v,1))});
  const short=['Hartree–Fock','LDA (no spin)','LSDA','B88 + LSDA','PBE + LSDA'];
  rows.forEach((r,i)=>{const y=T+i*rowH,h=(rowH-10)/2;el('text',{x:L-8,y:y+rowH/2+4,'text-anchor':'end','font-size':12.5,fill:'var(--ink)'},svg,short[i]);
    el('rect',{x:X(0),y:y+2,width:X(r.J)-X(0),height:h,fill:'var(--muted)',opacity:0.55,rx:2},svg);
    el('rect',{x:X(r.Ex),y:y+4+h,width:X(0)-X(r.Ex),height:h,fill:'var(--accent)',rx:2},svg);
    if(r.Ec<0)el('rect',{x:X(r.Ex+r.Ec),y:y+4+h,width:X(r.Ex)-X(r.Ex+r.Ec),height:h,fill:'var(--rho-l)',rx:2},svg);
    const s=r.s,cx=X(s),cy=y+rowH/2+1;el('path',{d:`M${cx},${cy-7} l7,7 l-7,7 l-7,-7 z`,fill:Math.abs(s)<1e-4?'var(--ok)':'var(--warn)',stroke:'var(--panel)','stroke-width':1},svg)});
  el('text',{x:X(0.4),y:12,'text-anchor':'end','font-size':11.5,fill:'var(--muted)'},svg,'a.u.');
  const ls=rows[2],b=rows[3];
  $('t1').innerHTML=`LSDA underestimates exchange by ${fmt(Z.pct,0).replace('−','')} % and, on top of that, gives a spurious correlation energy of ${fmt(ls.Ec,3)}: the electron “repels itself” by ${fmt(Z.sie,3)} a.u. (${fmt(Z.sieKJ,0)} kJ/mol). GGA exchange (B88, PBE) is nearly exact for H, but LSDA correlation spoils everything. Without spin the error is even larger: for one electron ρ<sub>α</sub> = ρ, ρ<sub>β</sub> = 0, so the system is fully polarized. Last column: total energy of the atom at the optimal ζ; the exact value is −0.5.`}
// ---------- 2. E(N) ----------
let ai=0,Ri=0,AL=[];const liveEN=QC.live('dft.en'),liveH2=QC.live('dft.h2');
async function sec2(){let Z;try{Z=await liveEN({ai})}catch(e){return}const a=Z.a,E=Z.E,H=Z.H,NN=Z.NN;
  let svg=$('enChart');svg.innerHTML='';let o={W:540,H:300,L:56,R:12,T:12,B:38,x0:0,x1:2,y0:-0.6,y1:0.02,xt:[0,0.5,1,1.5,2],yt:[-0.6,-0.5,-0.4,-0.3,-0.2,-0.1,0],xl:'number of electrons N',xd:1};let A=axes(svg,o);
  el('path',{d:line(NN.map((N,i)=>[N,Z.exact[i]]),A.X,A.Y),fill:'none',stroke:'var(--ink)','stroke-width':2},svg);
  el('path',{d:line(NN.map((N,i)=>[N,H[i]]),A.X,A.Y),fill:'none',stroke:'var(--muted)','stroke-width':1.8,'stroke-dasharray':'6 4'},svg);
  el('path',{d:line(NN.map((N,i)=>[N,E[i]]),A.X,A.Y),fill:'none',stroke:'var(--accent)','stroke-width':2.6},svg);
  const i1=NN.indexOf(1),sL=Z.sL,sR=Z.sR;
  Z.tan.forEach(t=>el('path',{d:line(t,A.X,A.Y),fill:'none',stroke:'var(--rho-l)','stroke-width':1.6,'stroke-dasharray':'2 3'},svg));
  [0,1,2].forEach(N=>el('circle',{cx:A.X(N),cy:A.Y(Z.ex012[N]),r:3.5,fill:'var(--ink)'},svg));
  [['H⁺',0],['H',1],['H⁻',2]].forEach(([t,N])=>el('text',{x:A.X(N)+(N===2?-6:6),y:A.Y(Z.ex012[N])-8,'text-anchor':N===2?'end':'start','font-size':12,fill:'var(--ink)'},svg,t));
  svg=$('devChart');svg.innerHTML='';o={W:540,H:300,L:56,R:12,T:12,B:38,x0:0,x1:2,y0:-0.06,y1:0.03,xt:[0,0.5,1,1.5,2],yt:[-0.06,-0.04,-0.02,0,0.02],xl:'number of electrons N',xd:1};A=axes(svg,o);
  el('path',{d:line(NN.map(N=>[N,0]),A.X,A.Y),fill:'none',stroke:'var(--ink)','stroke-width':2},svg);
  el('path',{d:line(NN.map((N,i)=>[N,Z.devH[i]]),A.X,A.Y,o.y0,o.y1),fill:'none',stroke:'var(--muted)','stroke-width':1.8,'stroke-dasharray':'6 4'},svg);
  el('path',{d:line(NN.map((N,i)=>[N,Z.devE[i]]),A.X,A.Y,o.y0,o.y1),fill:'none',stroke:'var(--accent)','stroke-width':2.6},svg);
  el('text',{x:A.X(0.5),y:A.Y(0.022),'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'above the line — concave (localization error)');
  el('text',{x:A.X(0.5),y:A.Y(-0.055),'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'below the line — convex (delocalization error)');
  
  $('enKv').innerHTML=`<span>ε<sub>HOMO</sub> = <span class=fr><span>dE</span><span>dN</span></span> at N → 1⁻</span><b>${fmt(sL,3)} (should be −I = −0.5)</b><span>I = E(H⁺) − E(H)</span><b>${fmt(Z.I,3)} (exact 0.5)</b><span>slope at N → 1⁺</span><b>${fmt(sR,3)} (should be −A = −0.028)</b><span>slope jump (gap)</span><b>${fmt(Z.gap,3)} (exact I − A = 0.472)</b><span>E(½) − ½E(1)</span><b>${fsig(Z.half,4)} (exact 0)</b>`;
  let t=a===0?`<b>LSDA:</b> the curve is convex, half an electron lies “below the line” by ${fmt(Math.abs(Z.half),3)} a.u. Hence the main point: the HOMO energy ${fmt(sL,2)} is almost half the ionization potential, although the ionization energy itself, computed as an energy difference, is close to exact. The jump in slope at N = 1 (${fmt(Z.gap,2)}) for a smooth functional is just its KS orbital gap: there is no derivative discontinuity Δ<sub>xc</sub>. So HOMO–LUMO gaps in LDA and GGA are much smaller than I − A for two reasons: there is no Δ<sub>xc</sub>, and the convexity of E(N) shifts the orbital energies themselves.`:
    `At a = ${fmt(a,2)} the curvature ${Math.abs(Z.half)<0.005?'has almost vanished':'is smaller'}: exact exchange bends E(N) upwards (as in Hartree–Fock, dashed), LSDA downwards, and they partly compensate. That is why hybrid functionals (B3LYP: a = 0.20; PBE0: a = 0.25) describe orbital energies and gaps better. But no single a gives full compensation for all systems — hence range-separated functionals.`;
  $('t2').innerHTML=t}
// ---------- 3. H₂⁺ ----------
async function sec3(){let Z;try{Z=await liveH2({ai,ri:Ri})}catch(e){return}const a=Z.a,RR=Z.RR,hf=Z.hf,d=Z.d,l=Z.l;const svg=$('h2Chart');svg.innerHTML='';
  const o={W:540,H:320,L:56,R:12,T:12,B:38,x0:0.6,x1:10,y0:-0.62,y1:-0.38,xt:[1,2,4,6,8,10],yt:[-0.6,-0.55,-0.5,-0.45,-0.4],xl:'R, bohr'};const A=axes(svg,o);
  el('line',{x1:A.X(0.6),x2:A.X(10),y1:A.Y(-0.5),y2:A.Y(-0.5),stroke:'var(--ok)','stroke-dasharray':'3 4','stroke-width':1.2},svg);
  el('text',{x:A.X(9.9),y:A.Y(-0.5)+16,'text-anchor':'end','font-size':11.5,fill:'var(--ok)'},svg,'H + H⁺: −0.5');
  el('path',{d:line(RR.map((R,i)=>[R,hf[i]]),A.X,A.Y,o.y0,o.y1),fill:'none',stroke:'var(--ink)','stroke-width':2},svg);
  el('path',{d:line(RR.map((R,i)=>[R,l[i]]),A.X,A.Y,o.y0,o.y1),fill:'none',stroke:'var(--rho-l)','stroke-width':2,'stroke-dasharray':'6 4'},svg);
  el('path',{d:line(RR.map((R,i)=>[R,d[i]]),A.X,A.Y,o.y0,o.y1),fill:'none',stroke:'var(--accent)','stroke-width':2.6},svg);
  const R=RR[Ri];el('line',{x1:A.X(R),x2:A.X(R),y1:o.T,y2:o.H-o.B,stroke:'var(--muted)','stroke-dasharray':'3 3','stroke-width':1},svg);
  [[hf,'var(--ink)'],[l,'var(--rho-l)'],[d,'var(--accent)']].forEach(([arr,c])=>{const v=arr[Ri];if(v>=o.y0&&v<=o.y1)el('circle',{cx:A.X(R),cy:A.Y(v),r:4,fill:c},svg)});
  $('Rv').textContent=fmt(R,1)+' bohr';
  $('h2Kv').innerHTML=`<span>Hartree–Fock (exact)</span><b>${fmt(hf[Ri],4)}</b><span>functional, σ<sub>g</sub></span><b>${fmt(d[Ri],4)} (${fsig(Z.dkj,0)} kJ/mol)</b><span>functional, on one atom</span><b>${fmt(l[Ri],4)}</b>`;
  const iF=RR.length-1;$('t3').innerHTML=a===0?`At R = 10 bohr, LSDA gives ${fmt(d[iF],3)} for the electron shared between the atoms and ${fmt(l[iF],3)} for the electron on one atom. They should be equal to each other and to −0.5 (in this basis, ${fmt(hf[iF],3)}). The error is ≈ ${fmt(Z.errF,0)} kJ/mol, and the curve even goes down on stretching. The same error overestimates charge transfer, underestimates reaction barriers, and makes anions and charge-transfer complexes too “smeared out”.`:
   `With a fraction of exact exchange a = ${fmt(a,2)}, the error at R = 10 bohr is ${fmt(Z.errF,0)} kJ/mol. Even at a = 1 the curve does not match the exact one: LSDA correlation also contains self-interaction (≈ −0.02 a.u. per H atom).`}
// ---------- управление ----------
function setA(i){ai=i;document.querySelectorAll('.aS').forEach(s=>s.value=i);document.querySelectorAll('.aV').forEach(v=>v.textContent='a = '+fmt(AL[i],2)+(i===0?' (LSDA)':i===4?' (fraction as in B3LYP)':i===5?' (fraction as in PBE0)':i===20?' (Hartree–Fock exchange + LSDA correlation)':''));sec2();sec3()}
document.querySelectorAll('.aS').forEach(s=>s.oninput=e=>setA(+e.target.value));
$('Rs').oninput=e=>{Ri=+e.target.value;sec3()};
sec1();QC.api('dft.meta',{}).then(M=>{AL=M.A;Ri=M.ri0;$('Rs').value=Ri;setA(0)}).catch(()=>{});
