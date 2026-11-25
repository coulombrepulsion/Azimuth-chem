/* Equilibrium page (Atlas v2).  Reaction data, RRHO thermochemistry, dH°,
   dS°, dG°, K, the temperature chart, the sensitivity estimate and the
   own-reaction calculation come from quas_atlas.core.equilibrium
   (eq.reactions, eq.state, eq.sens, eq.chart, eq.example, eq.custom). */

const ruN=(n,a,b,c)=>{n=Math.abs(Math.round(n));const m=n%10,h=n%100;return m===1&&h!==11?a:m>=2&&m<=4&&(h<12||h>14)?b:c};
// ---------- страница «Равновесие: от энергии к константе» ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const SUP=s=>String(s).split('').map(c=>c==='-'?'⁻':'⁰¹²³⁴⁵⁶⁷⁸⁹'[+c]).join('');
function sci(x){if(!isFinite(x))return '—';if(x===0)return '0';const e=Math.floor(Math.log10(Math.abs(x)));if(e>=-2&&e<4)return fmt(x,e>=2?0:e>=0?2:3);const m=x/Math.pow(10,e);return fmt(m,2)+'·10'+SUP(e)}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const P0=1e5;
const RXN=['ammonia synthesis','water–gas shift','steam reforming of methane','combustion of hydrogen'];let RX=null;
const Q={rx:0,T:298.15,q:0};
function coefStr(v){return v===1?'':String(v)}
function rxnHTML(r){const L=r.s.filter(x=>x[1]<0).map(([s,v])=>coefStr(-v)+s),Rr=r.s.filter(x=>x[1]>0).map(([s,v])=>coefStr(v)+s);return L.join(' + ')+' ⇌ '+Rr.join(' + ')}
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
chips($('rxG'),RXN,0,i=>{Q.rx=i;mark($('rxG'),i);draw()});
chips($('qG'),['ΔG°, ΔH° and −TΔS°','lg K'],0,i=>{Q.q=i;mark($('qG'),i);chart()});
$('T').value=298;$('T').oninput=()=>{Q.T=+$('T').value;draw()};$('bT298').textContent=fmt(298.15,2)+' K';$('bT298').onclick=()=>{Q.T=298.15;$('T').value=298;draw()};
$('dG').oninput=sens;
const liveQ=QC.live('eq.state'),liveC=QC.live('eq.chart'),liveS=QC.live('eq.sens');
async function draw(){if(!RX)return;const r=RX[Q.rx],T=Q.T;let Z;try{Z=await liveQ({rx:Q.rx,T})}catch(e){return}const c=Z.c;$('Tv').textContent=fmt(T,T===298.15?2:0)+' K';$('rxn').textContent=rxnHTML(r);
  $('rxInfo').textContent='Δn(gas) = '+(c.dn>0?'+':'')+String(c.dn).replace('-','−')+': the constant K is written in terms of pressures in bar, K = Π(p/p°)^ν, p° = 1 bar. The electronic reaction energy is back-calculated from the tabulated ΔH°(298) — these are the numbers a very accurate calculation would give.';
  const st=[['ΔE<sub>el</sub> — electronic energy',c.dEel,'--nu'],['+ ΔZPE — zero-point vibrations',c.dZPE,'--el'],['= ΔH°(0 K)',c.dH0,'--ink',1],['+ thermal correction ΔH(T) − ΔH(0)',c.dHth,'--virt'],['= ΔH°(T)',c.dH,'--ink',1],['− TΔS°',Z.mTdS,'--ok'],['= ΔG°(T)',c.dG,'--accent',1]];
  const mx=Math.max(...st.map(x=>Math.abs(x[1])));
  $('steps').innerHTML=st.map(([n,v,col,tot])=>{const w=Math.abs(v)/mx*50,l=v<0?50-w:50;return '<span class="'+(tot?'tot':'')+'">'+n+'</span><span class="bar"><i style="left:'+l+'%;width:'+w+'%;background:'+tok(col)+'"></i><i style="left:50%;width:1px;background:'+tok('--muted')+'"></i></span><b>'+fmt(v,1)+'</b>'}).join('');
  const K=Z.K,card=(t,v,s)=>'<div class="card"><span class="t">'+t+'</span><b>'+v+'</b>'+(s?'<small>'+s+'</small>':'')+'</div>';
  $('cards').innerHTML=card('ΔH°(T)',fmt(c.dH,1)+' kJ/mol')+card('ΔS°(T)',fmt(c.dS,1)+' J/(mol·K)')+card('ΔG°(T)',fmt(c.dG,1)+' kJ/mol')+card('K(T)',sci(K),'lg K = '+fmt(Z.lgK,2));
  const rb=$('refBox');if(Math.abs(T-298.15)<0.01){const g=Z.g298;rb.className='ref';rb.innerHTML='NIST-JANAF tables: ΔG°(298.15 K) = <b>'+fmt(g,2)+'</b> kJ/mol; calculated from frequencies '+fmt(c.dG,2)+', difference '+fmt(c.dG-g,2)+' kJ/mol.'}
  else{rb.className='ref off';rb.textContent='The comparison with the tables is made at 298.15 K.'}
  chart();sens()}
