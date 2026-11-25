/* Woodward-Hoffmann page (Atlas v2).  The Hueckel orbitals, the electrocyclic
   frontier orbital, the correlation diagrams and the cycloaddition analysis come
   from quas_atlas.core.huckel (endpoints wh.hk, wh.electro, wh.correl, wh.cyclo);
   this script draws. */
// Метод Хюккеля: π-система из атомов с параметрами h (α_X = α + hβ) и k (β_CX = kβ)
const HT={
 C :{lab:'C',h:0,  k:1,  z:1,name:'C'},
 N1:{lab:'N',h:0.5,k:1,  z:1,name:'N пиридиновый (1 π-электрон)'},
 N2:{lab:'N',h:1.5,k:0.8,z:2,name:'N пиррольный (2 π-электрона)'},
 O1:{lab:'O',h:1.0,k:1,  z:1,name:'O карбонильный (1 π-электрон)'},
 O2:{lab:'O',h:2.0,k:0.8,z:2,name:'O фурановый (2 π-электрона)'}};
const TYPE_CYCLE=['C','N1','N2','O1','O2'];
// Реакционная способность: только атомы C, у которых есть H (не более двух соседей)
// mode 'q' — зарядовый контроль, 'fo' — орбитальный (плотность ВЗМО/НСМО); радикал — по индексу свободной валентности
// Правила Вудворда–Хоффмана: логика на основе хюккелевских МО полиенов
// электроциклическая реакция: n атомов, ne π-электронов
// симметрия МО цепи: относительно зеркала (дисротация) S, если c_k = c_{n+1-k}; относительно C2 (конротация) S, если c_k = −c_{n+1-k}
// корреляционная диаграмма; mode 'con' (C2) или 'dis' (σ)
// ---------- страница «π-орбитали и перициклические реакции» ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=3)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('.',',').replace('-','−')};
const eLab=x=>{if(Math.abs(x)<5e-4)return 'α';const a=Math.abs(x);return 'α '+(x>0?'+ ':'− ')+(Math.abs(a-1)<5e-4?'':fmt(a))+'β'};
function chips(id,items,cur,set){const g=$(id);g.innerHTML='';items.forEach(([v,l])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.innerHTML=l;b.setAttribute('aria-pressed',v===cur);b.onclick=()=>set(v);g.appendChild(b)})}
// лепестки p-орбитали: верхний — знак c; угол в градусах (по часовой стрелке)
function lobes(svg,x,y,c,ang,scale=1,op=1){const a=Math.abs(c);if(a<1e-3){el('text',{x,y:y+4,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,'×');return}
  const L=(14+50*a)*scale,w=L*0.42,g=el('g',{transform:`rotate(${ang} ${x} ${y})`,opacity:op},svg);const up=c>0;
  el('ellipse',{cx:x,cy:y-L/2,rx:w,ry:L/2,fill:up?'var(--lp-bg)':'var(--ln-bg)',stroke:up?'var(--lp)':'var(--ln)','stroke-width':1.5},g);
  el('ellipse',{cx:x,cy:y+L/2,rx:w,ry:L/2,fill:up?'var(--ln-bg)':'var(--lp-bg)',stroke:up?'var(--ln)':'var(--lp)','stroke-width':1.5},g)}
const rot=(dx,dy,deg)=>{const t=deg*Math.PI/180;return [dx*Math.cos(t)-dy*Math.sin(t),dx*Math.sin(t)+dy*Math.cos(t)]};
// ---------- 1. π-орбитали (метод Хюккеля) ----------
const HK=[{k:'eth',n:2,name:'этилен',ring:false,ch:0},{k:'all+',n:3,name:'аллил-катион',ring:false,ch:1},{k:'buta',n:4,name:'бутадиен',ring:false,ch:0},
 {k:'hexa',n:6,name:'гексатриен',ring:false,ch:0},{k:'cbd',n:4,name:'циклобутадиен',ring:true,ch:0},{k:'bz',n:6,name:'бензол',ring:true,ch:0}];
const hk={sys:'buta',mo:null};
const liveHK=QC.live('wh.hk'),liveE=QC.live('wh.electro'),liveC=QC.live('wh.correl'),liveY=QC.live('wh.cyclo');
async function sec0(){const d=HK.find(x=>x.k===hk.sys);let R;try{R=await liveHK({sys:hk.sys})}catch(e){return}const n=d.n,mos=R.mos;
  chips('hkG',HK.map(x=>[x.k,x.name]),hk.sys,v=>{hk.sys=v;hk.mo=null;sec0()});
  const homoMO=R.homo>=0?R.shells[R.homo].mo[R.shells[R.homo].mo.length-1]:0;if(hk.mo==null||hk.mo>=mos.length)hk.mo=homoMO;
  const m=mos[hk.mo];
  // молекула
  let svg=$('hkMol');svg.innerHTML='';
  const P=d.ring?[...Array(n)].map((_,k)=>{const t=2*Math.PI*k/n-Math.PI/2-(n===4?Math.PI/4:0);return [230+95*Math.cos(t),150+95*Math.sin(t)]})
    :[...Array(n)].map((_,k)=>[230+(k-(n-1)/2)*Math.min(78,380/Math.max(1,n-1)),150+(k%2?28:-28)*(n>2?1:0)]);
  const bonds=[...Array(n-1)].map((_,i)=>[i,i+1]);if(d.ring)bonds.push([n-1,0]);
  bonds.forEach(([i,j])=>el('line',{x1:P[i][0],y1:P[i][1],x2:P[j][0],y2:P[j][1],stroke:'var(--ink)','stroke-width':2.2},svg));
  P.forEach((q,k)=>lobes(svg,q[0],q[1],m.c[k],0,0.85));
  P.forEach(q=>el('circle',{cx:q[0],cy:q[1],r:3.5,fill:'var(--ink)'},svg));
  el('text',{x:230,y:22,'text-anchor':'middle','font-size':13,'font-weight':600,fill:'var(--ink)'},svg,'ψ'+(hk.mo+1)+': E = '+eLab(m.x));
  // уровни
  svg=$('hkLev');svg.innerHTML='';const Y=x=>150+x*58;
  el('line',{x1:60,x2:400,y1:Y(0),y2:Y(0),stroke:'var(--muted)','stroke-dasharray':'3 4','stroke-width':1},svg);
  el('text',{x:54,y:Y(0)+4,'text-anchor':'end','font-size':12,fill:'var(--muted)'},svg,'α');
  el('text',{x:30,y:24,'font-size':11.5,fill:'var(--muted)'},svg,'энергия ↑');
  R.shells.forEach(sh=>{const g=sh.mo.length;sh.mo.forEach((i,j)=>{const cx=g===1?200:200+(j-(g-1)/2)*90,y=Y(mos[i].x),on=i===hk.mo;
      el('line',{x1:cx-32,x2:cx+32,y1:y,y2:y,stroke:on?'var(--accent)':'var(--ink)','stroke-width':on?3.6:2.2},svg);
      const o=Math.round(mos[i].occ*1e6)/1e6;const ne=o>=1.999?2:(o>=0.999?1:(o>0.4?1:0));
      [[-7,true],[7,false]].slice(0,ne).forEach(([dx,up])=>{const a=up?[y+8,y-8]:[y-8,y+8];el('line',{x1:cx+dx,y1:a[0],x2:cx+dx,y2:a[1],stroke:'var(--ink)','stroke-width':1.6},svg);el('path',{d:`M${cx+dx-3},${a[1]+(up?5:-5)} L${cx+dx},${a[1]} L${cx+dx+3},${a[1]+(up?5:-5)}`,fill:'none',stroke:'var(--ink)','stroke-width':1.6},svg)});
      const r=el('rect',{x:cx-36,y:y-12,width:72,height:24,fill:'transparent',class:'lv',tabindex:0,role:'button','aria-label':'ψ'+(i+1)},svg);
      r.addEventListener('click',()=>{hk.mo=i;sec0()});r.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();hk.mo=i;sec0()}})});
    el('text',{x:330,y:Y(sh.x)+4,'font-size':12,fill:'var(--muted)','font-family':'var(--f-mono)'},svg,eLab(sh.x)+(sh.mo.length>1?'  (×'+sh.mo.length+')':''))});
  // текст
  const occ=m.occ>1.5?'занята':(m.occ>0.1?'занята наполовину':'свободна'),isH=R.homo>=0&&R.shells[R.homo].mo.includes(hk.mo),isL=R.lumo>=0&&R.shells[R.lumo].mo.includes(hk.mo);
  let t=`<b>ψ<sub>${hk.mo+1}</sub></b> (${occ}${isH?', ВЗМО':''}${isL?', НСМО':''}): E = ${eLab(m.x)}. `;
  if(!d.ring)t+=`У цепи из ${n} атомов уровни невырождены, и у ψ<sub>k</sub> ровно k − 1 узлов (смен знака вдоль цепи): чем больше узлов, тем выше энергия. Для правил Вудворда–Хоффмана важны знаки на концах: у ψ<sub>${hk.mo+1}</sub> они ${m.c[0]*m.c[n-1]>0?'<b>одинаковые</b>':'<b>противоположные</b>'}. `;
  else t+=`У цикла уровни, кроме нижнего (и верхнего при чётном n), дважды вырождены — это круг Фроста. `+(n===6?'Шесть π-электронов (4n + 2) заполняют все связывающие уровни, оболочка замкнута — бензол ароматичен. ':'Четыре π-электрона (4n): два из них занимают вырожденную пару несвязывающих уровней по одному — циклобутадиен антиароматичен (в реальности он искажается в прямоугольник). ');
  if(R.DE!=null)t+=`Энергия делокализации по сравнению с изолированными связями C=C: ${fmt(R.DE,3)}|β|.`;
  $('t0').innerHTML=t}
