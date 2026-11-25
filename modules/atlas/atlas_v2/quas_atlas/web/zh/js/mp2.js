/* Perturbation theory and MP2 page (Atlas v2).  The H2 corrections, the MPn
   series of water and the MP2/CCSD(T) table come from quas_atlas.core.mp2
   (endpoints mp2.meta, mp2.h2, mp2.series, mp2.tab; data core/data/mp2_series.json);
   this script draws. */
// ---------- страница «Теория возмущений и MP2» (H₂ в STO-3G и ряд MPn для воды посчитаны в PySCF) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
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
  let ly=top+14;[['哈特里–福克','--warn','7 5'],['MP2','--mp2',''],['精确解（完全 CI）','--accent','4 3']].forEach(([l,c,d])=>{const x=W-rt-200;el('line',{x1:x,x2:x+22,y1:ly-4,y2:ly-4,stroke:tok(c),'stroke-width':2.4,'stroke-dasharray':d},svg);el('text',{x:x+28,y:ly,'font-size':12,fill:tok('--ink')},svg,l);ly+=17});
  const e0=Z.e0,e1=Z.e1,e2=Z.e2,de=Z.de,ec=Z.ec;
  $('h2M').innerHTML='<div class="t">逐阶修正，Eₕ</div><div class="kvt"><span>E<sup>(0)</sup> = 2ε<sub>g</sub></span><b>'+fmt(e0,4)+'</b><span>E<sup>(1)</sup></span><b>'+fmt(e1,4)+'</b><span>E<sup>(0)</sup> + E<sup>(1)</sup> + V<sub>NN</sub> = E<sub>HF</sub></span><b>'+fmt(p.HF,4)+'</b><span>ε<sub>u</sub> − ε<sub>g</sub></span><b>'+fmt(de,4)+'</b><span>K</span><b>'+fmt(p.K,4)+'</b><span>E<sup>(2)</sup> = −K² / 2(ε<sub>u</sub> − ε<sub>g</sub>)</span><b>'+fmt(e2,4)+'</b><span>精确相关能</span><b>'+fmt(ec,4)+'</b><span>MP2 / 精确</span><b>'+fmt(Z.pc,0)+' %</b></div>';
  const pc=Z.pc;
  $('h2N').innerHTML=pc<100?`能隙 ε<sub>u</sub> − ε<sub>g</sub> = ${fmt(de,2)} Eₕ，MP2 给出 ${fmt(pc,0)} % 的相关能；其余来自更高阶。在最小基组中 H₂ 只有一个激发，因此这里 MP2 的比例明显低于好基组中的真实分子（第 3 节）。`:
    `键被拉长：能隙减小到 ${fmt(de,2)} Eₕ，而它位于 E<sup>(2)</sup> 的分母中。MP2 已给出 ${fmt(pc,0)} % 的相关能——越过精确能量，低了 ${fmt(Z.dmf,0)} kJ/mol。完全断键时能隙趋于零，二阶修正无限增大：从单个行列式出发的微扰理论在这里不可用（见 CASSCF 一页）。`}
$('R').oninput=h2;
// ---------- 2. ряд MPn для воды ----------
const GL=['R<sub>e</sub>','1,5 R<sub>e</sub>','2 R<sub>e</sub>'];let g=0;
chips($('geoG'),GL,g,i=>{g=i;mark($('geoG'),i);ser()});
async function ser(){let s;try{s=await liveSer({g})}catch(e){return}const L=s.L,n=+$('ord').value;$('ordV').textContent='MP'+n;
  const svg=$('serC');svg.innerHTML='';const W=560,H=330,lft=62,rt=14,top=14,bot=40,lo=-3,hi=3;
  const X=k=>lft+(k-2)/(L.length-1)*(W-lft-rt),Y=v=>top+(hi-Math.max(lo,Math.min(hi,v)))/(hi-lo)*(H-top-bot);
  for(let v=lo;v<=hi;v++){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,'10'+String(v).replace('-','⁻').replace(/\d/g,c=>'⁰¹²³⁴⁵⁶⁷⁸⁹'[+c]))}
  [2,5,10,15,20,25].filter(k=>k<=L.length+1).forEach(k=>el('text',{x:X(k),y:H-20,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,k));
  el('text',{x:(lft+W-rt)/2,y:H-3,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'阶数 n');
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,'|MPn 误差|，mEₕ');
  const lg=v=>Math.log10(Math.max(Math.abs(v),1e-6));
  let d='';L.forEach((q,i)=>d+=(i?'L':'M')+X(q.n).toFixed(1)+' '+Y(lg(q.err)).toFixed(1));el('path',{d,fill:'none',stroke:tok('--muted'),'stroke-width':1.2},svg);
  L.forEach(q=>el('circle',{cx:X(q.n),cy:Y(lg(q.err)),r:q.n===n?6.5:4,fill:tok(q.err>0?'--accent':'--warn'),stroke:q.n===n?tok('--ink'):'none','stroke-width':1.5},svg));
  {let x=lft+10,y=top+14;[['--accent','高于精确能量'],['--warn','低于精确能量']].forEach(([c,l])=>{el('circle',{cx:x,cy:y-4,r:4.5,fill:tok(c)},svg);el('text',{x:x+10,y,'font-size':12,fill:tok('--ink')},svg,l);y+=17})}
  const rows=[2,3,4,5,10,15,20,25].filter(k=>k<=L.length+1);if(!rows.includes(n))rows.push(n);rows.sort((a,b)=>a-b);
  $('serT').innerHTML='<table class="mtab"><thead><tr><th>n</th><th>E<sup>(n)</sup>，mEₕ</th><th>MPn − 完全 CI，mEₕ</th></tr></thead><tbody>'+rows.map(k=>{const q=L[k-2];return '<tr'+(k===n?' class="hot"':'')+'><td>'+k+'</td><td>'+fmt(q.e*1000,3)+'</td><td>'+fmt(q.err,3)+'</td></tr>'}).join('')+'</tbody></table><p class="hint">E(HF) = '+fmt(s.HF,5)+'，E(完全 CI) = '+fmt(s.FCI,5)+' Eₕ</p>';
  const q=L[n-2],last=L[L.length-1];
  $('serN').innerHTML=(g===0?`在平衡几何构型下级数收敛很快：MP2 误差为 ${fmt(L[0].err,1)} mEₕ，MP4 为 ${fmt(L[2].err,2)}，到第 12 阶已小于 0.001 mEₕ。几乎全部相关能来自二阶。`:
    g===1?`键长为 1.5 倍时级数收敛更慢且不均匀：MP3（${fmt(L[1].err,1)} mEₕ）比 MP2（${fmt(L[0].err,1)}）更差，直到第 10 阶误差才降到 0.1 mEₕ 以下。当前 MP${n}：${fmt(q.err,3)} mEₕ。`:
    `键长加倍时级数振荡：MP3（${fmt(L[1].err,0)} mEₕ）比 MP2（${fmt(L[0].err,0)}）更差，MP4 与 MP5 几乎相同，从第 9 阶起部分和越过精确能量向下，到第 25 阶误差仍有 ${fmt(last.err,3)} mEₕ。这里级数终究收敛，但在含弥散函数的基组中，同样分子的 Møller–Plesset 级数可能发散（Olsen 等，1996）。因此“MP3 好于 MP2，MP4 更好”并不是规律。`)}
