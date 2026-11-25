/* Diatomic MO page (Atlas v2).  The extended-Hueckel MOs, names, occupations,
   bond orders, terms and the species table come from quas_atlas.core.diatomics
   (dia.spec, dia.build); this script draws. */
const ELS=['H','He','Li','Be','B','C','N','O','F','Ne'];
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt=(x,d=1)=>x.toFixed(d).replace('-','−');
const FR=(a,b)=>'<span class=fr><span>'+a+'</span><span>'+b+'</span></span>';
const SUP=s=>String(s).replace(/[0-9+−-]/g,c=>({'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹','+':'⁺','−':'⁻','-':'⁻'})[c]);
const SUB=s=>String(s).replace(/\d/g,d=>'₀₁₂₃₄₅₆₇₈₉'[d]);
const isH=X=>X==='H'||X==='He';
let SPEC=[];
const HOM=12;
function fname(A,B,q){const f=A===B?A+'₂':A+B;return f+(q?(Math.abs(q)>1?SUP(Math.abs(q)):'')+(q>0?'⁺':'⁻'):'')}
let A='N',B='N',Q=0,mix=true,sel=-1,cur=null;
const TMULT=m=>m+' 重态（多个开壳层）';
const liveB=QC.live('dia.build');
const build=(A,B,Q,mix)=>QC.api('dia.build',{A,B,Q,mix}).then(R=>{if(R.term==null)R.term=TMULT(R.termMult);return R});
const bo2s=b=>Number.isInteger(b)?String(b):FR(Math.round(b*2),2)+' = '+fmt(b,1);
// ---------- рисование диаграммы ----------
function arrows(p,x,y,n,maxn){// n электронов на одном уровне (0..2)
  const up=(cx)=>el('path',{d:`M${cx},${y+9} L${cx},${y-9} M${cx-4},${y-4} L${cx},${y-10} L${cx+4},${y-4}`,stroke:tok('--ink'),'stroke-width':1.8,fill:'none'},p);
  const dn=(cx)=>el('path',{d:`M${cx},${y-9} L${cx},${y+9} M${cx-4},${y+4} L${cx},${y+10} L${cx+4},${y+4}`,stroke:tok('--ink'),'stroke-width':1.8,fill:'none'},p);
  if(n>=1)up(x-(n===2?5:0));if(n===2)dn(x+5)}
function piArr(o){// распределение электронов по двум вырожденным уровням (правило Хунда)
  const n=o.occ;return n<=2?[Math.min(1,n),n>=2?1:0]:[n===3?2:2,n===3?1:2]}
function aoArr(X,nE){// электроны на АО атома: [s, p]
  if(isH(X))return [Math.min(2,nE),0];return [Math.min(2,nE),Math.max(0,nE-2)]}
