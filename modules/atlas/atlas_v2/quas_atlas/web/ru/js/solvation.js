/* Solvent models page (Atlas v2).  The Born model, the C-PCM data set and the
   permittivity curve come from quas_atlas.core.solvation (solv.born, solv.pcm,
   solv.eps); this script keeps the texts and draws. */
const D={note:"Для полярных молекул C-PCM в среднем ошибается на −0,8 ккал/моль, для слабополярных (этан, бензол, хлороформ) — на −1,9. Расчёт почти для всех молекул слишком отрицателен: в нём нет положительного вклада образования полости. У слабополярных молекул это особенно заметно — сама электростатика у них мала, и этан выходит «гидрофильным», хотя на самом деле в воду идёт неохотно (+1,8 ккал/моль)."};
// ---------- страница «Модели растворителя» (модель Борна на странице, C-PCM посчитан в PySCF) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('.',',').replace('-','−')};
const sg=(x,d=2)=>(x>0.5*Math.pow(10,-d)?'+':'')+fmt(x,d);
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
const KJ=4.184;const Q={eps:78.4,dp:0,dm:0,em:0};
// ---------- 1. модель Борна ----------
[['eps','epsV',v=>fmt(v,1)],['dp','dpV',v=>fmt(v,2)+' Å'],['dm','dmV',v=>fmt(v,2)+' Å']].forEach(([id,vid,f])=>{const s=$(id);s.value=Q[id];$(vid).textContent=f(Q[id]);s.oninput=e=>{Q[id]=+e.target.value;$(vid).textContent=f(Q[id]);bornD()}});
const liveB=QC.live('solv.born');
async function bornD(){let B;try{B=await liveB({eps:Q.eps,dp:Q.dp,dm:Q.dm})}catch(e){return}const svg=$('bornC');svg.innerHTML='';const W=960,H=320,lft=64,rt=16,top=14,bot=40,n=B.rows.length,bw=(W-lft-rt)/n;
  const rows=B.rows;
  const lo=Math.min(-800,...rows.map(r=>r.b))*1.06,Y=v=>top+(0-v)/(0-lo)*(H-top-bot);
  for(let v=0;v>=lo;v-=100){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,fmt(v,0))}
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,'ΔG, кДж/моль');
  rows.forEach((r,i)=>{const x=lft+i*bw;el('rect',{x:x+bw*.14,y:Y(0),width:bw*.34,height:Y(r.b)-Y(0),fill:tok('--accent'),rx:2},svg);el('rect',{x:x+bw*.52,y:Y(0),width:bw*.34,height:Y(r.ex)-Y(0),fill:tok('--muted'),rx:2,opacity:.7},svg);
    el('text',{x:x+bw/2,y:H-16,'text-anchor':'middle','font-size':14,fill:tok('--ink')},svg,r.s)});
  $('bornL').innerHTML='<span><span class="sw" style="border-color:'+tok('--accent')+'"></span>модель Борна</span><span><span class="sw" style="border-color:'+tok('--muted')+'"></span>эксперимент (Маркус)</span>';
  const mae=B.mae;
  $('bornT').innerHTML='<table class="mtab"><thead><tr><th>ион</th><th>r, Å</th><th>a = r + δ, Å</th><th>Борн</th><th>эксперимент</th><th>разность</th></tr></thead><tbody>'+rows.map(r=>'<tr><td>'+r.s+'</td><td>'+fmt(r.r,2)+'</td><td>'+fmt(r.a,2)+'</td><td>'+fmt(r.b,0)+'</td><td>'+fmt(r.ex,0)+'</td><td>'+sg(r.b-r.ex,0)+'</td></tr>').join('')+'</tbody></table><p class="hint">кДж/моль; r — кристаллические радиусы Шеннона (КЧ 6). Средняя абсолютная ошибка: '+fmt(mae,0)+' кДж/моль.</p>';
  $('bornN').textContent=Q.dp<0.3&&Q.dm<0.3?'С кристаллическими радиусами модель Борна переоценивает выигрыш почти вдвое: ближайшие молекулы воды не могут подойти к иону вплотную, и «эффективная» полость больше иона.':'Увеличенные радиусы учитывают, что первый слой воды не является сплошной средой. Латимер, Питцер и Сланский (1939) подобрали добавки около 0,85 Å для катионов и 0,1 Å для анионов: катион «видит» атом кислорода молекулы воды, анион — более близкий атом водорода.'}
