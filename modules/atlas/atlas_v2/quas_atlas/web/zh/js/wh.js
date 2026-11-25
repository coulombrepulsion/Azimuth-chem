/* Woodward-Hoffmann page (Atlas v2).  The Hueckel orbitals, the electrocyclic
   frontier orbital, the correlation diagrams and the cycloaddition analysis come
   from quas_atlas.core.huckel (endpoints wh.hk, wh.electro, wh.correl, wh.cyclo);
   this script draws. */
// Метод Хюккеля: π-система из атомов с параметрами h (α_X = α + hβ) и k (β_CX = kβ)
const HT={
 C :{lab:'C',h:0,  k:1,  z:1,name:'C'},
 N1:{lab:'N',h:0.5,k:1,  z:1,name:'吡啶型 N（1 个 π 电子）'},
 N2:{lab:'N',h:1.5,k:0.8,z:2,name:'吡咯型 N（2 个 π 电子）'},
 O1:{lab:'O',h:1.0,k:1,  z:1,name:'羰基型 O（1 个 π 电子）'},
 O2:{lab:'O',h:2.0,k:0.8,z:2,name:'呋喃型 O（2 个 π 电子）'}};
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
const fmt=(x,d=3)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const eLab=x=>{if(Math.abs(x)<5e-4)return 'α';const a=Math.abs(x);return 'α '+(x>0?'+ ':'− ')+(Math.abs(a-1)<5e-4?'':fmt(a))+'β'};
function chips(id,items,cur,set){const g=$(id);g.innerHTML='';items.forEach(([v,l])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.innerHTML=l;b.setAttribute('aria-pressed',v===cur);b.onclick=()=>set(v);g.appendChild(b)})}
// лепестки p-орбитали: верхний — знак c; угол в градусах (по часовой стрелке)
function lobes(svg,x,y,c,ang,scale=1,op=1){const a=Math.abs(c);if(a<1e-3){el('text',{x,y:y+4,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,'×');return}
  const L=(14+50*a)*scale,w=L*0.42,g=el('g',{transform:`rotate(${ang} ${x} ${y})`,opacity:op},svg);const up=c>0;
  el('ellipse',{cx:x,cy:y-L/2,rx:w,ry:L/2,fill:up?'var(--lp-bg)':'var(--ln-bg)',stroke:up?'var(--lp)':'var(--ln)','stroke-width':1.5},g);
  el('ellipse',{cx:x,cy:y+L/2,rx:w,ry:L/2,fill:up?'var(--ln-bg)':'var(--lp-bg)',stroke:up?'var(--ln)':'var(--lp)','stroke-width':1.5},g)}
const rot=(dx,dy,deg)=>{const t=deg*Math.PI/180;return [dx*Math.cos(t)-dy*Math.sin(t),dx*Math.sin(t)+dy*Math.cos(t)]};
// ---------- 1. π-орбитали (метод Хюккеля) ----------
const HK=[{k:'eth',n:2,name:'乙烯',ring:false,ch:0},{k:'all+',n:3,name:'烯丙基正离子',ring:false,ch:1},{k:'buta',n:4,name:'丁二烯',ring:false,ch:0},
 {k:'hexa',n:6,name:'己三烯',ring:false,ch:0},{k:'cbd',n:4,name:'环丁二烯',ring:true,ch:0},{k:'bz',n:6,name:'苯',ring:true,ch:0}];
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
  el('text',{x:30,y:24,'font-size':11.5,fill:'var(--muted)'},svg,'能量 ↑');
  R.shells.forEach(sh=>{const g=sh.mo.length;sh.mo.forEach((i,j)=>{const cx=g===1?200:200+(j-(g-1)/2)*90,y=Y(mos[i].x),on=i===hk.mo;
      el('line',{x1:cx-32,x2:cx+32,y1:y,y2:y,stroke:on?'var(--accent)':'var(--ink)','stroke-width':on?3.6:2.2},svg);
      const o=Math.round(mos[i].occ*1e6)/1e6;const ne=o>=1.999?2:(o>=0.999?1:(o>0.4?1:0));
      [[-7,true],[7,false]].slice(0,ne).forEach(([dx,up])=>{const a=up?[y+8,y-8]:[y-8,y+8];el('line',{x1:cx+dx,y1:a[0],x2:cx+dx,y2:a[1],stroke:'var(--ink)','stroke-width':1.6},svg);el('path',{d:`M${cx+dx-3},${a[1]+(up?5:-5)} L${cx+dx},${a[1]} L${cx+dx+3},${a[1]+(up?5:-5)}`,fill:'none',stroke:'var(--ink)','stroke-width':1.6},svg)});
      const r=el('rect',{x:cx-36,y:y-12,width:72,height:24,fill:'transparent',class:'lv',tabindex:0,role:'button','aria-label':'ψ'+(i+1)},svg);
      r.addEventListener('click',()=>{hk.mo=i;sec0()});r.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();hk.mo=i;sec0()}})});
    el('text',{x:330,y:Y(sh.x)+4,'font-size':12,fill:'var(--muted)','font-family':'var(--f-mono)'},svg,eLab(sh.x)+(sh.mo.length>1?'  (×'+sh.mo.length+')':''))});
  // текст
  const occ=m.occ>1.5?'占据':(m.occ>0.1?'半占据':'空'),isH=R.homo>=0&&R.shells[R.homo].mo.includes(hk.mo),isL=R.lumo>=0&&R.shells[R.lumo].mo.includes(hk.mo);
  let t=`<b>ψ<sub>${hk.mo+1}</sub></b>（${occ}${isH?'，HOMO':''}${isL?'，LUMO':''}）：E = ${eLab(m.x)}。`;
  if(!d.ring)t+=`由 ${n} 个原子组成的链能级不简并，ψ<sub>k</sub> 恰好有 k − 1 个节点（沿链的变号次数）：节点越多，能量越高。对伍德沃德–霍夫曼规则重要的是末端的符号：ψ<sub>${hk.mo+1}</sub> 的末端符号${m.c[0]*m.c[n-1]>0?'<b>相同</b>':'<b>相反</b>'}。`;
  else t+=`在环中，除最低能级（n 为偶数时还有最高能级）外，其余能级都是二重简并的——这就是 Frost 圆。`+(n===6?'六个 π 电子（4n + 2）填满所有成键能级，壳层闭合——苯具有芳香性。':'四个 π 电子（4n）：其中两个各占据一对简并非键能级中的一个——环丁二烯具有反芳香性（实际上它会畸变为长方形）。');
  if(R.DE!=null)t+=`与孤立 C=C 键相比的离域能：${fmt(R.DE,3)}|β|。`;
  $('t0').innerHTML=t}