function draw(){const R=cur,sv=$('dia');sv.innerHTML='';const W=520,H=520,T=34,Bm=24;
  const aoA=R.aoA,aoB=R.aoB;const allE=R.M.map(o=>o.E).concat(aoA,aoB);
  const lo=Math.min(...allE)-1.5;const hiC=Math.max(...aoA,...aoB,...R.M.filter(o=>o.occ>0).map(o=>o.E))+4;const hi=Math.min(Math.max(...allE)+1,Math.max(hiC,lo+8));
  const sy=e=>T+(H-T-Bm)*(1-(Math.min(e,hi)-lo)/(hi-lo));
  const xA=105,xB=440,xM=272,ink=tok('--ink'),mu=tok('--muted'),acc=tok('--accent');
  el('text',{x:xA,y:18,'text-anchor':'middle','font-size':15,'font-weight':600,fill:ink},sv,A);el('text',{x:xB,y:18,'text-anchor':'middle','font-size':15,'font-weight':600,fill:ink},sv,B);
  el('text',{x:xM,y:18,'text-anchor':'middle','font-size':15,'font-weight':600,fill:ink},sv,fname(A,B,Q));
  el('line',{x1:14,y1:T,x2:14,y2:H-Bm,stroke:mu},sv);el('text',{x:18,y:T-6,'font-size':11,fill:mu},sv,'E, eV');
  for(let e=Math.ceil(lo/5)*5;e<=hi;e+=5){el('line',{x1:10,y1:sy(e),x2:18,y2:sy(e),stroke:mu},sv);el('text',{x:20,y:sy(e)+4,'font-size':10,fill:mu},sv,fmt(e,0))}
  // АО и электроны атомов (нейтральные атомы; заряд показан на молекуле)
  const ea=R.vA,eb=R.vB;
  const aoPos={};[[A,aoA,xA,ea,0],[B,aoB,xB,eb,1]].forEach(([X,ao,x,ne,at])=>{const [ns,np]=aoArr(X,ne);
    el('line',{x1:x-22,y1:sy(ao[0]),x2:x+22,y2:sy(ao[0]),stroke:ink,'stroke-width':2},sv);el('text',{x:at?x+28:x-28,y:sy(ao[0])+4,'text-anchor':at?'start':'end','font-size':11.5,fill:mu},sv,isH(X)?'1s':'2s');arrows(sv,x,sy(ao[0]),ns);
    aoPos[at+'s']=[at?x-24:x+24,sy(ao[0])];
    if(ao.length>1){const yy=sy(ao[1]);for(let k=-1;k<=1;k++){el('line',{x1:x+k*24-9,y1:yy,x2:x+k*24+9,y2:yy,stroke:ink,'stroke-width':2},sv)}
      el('text',{x:at?x+40:x-40,y:yy+4,'text-anchor':at?'start':'end','font-size':11.5,fill:mu},sv,'2p');
      const pe=[0,0,0];for(let k=0;k<np;k++)pe[k%3]++;pe.forEach((n,k)=>arrows(sv,x+(k-1)*24,yy,n));aoPos[at+'p']=[at?x-34:x+34,yy]}});
  // МО
  R.M.forEach((o,i)=>{const y=sy(o.E),g=el('g',{class:'mvl',tabindex:0,role:'button','aria-label':o.nm},sv);
    const w=(o.E>hi)?1:0;const colr=i===sel?tok('--warn'):ink;
    // соединительные линии к АО с заметным вкладом
    ['s','p'].forEach(t=>[0,1].forEach(at=>{const wgt=o.w[at+t]||0;if(wgt>0.08&&aoPos[at+t]){const [ax,ay]=aoPos[at+t];
      el('line',{x1:ax,y1:ay,x2:at?xM+(o.deg>1?56:32):xM-(o.deg>1?56:32),y2:y,stroke:mu,'stroke-dasharray':'3 3','stroke-width':1,opacity:Math.min(1,0.35+wgt)},sv,null)}}));
    if(o.deg===1){el('line',{class:'lv',x1:xM-30,y1:y,x2:xM+30,y2:y,stroke:colr,'stroke-width':i===sel?3:2.2},g);arrows(g,xM,y,o.occ)}
    else{const pa=piArr(o);[-1,1].forEach((s,k)=>{el('line',{class:'lv',x1:xM+s*28-22,y1:y,x2:xM+s*28+22,y2:y,stroke:colr,'stroke-width':i===sel?3:2.2},g);arrows(g,xM+s*28,y,pa[k])})}
    el('rect',{x:xM-60,y:y-11,width:120,height:22,fill:'transparent'},g);
    const lb=el('text',{x:xM+(o.deg>1?60:36),y:y+4,'font-size':12.5,fill:o.bt>0?tok('--ok'):o.bt<0?tok('--warn'):mu},g,o.nm);
    if(w){el('text',{x:xM-(o.deg>1?60:36),y:y+4,'text-anchor':'end','font-size':11,fill:mu},g,'↑ '+fmt(o.E,1)+' eV')}
    g.onclick=()=>{sel=i;draw();shape()};g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();sel=i;draw();shape()}}});
  if(R.core)el('text',{x:W-6,y:H-6,'text-anchor':'end','font-size':11,fill:mu},sv,'1s 电子（'+(R.core===2?'KK':'K')+'）未画出')}