async function chart(){if(!RX)return;let Cz;try{Cz=await liveC({rx:Q.rx})}catch(e){return}const svg=$('chart');svg.innerHTML='';const r=RX[Q.rx],W=960,Hh=330,L=64,Rr=16,Tp=18,B=38,T0=200,T1=1500;const pts=Cz.pts;
  const ser=Q.q?[['lg K',p=>p.lgK,'--accent']]:[['ΔG°',p=>p.dG,'--accent'],['ΔH°',p=>p.dH,'--virt'],['−TΔS°',p=>p.mTdS,'--ok']];
  let lo=0,hi=0;pts.forEach(([T,p])=>ser.forEach(([,f])=>{const v=f(p,T);lo=Math.min(lo,v);hi=Math.max(hi,v)}));const pad=(hi-lo)*0.05||1;lo-=pad;hi+=pad;
  const X=t=>L+(t-T0)/(T1-T0)*(W-L-Rr),Y=v=>Tp+(hi-v)/(hi-lo)*(Hh-B-Tp);const ax=tok('--line');
  const step=(()=>{const s=(hi-lo)/6,p=Math.pow(10,Math.floor(Math.log10(s)));return [1,2,5,10].map(k=>k*p).find(k=>k>=s)})();
  for(let v=Math.ceil(lo/step)*step;v<=hi;v+=step){el('line',{x1:L,x2:W-Rr,y1:Y(v),y2:Y(v),stroke:Math.abs(v)<1e-9?tok('--muted'):ax,'stroke-width':1},svg);el('text',{x:L-6,y:Y(v)+4,'text-anchor':'end'},svg,fmt(v,step<1?1:0))}
  for(let t=300;t<=1500;t+=200)el('text',{x:X(t),y:Hh-B+16,'text-anchor':'middle'},svg,String(t));
  el('text',{x:(L+W-Rr)/2,y:Hh-4,'text-anchor':'middle'},svg,'T, K');el('text',{x:8,y:Tp-4},svg,Q.q?'lg K':'kJ/mol');
  ser.forEach(([,f,c],i)=>el('path',{d:pts.map(([T,p],j)=>(j?'L':'M')+X(T).toFixed(1)+' '+Y(f(p,T)).toFixed(1)).join(''),fill:'none',stroke:tok(c),'stroke-width':i?1.8:2.6},svg));
  el('line',{x1:X(Q.T),x2:X(Q.T),y1:Tp,y2:Hh-B,stroke:tok('--muted'),'stroke-dasharray':'4 4'},svg);
  $('leg').innerHTML=ser.map(([n,,c])=>'<span><span class="sw" style="border-color:'+tok(c)+'"></span>'+n+'</span>').join('');
  const Tx=Cz.Tx;
  $('chartNote').textContent=(Tx?'ΔG° changes sign at about '+fmt(Tx,0)+' K; above this temperature '+(pts[0][1].dG<0?'K < 1':'K > 1')+'. ':'ΔG° does not change sign in this range. ')+'The slope of lg K versus 1/T is set by ΔH° (the van ’t Hoff equation): for ΔH° < 0, heating shifts the equilibrium to the left.'}
