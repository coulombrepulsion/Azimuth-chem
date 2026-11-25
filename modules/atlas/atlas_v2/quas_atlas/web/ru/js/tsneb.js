const LG=(document.documentElement.lang||'ru').slice(0,2),NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
const tr=o=>o[LG]||o.ru,DEC=LG==='ru'?',':'.';
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('.',DEC).replace('-','−')};
const SUP=s=>String(s).split('').map(c=>c==='-'?'⁻':'⁰¹²³⁴⁵⁶⁷⁸⁹'[+c]).join('');
function sci(x,d=2){if(!isFinite(x))return '—';if(x===0)return '0';const e=Math.floor(Math.log10(Math.abs(x)));if(e>=-2&&e<5)return fmt(x,e>=3?0:e>=1?1:d);return fmt(x/Math.pow(10,e),d)+'·10'+SUP(e)}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
const card=(a,b,c)=>'<div class="card"><span class="t">'+a+'</span><b>'+b+'</b>'+(c?'<small>'+c+'</small>':'')+'</div>';
const num=s=>Number(String(s).trim().replace(',','.').replace('−','-'));
/* redraw when the theme changes (the hub sets data-theme on the page) */
function onTheme(f){matchMedia('(prefers-color-scheme: dark)').addEventListener('change',f);new MutationObserver(f).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']})}
/* axis helper: a frame with ticks; returns X(v), Y(v) */
function frame(svg,W,H,box,xr,yr,xt,yt,xl,yl,rev){const [L,R,Tp,B]=box,ax=tok('--line');
  const X=v=>rev?W-R-(v-xr[0])/(xr[1]-xr[0])*(W-L-R):L+(v-xr[0])/(xr[1]-xr[0])*(W-L-R),Y=v=>Tp+(yr[1]-v)/(yr[1]-yr[0])*(H-Tp-B);
  xt.forEach(v=>{el('line',{x1:X(v),x2:X(v),y1:Tp,y2:H-B,stroke:ax,'stroke-width':.6},svg);el('text',{x:X(v),y:H-B+16,'text-anchor':'middle'},svg,String(v).replace('.',DEC).replace('-','−'))});
  yt.forEach(v=>{el('line',{x1:L,x2:W-R,y1:Y(v),y2:Y(v),stroke:ax,'stroke-width':.6},svg);el('text',{x:L-6,y:Y(v)+4,'text-anchor':'end'},svg,String(v).replace('.',DEC).replace('-','−'))});
  if(xl)el('text',{x:(L+W-R)/2,y:H-4,'text-anchor':'middle'},svg,xl);if(yl)el('text',{x:4,y:Tp-4},svg,yl);return [X,Y]}
/* The search for a transition state and the reaction path (Atlas v2): eigenvector following and the IRC on the surface
   of the lecture, the nudged elastic band and the climbing image on the Müller–Brown surface, a relaxed scan —
   quas_atlas.core.tsearch (ts.follow, ts.neb, ts.scan). */
const TX={
  modes:{ru:['вдоль x (координата реакции)','вдоль y'],en:['along x (the reaction coordinate)','along y'],zh:['沿 x（反应坐标）','沿 y']},modeKeys:['x','y'],
  kinds:{ru:['пружины без проекций','NEB','CI-NEB'],en:['springs without projections','NEB','CI-NEB'],zh:['无投影的弹簧','NEB','CI-NEB']},kindKeys:['plain','neb','ci'],
  coords:{ru:['скан по y','скан по x'],en:['scan of y','scan of x'],zh:['扫描 y','扫描 x']},coordKeys:['y','x'],
  stepAx:{ru:'шаг',en:'step',zh:'步'},EAx:{ru:'E',en:'E',zh:'E'},imgAx:{ru:'номер образа',en:'image',zh:'像编号'},
  fLeg:{ru:['следование моде','метод Ньютона','IRC из седла'],en:['eigenvector following','Newton method','IRC from the saddle'],zh:['本征矢跟踪','牛顿法','由鞍点出发的 IRC']},
  fT:{ru:['шагов до седла','найдено','собственные значения гессиана','Ньютон пришёл в'],en:['steps to the saddle','found','eigenvalues of the Hessian','Newton ended at'],zh:['到鞍点的步数','找到','Hessian 本征值','牛顿法终点']},
  saddle:{ru:'седло 1-го порядка',en:'a first-order saddle',zh:'一阶鞍点'},notS:{ru:'не седло',en:'not a saddle',zh:'不是鞍点'},
  fNote:{ru:(ok,m)=>ok?'Вдоль выбранной моды шаг идёт вверх, вдоль остальных — вниз: седло найдено, у гессиана одно отрицательное собственное значение. Из седла IRC спускается в обе стороны — в реагент и в продукт: это проверка, что седло то самое. Метод Ньютона из той же точки скатывается в минимум: оптимизатор минимума ищет яму, а не перевал. Без ограничения шага (доверительного радиуса) один шаг перебросил бы систему через седло в другую яму.':m==='y'?'Вдоль y поверхность — парабола, перевала нет: следование не той моде уводит вверх по склону. В молекуле так бывает, когда за координату реакции приняли, например, вращение метильной группы — анимируйте моду перед поиском.':'Седла не нашли: попробуйте другую стартовую точку или меньший радиус. Область, из которой метод сходится к седлу, уже чаши минимума — поэтому старт берут из скана или из ленты.',
    en:(ok,m)=>ok?'Along the chosen mode the step goes up, along the others down: the saddle is found, the Hessian has one negative eigenvalue. From the saddle the IRC goes down both ways — to the reactant and to the product: this checks that it is the right saddle. The Newton method from the same point rolls down to a minimum: a minimizer looks for a pit, not a pass. Without a limit on the step (a trust radius) one step would throw the system over the saddle into the other pit.':m==='y'?'Along y the surface is a parabola, there is no pass: following the wrong mode leads up the slope. In a molecule this happens when, say, the rotation of a methyl group is taken for the reaction coordinate — animate the mode before the search.':'No saddle found: try another starting point or a smaller radius. The region from which the method converges to the saddle is narrower than the bowl of a minimum — this is why the start is taken from a scan or a band.',
    zh:(ok,m)=>ok?'沿选定模式步长向上，沿其余模式向下：找到鞍点，Hessian 有一个负本征值。IRC 从鞍点向两侧下降——到反应物和产物：这验证了鞍点正确。从同一点出发的牛顿法滚入极小值：极小值优化器寻找的是坑而不是山口。如果不限制步长（信赖半径），一步就会把体系越过鞍点甩到另一个坑里。':m==='y'?'沿 y 表面是抛物线，没有山口：跟踪错误的模式会沿坡向上。在分子中，把例如甲基转动当作反应坐标时就会这样——搜索前先动画显示该模式。':'没有找到鞍点：换一个起点或减小半径。方法收敛到鞍点的区域比极小值的碗窄——所以起点取自扫描或弹性带。'},
  nLeg:{ru:['начальная лента','лента после оптимизации','настоящее седло'],en:['initial band','band after the optimization','the true saddle'],zh:['初始弹性带','优化后的弹性带','真实鞍点']},
  nT:{ru:['барьер по ленте','настоящий барьер','верхний образ от седла','расчётов градиента'],en:['barrier from the band','the true barrier','top image from the saddle','gradient calculations'],zh:['由弹性带得到的势垒','真实势垒','最高像到鞍点距离','梯度计算次数']},
  nNote:{ru:(k)=>k==='plain'?'Без проекций пружины тянут образы с дна долины — путь срезает угол, а истинная сила вдоль пути стаскивает образы к концам: у вершины никого, и барьер сильно занижен.':k==='neb'?'NEB: от истинной силы оставлена только поперечная часть, от пружины — продольная. Лента легла на путь минимальной энергии, образы стоят равномерно. Но самый высокий образ — рядом с седлом, а не в нём: барьер чуть занижен.':'CI-NEB: самый высокий образ без пружины и карабкается вверх вдоль пути — он сходится точно в седло. Его геометрия — хороший старт для OptTS, а затем частоты и IRC.',
    en:(k)=>k==='plain'?'Without projections the springs pull the images off the valley floor — the path cuts the corner, and the true force along the path drags the images to the ends: there is no one at the top, and the barrier is much too low.':k==='neb'?'NEB: of the true force only the part across the path is kept, of the spring only the part along it. The band lies on the minimum-energy path, the images are evenly spaced. But the highest image is near the saddle, not in it: the barrier is a little too low.':'CI-NEB: the highest image has no spring and climbs up along the path — it converges exactly to the saddle. Its geometry is a good start for OptTS, then frequencies and the IRC.',
    zh:(k)=>k==='plain'?'没有投影时弹簧把像拉离谷底——路径抄近道，而沿路径的真实力把像拖向两端：顶部没有像，势垒被严重低估。':k==='neb'?'NEB：真实力只保留垂直于路径的部分，弹簧只保留沿路径的部分。弹性带落在最小能量路径上，像分布均匀。但最高的像在鞍点附近而不在鞍点上：势垒略被低估。':'CI-NEB：最高的像没有弹簧，沿路径向上攀爬——它精确收敛到鞍点。它的几何是 OptTS 的好起点，然后是频率和 IRC。'},
  qAx:{ru:'фиксированная координата',en:'fixed coordinate',zh:'固定坐标'},
  sLeg:{ru:['скан вперёд (от A)','скан назад (от C)','настоящее седло'],en:['scan forward (from A)','scan backward (from C)','the true saddle'],zh:['正向扫描（从 A）','反向扫描（从 C）','真实鞍点']},
  sT:{ru:['максимум вперёд','максимум назад','настоящее седло','разрыв профиля'],en:['maximum forward','maximum backward','the true saddle','break of the profile'],zh:['正向最大值','反向最大值','真实鞍点','剖面断裂']},
  sNote:{ru:'Релаксированный скан: координата задана, остальное оптимизировано. Путь реакции здесь изогнут и идёт по двум координатам сразу, поэтому профиль рвётся: структура скачком перескакивает в другую долину, и скан вперёд и скан назад расходятся. Максимум скана — хороший старт, но не переходное состояние: гессиан там никто не проверял.',
    en:'A relaxed scan: the coordinate is set, the rest optimized. The reaction path here is curved and runs along two coordinates at once, so the profile breaks: the structure jumps into the other valley, and the scan forward and the scan backward diverge. The maximum of a scan is a good start, but not a transition state: no one checked the Hessian there.',
    zh:'弛豫扫描：固定一个坐标，其余优化。这里的反应路径是弯曲的，同时沿两个坐标进行，所以剖面会断裂：结构突然跳入另一个谷，正向和反向扫描不一致。扫描最大值是好的起点，但不是过渡态：那里没人检查过 Hessian。'}
};
const Q={x0:0.8,y0:0.3,r:0.3,mode:0,kind:2,n:9,k:50,coord:0};let F=null,N=null,S=null;
const liveF=QC.live('ts.follow'),liveN=QC.live('ts.neb'),liveS=QC.live('ts.scan');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show()};
slider('fx',v=>{Q.x0=v;fol()},2);slider('fy',v=>{Q.y0=v;fol()},2);slider('rr',v=>{Q.r=v;fol()},2);
chips($('mG'),tr(TX.modes),Q.mode,i=>{Q.mode=i;mark($('mG'),i);fol()});
chips($('kG'),tr(TX.kinds),Q.kind,i=>{Q.kind=i;mark($('kG'),i);nb()});slider('ni',v=>{Q.n=v;nb()},0);slider('ks',v=>{Q.k=v;nb()},0);
chips($('cG'),tr(TX.coords),Q.coord,i=>{Q.coord=i;mark($('cG'),i);sc()});
const ticks=(lo,hi,n)=>{const r=(hi-lo)/n,p=Math.pow(10,Math.floor(Math.log10(r))),s=[1,2,2.5,5,10].map(k=>k*p).find(k=>k>=r);const t=[];for(let v=Math.ceil(lo/s)*s;v<=hi+1e-9;v+=s)t.push(+v.toFixed(6));return t};
const legend=(id,names,colors)=>{$(id).innerHTML=names.map((s,j)=>'<span><i class="sw" style="border-color:'+colors[j]+'"></i>'+s+'</span>').join('')};
function map(svg,W,H,G){svg.innerHTML='';const xs=G.x,ys=G.y,flat=[].concat(...G.E),lo=Math.min(...flat),hi=Math.max(...flat),ac=tok('--accent');
  const [X,Y]=frame(svg,W,H,[40,10,10,30],[xs[0],xs[xs.length-1]],[ys[0],ys[ys.length-1]],ticks(xs[0],xs[xs.length-1],4),ticks(ys[0],ys[ys.length-1],4),'x','y');
  const dx=(X(xs[1])-X(xs[0])),dy=(Y(ys[0])-Y(ys[1]));
  const g=el('g',{'shape-rendering':'crispEdges'},svg);  // levels of the energy: contours as bands
  G.E.forEach((row,j)=>row.forEach((e,i)=>{const t=Math.floor(10*(e-lo)/(hi-lo||1))/10;el('rect',{x:X(xs[i])-dx/2,y:Y(ys[j])-dy/2,width:dx,height:dy,fill:ac,opacity:(0.6*(1-t)).toFixed(3)},g)}));
  return [X,Y,xs,ys]}