// ---------- форма и состав выбранной МО ----------
function shape(){const sv=$('shape');sv.innerHTML='';const R=cur;if(sel<0||!R.M[sel]){$('comp').innerHTML='';$('moT').textContent='';/* a hint instead of an empty field */const h=document.createElementNS('http://www.w3.org/2000/svg','text');h.setAttribute('x',210);h.setAttribute('y',90);h.setAttribute('text-anchor','middle');h.setAttribute('font-size',13);h.setAttribute('fill','var(--muted)');h.textContent='点击图中的某个能级，这里会显示该轨道的形状';sv.appendChild(h);return}
  const o=R.M[sel],xa=150,xb=270,y=85,pos=tok('--lp-bg'),neg=tok('--ln-bg'),pl=tok('--lp'),nl=tok('--ln');
  $('moT').innerHTML='MO '+o.num+' = '+o.nm+' · E = '+fmt(o.E,1)+' eV · '+(o.bt>0?'成键':o.bt<0?'反键':'非键');
  el('line',{x1:40,y1:y,x2:380,y2:y,stroke:tok('--line'),'stroke-dasharray':'4 4'},sv);
  const lobe=(cx,cy,dx,dy,r,c)=>{const col=c>0?pos:neg,ln=c>0?pl:nl;el('ellipse',{cx:cx+dx*r,cy:cy+dy*r,rx:dx?r:r*0.62,ry:dy?r:r*0.62,fill:col,stroke:ln,'stroke-width':1.3},sv)};
  o.c.forEach(x=>{const cx=x.at?xb:xa;const a=Math.abs(x.c);if(a<0.06)return;const r=10+34*Math.min(1,a);
    if(x.t==='s'){el('circle',{cx,cy:y,r:r*0.9,fill:x.c>0?pos:neg,stroke:x.c>0?pl:nl,'stroke-width':1.3},sv)}
    else if(o.sym==='σ'){const d=x.at?-1:1;lobe(cx,y,d,0,r,x.c);lobe(cx,y,-d,0,r,-x.c)}
    else{lobe(cx,y,0,-1,r,x.c);lobe(cx,y,0,1,r,-x.c)}});
  [[xa,A],[xb,B]].forEach(([x,X])=>{el('circle',{cx:x,cy:y,r:4,fill:tok('--ink')},sv);el('text',{x,y:160,'text-anchor':'middle','font-size':13,fill:tok('--ink')},sv,X)});
  el('text',{x:410,y:20,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,'蓝：+ · 红：−');
  const parts=[];[0,1].forEach(at=>['s','p'].forEach(t=>{const X=at?B:A;const w=o.w[at+t];if((at+t) in o.w)parts.push([(isH(X)?'1s':t==='s'?'2s':(o.sym==='π'?'2p<sub>x</sub>':'2p<sub>z</sub>'))+' '+X,w])}));
  $('comp').innerHTML=parts.map(([n,w])=>'<div class="vb"><span>'+n+'</span><span class="t"><i style="width:'+(100*w).toFixed(1)+'%;background:var(--accent)"></i></span><b class="val">'+Math.round(100*w)+' %</b></div>').join('')}
// ---------- сводка ----------
function summary(){const R=cur;const occ=R.M.filter(o=>o.occ>0);
  const pre=R.core===2?'(KK) ':R.core===1?'(K) ':'';
  $('cfg').innerHTML=R.neg?'—':pre+occ.map(o=>'('+o.nm+')'+SUP(o.occ)).join(' ')+'<div class="hint" style="font-family:var(--f-body)">'+(R.hom?(R.noneP?'':'1σ<sub>g</sub>² 1σ<sub>u</sub>² ')+occ.map(o=>o.num+SUP(o.occ)).join(' '):(R.core?Array.from({length:R.core},(_,k)=>(k+1)+'σ²').join(' ')+' ':'')+occ.map(o=>o.num+SUP(o.occ)).join(' '))+'</div>';
  const mag=R.unp?'顺磁性':'抗磁性';
  $('sumTab').innerHTML='<table class="mtab"><tbody>'+
    '<tr><td>价电子数</td><td>'+R.nV+'</td></tr>'+
    '<tr><td>成键 / 反键 MO 上的电子</td><td>'+R.nb+' / '+R.na+'</td></tr>'+
    '<tr><td>键级</td><td>'+FR(R.nb+' − '+R.na,2)+' = '+bo2s(R.bo)+'</td></tr>'+
    '<tr><td>未成对电子</td><td>'+R.unp+' → '+mag+'</td></tr>'+
    '<tr><td>基态光谱项</td><td>'+R.term+'</td></tr></tbody></table>';
  let s='';if(R.both2){const sg=R.M.find(o=>o.nm==='σ2p'),pi=R.M.find(o=>o.nm==='π2p');
    s=!mix?'<b>s–p 混合已关闭。</b>没有混合时 σ2p 总是低于 π2p：p 轨道“头碰头”的重叠强于“肩并肩”。打开混合进行比较——对于 B₂、C₂ 和 N₂，能级顺序会改变。':sg.E>pi.E?'<b>π2p 低于 σ2p。</b>2s 与 2p 的能量差较小，因此由 2s 和 2p 形成的 σ 轨道强烈混合，σ2p 被推高（如 B₂、C₂、N₂）。':'<b>σ2p 低于 π2p。</b>2s 与 2p 的能量差较大，混合很弱，保持了“简单”的能级顺序（如 O₂、F₂）。';}
  else if(!R.noneP){const X=isH(A)?B:A,Hh=isH(A)?A:B;s=''+Hh+' 只有 1s 轨道。它与 2p<sub>z</sub>（原子 '+X+'）形成 σ 键，而 2s 和 2p<sub>x</sub>、2p<sub>y</sub>（原子 '+X+'）几乎保持非键——这就是孤对电子。'}
  if(R.bo<=0)s+=' 键级为零：分子不稳定（最多是弱的范德华复合物）。';
  $('st1').innerHTML=s||'在最小基组中 H 和 He 只有 1s 轨道，因此只有两个 MO：成键和反键。'}
async function update(){let R;try{R=await liveB({A,B,Q,mix})}catch(e){return}if(R.term==null)R.term=TMULT(R.termMult);cur=R;if(sel>=cur.M.length)sel=-1;draw();summary();shape();
  [...$('homG').children,...$('hetG').children].forEach(b=>b.setAttribute('aria-pressed',b.dataset.k===A+'|'+B+'|'+Q));
  $('selA').value=A;$('selB').value=B;$('qV').textContent=Q>0?'+'+Q:Q<0?'−'+(-Q):'0';
  [...$('mixG').children].forEach((b,k)=>b.setAttribute('aria-pressed',(k===0)===mix));
  [...$('propTab').querySelectorAll('tr.pick')].forEach(tr=>tr.classList.toggle('sel',tr.dataset.k===A+'|'+B+'|'+Q))}
async function pick(a,b,q){A=a;B=b;Q=q;let R;try{R=await build(A,B,Q,mix)}catch(e){return}const h=R.M.map((o,i)=>[o,i]).filter(x=>x[0].occ>0).pop();sel=h?h[1]:-1;update()}
// ---------- таблица свойств и график ----------
function props(){const rows=SPEC.map(s=>({a:s.a,b:s.b,q:s.q,re:s.re,d:s.d,R:{nV:s.nV,bo:s.bo,unp:s.unp}}));
  $('propTab').innerHTML='<table class="mtab"><thead><tr><th>粒子</th><th>价电子</th><th>键级</th><th>未成对</th><th>R<sub>e</sub>，Å</th><th>D₀，eV</th></tr></thead><tbody>'+
    rows.map(r=>'<tr class="pick" tabindex="0" data-k="'+r.a+'|'+r.b+'|'+r.q+'"><td>'+fname(r.a,r.b,r.q)+'</td><td>'+r.R.nV+'</td><td>'+(Number.isInteger(r.R.bo)?r.R.bo:fmt(r.R.bo,1))+'</td><td>'+r.R.unp+'</td><td>'+(r.re?fmt(r.re,3):'—')+'</td><td>'+(r.d==null?'—':r.d===0?'≈ 0':fmt(r.d,2))+'</td></tr>').join('')+'</tbody></table>';
  $('propTab').querySelectorAll('tr.pick').forEach(tr=>{const go=()=>{const [a,b,q]=tr.dataset.k.split('|');pick(a,b,+q);$('h1s').scrollIntoView({behavior:'smooth'})};tr.onclick=go;tr.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();go()}}});
  const sv=$('boPlot');sv.innerHTML='';const W=460,H=300,L=40,Rr=44,T=14,Bm=34;const sx=b=>L+b/3.5*(W-L-Rr),syD=d=>T+(H-T-Bm)*(1-d/12),syR=r=>T+(H-T-Bm)*(1-(r-0.6)/2.4);
  el('rect',{x:L,y:T,width:W-L-Rr,height:H-T-Bm,fill:'none',stroke:tok('--line')},sv);
  for(let b=0;b<=3.5;b+=0.5)el('text',{x:sx(b),y:H-16,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,fmt(b,1).replace(',0',''));
  el('text',{x:(W)/2,y:H-2,'text-anchor':'middle','font-size':11.5,fill:tok('--muted')},sv,'键级');
  for(let d=0;d<=12;d+=3)el('text',{x:L-5,y:syD(d)+4,'text-anchor':'end','font-size':11,fill:tok('--accent')},sv,String(d));
  for(let r=0.6;r<=3.01;r+=0.6)el('text',{x:W-Rr+5,y:syR(r)+4,'font-size':11,fill:tok('--warn')},sv,fmt(r,1));
  rows.forEach(r=>{const b=r.R.bo;if(r.d!=null&&r.d>0){const c=el('circle',{cx:sx(b),cy:syD(r.d),r:4.5,fill:tok('--accent')},sv);el('title',{},c,fname(r.a,r.b,r.q)+': D₀ = '+fmt(r.d,2)+' eV')}
    if(r.re){const q=el('rect',{x:sx(b)-4,y:syR(r.re)-4,width:8,height:8,fill:tok('--warn')},sv);el('title',{},q,fname(r.a,r.b,r.q)+': R = '+fmt(r.re,3)+' Å')}})}
