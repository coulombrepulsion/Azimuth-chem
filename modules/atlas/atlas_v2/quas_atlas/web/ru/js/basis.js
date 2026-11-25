/* Basis-set page (Atlas v2).  Gaussian expansions, the linear variational method,
   the exponent optimisation, the one-Gaussian virial example and the size of
   standard basis sets come from quas_atlas.core.basis (basis.part1,
   basis.optimize, basis.part2, basis.part3); this script draws. */
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=3)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('.',',').replace('-','−')};
const fp=(x,s=4)=>{const t=x.toPrecision(s);return (t.includes('e')?(+t).toString():t).replace('.',',')};
const big=x=>{if(x<1e4)return Math.round(x).toLocaleString('ru-RU');const e=Math.floor(Math.log10(x)),m=x/Math.pow(10,e);return fmt(m,1)+'·10'+String(e).split('').map(c=>'⁰¹²³⁴⁵⁶⁷⁸⁹'[+c]).join('')};
function bytes(x){const u=['Б','КБ','МБ','ГБ','ТБ','ПБ'];let i=0;while(x>=1024&&i<u.length-1){x/=1024;i++}return fmt(x,x<10?1:0)+' '+u[i]}
function chips(id,items,cur,set){const g=$(id);g.innerHTML='';items.forEach(([v,l])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.innerHTML=l;b.setAttribute('aria-pressed',v===cur);b.onclick=()=>set(v);g.appendChild(b)})}
function axes(svg,o){// o: {W,H,L,R,T,B,x0,x1,y0,y1,xt,yt,xl,yl,xf,yf}
  const X=x=>o.L+(x-o.x0)/(o.x1-o.x0)*(o.W-o.L-o.R),Y=y=>o.H-o.B-(y-o.y0)/(o.y1-o.y0)*(o.H-o.T-o.B);
  o.yt.forEach(v=>{el('line',{x1:o.L,x2:o.W-o.R,y1:Y(v),y2:Y(v),stroke:'var(--line)','stroke-width':1},svg);el('text',{x:o.L-6,y:Y(v)+4,'text-anchor':'end','font-size':11.5,fill:'var(--muted)'},svg,(o.yf||fmt)(v))});
  o.xt.forEach(v=>{el('line',{x1:X(v),x2:X(v),y1:o.H-o.B,y2:o.H-o.B+4,stroke:'var(--muted)','stroke-width':1},svg);el('text',{x:X(v),y:o.H-o.B+17,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,(o.xf||fmt)(v))});
  el('line',{x1:o.L,x2:o.W-o.R,y1:o.H-o.B,y2:o.H-o.B,stroke:'var(--muted)','stroke-width':1},svg);
  if(o.xl)el('text',{x:(o.L+o.W-o.R)/2,y:o.H-2,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,o.xl);
  if(o.yl)el('text',{x:o.L+4,y:o.T-4,'font-size':12,fill:'var(--muted)'},svg,o.yl);return {X,Y}}
// линия с разрывами: точки за пределами [lo, hi] не рисуются
const path=(pts,X,Y,lo=-1e9,hi=1e9)=>{let s='',pen=false;pts.forEach(p=>{if(!(p[1]>=lo&&p[1]<=hi)){pen=false;return}s+=(pen?'L':'M')+X(p[0]).toFixed(1)+','+Y(p[1]).toFixed(1);pen=true});return s};
// ---------- часть 1 ----------
let st={set:'sto',n:3,sc:'lin',cust:{1:[0.28],2:[0.2,1.3],3:[0.15,0.7,4.5],4:[0.12,0.45,2,13]}};
try{const s=JSON.parse(localStorage.getItem('qc-basis')||'null');if(s&&s.set)st=Object.assign(st,s)}catch(e){}
function curName(){const n=st.n;if(st.set==='sto')return 'STO-'+n+'G';if(st.set==='opt')return n+' гауссиан'+(n===1?'':n<5?'а':'ов')+', оптимизированных по энергии';return 'ваши показатели'}
const live1=QC.live('basis.part1'),live2=QC.live('basis.part2'),live3=QC.live('basis.part3');
function save(){try{localStorage.setItem('qc-basis',JSON.stringify(st))}catch(e){}}
async function draw1(){const nAll=st.set==='sto'?[1,2,3,6]:st.set==='opt'?[1,2,3,4,5,6]:[1,2,3,4];if(!nAll.includes(st.n))st.n=3;
  chips('setG',[['sto','STO-nG (стандартные сжатия)'],['opt','оптимальные по энергии'],['cust','свои показатели']],st.set,v=>{st.set=v;draw1()});
  chips('nG',nAll.map(n=>[n,String(n)]),st.n,v=>{st.n=v;draw1()});
  chips('scG',[['lin','обычный'],['log','логарифмический: ln|ψ|']],st.sc,v=>{st.sc=v;draw1()});
  save();let Z;try{Z=await live1({set:st.set,n:st.n,cust:st.set==='cust'?st.cust[st.n]:null,sc:st.sc})}catch(e){return}const B={a:Z.a,d:Z.d,name:curName(),bad:Z.bad},{a,d}=B;
  // ползунки для своих показателей
  const sl=$('sliders'),sig=st.set+'|'+st.n;/* while a slider is dragged the row is kept (it was rebuilt at every step, and the drag stopped) */if(st.set==='cust'&&sl.dataset.sig===sig&&sl.contains(document.activeElement)){sl.querySelectorAll('.slrow').forEach((r,i)=>{const x=st.cust[st.n][i],inp=r.querySelector('input'),v=r.querySelector('.val');if(v)v.textContent=fp(x);if(inp&&inp!==document.activeElement)inp.value=Math.log10(x)})}else{sl.dataset.sig=sig;sl.innerHTML='';if(st.set==='cust'){st.cust[st.n].forEach((x,i)=>{const r=document.createElement('div');r.className='slrow';r.innerHTML=`<span class="small">α<sub>${i+1}</sub></span><input type="range" min="-2" max="2.3" step="0.005" value="${Math.log10(x)}" aria-label="Показатель ${i+1}, логарифмическая шкала"><span class="val">${fp(x)}</span>`;
      r.querySelector('input').oninput=e=>{st.cust[st.n][i]=Math.pow(10,+e.target.value);draw1()};sl.appendChild(r)});
    const b=document.createElement('div');b.className='crow';b.innerHTML='<button class="btn primary" type="button">Оптимизировать показатели</button><span class="hint">коэффициенты всегда находит линейный вариационный метод; кнопка подбирает и показатели</span>';
    b.querySelector('button').onclick=async()=>{let r;try{r=await QC.api('basis.optimize',{start:st.cust[st.n]})}catch(e){return}st.cust[st.n]=r.a;draw1()};sl.appendChild(b)}}
  // график ψ
  const log=st.sc==='log';const sn1=QC.snap&&QC.snap($('psi')),sn2=QC.snap&&QC.snap($('rad'));let svg=$('psi');svg.innerHTML='';$('psiTitle').textContent=log?'ln|ψ(r)|: прямая для слейтеровской функции, парабола для гауссиана':'ψ(r), ат. ед.';
  const rmax=log?8:4,o=log?{W:540,H:300,L:46,R:12,T:16,B:38,x0:0,x1:8,y0:-12,y1:0.5,xt:[0,2,4,6,8],yt:[-12,-9,-6,-3,0],xl:'r, бор'}:{W:540,H:300,L:46,R:12,T:16,B:38,x0:0,x1:4,y0:-0.05,y1:Math.max(0.6,1.06*Math.max(...Z.gs.map(Math.abs),...Z.sl)),xt:[0,1,2,3,4],yt:[],xl:'r, бор'};
  /* the axis ψ grows with the curve (large exponents went off the top), its ticks follow */
  if(!log){const st=o.y1>2.4?1:o.y1>1.2?0.5:0.2;for(let v=0;v<=o.y1+1e-9;v+=st)o.yt.push(+v.toFixed(2))}
  o.yf=v=>fmt(v,log?0:1);o.xf=v=>String(v);const {X,Y}=axes(svg,o);
  const rs=Z.rs;const P=pts=>path(pts,X,Y,o.y0,o.y1);
  a.forEach((x,i)=>{if(!Z.prim[i])return;el('path',{d:P(rs.map((r,k)=>[r,Z.prim[i][k]])),fill:'none',stroke:'var(--rho-l)','stroke-width':1.3,'stroke-dasharray':'5 4'},svg)});
  el('path',{d:P(rs.map((r,k)=>[r,Z.sl[k]])),fill:'none',stroke:'var(--ink)','stroke-width':2},svg);
  el('path',{d:P(rs.map((r,k)=>[r,Z.gs[k]])),fill:'none',stroke:'var(--accent)','stroke-width':2.4},svg);
  if(!log){// подпись про касп
    el('text',{x:X(0.08),y:Y(Z.s0)-6,'font-size':11.5,fill:'var(--muted)'},svg,'излом (касп) у ядра: ψ′(0) = −ψ(0)');}
  // радиальная плотность
  svg=$('rad');svg.innerHTML='';const o2={W:540,H:300,L:46,R:12,T:16,B:38,x0:0,x1:5,y0:0,y1:Math.max(0.62,1.06*Math.max(...Z.radS,...Z.radG)),xt:[0,1,2,3,4,5],yt:[],xl:'r, бор',xf:v=>String(v),yf:v=>fmt(v,1)};{const st=o2.y1>2.4?1:o2.y1>1.2?0.5:0.2;for(let v=0;v<=o2.y1+1e-9;v+=st)o2.yt.push(+v.toFixed(2))}const A=axes(svg,o2);
  const rr=Z.rr;
  el('path',{d:path(rr.map((r,k)=>[r,Z.radS[k]]),A.X,A.Y),fill:'none',stroke:'var(--ink)','stroke-width':2},svg);
  el('path',{d:path(rr.map((r,k)=>[r,Z.radG[k]]),A.X,A.Y),fill:'none',stroke:'var(--accent)','stroke-width':2.4},svg);
  QC.tween&&(QC.tween($('psi'),sn1),QC.tween($('rad'),sn2));
  // числа
  const ec={E:Z.E,T:Z.T},ov=Z.ov,psi0=Z.psi0;
  $('kv').innerHTML=`<span>Энергия E</span><b>${fmt(ec.E,5)} ат. ед.</b><span>Ошибка E − E<sub>точн</sub></span><b>${fmt(Z.errm,2)} мЭ<sub>h</sub> = ${fmt(Z.errkj,1)} кДж/моль</b><span>Перекрывание со слейтеровской</span><b>${fmt(ov,5)}</b><span>ψ(0)</span><b>${fmt(psi0,3)} (точно ${fmt(Z.s0,3)})</b><span>T и V</span><b>${fmt(ec.T,4)} и ${fmt(Z.V,4)}; <span class=fr><span>V</span><span>T</span></span> = ${fmt(Z.VT,3)}</b>`;
  $('primTab').innerHTML='<table class="mtab bt"><thead><tr><th class="n">'+B.name+'</th>'+a.map((_,i)=>`<th>g<sub>${i+1}</sub></th>`).join('')+'</tr></thead><tbody><tr><td class="n">показатель α</td>'+a.map(x=>`<td>${fp(x)}</td>`).join('')+'</tr><tr><td class="n">коэффициент c (нормир. примитивы)</td>'+d.map(x=>`<td>${fmt(x,4)}</td>`).join('')+'</tr></tbody></table>';
  let t='';if(st.set==='sto')t=st.n===1?'Один гауссиан: у ядра нет излома, а вдали функция спадает слишком быстро. Ошибка в энергии — 76 мЭ<sub>h</sub>, это 200 кДж/моль, больше энергии многих химических связей.':'Чем больше гауссианов, тем ближе сумма к слейтеровской функции. Но излом у ядра не воспроизводится никогда: у любой суммы гауссианов производная в нуле равна нулю. Переключите масштаб на логарифмический — там видно, что и «хвост» гауссианы описывают плохо: ln ψ у них падает как −αr², а не как −r.';
  else if(st.set==='opt')t='Показатели подобраны минимизацией энергии. Обратите внимание: они образуют почти геометрическую прогрессию (каждый следующий в 3–6 раз больше) — на этом основаны «равномерно-темперированные» базисы.';
  else t=B.bad?'Показатели слишком близки: функции почти линейно зависимы, матрица перекрывания вырождена.':'Сдвигайте показатели: энергия всегда остаётся выше −0,5 (вариационный принцип). Если два показателя сделать почти равными, функции становятся почти линейно зависимыми и выигрыша нет.';
  $('t1').innerHTML=t;
  // таблица сравнения
  $('cmpTab').innerHTML='<table class="mtab bt"><thead><tr><th class="n">n</th><th>STO-nG: E</th><th>ошибка, кДж/моль</th><th>оптимальные: E</th><th>ошибка, кДж/моль</th></tr></thead><tbody>'+Z.cmp.map(({n,es,esErr,eo,eoErr})=>{const s=es!=null;return `<tr><td class="n">${n}</td><td>${s?fmt(es,5):'—'}</td><td>${s?fmt(esErr,1):'—'}</td><td>${fmt(eo,5)}</td><td>${fmt(eoErr,1)}</td></tr>`}).join('')+'</tbody></table>'}
// ---------- часть 2 ----------
let la=0;
async function draw2(){let Z;try{Z=await live2({la})}catch(e){return}const a=Z.a;$('al').value=la;$('alv').textContent='α = '+fp(a,3);const svg=$('ea');svg.innerHTML='';
  const o={W:540,H:280,L:52,R:14,T:16,B:38,x0:-2,x1:0.6,y0:-2,y1:3,xt:[-2,-1,0],yt:[-2,-1.5,-1,-0.5,0,0.5,1,1.5,2,2.5,3],xl:'α (логарифмическая шкала)',xf:v=>fp(Math.pow(10,v),2),yf:v=>fmt(v,1)};const {X,Y}=axes(svg,o);
  const cl=v=>Math.max(o.y0,Math.min(o.y1,v)),Pp=pts=>path(pts,X,Y,o.y0,o.y1);
  el('line',{x1:o.L,x2:o.W-o.R,y1:Y(-0.5),y2:Y(-0.5),stroke:'var(--muted)','stroke-dasharray':'2 3','stroke-width':1.2},svg);
  el('path',{d:Pp(Z.cT),fill:'none',stroke:'var(--warn)','stroke-width':1.6,'stroke-dasharray':'6 4'},svg);
  el('path',{d:Pp(Z.cV),fill:'none',stroke:'var(--ok)','stroke-width':1.6,'stroke-dasharray':'6 4'},svg);
  el('path',{d:Pp(Z.cE),fill:'none',stroke:'var(--accent)','stroke-width':2.4},svg);
  const e={T:Z.T,V:Z.V},E=Z.E;el('circle',{cx:X(la),cy:Y(cl(E)),r:5.5,fill:'var(--accent)'},svg);
  const am=Z.am;el('circle',{cx:X(Z.lam),cy:Y(Z.Em),r:5,fill:'none',stroke:'var(--ok)','stroke-width':2},svg);
  $('kv2').innerHTML=`<span>T = <span class=fr><span>3α</span><span>2</span></span></span><b>${fmt(e.T,4)}</b><span>V = −2√<span class=fr><span>2α</span><span>π</span></span></span><b>${fmt(e.V,4)}</b><span>E = T + V</span><b>${fmt(E,4)}</b><span><span class=fr><span>V</span><span>T</span></span></span><b>${fmt(Z.VT,3)}</b>`;
  const atMin=Z.atMin;
  $('t2').innerHTML=atMin?`<b>Минимум:</b> <span class=fr><span>dE</span><span>dα</span></span> = 0 при α = <span class=fr><span>8</span><span>9π</span></span> = ${fmt(am,4)}, E = −<span class=fr><span>4</span><span>3π</span></span> = ${fmt(Z.Em,4)} ат. ед. Здесь V = −2T, как требует теорема вириала для кулоновского потенциала: она выполняется для точного решения и для любой функции, оптимальной по масштабу.`:
   `<span class=fr><span>V</span><span>T</span></span> = ${fmt(Z.VT,2)}, а для точного решения и для оптимального масштаба должно быть −2. ${a<am?'Функция слишком размыта: мала кинетическая энергия, но слабо и притяжение к ядру.':'Функция слишком сжата: притяжение сильное, но кинетическая энергия растёт ещё быстрее.'}`}
$('al').oninput=e=>{la=+e.target.value;draw2()};$('alMin').onclick=async()=>{let Z;try{Z=await QC.api('basis.part2',{la})}catch(e){return}la=Z.lam;draw2()};
// ---------- часть 3 ----------
const ERRT={empty:()=>'Пустая формула',syntax:()=>'Не понимаю формулу: используйте символы элементов и числа, например C2H6O',element:a=>`Элемент ${a[0]} не поддерживается: только H, B, C, N, O, F`};
const PRES=[['H2','H₂'],['H2O','H₂O'],['CH4','CH₄'],['C6H6','бензол'],['C2H6O','этанол'],['C9H8O4','аспирин'],['C8H10N4O2','кофеин'],['C27H46O','холестерин']];
let selB='6-31G(d)';
const subF=f=>f.replace(/\s/g,'').replace(/\d/g,c=>'₀₁₂₃₄₅₆₇₈₉'[+c]);
async function draw3(){chips('fmG',PRES.map(([f,l])=>[f,l]),$('fm').value.replace(/\s/g,''),v=>{$('fm').value=v;draw3()});
  let P;try{P=await live3({f:$('fm').value})}catch(e){return}if(P.err){$('fmErr').textContent=ERRT[P.err](P.a||[]);$('bTab').innerHTML='';$('bBar').innerHTML='';$('t3').textContent='';return}$('fmErr').textContent='';
  const heavy=P.heavy,nH=P.nH;
  const rows=P.rows;
  const occ=P.occ;
  $('bTab').innerHTML='<table class="mtab bt"><thead><tr><th class="n">базис</th><th class="n">тяжёлый атом</th><th class="n">H</th><th>N функций</th><th>примитивов</th><th>занятых / виртуальных</th><th>интегралов ≈ <span class=fr><span>N⁴</span><span>8</span></span></th><th>память, 8 байт на интеграл</th><th>время HF ∝ N⁴ (STO-3G = 1)</th></tr></thead><tbody>'+
    rows.map(r=>`<tr class="${r.b===selB?'sel':''}" data-b="${r.b}" style="cursor:pointer"><td class="n">${r.b}</td><td class="nt">${heavy?r.nX:'—'}</td><td class="nt">${nH?r.nHn:'—'}</td><td>${r.nf}</td><td>${r.np}</td><td>${occ} / ${r.nf-occ}</td><td>${big(r.ints)}</td><td>${bytes(r.mem)}</td><td>${big(r.rel)}</td></tr>`).join('')+'</tbody></table>';
  $('bTab').querySelectorAll('[data-b]').forEach(tr=>tr.onclick=()=>{selB=tr.dataset.b;draw3()});
  // столбики (лог. шкала N) + стоимость
  const svg=$('bBar');svg.innerHTML='';const L=120,Rm=200,T=10,rowH=(300-T-24)/rows.length,mx=Math.max(...rows.map(r=>r.nf));const lmax=Math.ceil(Math.log10(mx)+0.05),lmin=Math.floor(Math.log10(Math.min(...rows.map(r=>r.nf))));
  const X=v=>L+(Math.log10(v)-lmin)/(lmax-lmin)*(900-L-Rm);
  for(let k=lmin;k<=lmax;k++){el('line',{x1:X(Math.pow(10,k)),x2:X(Math.pow(10,k)),y1:T,y2:300-22,stroke:'var(--line)','stroke-width':1},svg);el('text',{x:X(Math.pow(10,k)),y:296,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,String(Math.pow(10,k)))}
  rows.forEach((r,i)=>{const y=T+i*rowH;el('text',{x:L-8,y:y+rowH/2+4,'text-anchor':'end','font-size':12.5,fill:'var(--ink)','font-weight':r.b===selB?600:400},svg,r.b);
    el('rect',{x:L,y:y+3,width:Math.max(1,X(r.nf)-L),height:rowH-6,rx:3,fill:r.b===selB?'var(--accent)':'var(--acc-bg)',stroke:'var(--accent)','stroke-width':1},svg);
    el('text',{x:X(r.nf)+6,y:y+rowH/2+4,'font-size':12,fill:'var(--ink)','font-family':'var(--f-mono)'},svg,String(r.nf));
    el('text',{x:900-8,y:y+rowH/2+4,'text-anchor':'end','font-size':12,fill:'var(--muted)','font-family':'var(--f-mono)'},svg,'×'+big(r.rel)+' по времени HF')});
  const s=rows.find(r=>r.b===selB);const ri=s.ints;
  $('t3').innerHTML=`<b>${selB}</b> для ${subF($('fm').value)}: базисных функций N = ${s.nf}; занятых орбиталей — ${occ}, виртуальных — ${s.nf-occ}. Уникальных интегралов (μν|λσ) около ${big(ri)} — ${bytes(s.mem)} памяти. `+
    (s.direct?'Хранить их негде, поэтому современные программы работают в «прямом» режиме: пересчитывают интегралы на каждой итерации SCF, отбрасывая пренебрежимо малые. ':'Такой массив ещё помещается в память обычного компьютера. ')+
    `Время HF формально растёт как N⁴. Для коррелированных методов важно, какое пространство растёт: при смене базиса число занятых орбиталей (${occ}) не меняется, растёт только виртуальное, а ведущий член CCSD(T) стоит ~n<sub>occ</sub>³n<sub>virt</sub>⁴. Закон N⁷ относится к одновременному росту обоих пространств — например, при увеличении молекулы.`}
$('fm').addEventListener('input',draw3);
draw1();draw2();draw3();