const inside=(p,xs,ys)=>p[0]>=xs[0]&&p[0]<=xs[xs.length-1]&&p[1]>=ys[0]&&p[1]<=ys[ys.length-1];
function path(svg,X,Y,pts,c,w,dash,dots,xs,ys){const q=pts.filter(p=>inside(p,xs,ys));el('polyline',{points:q.map(p=>X(p[0])+','+Y(p[1])).join(' '),fill:'none',stroke:c,'stroke-width':w,'stroke-dasharray':dash||''},svg);if(dots)q.forEach(p=>el('circle',{cx:X(p[0]),cy:Y(p[1]),r:dots,fill:c},svg))}
async function fol(){try{F=await liveF({x0:Q.x0,y0:Q.y0,mode:TX.modeKeys[Q.mode],radius:Q.r})}catch(e){return}drawF()}
function drawF(){if(!F)return;const wr=tok('--warn'),ink=tok('--ink'),ok=tok('--ok'),svg=$('fchart');const [X,Y,xs,ys]=map(svg,560,440,F.grid);
  F.irc.forEach(p=>path(svg,X,Y,p,ok,2.4,'',0,xs,ys));
  path(svg,X,Y,F.newton,tok('--muted'),1.6,'5 4',3.5,xs,ys);path(svg,X,Y,F.ef,wr,2.4,'',4.5,xs,ys);
  legend('fleg',tr(TX.fLeg),[wr,tok('--muted'),ok]);
  const g=$('feprof');g.innerHTML='';const es=F.ef.map(p=>p[2]).map(e=>Math.min(e,4)),mx=Math.max(1.2,...es);
  const [PX,PY]=frame(g,360,440,[40,10,24,30],[0,Math.max(1,F.ef.length-1)],[0,mx*1.05],ticks(0,Math.max(1,F.ef.length-1),4),ticks(0,mx,4),tr(TX.stepAx),tr(TX.EAx));
  el('polyline',{points:es.map((e,i)=>PX(i)+','+PY(e)).join(' '),fill:'none',stroke:wr,'stroke-width':2.4},g);es.forEach((e,i)=>el('circle',{cx:PX(i),cy:PY(e),r:3.5,fill:wr},g));
  const h=tr(TX.fT),last=F.ef[F.ef.length-1],nw=F.newton[F.newton.length-1],pt=p=>'('+fmt(p[0],2)+'; '+fmt(p[1],2)+')';
  $('fcards').innerHTML=card(h[0],F.found&&F.steps!=null?String(F.steps):'—')+card(h[1],(F.found?tr(TX.saddle):tr(TX.notS))+' '+pt(last))+card(h[2],F.lam.map(l=>fmt(l,2)).join('; '))+card(h[3],pt(nw));
  $('fNote').textContent=tr(TX.fNote)(F.found,TX.modeKeys[Q.mode])}