// ---------- 2. электроциклические ----------
const SYS=[{k:'buta',n:4,ne:4,name:'丁二烯 → 环丁烯',a:'丁二烯',p:'环丁烯'},{k:'hexa',n:6,ne:6,name:'己三烯 → 环己二烯',a:'己三烯',p:'环己二烯'},
 {k:'al+',n:3,ne:2,name:'烯丙基正离子 → 环丙基正离子',a:'烯丙基正离子',p:'环丙基正离子'},{k:'pd+',n:5,ne:4,name:'戊二烯基正离子 → 环戊烯基正离子',a:'戊二烯基正离子',p:'环戊烯基正离子'}];
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
    el('text',{x:210,y:30,'text-anchor':'middle','font-size':13,'font-weight':600,fill:bond?'var(--ok)':'var(--warn)'},svg,bond?'同相重叠 — 形成键':'反相重叠 — 节点')}
  if(th>=85){const cis=mode==='dis';el('text',{x:210,y:292,'text-anchor':'middle','font-size':12.5,fill:'var(--ink)'},svg,'Me '+(cis?'在同一侧 — 顺式产物':'在两侧 — 反式产物'))}
  return bond}
async function sec1(){const s=E1();let ev;try{ev=await liveE({sys:st.sys,photo:st.photo})}catch(e){return}
  chips('sysG',SYS.map(x=>[x.k,x.name]),st.sys,v=>{st.sys=v;st.th=0;sec1()});
  chips('condG',[[false,'加热'],[true,'光照（hν）']],st.photo,v=>{st.photo=v;sec1()});
  $('condHint').innerHTML=st.photo?`显示激发态的 HOMO — 即原来的 LUMO ψ<sub>${ev.fo+1}</sub>`:`显示 HOMO ψ<sub>${ev.fo+1}</sub>`;
  $('th').value=st.th;$('thv').textContent=st.th+'°';
  drawPanel('pCon','con',ev);drawPanel('pDis','dis',ev);
  const ok=ev.allowed;[['vCon','con'],['vDis','dis']].forEach(([id,m])=>{const e=$(id);e.className='verd '+(ok===m?'ok':'no');e.textContent=ok===m?'允许':'禁阻'});
  const k=s.ne,typ=k%4===0?'4n':'4n + 2',c1=ev.c[0],cn=ev.c[s.n-1];
  $('t1').innerHTML=`${s.a[0].toUpperCase()+s.a.slice(1)}：${k} 个 π 电子${k===2?'':k===4?'':''}（${typ}）。起决定作用的是轨道 ψ<sub>${ev.fo+1}</sub>：两端系数 c₁ = ${fmt(c1)}，c<sub>${s.n}</sub> = ${fmt(cn)} — 符号${c1*cn>0?'相同':'相反'}。要使两端相向转动时同号的波瓣相遇，两端必须${ok==='con'?'同向转动 — <b>顺旋</b>':'反向转动 — <b>对旋</b>'}。${st.photo?'光照时电子跃迁到 LUMO，其两端的对称性不同 — 允许的方式随之反转。':'点击“光照”— 方式将改变。'}`;
  sec1c()}
