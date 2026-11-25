/* Intermolecular-interactions page (Atlas v2).  The PySCF interaction curves,
   BSSE, minima and the R^-6 analysis come from quas_atlas.core.dispersion
   (disp.sys, disp.r6); this script draws. */
// ---------- страница «Межмолекулярные взаимодействия: водородная связь и дисперсия» ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('.',',').replace('-','−')};
function chips(id,items,isOn,set){const g=$(id);g.innerHTML='';items.forEach(([v,l])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.innerHTML=l;b.setAttribute('aria-pressed',isOn(v));b.onclick=()=>set(v);g.appendChild(b)})}
const BOHR=0.52917721092,CM=219474.63,KJ=2625.4996;
// столбцы данных: R, HF без поправки, MP2 без поправки, HF с поправкой, MP2 с поправкой (E_h)
const SYSD={
 he2:{name:'He₂',basis:'aug-cc-pVDZ',unit:'см⁻¹',k:CM,xu:'R, бор',y:[-10,10],ref:{R:5.6,E:-7.65,lab:'точно'},R0:5.6,d:2},
 w2:{name:'(H₂O)₂',basis:'6-31G*',unit:'кДж/моль',k:KJ,xu:'R(O···O), Å',y:[-35,20],ref:{R:2.91,E:-21.0,lab:'CCSD(T)/CBS'},R0:2.9,d:1}};