async function nb(){try{N=await liveN({n:Math.round(Q.n),k:Q.k,kind:TX.kindKeys[Q.kind]})}catch(e){return}drawN()}
function drawN(){if(!N)return;const ac=tok('--accent'),wr=tok('--warn'),mu=tok('--muted'),ink=tok('--ink'),svg=$('nchart');const [X,Y,xs,ys]=map(svg,480,440,N.grid);
  path(svg,X,Y,N.start,mu,1.4,'5 4',3,xs,ys);path(svg,X,Y,N.images,wr,2.4,'',5,xs,ys);
  el('circle',{cx:X(N.saddle.x),cy:Y(N.saddle.y),r:7,fill:'none',stroke:ink,'stroke-width':2},svg);
  legend('nleg',tr(TX.nLeg),[mu,wr,ink]);
  const g=$('nprof');g.innerHTML='';const e0=N.E[0],es=N.E.map(e=>e-e0),top=N.true_barrier*1.1;
  const [PX,PY]=frame(g,440,440,[44,10,24,30],[0,N.E.length-1],[Math.min(0,...es)-5,top],ticks(0,N.E.length-1,4),ticks(0,top,4),tr(TX.imgAx),'ΔE');
  el('line',{x1:PX(0),x2:PX(N.E.length-1),y1:PY(N.true_barrier),y2:PY(N.true_barrier),stroke:ink,'stroke-dasharray':'6 4','stroke-width':1.2},g);
  el('polyline',{points:es.map((e,i)=>PX(i)+','+PY(e)).join(' '),fill:'none',stroke:wr,'stroke-width':2.4},g);es.forEach((e,i)=>el('circle',{cx:PX(i),cy:PY(e),r:4,fill:i===N.top&&Q.kind===2?ac:wr},g));
  const h=tr(TX.nT);
  $('ncards').innerHTML=card(h[0],fmt(N.barrier,1))+card(h[1],fmt(N.true_barrier,1))+card(h[2],fmt(N.top_distance,3))+card(h[3],String(N.gradients));
  $('nNote').textContent=tr(TX.nNote)(TX.kindKeys[Q.kind])}
