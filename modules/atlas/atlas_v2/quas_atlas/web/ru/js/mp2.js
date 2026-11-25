/* Perturbation theory and MP2 page (Atlas v2).  The H2 corrections, the MPn
   series of water and the MP2/CCSD(T) table come from quas_atlas.core.mp2
   (endpoints mp2.meta, mp2.h2, mp2.series, mp2.tab; data core/data/mp2_series.json);
   this script draws. */
// ---------- страница «Теория возмущений и MP2» (H₂ в STO-3G и ряд MPn для воды посчитаны в PySCF) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('.',',').replace('-','−')};
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const HK=2625.4996;const liveH2=QC.live('mp2.h2'),liveSer=QC.live('mp2.series');
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
// ---------- 1. H₂: E(0), E(1), E(2) ----------
let P=[];
async function h2(){if(!P.length)return;const i=+$('R').value;let Z;try{Z=await liveH2({i})}catch(e){return}const p=Z.p;$('Rv').textContent=fmt(p.R,2)+' Å';
  const svg=$('h2C');svg.innerHTML='';const W=560,H=330,lft=60,rt=14,top=14,bot=40,lo=-1.4,hi=-0.4,R0=P[0].R,R1=P[P.length-1].R;
  const X=R=>lft+(R-R0)/(R1-R0)*(W-lft-rt),Y=v=>top+(hi-Math.max(lo,Math.min(hi,v)))/(hi-lo)*(H-top-bot);
  for(let v=-1.4;v<=-0.39;v+=0.2){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,fmt(v,1))}
  for(let R=0.5;R<=4.01;R+=0.5)el('text',{x:X(R),y:H-20,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,fmt(R,1));
  el('text',{x:(lft+W-rt)/2,y:H-3,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'R, Å');
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,'E, Eₕ');
  const line=(k,c,w,dash)=>{let d='',pen=false;P.forEach(q=>{const v=q[k];if(v<lo-0.02){pen=false;return}d+=(pen?'L':'M')+X(q.R).toFixed(1)+' '+Y(v).toFixed(1);pen=true});el('path',{d,fill:'none',stroke:tok(c),'stroke-width':w,'stroke-dasharray':dash||''},svg)};
  line('HF','--warn',2.4,'7 5');line('MP2','--mp2',2.6);line('FCI','--accent',2.2,'4 3');
  el('line',{x1:X(p.R),x2:X(p.R),y1:top,y2:H-bot,stroke:tok('--muted'),'stroke-dasharray':'2 3'},svg);
  [['HF','--warn'],['MP2','--mp2'],['FCI','--accent']].forEach(([k,c])=>{if(p[k]>=lo)el('circle',{cx:X(p.R),cy:Y(p[k]),r:4.5,fill:tok(c)},svg)});
  let ly=top+14;[['Хартри–Фок','--warn','7 5'],['MP2','--mp2',''],['точное решение (полное КВ)','--accent','4 3']].forEach(([l,c,d])=>{const x=W-rt-200;el('line',{x1:x,x2:x+22,y1:ly-4,y2:ly-4,stroke:tok(c),'stroke-width':2.4,'stroke-dasharray':d},svg);el('text',{x:x+28,y:ly,'font-size':12,fill:tok('--ink')},svg,l);ly+=17});
  const e0=Z.e0,e1=Z.e1,e2=Z.e2,de=Z.de,ec=Z.ec;
  $('h2M').innerHTML='<div class="t">Поправки по порядкам, Eₕ</div><div class="kvt"><span>E<sup>(0)</sup> = 2ε<sub>g</sub></span><b>'+fmt(e0,4)+'</b><span>E<sup>(1)</sup></span><b>'+fmt(e1,4)+'</b><span>E<sup>(0)</sup> + E<sup>(1)</sup> + V<sub>NN</sub> = E<sub>HF</sub></span><b>'+fmt(p.HF,4)+'</b><span>ε<sub>u</sub> − ε<sub>g</sub></span><b>'+fmt(de,4)+'</b><span>K</span><b>'+fmt(p.K,4)+'</b><span>E<sup>(2)</sup> = −K² / 2(ε<sub>u</sub> − ε<sub>g</sub>)</span><b>'+fmt(e2,4)+'</b><span>точная корреляционная энергия</span><b>'+fmt(ec,4)+'</b><span>MP2 / точная</span><b>'+fmt(Z.pc,0)+' %</b></div>';
  const pc=Z.pc;
  $('h2N').innerHTML=pc<100?`Щель ε<sub>u</sub> − ε<sub>g</sub> = ${fmt(de,2)} Eₕ, и MP2 даёт ${fmt(pc,0)} % корреляционной энергии; остальное приходит в высших порядках. В минимальном базисе у H₂ есть единственное возбуждение, поэтому доля MP2 здесь заметно меньше, чем у реальных молекул в хороших базисах (раздел 3).`:
    `Связь растянута: щель уменьшилась до ${fmt(de,2)} Eₕ, а она стоит в знаменателе E<sup>(2)</sup>. MP2 даёт уже ${fmt(pc,0)} % корреляции — проскакивает ниже точной энергии на ${fmt(Z.dmf,0)} кДж/моль. При полном разрыве щель стремится к нулю, и поправка второго порядка неограниченно растёт: теория возмущений от одного определителя здесь непригодна (см. страницу о CASSCF).`}
