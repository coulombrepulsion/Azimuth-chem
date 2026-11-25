/* Born-Oppenheimer page (Atlas v2).  Morse/harmonic levels, turning points,
   potentials, wavefunctions, <R> and the time scales come from
   quas_atlas.core.bo (bo.state); this script draws and formats. */
// ---------- страница «Борн–Оппенгеймер и колебательные уровни»: потенциал Морзе для H₂ (ат. ед.) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt=(x,d=3)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const n0=x=>String(Math.round(x)).replace(/\B(?=(\d{3})+(?!\d))/g,' ').replace('-','−');
const EV=27.211386,CM=219474.63,KJ=2625.4996,BOHR=0.529177,AUT=0.0241888,AMU=1822.888;
let DE=0.1745,RE=1.401;  /* replaced by the model's values on every response */              // D_e = 4,75 эВ, R_e = 0,741 Å, ω_e(H₂) = 4401 см⁻¹
const ISO=[['H₂',1.00783*1.00783/(2*1.00783)],['HD',1.00783*2.01410/(1.00783+2.01410)],['D₂',2.01410/2],['T₂',3.01605/2]];
let mu=ISO[0][1]*AMU,pot='both',v=0,prob=false;
const RG=Array.from({length:1400},(_,i)=>0.35+i*0.0045);
function draw(D){const p=D.p;const sv=$('pot');sv.innerHTML='';const W=560,H=380,L=48,R=14,T=14,B=36,pw=W-L-R,ph=H-T-B;
  const x0=0.3,x1=3.0,y0=-0.2,y1=5.6;const sx=r=>L+(r*BOHR-x0)/(x1-x0)*pw,sy=e=>T+ph-(e*EV-y0)/(y1-y0)*ph;
  el('rect',{x:L,y:T,width:pw,height:ph,fill:'none',stroke:tok('--line')},sv);
  for(let e=0;e<=5;e++){el('line',{x1:L,y1:sy(e/EV),x2:L+pw,y2:sy(e/EV),stroke:tok('--line'),'stroke-dasharray':'2 4'},sv);el('text',{x:L-6,y:sy(e/EV)+4,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,String(e))}
  for(let r=0.5;r<=3;r+=0.5)el('text',{x:L+(r-x0)/(x1-x0)*pw,y:H-18,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,fmt(r,1));
  el('text',{x:L+pw,y:H-3,'text-anchor':'end','font-size':12,fill:tok('--muted')},sv,'R, Å');el('text',{x:4,y:T+10,'font-size':12,fill:tok('--muted')},sv,'eV');
  const clip=e=>Math.max(y0/EV-0.01,Math.min(y1/EV+0.01,e));
  const path=a=>{let d='';RG.forEach((R,i)=>{if(R*BOHR<x0||R*BOHR>x1)return;const e=a[i];if(e*EV>y1+0.5)return;d+=(d?' L':'M')+sx(R).toFixed(1)+','+sy(clip(e)).toFixed(1)});return d};
  el('line',{x1:L,y1:sy(DE),x2:L+pw,y2:sy(DE),stroke:tok('--muted'),'stroke-dasharray':'6 4'},sv);el('text',{x:L+pw-4,y:sy(DE)-5,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,'H + H');
  if(pot!=='morse')el('path',{d:path(D.Uh),fill:'none',stroke:tok('--warn'),'stroke-width':1.8,'stroke-dasharray':'6 4'},sv);
  if(pot!=='harm')el('path',{d:path(D.U),fill:'none',stroke:tok('--accent'),'stroke-width':2.4},sv);
  const harmOnly=pot==='harm';const nLev=harmOnly?Math.min(40,Math.ceil(DE/p.w)+2):p.vmax+1;
  for(let k=0;k<nLev;k++){const E=harmOnly?p.Eh[k]:p.E[k];if(E*EV>y1)break;const [ra,rb]=harmOnly?D.turnH[k]:D.turnM[k];
    el('line',{x1:sx(Math.max(ra,x0/BOHR)),y1:sy(E),x2:sx(Math.min(rb,x1/BOHR)),y2:sy(E),stroke:k===v?tok('--ok'):tok(harmOnly?'--warn':'--accent'),'stroke-width':k===v?2.2:1,opacity:k===v?1:0.7},sv)}
  if(pot==='both')for(let k=0;k<6;k++){const E=p.Eh[k];const [ra,rb]=D.turnH[k];el('line',{x1:sx(rb)+2,y1:sy(E),x2:sx(rb)+14,y2:sy(E),stroke:tok('--warn'),'stroke-width':1.5},sv)}
  // волновая функция выбранного уровня
  const kv=D.kv;const E=harmOnly?p.Eh[kv]:p.E[kv];const psi=D.psi;
  if(psi){const amp=0.055*ph;const mx=Math.max(...psi.map(x=>Math.abs(prob?x*x:x)));let d='';RG.forEach((R,i)=>{if(R*BOHR<x0||R*BOHR>x1)return;if(Math.abs(psi[i])<0.002*Math.sqrt(mx)&&!d)return;const yv=prob?psi[i]*psi[i]:psi[i];d+=(d?' L':'M')+sx(R).toFixed(1)+','+(sy(E)-yv/mx*amp).toFixed(1)});
    el('path',{d,fill:'none',stroke:tok('--ok'),'stroke-width':2},sv)}
  // D_e и D_0
  const xa=L+pw*0.86;el('line',{x1:xa,y1:sy(0),x2:xa,y2:sy(DE),stroke:tok('--ink'),'stroke-width':1.2,'marker-end':''},sv);el('text',{x:xa+4,y:sy(DE/2),'font-size':12,fill:tok('--ink')},sv,'Dₑ');
  if(!harmOnly){const xb=L+pw*0.93;el('line',{x1:xb,y1:sy(p.E[0]),x2:xb,y2:sy(DE),stroke:tok('--ok'),'stroke-width':1.2},sv);el('text',{x:xb+4,y:sy((DE+p.E[0])/2)+12,'font-size':12,fill:tok('--ok')},sv,'D₀')}
  return p}
const getState=QC.live('bo.state');
async function render(){let D;try{D=await getState({mu,pot,v})}catch(e){return}DE=D.DE;RE=D.RE;const p=draw(D);const harmOnly=pot==='harm';const zpe=p.E[0],zh=p.Eh[0];
  $('muV').textContent='μ = '+n0(mu)+' mₑ = '+fmt(mu/AMU,4)+' u';
  document.querySelectorAll('#isoG .chip').forEach((b,i)=>b.setAttribute('aria-pressed',Math.abs(ISO[i][1]*AMU-mu)<1));
  document.querySelectorAll('#potG .chip').forEach(b=>b.setAttribute('aria-pressed',b.dataset.p===pot));
  const vmax=harmOnly?Infinity:p.vmax;if(v>vmax)v=Math.max(0,vmax);$('vV').textContent='v = '+v+(harmOnly?'':' of '+(p.vmax+1)+' levels');
  $('kvTab').innerHTML='<table class="mtab"><tbody>'+
   '<tr><td>ω<sub>e</sub> (vibrational frequency)</td><td>'+n0(p.w*CM)+' cm⁻¹</td></tr>'+
   '<tr><td>ω<sub>e</sub>x<sub>e</sub> (anharmonicity)</td><td>'+fmt(p.xe*CM,1)+' cm⁻¹</td></tr>'+
   '<tr><td>zero-point energy E₀ (Morse)</td><td>'+n0(zpe*CM)+' cm⁻¹ = '+fmt(zpe*KJ,2)+' kJ/mol</td></tr>'+
   '<tr><td>the same in the harmonic approximation, <span class=fr><span>ω</span><span>2</span></span></td><td>'+n0(zh*CM)+' cm⁻¹</td></tr>'+
   '<tr><td>D<sub>e</sub> — well depth</td><td>'+fmt(DE*EV,3)+' eV</td></tr>'+
   '<tr><td>D<sub>0</sub> = D<sub>e</sub> − E₀ — dissociation energy</td><td>'+(p.vmax>=0?fmt((DE-zpe)*EV,3)+' eV = '+fmt((DE-zpe)*KJ,1)+' kJ/mol':'—')+'</td></tr>'+
   '<tr><td>number of bound levels (Morse model)</td><td>'+(p.vmax+1)+'</td></tr></tbody></table>';
  let rows='';for(let k=0;k<Math.min(8,p.vmax);k++)rows+='<tr><td>'+k+' → '+(k+1)+'</td><td>'+n0((p.E[k+1]-p.E[k])*CM)+'</td><td>'+n0(p.w*CM)+'</td></tr>';
  $('lvTab').innerHTML='<table class="mtab"><thead><tr><th>transition v → v + 1</th><th>Morse, cm⁻¹</th><th>harmonic, cm⁻¹</th></tr></thead><tbody>'+rows+'</tbody></table>';
  const kv=D.kv;const mR=D.mR;
  const dRv=D.dR;
  $('st1').innerHTML='<b>Level v = '+kv+'</b>: E = '+n0((harmOnly?p.Eh[kv]:p.E[kv])*CM)+' cm⁻¹ above the well bottom, ⟨R⟩ = '+fmt(mR*BOHR,3)+' Å, ΔR = '+fmt(dRv*BOHR,3)+' Å. '+
    (kv===0?'Even in the ground state the nuclei are not at rest: these are zero-point vibrations, and E₀ > 0.':'As v grows, the anharmonic potential “opens” to the right: ⟨R⟩ grows and the levels crowd toward the dissociation limit.');
  // раздел 2
  const per=D.ts.per,zp=D.ts.zp;
  $('tsTab').innerHTML='<table class="mtab"><thead><tr><th>quantity</th><th>value</th><th>comment</th></tr></thead><tbody>'+
   '<tr><td>mass ratio <span class=fr><span>m<sub>e</sub></span><span>μ</span></span></td><td>'+fmt(D.ts.inv*1e3,3)+'·10⁻³</td><td>about <span class=fr><span>1</span><span>920</span></span> for H₂</td></tr>'+
   '<tr><td>vibrational period <span class=fr><span>2π</span><span>ω</span></span></td><td>'+fmt(per,2)+' fs</td><td>an electron orbit in the H atom takes 0.15 fs; ratio ≈ '+fmt(per/0.152,0)+'</td></tr>'+
   '<tr><td>zero-point amplitude √⟨(R − R<sub>e</sub>)²⟩</td><td>'+fmt(zp,3)+' Å</td><td>'+fmt(100*zp/(RE*BOHR),0)+' % of the 0.741 Å bond length</td></tr>'+
   '<tr><td>(<span class=fr><span>m<sub>e</sub></span><span>μ</span></span>)<sup>1/4</sup></td><td>'+fmt(D.ts.q4,3)+'</td><td>the same order as the relative amplitude</td></tr>'+
   '<tr><td>number of bound levels (Morse model)</td><td>'+(p.vmax+1)+'</td><td>'+(p.vmax<1?'<span class="bad">almost no bound states: zero-point vibrations are comparable to the well depth, the separation of motions fails</span>':'grows as √μ')+'</td></tr></tbody></table>'}
const ig=$('isoG');ISO.forEach(([n,m])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=n;b.onclick=()=>{mu=m*AMU;$('mu').value=Math.log10(mu);v=0;render()};ig.appendChild(b)});
const pg=$('potG');[['morse','Morse'],['harm','harmonic'],['both','both']].forEach(([k,n])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.dataset.p=k;b.textContent=n;b.onclick=()=>{pot=k;render()};pg.appendChild(b)});
$('mu').oninput=e=>{mu=Math.pow(10,+e.target.value);render()};
$('vUp').onclick=()=>{v++;render()};$('vDn').onclick=()=>{v=Math.max(0,v-1);render()};$('prob').onchange=e=>{prob=e.target.checked;render()};
$('mu').value=Math.log10(mu);render();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',render);