async function sec1c(){const s=E1();let C;try{C=await liveC({sys:st.sys,mode:st.cor})}catch(e){return}chips('corG',[['con','C₂（顺旋）'],['dis','σ（对旋）']],st.cor,v=>{st.cor=v;sec1c()});
  const svg=$('corr');svg.innerHTML='';const Y=x=>205+x*62,xl=[70,170],xr=[350,450];
  el('text',{x:120,y:16,'text-anchor':'middle','font-size':13,'font-weight':600,fill:'var(--ink)'},svg,s.a);el('text',{x:400,y:16,'text-anchor':'middle','font-size':13,'font-weight':600,fill:'var(--ink)'},svg,s.p);
  el('text',{x:260,y:16,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,'对称性：'+(st.cor==='con'?'C₂':'σ'));
  const half=s.ne/2;
  C.links.forEach(([i,j])=>{const bad=C.occL[i]>0&&j>=half;el('line',{x1:xl[1],y1:Y(C.L[i].x),x2:xr[0],y2:Y(C.R[j].x),stroke:bad?'var(--warn)':'var(--muted)','stroke-width':bad?2.6:1.2,'stroke-dasharray':bad?'none':'4 3'},svg)});
  const lev=(o,x0,x1,occ,left)=>{const y=Y(o.x);el('line',{x1:x0,x2:x1,y1:y,y2:y,stroke:'var(--ink)','stroke-width':2.4},svg);
    el('text',{x:left?x0-8:x1+8,y:y+4,'text-anchor':left?'end':'start','font-size':12.5,fill:'var(--ink)'},svg,o.name+' ');
    el('text',{x:left?x0-8-(o.name.length*7+8):x1+8+(o.name.length*7+8),y:y+4,'text-anchor':left?'end':'start','font-size':12,fill:o.sym==='S'?'var(--accent)':'var(--rho-l)','font-weight':600},svg,o.sym);
    if(occ>=1){const cx=(x0+x1)/2;[[-7,true],[7,false]].slice(0,occ).forEach(([dx,up])=>{const a=up?[y+8,y-8]:[y-8,y+8];el('line',{x1:cx+dx,y1:a[0],x2:cx+dx,y2:a[1],stroke:'var(--ink)','stroke-width':1.6},svg);el('path',{d:`M${cx+dx-3},${a[1]+(up?5:-5)} L${cx+dx},${a[1]} L${cx+dx+3},${a[1]+(up?5:-5)}`,fill:'none',stroke:'var(--ink)','stroke-width':1.6},svg)})}};
  C.L.forEach((o,i)=>lev(o,xl[0],xl[1],C.occL[i],true));C.R.forEach((o,j)=>lev(o,xr[0],xr[1],C.occR[j],false));
  el('text',{x:260,y:398,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'S — 对称，A — 反对称；');el('text',{x:260,y:413,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'右侧 — 电子沿连线去往何处');
  const badL=C.links.filter(([i,j])=>C.occL[i]>0&&j>=half).map(([i,j])=>C.L[i].name+' → '+C.R[j].name);
  $('t2').innerHTML=C.ok?`保持${st.cor==='con'?'C₂ 轴':'σ 镜面'}时，${s.a}的每个占据轨道都转化为产物的占据轨道（连线按能量顺序连接同一对称性的能级，互不交叉）。基态与基态相关联：反应<b>热允许</b>。`:
    `占据轨道与空轨道相关联：${badL.join(', ')}（红线）。反应物的基态转化为产物的激发态，因此途中存在高能垒：反应<b>热禁阻</b>。光照时电子已处于较高的轨道上，正是这条途径变得可行。`}
let anim=null;function play(){if(anim)cancelAnimationFrame(anim);const from=st.th>=90?0:st.th,t0=performance.now(),dur=matchMedia('(prefers-reduced-motion: reduce)').matches?1:1600*(90-from)/90;
  const step=now=>{const k=Math.min(1,(now-t0)/dur);st.th=Math.round(from+(90-from)*k);sec1();if(k<1)anim=requestAnimationFrame(step);else anim=null};anim=requestAnimationFrame(step)}
$('th').oninput=e=>{st.th=+e.target.value;sec1()};$('play').onclick=play;
// ---------- 3. циклоприсоединение ----------
const COMP={eth:{name:'乙烯',t:['C','C'],ends:[0,1],ne:2},buta:{name:'丁二烯',t:['C','C','C','C'],ends:[0,3],ne:4},hexa:{name:'己三烯',t:Array(6).fill('C'),ends:[0,5],ne:6},
  acro:{name:'丙烯醛',t:['O1','C','C','C'],ends:[2,3],ne:4,nr:2}};
async function sec2(){chips('aG',[['eth','乙烯（2π）'],['buta','丁二烯（4π）'],['hexa','己三烯（6π）']],st.A,v=>{st.A=v;st.pair=null;sec2()});
  chips('bG',[['eth','乙烯（2π）'],['acro','丙烯醛（C=C–C=O）'],['buta','丁二烯（4π）']],st.B,v=>{st.B=v;st.pair=null;sec2()});
  chips('cond2G',[[false,'加热'],[true,'光照 A（hν）']],st.photo2,v=>{st.photo2=v;st.pair=null;sec2()});
  let Z;try{Z=await liveY({A:st.A,B:st.B,photo:st.photo2,pair:st.pair})}catch(e){return}
  const A={...COMP[st.A],t:Z.tA},B={...COMP[st.B],t:Z.tB},hA=Z.hA,lA=Z.lA,hB=Z.hB,lB=Z.lB;const xA=Z.xA,xB=Z.xB;
  // пары: [индекс МО A, индекс МО B, подпись]
  const pairs=st.photo2?[['LL',lA,lB,'SOMO*(A) – LUMO(B)'],['HH',hA,hB,'SOMO(A) – HOMO(B)']]:[['HL',hA,lB,'HOMO(A) – LUMO(B)'],['LH',lA,hB,'LUMO(A) – HOMO(B)']];
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
    el('text',{x:p[0]+(p[0]<230?-14:14),y:(p[1]+q[1])/2+4,'text-anchor':p[0]<230?'end':'start','font-size':12.5,'font-weight':600,fill:s>0?'var(--ok)':'var(--warn)'},svg,s>0?'同相':'反相')});
  el('text',{x:230,y:22,'text-anchor':'middle','font-size':12.5,fill:'var(--ink)'},svg,'A: '+A.name+' — '+(pr[0][0]==='H'?(st.photo2?'SOMO':'HOMO'):(st.photo2?'SOMO*':'LUMO')));
  el('text',{x:230,y:330,'text-anchor':'middle','font-size':12.5,fill:'var(--ink)'},svg,'B: '+B.name+' — '+(pr[0][1]==='H'?'HOMO':'LUMO'));
  // уровни
  svg=$('lev');svg.innerHTML='';const all=[...xA,...xB],hi=Math.max(...all)+0.3,lo=Math.min(...all)-0.3,Y=x=>40+(x-lo)/(hi-lo)*270;el('text',{x:6,y:40,'font-size':11.5,fill:'var(--muted)'},svg,'能量 ↑');
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
  let t=`在环状过渡态中有 ${k} 个 π 电子${k%10>=2&&k%10<=4&&(k<10||k>20)?'':''}（${rule?'4n + 2':'4n'}）${st.B==='acro'?' — 丙烯醛只有 C=C 键参与':''}。按前线轨道分析：${allowed?'两端均为同相重叠 — <b>反应允许</b>':'一端相位不匹配 — <b>反应禁阻</b>（同面-同面）'}${st.photo2?' （光化学条件下）':' （加热条件下）'}。`;
  if(!st.photo2&&st.A==='buta'&&st.B!=='buta'){const gE=Z.gE,gC=Z.gC;t+=st.B==='acro'?`丙烯醛是“缺电子”亲双烯体：羰基降低了它的 LUMO，HOMO(双烯)–LUMO(亲双烯体) 能隙为 ${fmt(gC,2)}|β|，而乙烯为 ${fmt(gE,2)}|β|。能隙越小，相互作用越强，Diels–Alder 反应越快。`:'这是 Diels–Alder 反应。请与以丙烯醛为亲双烯体的情形比较。'}
  else if(!st.photo2&&!allowed)t+='开启光照：处于原 LUMO 上的激发电子改变了前线轨道的对称性 — [2+2] 环加成因而成为光化学允许的反应。';
  $('t3').innerHTML=t}
// ---------- 4. сводка ----------
$('rules').innerHTML='<table class="mtab bt"><thead><tr><th class="n">反应</th><th class="n">π 电子数</th><th class="n">加热</th><th class="n">光照</th></tr></thead><tbody>'+
 '<tr><td class="n">电环化</td><td class="n">4n（丁二烯、烯丙基负离子）</td><td class="n">顺旋</td><td class="n">对旋</td></tr>'+
 '<tr><td class="n">电环化</td><td class="n">4n + 2（己三烯、烯丙基正离子）</td><td class="n">对旋</td><td class="n">顺旋</td></tr>'+
 '<tr><td class="n">环加成，同面-同面</td><td class="n">4n（[2+2]、[4+4]）</td><td class="n">禁阻</td><td class="n">允许</td></tr>'+
 '<tr><td class="n">环加成，同面-同面</td><td class="n">4n + 2（[4+2]、[6+4]）</td><td class="n">允许</td><td class="n">禁阻</td></tr></tbody></table>'+
 '<p class="hint" style="margin-top:8px">伍德沃德–霍夫曼通用规则：若 (4q + 2)<sub>s</sub> 与 (4r)<sub>a</sub> 组分的总数为奇数，则热周环反应是允许的；s 为同面组分，a 为异面组分。“禁阻”意味着能垒高，而不是不可能发生。</p>';
sec0();sec1();sec2();