// ---------- 2. электроциклические ----------
const SYS=[{k:'buta',n:4,ne:4,name:'Бутадиен → циклобутен',a:'бутадиен',p:'циклобутен'},{k:'hexa',n:6,ne:6,name:'Гексатриен → циклогексадиен',a:'гексатриен',p:'циклогексадиен'},
 {k:'al+',n:3,ne:2,name:'Аллил-катион → циклопропил-катион',a:'аллил-катион',p:'циклопропил-катион'},{k:'pd+',n:5,ne:4,name:'Пентадиенил-катион → циклопентенил-катион',a:'пентадиенил-катион',p:'циклопентенил-катион'}];
let st={sys:'buta',photo:false,th:0,cor:'con',A:'buta',B:'eth',photo2:false,pair:null};
function E1(){return SYS.find(s=>s.k===st.sys)}
function drawPanel(id,mode,ev){const svg=$(id);svg.innerHTML='';const s=E1(),n=s.n,c=ev.c,th=st.th;
  const P=[...Array(n)].map((_,k)=>{const t=k/(n-1);return [210-100*Math.cos(Math.PI*t),95+(n>2?120*Math.sin(Math.PI*t):0)]});
  for(let k=0;k<n-1;k++)el('line',{x1:P[k][0],y1:P[k][1],x2:P[k+1][0],y2:P[k+1][1],stroke:'var(--ink)','stroke-width':2.2},svg);
  // зарождающаяся связь
  if(th>0)el('line',{x1:P[0][0],y1:P[0][1],x2:P[n-1][0],y2:P[n-1][1],stroke:'var(--muted)','stroke-width':1.5,'stroke-dasharray':'4 4',opacity:th/90},svg);
  const aL=th,aR=mode==='con'?th:-th;
  // метильные группы: исходно наружу
  [[0,-1,aL],[n-1,1,aR]].forEach(([k,dir,ang])=>{const [dx,dy]=rot(dir*34,0,ang);el('line',{x1:P[k][0],y1:P[k][1],x2:P[k][0]+dx,y2:P[k][1]+dy,stroke:'var(--muted)','stroke-width':2},svg);
    const [tx,ty]=rot(dir*50,0,ang);el('text',{x:P[k][0]+tx,y:P[k][1]+ty+4,'text-anchor':'middle','font-size':12,fill:'var(--muted)','font-weight':600},svg,'Me')});
  for(let k=1;k<n-1;k++)lobes(svg,P[k][0],P[k][1],c[k],0,0.8,0.75);
  lobes(svg,P[0][0],P[0][1],c[0],aL);lobes(svg,P[n-1][0],P[n-1][1],c[n-1],aR);
  P.forEach(p=>el('circle',{cx:p[0],cy:p[1],r:3.5,fill:'var(--ink)'},svg));
  // перекрывание внутренних лепестков
  const inL=Math.sign(c[0]),inR=mode==='con'?-Math.sign(c[n-1]):Math.sign(c[n-1]),bond=inL===inR;
  if(th>=30){const k=(th-30)/60;el('path',{d:`M${P[0][0]+30},${P[0][1]} Q210,${P[0][1]-20} ${P[n-1][0]-30},${P[n-1][1]}`,fill:'none',stroke:bond?'var(--ok)':'var(--warn)','stroke-width':1.5+3*k,'stroke-dasharray':bond?'none':'5 4',opacity:0.4+0.6*k},svg);
    el('text',{x:210,y:30,'text-anchor':'middle','font-size':13,'font-weight':600,fill:bond?'var(--ok)':'var(--warn)'},svg,bond?'перекрывание в фазе — связь образуется':'перекрывание в противофазе — узел')}
  if(th>=85){const cis=mode==='dis';el('text',{x:210,y:292,'text-anchor':'middle','font-size':12.5,fill:'var(--ink)'},svg,'Me '+(cis?'по одну сторону — цис-продукт':'по разные стороны — транс-продукт'))}
  return bond}