async function sc(){try{S=await liveS({coord:TX.coordKeys[Q.coord]})}catch(e){return}drawS()}
function drawS(){if(!S)return;const wr=tok('--warn'),ac=tok('--accent'),ink=tok('--ink'),svg=$('schart');const [X,Y,xs,ys]=map(svg,480,440,S.grid);
  const pts=s=>s.x.map((x,i)=>[x,s.y[i]]);path(svg,X,Y,pts(S.forward),wr,2.4,'',3.5,xs,ys);path(svg,X,Y,pts(S.backward),ac,2,'5 4',3,xs,ys);
  el('circle',{cx:X(S.saddle.x),cy:Y(S.saddle.y),r:7,fill:'none',stroke:ink,'stroke-width':2},svg);
  legend('sleg',tr(TX.sLeg),[wr,ac,ink]);
  const g=$('sprof');g.innerHTML='';const all=S.forward.E.concat(S.backward.E),lo=Math.min(...all)-5,hi=Math.max(S.saddle.E,...all)+8,q=S.forward.q,ql=Math.min(...q),qh=Math.max(...q);
  const [PX,PY]=frame(g,440,440,[48,10,24,30],[ql,qh],[lo,hi],ticks(ql,qh,4),ticks(lo,hi,4),tr(TX.qAx),'E');
  el('line',{x1:PX(ql),x2:PX(qh),y1:PY(S.saddle.E),y2:PY(S.saddle.E),stroke:ink,'stroke-dasharray':'6 4','stroke-width':1.2},g);
  [[S.forward,wr,''],[S.backward,ac,'5 4']].forEach(([s,c,d])=>el('polyline',{points:s.q.map((v,i)=>PX(v)+','+PY(s.E[i])).join(' '),fill:'none',stroke:c,'stroke-width':2.2,'stroke-dasharray':d},g));
  const h=tr(TX.sT);
  $('scards').innerHTML=card(h[0],fmt(S.max_f,1))+card(h[1],fmt(S.max_b,1))+card(h[2],fmt(S.saddle.E,1))+card(h[3],fmt(Math.abs(S.max_f-S.max_b),1));
  $('sNote').textContent=tr(TX.sNote)}
fol();nb();sc();onTheme(()=>{drawF();drawN();drawS()});