$('R').oninput=h2;
// ---------- 2. ряд MPn для воды ----------
const GL=['R<sub>e</sub>','1,5 R<sub>e</sub>','2 R<sub>e</sub>'];let g=0;
chips($('geoG'),GL,g,i=>{g=i;mark($('geoG'),i);ser()});
async function ser(){let s;try{s=await liveSer({g})}catch(e){return}const L=s.L,n=+$('ord').value;$('ordV').textContent='MP'+n;
  const svg=$('serC');svg.innerHTML='';const W=560,H=330,lft=62,rt=14,top=14,bot=40,lo=-3,hi=3;
  const X=k=>lft+(k-2)/(L.length-1)*(W-lft-rt),Y=v=>top+(hi-Math.max(lo,Math.min(hi,v)))/(hi-lo)*(H-top-bot);
  for(let v=lo;v<=hi;v++){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,'10'+String(v).replace('-','⁻').replace(/\d/g,c=>'⁰¹²³⁴⁵⁶⁷⁸⁹'[+c]))}
  [2,5,10,15,20,25].filter(k=>k<=L.length+1).forEach(k=>el('text',{x:X(k),y:H-20,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,k));
  el('text',{x:(lft+W-rt)/2,y:H-3,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'порядок n');
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,'|ошибка MPn|, мEₕ');
  const lg=v=>Math.log10(Math.max(Math.abs(v),1e-6));
  let d='';L.forEach((q,i)=>d+=(i?'L':'M')+X(q.n).toFixed(1)+' '+Y(lg(q.err)).toFixed(1));el('path',{d,fill:'none',stroke:tok('--muted'),'stroke-width':1.2},svg);
  L.forEach(q=>el('circle',{cx:X(q.n),cy:Y(lg(q.err)),r:q.n===n?6.5:4,fill:tok(q.err>0?'--accent':'--warn'),stroke:q.n===n?tok('--ink'):'none','stroke-width':1.5},svg));
  {let x=lft+10,y=top+14;[['--accent','выше точной энергии'],['--warn','ниже точной энергии']].forEach(([c,l])=>{el('circle',{cx:x,cy:y-4,r:4.5,fill:tok(c)},svg);el('text',{x:x+10,y,'font-size':12,fill:tok('--ink')},svg,l);y+=17})}
  const rows=[2,3,4,5,10,15,20,25].filter(k=>k<=L.length+1);if(!rows.includes(n))rows.push(n);rows.sort((a,b)=>a-b);
  $('serT').innerHTML='<table class="mtab"><thead><tr><th>n</th><th>E<sup>(n)</sup>, мEₕ</th><th>MPn − полное КВ, мEₕ</th></tr></thead><tbody>'+rows.map(k=>{const q=L[k-2];return '<tr'+(k===n?' class="hot"':'')+'><td>'+k+'</td><td>'+fmt(q.e*1000,3)+'</td><td>'+fmt(q.err,3)+'</td></tr>'}).join('')+'</tbody></table><p class="hint">E(HF) = '+fmt(s.HF,5)+', E(полное КВ) = '+fmt(s.FCI,5)+' Eₕ</p>';
  const q=L[n-2],last=L[L.length-1];
  $('serN').innerHTML=(g===0?`При равновесной геометрии ряд быстро сходится: ошибка MP2 — ${fmt(L[0].err,1)} мEₕ, MP4 — ${fmt(L[2].err,2)}, к 12-му порядку — меньше 0,001 мEₕ. Почти вся корреляция приходит во втором порядке.`:
    g===1?`При полуторной длине связей ряд сходится медленнее и неравномерно: MP3 (${fmt(L[1].err,1)} мEₕ) хуже MP2 (${fmt(L[0].err,1)}), и только к 10-му порядку ошибка падает ниже 0,1 мEₕ. Сейчас MP${n}: ${fmt(q.err,3)} мEₕ.`:
    `При двойной длине связей ряд колеблется: MP3 (${fmt(L[1].err,0)} мEₕ) хуже MP2 (${fmt(L[0].err,0)}), MP4 и MP5 почти одинаковы, с 9-го порядка сумма проскакивает ниже точной энергии, и даже к 25-му порядку ошибка ещё ${fmt(last.err,3)} мEₕ. Здесь ряд всё же сходится, но в базисах с диффузными функциями ряд Мёллера–Плессета для тех же молекул может расходиться (Olsen и соавт., 1996). Поэтому «MP3 лучше MP2, а MP4 ещё лучше» — не правило.`)}