// ---------- 2. C-PCM ----------
let PC=null,M=null;const NAME={water:'вода',methanol:'метанол',ethanol:'этанол',formaldehyde:'формальдегид',acetone:'ацетон','acetic acid':'уксусная кислота',ethane:'этан',chloroform:'хлороформ',benzene:'бензол',phenol:'фенол',pyridine:'пиридин'};
async function pcm(){if(!PC){try{PC=await QC.api('solv.pcm',{})}catch(e){return}M=PC.mols}const svg=$('pcmC');svg.innerHTML='';const W=960,H=360,lft=70,rt=30,top=16,bot=46;const lo=-10,hi=3;
  const X=v=>lft+(v-lo)/(hi-lo)*(W-lft-rt),Y=v=>top+(hi-v)/(hi-lo)*(H-top-bot);
  for(let v=lo;v<=hi;v+=1){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,fmt(v,0));
    el('text',{x:X(v),y:H-26,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,fmt(v,0))}
  el('line',{x1:X(lo),y1:Y(lo),x2:X(hi),y2:Y(hi),stroke:tok('--ok'),'stroke-width':1.5,'stroke-dasharray':'6 4'},svg);
  el('text',{x:(lft+W-rt)/2,y:H-6,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'эксперимент, ккал/моль');
  el('text',{x:16,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 16 ${top+(H-top-bot)/2})`},svg,'расчёт C-PCM, ккал/моль');
  const pl=M.map(m=>{const d=PC.r[m];return {m,x:X(d.exp),y:Y(d.dG),ly:Y(d.dG)+4,d}}).sort((a,b)=>a.y-b.y);
  pl.forEach((p,i)=>{for(let j=0;j<i;j++){const q=pl[j];if(Math.abs(q.x-p.x)<110&&Math.abs(q.ly-p.ly)<14)p.ly=q.ly+14}});
  pl.forEach(p=>{el('circle',{cx:p.x,cy:p.y,r:6,fill:tok(p.d.exp>0?'--warn':'--accent')},svg);if(Math.abs(p.ly-p.y-4)>3)el('line',{x1:p.x+6,y1:p.y,x2:p.x+10,y2:p.ly-4,stroke:tok('--muted')},svg);el('text',{x:p.x+11,y:p.ly,'font-size':12,fill:tok('--ink')},svg,NAME[p.m]||p.m)});
  const mae=PC.mae;
  $('pcmT').innerHTML='<table class="mtab"><thead><tr><th>молекула</th><th>C-PCM</th><th>эксперимент</th><th>разность</th></tr></thead><tbody>'+M.map(m=>{const d=PC.r[m];return '<tr><td>'+(NAME[m]||m)+'</td><td>'+fmt(d.dG,2)+'</td><td>'+fmt(d.exp,2)+'</td><td>'+sg(d.dG-d.exp,2)+'</td></tr>'}).join('')+'</tbody></table><p class="hint">ккал/моль. Экспериментальные значения — база FreeSolv (вода — по Бен-Наиму и Маркусу). Средняя абсолютная ошибка: '+fmt(mae,2)+' ккал/моль.</p>';
  $('pcmN').textContent=D.note}
// ---------- 3. зависимость от ε ----------
let EM=null;const liveE=QC.live('solv.eps');
const SOLV=[[2.38,'толуол'],[4.81,'хлороформ'],[7.43,'ТГФ'],[20.7,'ацетон'],[32.6,'метанол'],[46.7,'ДМСО'],[78.36,'вода']];
async function epsD(){if(!EM){if(!PC)return;EM=PC.epsMols;chips($('emG'),EM.map(m=>NAME[m]||m),Q.em,i=>{Q.em=i;mark($('emG'),i);epsD()})}
  let R;try{R=await liveE({i:Q.em})}catch(e){return}const m=R.m,ks=R.ks,svg=$('epsC');svg.innerHTML='';const W=960,H=320,lft=64,rt=24,top=16,bot=46;
  const vals=R.vals;const lo=Math.min(...vals)*1.15,hi=0,ex=80;
  const X=e=>lft+Math.log(e)/Math.log(ex)*(W-lft-rt),Y=v=>top+(hi-v)/(hi-lo)*(H-top-bot);
  for(let v=0;v>=lo;v-=1){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,fmt(v,0))}
  [1,2,5,10,20,50,80].forEach(e=>el('text',{x:X(e),y:H-26,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,e));
  el('text',{x:(lft+W-rt)/2,y:H-6,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'ε (логарифмическая шкала)');
  el('text',{x:16,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 16 ${top+(H-top-bot)/2})`},svg,'ΔG, ккал/моль');
  let d='';R.curve.forEach(([e,v])=>{d+=(d?'L':'M')+X(e).toFixed(1)+' '+Y(v).toFixed(1)});el('path',{d,fill:'none',stroke:tok('--muted'),'stroke-width':1.6,'stroke-dasharray':'5 4'},svg);
  let p='';ks.forEach((k,i)=>p+=(i?'L':'M')+X(k).toFixed(1)+' '+Y(vals[i]).toFixed(1));el('path',{d:p,fill:'none',stroke:tok('--accent'),'stroke-width':2.6},svg);ks.forEach((k,i)=>el('circle',{cx:X(k),cy:Y(vals[i]),r:4.5,fill:tok('--accent')},svg));
  SOLV.forEach(([e,n])=>{const i=ks.findIndex(k=>Math.abs(k-e)<0.01);if(i<0)return;el('text',{x:X(e),y:Y(vals[i])-10,'text-anchor':'middle','font-size':11,fill:tok('--ink')},svg,n)});
  $('epsN').textContent='Сплошная линия — расчёт C-PCM, штриховая — множитель (ε − 1)/ε, отнормированный на значение в воде. В хлороформе (ε = 4,8) '+(NAME[m]||m)+' получает уже '+fmt(R.pct,0)+' % энергии сольватации в воде: для полярности растворителя важнее всего первые единицы ε.'}
async function all(){bornD();await pcm();epsD()}
all();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',all);new MutationObserver(all).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