async function sens(){const d=+$('dG').value,T=Q.T;let Z;try{Z=await liveS({d,T})}catch(e){return}const f=Z.f;$('dGv').textContent=fmt(d,1);
  const k10=Z.k10;
  $('sens').innerHTML='An error of '+fmt(d,1)+' kJ/mol in ΔG° at '+fmt(T,0)+' K changes K by a factor of <b>'+sci(Z.fmax)+'</b> '+(/,/.test(sci(Math.max(f,1/f)))?'times':ruN(Math.max(f,1/f),'times','times','times'))+' ('+(f<1?'K underestimated':'K overestimated')+'). A tenfold change in K corresponds to '+fmt(k10,2)+' kJ/mol. A chemical accuracy of 4 kJ/mol at 298 K means K is known only “to within a factor of five”, not to within percent.'}
// ---------- своя реакция ----------
function rowsInit(n){const tb=$('cRows');tb.innerHTML='';for(let i=0;i<n;i++){const tr=document.createElement('tr');tr.innerHTML='<td><input aria-label="participant"></td><td><input inputmode="decimal" aria-label="coefficient"></td><td><input inputmode="decimal" aria-label="E"></td><td><input inputmode="decimal" aria-label="G"></td>';tb.appendChild(tr)}}
rowsInit(5);
const num=s=>Number(String(s).trim().replace(',','.').replace('−','-'));
$('bEx').onclick=async()=>{let X;try{X=await QC.api('eq.example',{})}catch(e){return}
  const tr=[...$('cRows').children];X.rows.forEach(([s,v,e,g],i)=>{const inp=tr[i].querySelectorAll('input');inp[0].value=s;inp[1].value=String(v);inp[2].value=e.toFixed(6);inp[3].value=g.toFixed(6)});
  for(let i=X.rows.length;i<tr.length;i++)tr[i].querySelectorAll('input').forEach(x=>x.value='');$('cT').value='298.15';
  $('cMsg').textContent='Model numbers: the electronic energies are chosen to reproduce the tabulated ΔH°, and the G corrections come from the frequency calculation on this page. Click “Calculate”.'};
$('bCalc').onclick=async()=>{const T=num($('cT').value),msg=$('cMsg');if(!(T>0)){msg.textContent='Enter the temperature.';return}
  const rows=[];let n=0,bad=false;[...$('cRows').children].forEach(tr=>{const v=[...tr.querySelectorAll('input')].map(x=>x.value);if(!v[1]&&!v[2]&&!v[3])return;const k=num(v[1]),e=num(v[2]),g=num(v[3]);if(!isFinite(k)||!isFinite(e)||!isFinite(g)||k===0){bad=true;return}n++;rows.push([k,e,g])});
  if(bad||n<2){msg.textContent='At least two participants are needed; the coefficient, E and G must be numbers, and the coefficient must not be zero.';return}
  let Z;try{Z=await QC.api('eq.custom',{T,rows})}catch(e){return}const dE=Z.dE,dG=Z.dG,dn=Z.dn,dEk=Z.dEk,dGk=Z.dGk,K=Z.K;
  msg.innerHTML='ΔE<sub>el</sub> = '+fmt(dEk,1)+' kJ/mol; ΔG° = '+fmt(dGk,1)+' kJ/mol ('+fmt(dG,6)+' E<sub>h</sub>); K = <b>'+sci(K)+'</b> at '+fmt(T,2)+' K'+(Math.abs(dn)>1e-9?' (Δn = '+fmt(dn,0)+', pressures in bar).':'.')+(Math.abs(dE)>1?' Warning: |ΔE| exceeds 1 E<sub>h</sub> — check that the atoms balance.':'')};
QC.api('eq.reactions',{}).then(S=>{RX=S.map((s,i)=>({n:RXN[i],s}));draw()}).catch(()=>{});matchMedia('(prefers-color-scheme: dark)').addEventListener('change',draw);
