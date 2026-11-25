/* Density-functional page (Atlas v2).  The functionals (LSDA, B88, PBE, PW92), the
   radial and Becke quadratures, the self-interaction table, E(N) and the H2+
   curves come from quas_atlas.core.dft (endpoints dft.meta, dft.sie, dft.en,
   dft.h2; the precomputed arrays are core/data/dft.json); this script draws. */
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=3)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('.',',').replace('-','−')};
const fsig=(x,d=3)=>(x>0.5*Math.pow(10,-d)?'+':'')+fmt(x,d);
const KJ=2625.5;
function axes(svg,o){const X=x=>o.L+(x-o.x0)/(o.x1-o.x0)*(o.W-o.L-o.R),Y=y=>o.H-o.B-(y-o.y0)/(o.y1-o.y0)*(o.H-o.T-o.B);
  o.yt.forEach(v=>{el('line',{x1:o.L,x2:o.W-o.R,y1:Y(v),y2:Y(v),stroke:Math.abs(v)<1e-12?'var(--muted)':'var(--line)','stroke-width':1},svg);el('text',{x:o.L-6,y:Y(v)+4,'text-anchor':'end','font-size':11.5,fill:'var(--muted)'},svg,fmt(v,o.yd??2))});
  o.xt.forEach(v=>{el('line',{x1:X(v),x2:X(v),y1:o.H-o.B,y2:o.H-o.B+4,stroke:'var(--muted)','stroke-width':1},svg);el('text',{x:X(v),y:o.H-o.B+17,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,fmt(v,o.xd??0))});
  el('line',{x1:o.L,x2:o.W-o.R,y1:o.H-o.B,y2:o.H-o.B,stroke:'var(--muted)','stroke-width':1},svg);
  if(o.xl)el('text',{x:(o.L+o.W-o.R)/2,y:o.H-2,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,o.xl);return {X,Y}}
const line=(pts,X,Y,lo=-1e9,hi=1e9)=>{let s='',pen=false;pts.forEach(p=>{if(!(p[1]>=lo&&p[1]<=hi)){pen=false;return}s+=(pen?'L':'M')+X(p[0]).toFixed(1)+','+Y(p[1]).toFixed(1);pen=true});return s};
// ---------- 1. самодействие ----------
const FUNCS=[{n:'Хартри–Фок (точный обмен)',x:'hf',c:null},{n:'LDA без учёта спина',x:'xlda',c:'clda'},{n:'LSDA',x:'xlsda',c:'clsda'},{n:'B88-обмен + LSDA-корреляция',x:'xb88',c:'clsda'},{n:'PBE-обмен + LSDA-корреляция',x:'xpbe',c:'clsda'}];
async function sec1(){let Z;try{Z=await QC.api('dft.sie',{})}catch(e){return}const rows=FUNCS.map((f,i)=>({...f,...Z.rows[i]}));
  $('sieTab').innerHTML='<table class="mtab bt"><thead><tr><th class="n">функционал</th><th>E<sub>x</sub></th><th>E<sub>c</sub></th><th>J + E<sub>x</sub> + E<sub>c</sub></th><th>E при лучшем ζ</th></tr></thead><tbody>'+
    rows.map(r=>`<tr><td class="n">${r.n}</td><td>${fmt(r.Ex,4)}</td><td>${fmt(r.Ec,4)}</td><td>${fsig(r.s,4)}</td><td>${fmt(r.Eo,4)} <span class="hint">(ζ = ${fmt(r.zo,3)})</span></td></tr>`).join('')+'</tbody></table>';
  const svg=$('sieBar');svg.innerHTML='';const L=150,W=540,Rr=14,T=20,rowH=(300-T-30)/rows.length,x0=-0.4,x1=0.4,X=v=>L+(v-x0)/(x1-x0)*(W-L-Rr);
  [-0.4,-0.2,0,0.2,0.4].forEach(v=>{el('line',{x1:X(v),x2:X(v),y1:T-6,y2:300-24,stroke:v===0?'var(--muted)':'var(--line)','stroke-width':1},svg);el('text',{x:X(v),y:296,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,fmt(v,1))});
  const short=['Хартри–Фок','LDA (без спина)','LSDA','B88 + LSDA','PBE + LSDA'];
  rows.forEach((r,i)=>{const y=T+i*rowH,h=(rowH-10)/2;el('text',{x:L-8,y:y+rowH/2+4,'text-anchor':'end','font-size':12.5,fill:'var(--ink)'},svg,short[i]);
    el('rect',{x:X(0),y:y+2,width:X(r.J)-X(0),height:h,fill:'var(--muted)',opacity:0.55,rx:2},svg);
    el('rect',{x:X(r.Ex),y:y+4+h,width:X(0)-X(r.Ex),height:h,fill:'var(--accent)',rx:2},svg);
    if(r.Ec<0)el('rect',{x:X(r.Ex+r.Ec),y:y+4+h,width:X(r.Ex)-X(r.Ex+r.Ec),height:h,fill:'var(--rho-l)',rx:2},svg);
    const s=r.s,cx=X(s),cy=y+rowH/2+1;el('path',{d:`M${cx},${cy-7} l7,7 l-7,7 l-7,-7 z`,fill:Math.abs(s)<1e-4?'var(--ok)':'var(--warn)',stroke:'var(--panel)','stroke-width':1},svg)});
  el('text',{x:X(0.4),y:12,'text-anchor':'end','font-size':11.5,fill:'var(--muted)'},svg,'ат. ед.');
  const ls=rows[2],b=rows[3];
  $('t1').innerHTML=`LSDA недооценивает обмен на ${fmt(Z.pct,0).replace('−','')} % и вдобавок даёт ложную корреляционную энергию ${fmt(ls.Ec,3)}: электрон «отталкивается сам от себя» на ${fmt(Z.sie,3)} ат. ед. (${fmt(Z.sieKJ,0)} кДж/моль). GGA-обмен (B88, PBE) почти точен для H, но корреляция LSDA всё портит. Без учёта спина ошибка ещё больше: для одного электрона ρ<sub>α</sub> = ρ, ρ<sub>β</sub> = 0 — система полностью поляризована. Последний столбец: полная энергия атома при оптимальном ζ; точная −0,5.`}
// ---------- 2. E(N) ----------
let ai=0,Ri=0,AL=[];const liveEN=QC.live('dft.en'),liveH2=QC.live('dft.h2');
async function sec2(){let Z;try{Z=await liveEN({ai})}catch(e){return}const a=Z.a,E=Z.E,H=Z.H,NN=Z.NN;
  let svg=$('enChart');svg.innerHTML='';let o={W:540,H:300,L:56,R:12,T:12,B:38,x0:0,x1:2,y0:-0.6,y1:0.02,xt:[0,0.5,1,1.5,2],yt:[-0.6,-0.5,-0.4,-0.3,-0.2,-0.1,0],xl:'число электронов N',xd:1};let A=axes(svg,o);
  el('path',{d:line(NN.map((N,i)=>[N,Z.exact[i]]),A.X,A.Y),fill:'none',stroke:'var(--ink)','stroke-width':2},svg);
  el('path',{d:line(NN.map((N,i)=>[N,H[i]]),A.X,A.Y),fill:'none',stroke:'var(--muted)','stroke-width':1.8,'stroke-dasharray':'6 4'},svg);
  el('path',{d:line(NN.map((N,i)=>[N,E[i]]),A.X,A.Y),fill:'none',stroke:'var(--accent)','stroke-width':2.6},svg);
  const i1=NN.indexOf(1),sL=Z.sL,sR=Z.sR;
  Z.tan.forEach(t=>el('path',{d:line(t,A.X,A.Y),fill:'none',stroke:'var(--rho-l)','stroke-width':1.6,'stroke-dasharray':'2 3'},svg));
  [0,1,2].forEach(N=>el('circle',{cx:A.X(N),cy:A.Y(Z.ex012[N]),r:3.5,fill:'var(--ink)'},svg));
  [['H⁺',0],['H',1],['H⁻',2]].forEach(([t,N])=>el('text',{x:A.X(N)+(N===2?-6:6),y:A.Y(Z.ex012[N])-8,'text-anchor':N===2?'end':'start','font-size':12,fill:'var(--ink)'},svg,t));
  svg=$('devChart');svg.innerHTML='';o={W:540,H:300,L:56,R:12,T:12,B:38,x0:0,x1:2,y0:-0.06,y1:0.03,xt:[0,0.5,1,1.5,2],yt:[-0.06,-0.04,-0.02,0,0.02],xl:'число электронов N',xd:1};A=axes(svg,o);
  el('path',{d:line(NN.map(N=>[N,0]),A.X,A.Y),fill:'none',stroke:'var(--ink)','stroke-width':2},svg);
  el('path',{d:line(NN.map((N,i)=>[N,Z.devH[i]]),A.X,A.Y,o.y0,o.y1),fill:'none',stroke:'var(--muted)','stroke-width':1.8,'stroke-dasharray':'6 4'},svg);
  el('path',{d:line(NN.map((N,i)=>[N,Z.devE[i]]),A.X,A.Y,o.y0,o.y1),fill:'none',stroke:'var(--accent)','stroke-width':2.6},svg);
  el('text',{x:A.X(0.5),y:A.Y(0.022),'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'выше прямой — выпуклость вверх (ошибка локализации)');
  el('text',{x:A.X(0.5),y:A.Y(-0.055),'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'ниже прямой — выпуклость вниз (ошибка делокализации)');
  
  $('enKv').innerHTML=`<span>ε<sub>ВЗМО</sub> = <span class=fr><span>dE</span><span>dN</span></span> при N → 1⁻</span><b>${fmt(sL,3)} (должно быть −I = −0,5)</b><span>I = E(H⁺) − E(H)</span><b>${fmt(Z.I,3)} (точно 0,5)</b><span>наклон при N → 1⁺</span><b>${fmt(sR,3)} (должно быть −A = −0,028)</b><span>скачок наклона (щель)</span><b>${fmt(Z.gap,3)} (точно I − A = 0,472)</b><span>E(½) − ½E(1)</span><b>${fsig(Z.half,4)} (точно 0)</b>`;
  let t=a===0?`<b>LSDA:</b> кривая выпукла вниз, половина электрона «ниже прямой» на ${fmt(Math.abs(Z.half),3)} ат. ед. Отсюда главное: энергия ВЗМО ${fmt(sL,2)} почти вдвое меньше потенциала ионизации, хотя сама энергия ионизации, посчитанная как разность энергий, близка к точной. Скачок наклона при N = 1 (${fmt(Z.gap,2)}) у гладкого функционала — это просто его орбитальная щель КШ: разрыва производной Δ<sub>xc</sub> нет. Поэтому щели ВЗМО–НСМО в LDA и GGA сильно меньше I − A по двум причинам: нет Δ<sub>xc</sub> и выпуклость E(N) сдвигает сами орбитальные энергии.`:
    `При a = ${fmt(a,2)} кривизна ${Math.abs(Z.half)<0.005?'почти исчезла':'меньше'}: точный обмен выгибает E(N) вверх (как у Хартри–Фока, пунктир), LSDA — вниз, и они частично компенсируются. Поэтому гибридные функционалы (B3LYP: a = 0,20; PBE0: a = 0,25) лучше описывают энергии орбиталей и щели. Но полной компенсации при одном a для всех систем нет — отсюда функционалы с разделением по расстоянию.`;
  $('t2').innerHTML=t}
// ---------- 3. H₂⁺ ----------
async function sec3(){let Z;try{Z=await liveH2({ai,ri:Ri})}catch(e){return}const a=Z.a,RR=Z.RR,hf=Z.hf,d=Z.d,l=Z.l;const svg=$('h2Chart');svg.innerHTML='';
  const o={W:540,H:320,L:56,R:12,T:12,B:38,x0:0.6,x1:10,y0:-0.62,y1:-0.38,xt:[1,2,4,6,8,10],yt:[-0.6,-0.55,-0.5,-0.45,-0.4],xl:'R, бор'};const A=axes(svg,o);
  el('line',{x1:A.X(0.6),x2:A.X(10),y1:A.Y(-0.5),y2:A.Y(-0.5),stroke:'var(--ok)','stroke-dasharray':'3 4','stroke-width':1.2},svg);
  el('text',{x:A.X(9.9),y:A.Y(-0.5)+16,'text-anchor':'end','font-size':11.5,fill:'var(--ok)'},svg,'H + H⁺: −0,5');
  el('path',{d:line(RR.map((R,i)=>[R,hf[i]]),A.X,A.Y,o.y0,o.y1),fill:'none',stroke:'var(--ink)','stroke-width':2},svg);
  el('path',{d:line(RR.map((R,i)=>[R,l[i]]),A.X,A.Y,o.y0,o.y1),fill:'none',stroke:'var(--rho-l)','stroke-width':2,'stroke-dasharray':'6 4'},svg);
  el('path',{d:line(RR.map((R,i)=>[R,d[i]]),A.X,A.Y,o.y0,o.y1),fill:'none',stroke:'var(--accent)','stroke-width':2.6},svg);
  const R=RR[Ri];el('line',{x1:A.X(R),x2:A.X(R),y1:o.T,y2:o.H-o.B,stroke:'var(--muted)','stroke-dasharray':'3 3','stroke-width':1},svg);
  [[hf,'var(--ink)'],[l,'var(--rho-l)'],[d,'var(--accent)']].forEach(([arr,c])=>{const v=arr[Ri];if(v>=o.y0&&v<=o.y1)el('circle',{cx:A.X(R),cy:A.Y(v),r:4,fill:c},svg)});
  $('Rv').textContent=fmt(R,1)+' бор';
  $('h2Kv').innerHTML=`<span>Хартри–Фок (точно)</span><b>${fmt(hf[Ri],4)}</b><span>функционал, σ<sub>g</sub></span><b>${fmt(d[Ri],4)} (${fsig(Z.dkj,0)} кДж/моль)</b><span>функционал, на одном атоме</span><b>${fmt(l[Ri],4)}</b>`;
  const iF=RR.length-1;$('t3').innerHTML=a===0?`При R = 10 бор LSDA даёт ${fmt(d[iF],3)} для электрона, поделённого между атомами, и ${fmt(l[iF],3)} для электрона на одном атоме. Должно быть одинаково и равно −0,5 (в этом базисе ${fmt(hf[iF],3)}). Ошибка ≈ ${fmt(Z.errF,0)} кДж/моль, и кривая даже идёт вниз при растяжении. Та же ошибка завышает перенос заряда, занижает барьеры реакций и делает «размазанными» анионы и комплексы с переносом заряда.`:
   `С долей точного обмена a = ${fmt(a,2)} ошибка при R = 10 бор — ${fmt(Z.errF,0)} кДж/моль. Даже при a = 1 кривая не совпадает с точной: корреляция LSDA тоже содержит самодействие (≈ −0,02 ат. ед. на атом H).`}
// ---------- управление ----------
function setA(i){ai=i;document.querySelectorAll('.aS').forEach(s=>s.value=i);document.querySelectorAll('.aV').forEach(v=>v.textContent='a = '+fmt(AL[i],2)+(i===0?' (LSDA)':i===4?' (доля как в B3LYP)':i===5?' (доля как в PBE0)':i===20?' (обмен Хартри–Фока + корреляция LSDA)':''));sec2();sec3()}
document.querySelectorAll('.aS').forEach(s=>s.oninput=e=>setA(+e.target.value));
$('Rs').oninput=e=>{Ri=+e.target.value;sec3()};
sec1();QC.api('dft.meta',{}).then(M=>{AL=M.A;Ri=M.ri0;$('Rs').value=Ri;setA(0)}).catch(()=>{});