// ---------- тренажёр ----------
let qz=null;
async function newQ(){let k;do{k=Math.floor(Math.random()*SPEC.length)}while(qz&&k===qz.k);const {a,b,q}=SPEC[k];let R;try{R=await build(a,b,q,true)}catch(e){return}qz={k,R,a,b,q};
  $('qMol').textContent=fname(a,b,q);$('q0').value='';$('q1').value='';$('q0').className='';$('q1').className='';$('qRes').textContent='输入答案并点击“检查”。'}
const parseN=s=>{s=String(s).trim().replace(',','.');if(/^\d+\s*\/\s*\d+$/.test(s)){const [p,q]=s.split('/');return +p/+q}return s===''?NaN:+s};
$('qNew').onclick=newQ;
// «Проверьте себя» с выбором ответа (assets/js/try.*.js, initSelf): правильные ответы для вариантов
window.qcSelf=()=>[String(qz.R.bo),String(qz.R.unp)];
$('qChk').onclick=()=>{const a=parseN($('q0').value),u=parseN($('q1').value);const ok0=Math.abs(a-qz.R.bo)<1e-6,ok1=u===qz.R.unp;
  $('q0').className=$('q0').value===''?'':ok0?'ok':'bad';$('q1').className=$('q1').value===''?'':ok1?'ok':'bad';
  $('qRes').innerHTML=ok0&&ok1?'<b>正确！</b>':'还不完全正确。数出价电子，从下往上填充 MO；键级 = (成键 − 反键) / 2。'};