const st={sys:'he2',met:{hf:true,mp2:true},cp:'both',i:{}};
const COL={hf:'var(--muted)',mp2:'var(--accent)'};
const S=()=>SYSD[st.sys];
const col=(m,cp)=>(m==='hf'?1:2)+(cp?2:0);
const liveS=QC.live('disp.sys');
async function sec1(){const s=S();let Z;try{Z=await liveS({sys:st.sys})}catch(e){return}if(st.i[st.sys]==null)st.i[st.sys]=Z.i0;const i=st.i[st.sys],P=[Z.R[i]];
  chips('sysG',[['he2','He₂ — только дисперсия'],['w2','(H₂O)₂ — водородная связь']],v=>v===st.sys,v=>{st.sys=v;sec1()});
  chips('metG',[['hf','HF'],['mp2','MP2']],v=>st.met[v],v=>{st.met[v]=!st.met[v];if(!st.met.hf&&!st.met.mp2)st.met[v]=true;sec1()});
  chips('cpG',[['raw','без поправки'],['cp','с поправкой'],['both','обе кривые']],v=>v===st.cp,v=>{st.cp=v;sec1()});
  const sl=$('R');sl.max=Z.R.length-1;sl.value=i;
  $('RV').textContent=st.sys==='he2'?`R = ${fmt(P[0],1)} бор (${fmt(P[0]*BOHR,2)} Å)`:`R(O···O) = ${fmt(P[0],2)} Å`;
  $('ttl1').innerHTML=`ΔE(R) для ${s.name}, ${s.unit}; базис ${s.basis}`;
  // график
  const sv=$('cSvg');sv.innerHTML='';const W=540,H=330,L=54,Rm=14,T=14,B=34,pw=W-L-Rm,ph=H-T-B;const x0=Z.R[0],x1=Z.R[Z.R.length-1],[y0,y1]=s.y;
  const sx=x=>L+(x-x0)/(x1-x0)*pw,sy=e=>T+ph*(y1-e)/(y1-y0);
  el('rect',{x:L,y:T,width:pw,height:ph,fill:'none',stroke:tok('--line')},sv);
  const yt=st.sys==='he2'?[-10,-5,0,5,10]:[-30,-20,-10,0,10,20],xt=st.sys==='he2'?[5,6,7,8,9,10,11,12]:[2.5,3,3.5,4,4.5,5];
  yt.forEach(e=>{el('line',{x1:L,y1:sy(e),x2:L+pw,y2:sy(e),stroke:tok('--line'),'stroke-dasharray':e===0?'none':'2 4'},sv);el('text',{x:L-5,y:sy(e)+4,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,fmt(e,0))});
  xt.forEach(x=>el('text',{x:sx(x),y:H-B+16,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,fmt(x,st.sys==='he2'?0:1)));
  el('text',{x:L+pw,y:H-3,'text-anchor':'end','font-size':11.5,fill:tok('--muted')},sv,s.xu);el('text',{x:4,y:T+10,'font-size':11.5,fill:tok('--muted')},sv,'ΔE');
  const cps=st.cp==='both'?[false,true]:[st.cp==='cp'];const lg=[];
  ['hf','mp2'].filter(m=>st.met[m]).forEach(m=>cps.forEach(cp=>{const j=col(m,cp);let d='',pen=false;
    Z.R.forEach((R,q)=>{const e=Z.E[j][q];if(e>y1+2||e<y0-2){pen=false;return}d+=(pen?' L':' M')+sx(R).toFixed(1)+','+sy(e).toFixed(1);pen=true});
    el('path',{d,fill:'none',stroke:COL[m],'stroke-width':2.4,'stroke-dasharray':cp?'none':'6 4'},sv);
    lg.push(`<span><i class="sw" style="border-color:${COL[m]};${cp?'':'border-top-style:dashed'}"></i>${m.toUpperCase()}, ${cp?'с поправкой':'без поправки'}</span>`)}));
  // эталон
  const rf=s.ref;el('circle',{cx:sx(rf.R),cy:sy(rf.E),r:5,fill:tok('--ok')},sv);el('text',{x:sx(rf.R)+8,y:sy(rf.E)+14,'font-size':11.5,fill:tok('--ok')},sv,rf.lab+': '+fmt(rf.E,st.sys==='he2'?2:1));
  lg.push(`<span><i class="box" style="background:var(--ok);border-radius:50%;width:10px;height:10px"></i>эталон: ${rf.lab}</span>`);
  // курсор
  el('line',{x1:sx(P[0]),y1:T,x2:sx(P[0]),y2:T+ph,stroke:tok('--ink'),'stroke-width':1,'stroke-dasharray':'3 3',opacity:0.6},sv);
  $('lg1').innerHTML=lg.join('');
  // таблица
  const TB=Z.tab[i],v=j=>TB.v[j-1],dd=s.d+1;
  $('tab1').innerHTML=`<table class="mtab"><thead><tr><th class="l">ΔE, ${s.unit}</th><th>без поправки</th><th>с поправкой</th><th>BSSE</th></tr></thead><tbody>`+
    `<tr><td class="l">HF</td><td>${fmt(v(1),dd)}</td><td>${fmt(v(3),dd)}</td><td>${fmt(TB.bsseHF,dd)}</td></tr>`+
    `<tr><td class="l">MP2</td><td>${fmt(v(2),dd)}</td><td>${fmt(v(4),dd)}</td><td>${fmt(TB.bsseMP2,dd)}</td></tr>`+
    `<tr><td class="l">корреляция (MP2 − HF)</td><td>${fmt(TB.corrRaw,dd)}</td><td>${fmt(TB.corrCp,dd)}</td><td></td></tr></tbody></table>`;
  drawMol(P[0]);
  // текст
  const mH=Z.mins.hf_cp,mM=Z.mins.mp2_cp,mMr=Z.mins.mp2_raw,mHr=Z.mins.hf_raw;
  let t;
  if(st.sys==='he2')t=`<b>HF с поправкой</b>: ${mH?'минимум '+fmt(mH.E,2):'минимума нет — кривая отталкивательная при всех R'}. Без поправки у HF появляется ложная ямка ${mHr?fmt(mHr.E,2)+' '+s.unit+' при '+fmt(mHr.R,1)+' бор':''} — это чистая BSSE. <b>MP2 с поправкой</b>: минимум ${fmt(mM.E,2)} ${s.unit} при ${fmt(mM.R,1)} бор, примерно ${Z.pct} % точной глубины ${fmt(rf.E,2)} ${s.unit} (R<sub>e</sub> = 5,6 бор). Базис aug-cc-pVDZ мал для дисперсии, да и сам MP2 её не дотягивает. Без поправки MP2 даёт ${fmt(mMr.E,2)} ${s.unit} — почти точное число, но по неверной причине: недостаток базиса компенсируется суперпозиционной ошибкой. Для сравнения: 7,65 см⁻¹ ≈ 0,09 кДж/моль — почти в 30 раз меньше kT при комнатной температуре (2,5 кДж/моль), поэтому димер гелия существует лишь при температурах порядка милликельвинов.`;
  else t=`<b>HF с поправкой</b>: минимум ${fmt(mH.E,1)} ${s.unit} при R(O···O) = ${fmt(mH.R,2)} Å — в этом базисе основная часть энергии связи получается уже без корреляции: электростатика, поляризация и перенос заряда описываются средним полем. <b>MP2 с поправкой</b>: ${fmt(mM.E,1)} ${s.unit} — корреляция (в том числе дисперсия) добавляет здесь ${fmt(Z.dHM,1)} ${s.unit}. Эталон CCSD(T) в полном базисе — около −21,0 ${s.unit} при 2,91 Å, а HF в пределе полного базиса даёт около −15 ${s.unit}: при полном базисе на корреляцию приходится примерно четверть энергии связи, так что малый вклад корреляции здесь — свойство базиса 6-31G*, а не водородных связей вообще. Без поправки MP2 в базисе 6-31G* даёт ${fmt(mMr.E,1)} ${s.unit}: суперпозиционная ошибка завышает связь почти на ${fmt(Z.dRM,0).replace('−','')} ${s.unit}.`;
  $('st1').innerHTML=t}
function drawMol(R){const sv=$('mSvg');sv.innerHTML='';const s=S();
  const atom=(x,y,l,r,c)=>{el('circle',{cx:x,cy:y,r,fill:'var(--panel)',stroke:c,'stroke-width':2},sv);el('text',{x,y:y+4.5,'text-anchor':'middle','font-size':r>12?13:11,'font-weight':600,fill:c},sv,l)};
  if(st.sys==='he2'){const sc=26,c=260,a=c-R*sc/2,b=c+R*sc/2;
    el('line',{x1:a,y1:120,x2:b,y2:120,stroke:'var(--muted)','stroke-width':1.2,'stroke-dasharray':'4 4'},sv);
    el('text',{x:c,y:146,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},sv,'R = '+fmt(R,1)+' бор');
    [a,b].forEach(x=>{el('circle',{cx:x,cy:80,r:28,fill:'var(--acc-bg)',stroke:'none'},sv);atom(x,80,'He',14,'var(--ink)')})}
  else{const sc=58,r=0.9572,h=104.52*Math.PI/180,u=57*Math.PI/180,X=x=>110+x*sc,Y=y=>95-y*sc;
    const O1=[0,0],H1=[r,0],H2=[r*Math.cos(h),r*Math.sin(h)],O2=[R,0];
    const a1=Math.PI-u;const H3=[R+r*Math.cos(h/2)*Math.cos(u),-r*Math.cos(h/2)*Math.sin(u)];
    [[O1,H1],[O1,H2]].forEach(([p,q])=>el('line',{x1:X(p[0]),y1:Y(p[1]),x2:X(q[0]),y2:Y(q[1]),stroke:'var(--ink)','stroke-width':2.2},sv));
    el('line',{x1:X(O2[0]),y1:Y(O2[1]),x2:X(H3[0]),y2:Y(H3[1]),stroke:'var(--ink)','stroke-width':2.2},sv);
    el('line',{x1:X(H1[0])+8,y1:Y(0),x2:X(O2[0])-12,y2:Y(0),stroke:'var(--accent)','stroke-width':2,'stroke-dasharray':'3 4'},sv);
    el('circle',{cx:X(H3[0])+7,cy:Y(H3[1])-5,r:11,fill:'var(--panel)',stroke:'var(--muted)','stroke-width':1.5,'stroke-dasharray':'3 2'},sv);atom(X(H3[0]),Y(H3[1]),'H',11,'var(--ink)');atom(X(O1[0]),Y(O1[1]),'O',14,'var(--warn)');atom(X(H1[0]),Y(H1[1]),'H',11,'var(--ink)');atom(X(H2[0]),Y(H2[1]),'H',11,'var(--ink)');atom(X(O2[0]),Y(O2[1]),'O',14,'var(--warn)');
    el('text',{x:(X(0)+X(R))/2,y:150,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},sv,'R(O···O) = '+fmt(R,2)+' Å; донор слева, акцептор справа (его атомы H — над и под плоскостью)')}}
$('R').oninput=e=>{st.i[st.sys]=+e.target.value;sec1()};
// ---------- 2. закон R⁻⁶ ----------
async function sec2(){let Z;try{Z=await QC.api('disp.r6',{})}catch(e){return}const pts=Z.pts;
  const sv=$('lSvg');sv.innerHTML='';const W=540,H=320,L=60,Rm=14,T=14,B=36,pw=W-L-Rm,ph=H-T-B;
  const lx0=Math.log10(6.5),lx1=Math.log10(12),ly0=-7,ly1=-4.3;const sx=x=>L+(Math.log10(x)-lx0)/(lx1-lx0)*pw,sy=y=>T+ph*(ly1-Math.log10(y))/(ly1-ly0);
  el('rect',{x:L,y:T,width:pw,height:ph,fill:'none',stroke:tok('--line')},sv);
  [7,8,9,10,12].forEach(x=>el('text',{x:sx(x),y:H-B+16,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,String(x)));
  [1e-7,1e-6,1e-5].forEach(y=>{el('line',{x1:L,y1:sy(y),x2:L+pw,y2:sy(y),stroke:tok('--line'),'stroke-dasharray':'2 4'},sv);el('text',{x:L-5,y:sy(y)+4,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,{'-7':'10⁻⁷','-6':'10⁻⁶','-5':'10⁻⁵'}[Math.round(Math.log10(y))])});
  el('text',{x:L+pw,y:H-3,'text-anchor':'end','font-size':11.5,fill:tok('--muted')},sv,'R, бор (лог. шкала)');el('text',{x:4,y:T+10,'font-size':11.5,fill:tok('--muted')},sv,'|ΔE|, Eₕ');
  let d='';pts.forEach((p,k)=>{const c=p[1];d+=(k?' L':'M')+sx(p[0]).toFixed(1)+','+sy(c).toFixed(1)});el('path',{d,fill:'none',stroke:'var(--accent)','stroke-width':2.4},sv);
  d='';Z.line.forEach(([x,y],k)=>{d+=(k?' L':'M')+sx(x).toFixed(1)+','+sy(y).toFixed(1)});el('path',{d,fill:'none',stroke:'var(--ok)','stroke-width':2,'stroke-dasharray':'6 4'},sv);
  const slope=Z.slope,C6m=Z.C6m;
  $('st2').innerHTML=`Между 8 и 12 бор наклон прямой ${fmt(slope,2)} — практически −6, как и требует теория Лондона. Эффективный коэффициент MP2/aug-cc-pVDZ C₆ ≈ ${fmt(C6m,2)} ат. ед., точное значение 1,46: даже асимптотика в малом базисе занижена. При меньших R прямая загибается — сказываются перекрывание плотностей и члены C₈/R⁸, C₁₀/R¹⁰.`}
function draw(){sec1();sec2()}
draw();
new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