$('ord').oninput=ser;
// ---------- 3. доля корреляции ----------
const MN={H2O:'H₂O',NH3:'NH₃',CH4:'CH₄',HF:'HF',N2:'N₂',CO:'CO',C2H4:'C₂H₄',F2:'F₂',O3:'O₃'};
async function tab(){let Z;try{Z=await QC.api('mp2.tab',{})}catch(e){return}const T=Z.rows;const svg=$('tabC');svg.innerHTML='';const W=960,H=300,lft=60,rt=16,top=16,bot=40,bw=(W-lft-rt)/T.length,hi=120;
  const Y=v=>top+(1-v/hi)*(H-top-bot);
  for(let v=0;v<=hi;v+=20){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok(v===100?'--muted':'--line'),'stroke-dasharray':v===100?'4 3':''},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,v+' %')}
  T.forEach((r,i)=>{const pc=r.pc,x=lft+i*bw;el('rect',{x:x+bw*.2,y:Y(Math.min(pc,hi)),width:bw*.6,height:Y(0)-Y(Math.min(pc,hi)),fill:tok(pc>100?'--warn':'--mp2'),rx:2},svg);
    el('text',{x:x+bw/2,y:Y(Math.min(pc,hi))-6,'text-anchor':'middle','font-size':12,fill:tok('--ink')},svg,fmt(pc,0)+' %');
    el('text',{x:x+bw/2,y:H-20,'text-anchor':'middle','font-size':13,fill:tok('--ink')},svg,MN[r.m]||r.m)});
  el('text',{x:(lft+W-rt)/2,y:H-3,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'корреляционная энергия MP2 в процентах от CCSD(T), cc-pVDZ');
  $('tabT').innerHTML='<table class="mtab"><thead><tr><th>молекула</th><th>MP2, мEₕ</th><th>CCSD, мEₕ</th><th>CCSD(T), мEₕ</th><th>MP2 / CCSD(T)</th></tr></thead><tbody>'+T.map(r=>'<tr><td>'+(MN[r.m]||r.m)+'</td><td>'+fmt(r.MP2*1000,1)+'</td><td>'+fmt(r.CCSD*1000,1)+'</td><td>'+fmt(r.CCSDT*1000,1)+'</td><td>'+fmt(r.pc,1)+' %</td></tr>').join('')+'</tbody></table>';
  const pcs=T.map(r=>r.pc),mLo={m:Z.mLo},mHi={m:Z.mHi};
  $('tabN').innerHTML=`MP2 даёт ${fmt(Math.min(...pcs),0)}–${fmt(Math.max(...pcs),0)} % корреляционной энергии CCSD(T): меньше всего у ${MN[mLo.m]}, больше всего у ${MN[mHi.m]}. Недостающая часть — в основном вклады высших порядков (тройные возбуждения и связь пар между собой), поэтому MP2 хорош для геометрий и межмолекулярных взаимодействий, но для энергий реакций его ошибка может быть несколько ккал/моль.`}
// размерная согласованность (H₂)ₙ — числа идут в карточку
function all(){h2();ser();tab()}
QC.api('mp2.meta',{}).then(M=>{P=M.h2;$('R').max=P.length-1;all()}).catch(()=>{});
new MutationObserver(all).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