async function sec1(){const s=E1();let ev;try{ev=await liveE({sys:st.sys,photo:st.photo})}catch(e){return}
  chips('sysG',SYS.map(x=>[x.k,x.name]),st.sys,v=>{st.sys=v;st.th=0;sec1()});
  chips('condG',[[false,'нагревание'],[true,'облучение (hν)']],st.photo,v=>{st.photo=v;sec1()});
  $('condHint').innerHTML=st.photo?`показана ВЗМО возбуждённого состояния — бывшая НСМО ψ<sub>${ev.fo+1}</sub>`:`показана ВЗМО ψ<sub>${ev.fo+1}</sub>`;
  $('th').value=st.th;$('thv').textContent=st.th+'°';
  drawPanel('pCon','con',ev);drawPanel('pDis','dis',ev);
  const ok=ev.allowed;[['vCon','con'],['vDis','dis']].forEach(([id,m])=>{const e=$(id);e.className='verd '+(ok===m?'ok':'no');e.textContent=ok===m?'разрешено':'запрещено'});
  const k=s.ne,typ=k%4===0?'4n':'4n + 2',c1=ev.c[0],cn=ev.c[s.n-1];
  $('t1').innerHTML=`${s.a[0].toUpperCase()+s.a.slice(1)}: ${k} π-электрон${k===2?'а':k===4?'а':'ов'} (${typ}). Решает орбиталь ψ<sub>${ev.fo+1}</sub>: на концах c₁ = ${fmt(c1)}, c<sub>${s.n}</sub> = ${fmt(cn)} — знаки ${c1*cn>0?'одинаковые':'противоположные'}. Чтобы при повороте навстречу друг другу оказались лепестки одного знака, концы должны вращаться ${ok==='con'?'в одну сторону — <b>конротаторно</b>':'в разные стороны — <b>дисротаторно</b>'}. ${st.photo?'При облучении электрон переходит на НСМО, у неё другая симметрия концов — и разрешённый режим меняется на противоположный.':'Нажмите «Облучение» — режим сменится.'}`;
  sec1c()}