$('qShow').onclick=()=>{const R=qz.R;$('q0').value=String(R.bo);$('q1').value=R.unp;$('q0').className=$('q1').className='ok';
  $('qRes').innerHTML=R.nV+' 个价电子：'+R.M.filter(o=>o.occ>0).map(o=>'('+o.nm+')'+SUP(o.occ)).join(' ')+'。键级 '+FR(R.nb+' − '+R.na,2)+' = '+bo2s(R.bo)+'，未成对电子 '+R.unp+'.';pick(qz.a,qz.b,qz.q)};
// ---------- управление ----------
ELS.forEach(X=>{['selA','selB'].forEach(id=>{const o=document.createElement('option');o.value=X;o.textContent=X;$(id).appendChild(o)})});
$('selA').onchange=e=>{A=e.target.value;sel=-1;update()};$('selB').onchange=e=>{B=e.target.value;sel=-1;update()};
$('qDn').onclick=()=>{if(Q>-2){Q--;update()}};$('qUp').onclick=()=>{if(Q<2){Q++;update()}};
[['考虑',true],['关闭',false]].forEach(([t,v])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=t;b.onclick=()=>{mix=v;update()};$('mixG').appendChild(b)});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{draw();shape();props()});
(async()=>{try{SPEC=await QC.api('dia.spec',{})}catch(e){return}
  SPEC.forEach(({a,b,q},i)=>{const bt=document.createElement('button');bt.type='button';bt.className='chip';bt.textContent=fname(a,b,q);bt.dataset.k=a+'|'+b+'|'+q;bt.onclick=()=>pick(a,b,q);(i<HOM?$('homG'):$('hetG')).appendChild(bt)});
  props();await pick('N','N',0);newQ()})();