$('ord').oninput=ser;
// ---------- 3. доля корреляции ----------
const MN={H2O:'H₂O',NH3:'NH₃',CH4:'CH₄',HF:'HF',N2:'N₂',CO:'CO',C2H4:'C₂H₄',F2:'F₂',O3:'O₃'};
async function tab(){let Z;try{Z=await QC.api('mp2.tab',{})}catch(e){return}const T=Z.rows;const svg=$('tabC');svg.innerHTML='';const W=960,H=300,lft=60,rt=16,top=16,bot=40,bw=(W-lft-rt)/T.length,hi=120;
  const Y=v=>top+(1-v/hi)*(H-top-bot);
  for(let v=0;v<=hi;v+=20){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok(v===100?'--muted':'--line'),'stroke-dasharray':v===100?'4 3':''},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,v+' %')}
  T.forEach((r,i)=>{const pc=r.pc,x=lft+i*bw;el('rect',{x:x+bw*.2,y:Y(Math.min(pc,hi)),width:bw*.6,height:Y(0)-Y(Math.min(pc,hi)),fill:tok(pc>100?'--warn':'--mp2'),rx:2},svg);
    el('text',{x:x+bw/2,y:Y(Math.min(pc,hi))-6,'text-anchor':'middle','font-size':12,fill:tok('--ink')},svg,fmt(pc,0)+' %');
    el('text',{x:x+bw/2,y:H-20,'text-anchor':'middle','font-size':13,fill:tok('--ink')},svg,MN[r.m]||r.m)});
  el('text',{x:(lft+W-rt)/2,y:H-3,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'MP2 相关能占 CCSD(T) 的百分比，cc-pVDZ');
  $('tabT').innerHTML='<table class="mtab"><thead><tr><th>分子</th><th>MP2，mEₕ</th><th>CCSD，mEₕ</th><th>CCSD(T)，mEₕ</th><th>MP2 / CCSD(T)</th></tr></thead><tbody>'+T.map(r=>'<tr><td>'+(MN[r.m]||r.m)+'</td><td>'+fmt(r.MP2*1000,1)+'</td><td>'+fmt(r.CCSD*1000,1)+'</td><td>'+fmt(r.CCSDT*1000,1)+'</td><td>'+fmt(r.pc,1)+' %</td></tr>').join('')+'</tbody></table>';
  const pcs=T.map(r=>r.pc),mLo={m:Z.mLo},mHi={m:Z.mHi};
  $('tabN').innerHTML=`MP2 给出 CCSD(T) 相关能的 ${fmt(Math.min(...pcs),0)}–${fmt(Math.max(...pcs),0)} %：${MN[mLo.m]} 最少，${MN[mHi.m]} 最多。缺少的部分主要是更高阶的贡献（三重激发以及电子对之间的耦合），因此 MP2 适合几何构型和分子间相互作用，但对反应能的误差可能达到几 kcal/mol。`}
// размерная согласованность (H₂)ₙ — числа идут в карточку
function all(){h2();ser();tab()}
QC.api('mp2.meta',{}).then(M=>{P=M.h2;$('R').max=P.length-1;all()}).catch(()=>{});
new MutationObserver(all).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