async function sec1c(){const s=E1();let C;try{C=await liveC({sys:st.sys,mode:st.cor})}catch(e){return}chips('corG',[['con','C₂ (конротаторно)'],['dis','σ (дисротаторно)']],st.cor,v=>{st.cor=v;sec1c()});
  const svg=$('corr');svg.innerHTML='';const Y=x=>205+x*62,xl=[70,170],xr=[350,450];
  el('text',{x:120,y:16,'text-anchor':'middle','font-size':13,'font-weight':600,fill:'var(--ink)'},svg,s.a);el('text',{x:400,y:16,'text-anchor':'middle','font-size':13,'font-weight':600,fill:'var(--ink)'},svg,s.p);
  el('text',{x:260,y:16,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,'симметрия: '+(st.cor==='con'?'C₂':'σ'));
  const half=s.ne/2;
  C.links.forEach(([i,j])=>{const bad=C.occL[i]>0&&j>=half;el('line',{x1:xl[1],y1:Y(C.L[i].x),x2:xr[0],y2:Y(C.R[j].x),stroke:bad?'var(--warn)':'var(--muted)','stroke-width':bad?2.6:1.2,'stroke-dasharray':bad?'none':'4 3'},svg)});
  const lev=(o,x0,x1,occ,left)=>{const y=Y(o.x);el('line',{x1:x0,x2:x1,y1:y,y2:y,stroke:'var(--ink)','stroke-width':2.4},svg);
    el('text',{x:left?x0-8:x1+8,y:y+4,'text-anchor':left?'end':'start','font-size':12.5,fill:'var(--ink)'},svg,o.name+' ');
    el('text',{x:left?x0-8-(o.name.length*7+8):x1+8+(o.name.length*7+8),y:y+4,'text-anchor':left?'end':'start','font-size':12,fill:o.sym==='S'?'var(--accent)':'var(--rho-l)','font-weight':600},svg,o.sym);
    if(occ>=1){const cx=(x0+x1)/2;[[-7,true],[7,false]].slice(0,occ).forEach(([dx,up])=>{const a=up?[y+8,y-8]:[y-8,y+8];el('line',{x1:cx+dx,y1:a[0],x2:cx+dx,y2:a[1],stroke:'var(--ink)','stroke-width':1.6},svg);el('path',{d:`M${cx+dx-3},${a[1]+(up?5:-5)} L${cx+dx},${a[1]} L${cx+dx+3},${a[1]+(up?5:-5)}`,fill:'none',stroke:'var(--ink)','stroke-width':1.6},svg)})}};
  C.L.forEach((o,i)=>lev(o,xl[0],xl[1],C.occL[i],true));C.R.forEach((o,j)=>lev(o,xr[0],xr[1],C.occR[j],false));
  el('text',{x:260,y:398,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'S — симметрична, A — антисимметрична;');el('text',{x:260,y:413,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'справа — куда переходят электроны по линиям');
  const badL=C.links.filter(([i,j])=>C.occL[i]>0&&j>=half).map(([i,j])=>C.L[i].name+' → '+C.R[j].name);
  $('t2').innerHTML=C.ok?`При сохранении ${st.cor==='con'?'оси C₂':'плоскости σ'} каждая занятая орбиталь ${s.a}а переходит в занятую орбиталь продукта (линии соединяют уровни одной симметрии в порядке энергии, не пересекаясь). Основное состояние коррелирует с основным: реакция <b>термически разрешена</b>.`:
    `Занятая орбиталь коррелирует с незанятой: ${badL.join(', ')} (красные линии). Основное состояние реагента переходит в возбуждённое состояние продукта, поэтому на пути — высокий барьер: реакция <b>термически запрещена</b>. При облучении электрон уже на верхней орбитали, и именно этот путь становится доступным.`}
let anim=null;function play(){if(anim)cancelAnimationFrame(anim);const from=st.th>=90?0:st.th,t0=performance.now(),dur=matchMedia('(prefers-reduced-motion: reduce)').matches?1:1600*(90-from)/90;
  const step=now=>{const k=Math.min(1,(now-t0)/dur);st.th=Math.round(from+(90-from)*k);sec1();if(k<1)anim=requestAnimationFrame(step);else anim=null};anim=requestAnimationFrame(step)}
$('th').oninput=e=>{st.th=+e.target.value;sec1()};$('play').onclick=play;
// ---------- 3. циклоприсоединение ----------
const COMP={eth:{name:'этилен',t:['C','C'],ends:[0,1],ne:2},buta:{name:'бутадиен',t:['C','C','C','C'],ends:[0,3],ne:4},hexa:{name:'гексатриен',t:Array(6).fill('C'),ends:[0,5],ne:6},
  acro:{name:'акролеин',t:['O1','C','C','C'],ends:[2,3],ne:4,nr:2}};
async function sec2(){chips('aG',[['eth','этилен (2π)'],['buta','бутадиен (4π)'],['hexa','гексатриен (6π)']],st.A,v=>{st.A=v;st.pair=null;sec2()});
  chips('bG',[['eth','этилен (2π)'],['acro','акролеин (C=C–C=O)'],['buta','бутадиен (4π)']],st.B,v=>{st.B=v;st.pair=null;sec2()});
  chips('cond2G',[[false,'нагревание'],[true,'облучение A (hν)']],st.photo2,v=>{st.photo2=v;st.pair=null;sec2()});
  let Z;try{Z=await liveY({A:st.A,B:st.B,photo:st.photo2,pair:st.pair})}catch(e){return}
  const A={...COMP[st.A],t:Z.tA},B={...COMP[st.B],t:Z.tB},hA=Z.hA,lA=Z.lA,hB=Z.hB,lB=Z.lB;const xA=Z.xA,xB=Z.xB;
  // пары: [индекс МО A, индекс МО B, подпись]
  const pairs=st.photo2?[['LL',lA,lB,'ОЗМО*(A) – НСМО(B)'],['HH',hA,hB,'ОЗМО(A) – ВЗМО(B)']]:[['HL',hA,lB,'ВЗМО(A) – НСМО(B)'],['LH',lA,hB,'НСМО(A) – ВЗМО(B)']];
  st.pair=Z.pair;
  const pr=pairs.find(p=>p[0]===st.pair),cA=Z.cA,cB=Z.cB;
  const [a1,a2]=[0,A.t.length-1],[b1,b2]=Z.endsB;
  const s1=Z.s1,s2=Z.s2,allowed=Z.allowed;
  // рисунок: A сверху (дуга вниз концами), B снизу
  let svg=$('fmo');svg.innerHTML='';const XL=150,XR=310;
  const arc=(n,y0,dir)=>[...Array(n)].map((_,k)=>{const t=n>1?k/(n-1):0;return n===2?[XL+(XR-XL)*t,y0]:[230-80*Math.cos(Math.PI*t),y0+dir*70*Math.sin(Math.PI*t)]});
  const PA=arc(A.t.length,120,-1);let PB;
  if(st.B==='acro')PB=[[52,262],[100,240],[XL,220],[XR,220]];else PB=arc(B.t.length,220,1);
  const drawChain=(P,ch,c,ends,alpha)=>{for(let k=0;k<P.length-1;k++)el('line',{x1:P[k][0],y1:P[k][1],x2:P[k+1][0],y2:P[k+1][1],stroke:'var(--ink)','stroke-width':2.2},svg);
    P.forEach((p,k)=>{lobes(svg,p[0],p[1],c[k],0,0.75,ends.includes(k)?1:alpha);const het=ch[k]!=='C';el('circle',{cx:p[0],cy:p[1],r:het?9:3.5,fill:het?'var(--panel)':'var(--ink)',stroke:het?'var(--el)':'none','stroke-width':1.5},svg);if(het)el('text',{x:p[0],y:p[1]+4.5,'text-anchor':'middle','font-size':12,'font-weight':600,fill:'var(--el)'},svg,'O')})};
  drawChain(PA,A.t,cA,[a1,a2],0.55);drawChain(PB,B.t,cB,[b1,b2],0.55);
  [[PA[a1],PB[b1],s1],[PA[a2],PB[b2],s2]].forEach(([p,q,s])=>{el('line',{x1:p[0],y1:p[1]+30,x2:q[0],y2:q[1]-30,stroke:s>0?'var(--ok)':'var(--warn)','stroke-width':3,'stroke-dasharray':s>0?'none':'5 4'},svg);
    el('text',{x:p[0]+(p[0]<230?-14:14),y:(p[1]+q[1])/2+4,'text-anchor':p[0]<230?'end':'start','font-size':12.5,'font-weight':600,fill:s>0?'var(--ok)':'var(--warn)'},svg,s>0?'в фазе':'в противофазе')});
  el('text',{x:230,y:22,'text-anchor':'middle','font-size':12.5,fill:'var(--ink)'},svg,'A: '+A.name+' — '+(pr[0][0]==='H'?(st.photo2?'ОЗМО':'ВЗМО'):(st.photo2?'ОЗМО*':'НСМО')));
  el('text',{x:230,y:330,'text-anchor':'middle','font-size':12.5,fill:'var(--ink)'},svg,'B: '+B.name+' — '+(pr[0][1]==='H'?'ВЗМО':'НСМО'));
  // уровни
  svg=$('lev');svg.innerHTML='';const all=[...xA,...xB],hi=Math.max(...all)+0.3,lo=Math.min(...all)-0.3,Y=x=>40+(x-lo)/(hi-lo)*270;el('text',{x:6,y:40,'font-size':11.5,fill:'var(--muted)'},svg,'энергия ↑');
  el('line',{x1:40,x2:440,y1:Y(0),y2:Y(0),stroke:'var(--muted)','stroke-dasharray':'3 4','stroke-width':1},svg);el('text',{x:36,y:Y(0)+4,'text-anchor':'end','font-size':12,fill:'var(--muted)'},svg,'α');
  el('text',{x:110,y:16,'text-anchor':'middle','font-size':12.5,'font-weight':600,fill:'var(--ink)'},svg,'A: '+A.name);el('text',{x:350,y:16,'text-anchor':'middle','font-size':12.5,'font-weight':600,fill:'var(--ink)'},svg,'B: '+B.name);
  const occA=Z.occA,occB=Z.occB;
  const draw=(xs,occ,cx,hl)=>xs.forEach((x,i)=>{const y=Y(x),on=i===hl;el('line',{x1:cx-28,x2:cx+28,y1:y,y2:y,stroke:on?'var(--accent)':'var(--ink)','stroke-width':on?3.6:2},svg);
    el('text',{x:cx+(cx<230?-36:36),y:y+4,'text-anchor':cx<230?'end':'start','font-size':11.5,fill:'var(--muted)','font-family':'var(--f-mono)'},svg,eLab(x));
    const o=occ[i];[[-6,true],[6,false]].slice(0,o).forEach(([dx,up])=>{const a=up?[y+8,y-8]:[y-8,y+8];el('line',{x1:cx+dx,y1:a[0],x2:cx+dx,y2:a[1],stroke:'var(--ink)','stroke-width':1.5},svg);el('path',{d:`M${cx+dx-3},${a[1]+(up?5:-5)} L${cx+dx},${a[1]} L${cx+dx+3},${a[1]+(up?5:-5)}`,fill:'none',stroke:'var(--ink)','stroke-width':1.5},svg)})});
  draw(xA,occA,110,pr[1]);draw(xB,occB,350,pr[2]);
  el('line',{x1:140,y1:Y(xA[pr[1]]),x2:320,y2:Y(xB[pr[2]]),stroke:'var(--accent)','stroke-width':1.6,'stroke-dasharray':'5 4'},svg);
  el('text',{x:230,y:Math.min(Y(xA[pr[1]]),Y(xB[pr[2]]))-12,'text-anchor':'middle','font-size':12.5,fill:'var(--accent)','font-weight':600},svg,'Δ = '+fmt(Z.gap,2)+'|β|');
  const k=Z.k,rule=Z.rule;
  let t=`В циклическом переходном состоянии ${k} π-электрон${k%10>=2&&k%10<=4&&(k<10||k>20)?'а':'ов'} (${rule?'4n + 2':'4n'})${st.B==='acro'?' — у акролеина участвует только связь C=C':''}. По граничным орбиталям: ${allowed?'перекрывание в фазе на обоих концах — <b>реакция разрешена</b>':'на одном конце фазы не совпадают — <b>реакция запрещена</b> (супра-супра)'}${st.photo2?' фотохимически':' термически'}. `;
  if(!st.photo2&&st.A==='buta'&&st.B!=='buta'){const gE=Z.gE,gC=Z.gC;t+=st.B==='acro'?`Акролеин — «электронодефицитный» диенофил: карбонил опускает его НСМО, щель ВЗМО(диен)–НСМО(диенофил) ${fmt(gC,2)}|β| вместо ${fmt(gE,2)}|β| у этилена. Чем меньше щель, тем сильнее взаимодействие и быстрее реакция Дильса–Альдера.`:'Это реакция Дильса–Альдера. Сравните с акролеином в качестве диенофила.'}
  else if(!st.photo2&&!allowed)t+='Включите облучение: возбуждённый электрон на бывшей НСМО меняет симметрию граничной орбитали — и [2+2]-циклоприсоединение становится фотохимически разрешённым.';
  $('t3').innerHTML=t}
// ---------- 4. сводка ----------
$('rules').innerHTML='<table class="mtab bt"><thead><tr><th class="n">реакция</th><th class="n">π-электронов</th><th class="n">нагревание</th><th class="n">облучение</th></tr></thead><tbody>'+
 '<tr><td class="n">электроциклическая</td><td class="n">4n (бутадиен, аллил-анион)</td><td class="n">конротаторно</td><td class="n">дисротаторно</td></tr>'+
 '<tr><td class="n">электроциклическая</td><td class="n">4n + 2 (гексатриен, аллил-катион)</td><td class="n">дисротаторно</td><td class="n">конротаторно</td></tr>'+
 '<tr><td class="n">циклоприсоединение, супра-супра</td><td class="n">4n ([2+2], [4+4])</td><td class="n">запрещено</td><td class="n">разрешено</td></tr>'+
 '<tr><td class="n">циклоприсоединение, супра-супра</td><td class="n">4n + 2 ([4+2], [6+4])</td><td class="n">разрешено</td><td class="n">запрещено</td></tr></tbody></table>'+
 '<p class="hint" style="margin-top:8px">Общее правило Вудворда–Хоффмана: термическая перициклическая реакция разрешена, если суммарное число компонентов (4q + 2)<sub>s</sub> и (4r)<sub>a</sub> нечётно; s — супраповерхностный компонент, a — антараповерхностный. «Запрещено» означает высокий барьер, а не невозможность.</p>';
sec0();sec1();sec2();
