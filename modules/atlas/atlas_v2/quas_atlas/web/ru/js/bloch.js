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
/* The Bloch theorem and k-points (Atlas v2). The Bloch wave of a chain, the k-mesh of a metal and of an insulator,
   the mesh of a square lattice and its points by symmetry, the plane waves of a cutoff — quas_atlas.core.solids
   (sol.wave, sol.mesh, sol.mesh2d, sol.pw). */
const TX={
  kc:{ru:'волновой вектор k',en:'wave vector k',zh:'波矢 k'},E:{ru:'энергия E(k)',en:'energy E(k)',zh:'能量 E(k)'},
  lam:{ru:'длина волны',en:'wavelength',zh:'波长'},
  mG:{ru:['k + 2π/a','k + 4π/a','k − 2π/a'],en:['k + 2π/a','k + 4π/a','k − 2π/a'],zh:['k + 2π/a','k + 4π/a','k − 2π/a']},
  wNote:{ru:(k,m)=>'Сплошная линия — cos(kx) при k = '+k+' π/a, пунктир — та же функция с k + '+(2*m)+'π/a. Между атомами они разные, а на самих атомах (точки) совпадают: на решётке это одно и то же состояние. Поэтому k достаточно брать в первой зоне Бриллюэна, от −π/a до π/a.',
    en:(k,m)=>'Solid line — cos(kx) at k = '+k+' π/a, dashed — the same function with k + '+(2*m)+'π/a. Between the atoms they differ, but on the atoms (dots) they coincide: on the lattice this is one and the same state. That is why k is taken in the first Brillouin zone, from −π/a to π/a.',
    zh:(k,m)=>'实线为 k = '+k+' π/a 时的 cos(kx)，虚线为 k + '+(2*m)+'π/a 时的同一函数。它们在原子之间不同，但在原子上（圆点）完全相同：在晶格上这是同一个状态。因此 k 只需取在第一布里渊区内，即 −π/a 到 π/a。'},
  band:{ru:'Зона E(k) = 2β cos ka (β < 0)',en:'Band E(k) = 2β cos ka (β < 0)',zh:'能带 E(k) = 2β cos ka（β < 0）'},
  met:{ru:'металл: зона заполнена наполовину',en:'metal: a half-filled band',zh:'金属：半满能带'},
  ins:{ru:'диэлектрик: нижняя зона заполнена',en:'insulator: the lower band full',zh:'绝缘体：下能带全满'},
  nax:{ru:'число k-точек n',en:'number of k-points n',zh:'k 点数 n'},err:{ru:'|ошибка|, |β|',en:'|error|, |β|',zh:'|误差|，|β|'},
  need:{ru:'k-точек до ошибки < 0,001|β|',en:'k-points for an error < 0.001|β|',zh:'误差 < 0.001|β| 所需 k 点'},
  mNote:{ru:(a,b)=>'Энергия на ячейку — сумма по k-точкам вместо интеграла по зоне. У диэлектрика заполненная зона даёт гладкую функцию, и ошибка падает в разы с каждой точкой: хватает '+a+'. У металла уровень Ферми режет зону, и ошибка убывает медленно и скачет: нужно '+b+'. Поэтому металлам ставят густую сетку и размытие (smearing).',
    en:(a,b)=>'The energy per cell is a sum over k-points instead of an integral over the zone. A full band of an insulator is a smooth function, and the error drops several-fold with each point: '+a+' are enough. In a metal the Fermi level cuts the band, and the error falls slowly and jumps: '+b+' are needed. That is why metals get a dense mesh and a smearing.',
    zh:(a,b)=>'每个晶胞的能量是对 k 点求和，而不是对布里渊区积分。绝缘体的满带是光滑函数，每增加一个点误差就成倍下降：'+a+' 个就够了。金属的费米能级切断能带，误差下降缓慢且跳动：需要 '+b+' 个。因此金属要用更密的网格并加展宽（smearing）。'},
  nG:{ru:['2 × 2','3 × 3','4 × 4','6 × 6','8 × 8'],en:['2 × 2','3 × 3','4 × 4','6 × 6','8 × 8'],zh:['2 × 2','3 × 3','4 × 4','6 × 6','8 × 8']},
  shG:{ru:['с точкой Γ','сдвинутая на ½'],en:['with the Γ point','shifted by ½'],zh:['含 Γ 点','平移 ½']},
  allk:{ru:'всего точек',en:'points in all',zh:'总点数'},irr:{ru:'разных по симметрии',en:'different by symmetry',zh:'按对称性不同的'},
  zNote:{ru:(n,m)=>'Сетка '+n+' × '+n+' в зоне квадратной решётки: '+n*n+' точек, но повороты и отражения квадрата переводят многие из них друг в друга. Считать нужно только '+m+' (крупные точки, число — вес). Так в выводе Quantum ESPRESSO появляется «number of k points» меньше, чем n³ сетки.',
    en:(n,m)=>'An '+n+' × '+n+' mesh in the zone of a square lattice: '+n*n+' points, but the rotations and reflections of the square turn many of them into each other. Only '+m+' have to be computed (large dots, the number is the weight). This is why Quantum ESPRESSO prints a «number of k points» smaller than the n³ of the mesh.',
    zh:(n,m)=>'正方晶格布里渊区中的 '+n+' × '+n+' 网格：共 '+n*n+' 个点，但正方形的旋转和反射把其中许多点互相变换。只需计算 '+m+' 个（大点，数字为权重）。所以 Quantum ESPRESSO 输出中的 “number of k points” 小于网格的 n³。'},
  cG:{ru:['кремний Si','NaCl','медь Cu'],en:['silicon Si','NaCl','copper Cu'],zh:['硅 Si','NaCl','铜 Cu']},cK:['si','nacl','cu'],
  pT:{ru:['плоских волн орбитали','оценка V·G³/6π²','векторов плотности, 4·E<sub>cut</sub>','8·E<sub>cut</sub> (ультрамягкие)'],en:['plane waves of an orbital','estimate V·G³/6π²','density vectors, 4·E<sub>cut</sub>','8·E<sub>cut</sub> (ultrasoft)'],zh:['轨道平面波数','估计 V·G³/6π²','密度矢量，4·E<sub>cut</sub>','8·E<sub>cut</sub>（超软）']},
  ex:{ru:'E<sub>cut</sub>, Ry',en:'E<sub>cut</sub>, Ry',zh:'E<sub>cut</sub>，Ry'},
  pAx:{ru:'плоских волн',en:'plane waves',zh:'平面波'},
  pNote:{ru:(v,e)=>'Ячейка '+v+' бор³. Волна e<sup>iG·r</sup> входит в базис, если её кинетическая энергия |G|² не больше E<sub>cut</sub> = '+e+' Ry: это точки обратной решётки внутри шара. Их число растёт как E<sub>cut</sub><sup>3/2</sup> и как объём ячейки. Для Si при 30 Ry здесь получается то же, что печатает Quantum ESPRESSO: 5985 векторов плотности при 120 Ry («Smooth grid») и 16889 при 240 Ry («Dense grid»).',
    en:(v,e)=>'The cell is '+v+' bohr³. A wave e<sup>iG·r</sup> is in the basis when its kinetic energy |G|² is at most E<sub>cut</sub> = '+e+' Ry: the points of the reciprocal lattice inside a sphere. Their number grows as E<sub>cut</sub><sup>3/2</sup> and as the volume of the cell. For Si at 30 Ry this gives what Quantum ESPRESSO prints: 5985 density vectors at 120 Ry («Smooth grid») and 16889 at 240 Ry («Dense grid»).',
    zh:(v,e)=>'晶胞体积 '+v+' bohr³。当平面波 e<sup>iG·r</sup> 的动能 |G|² 不超过 E<sub>cut</sub> = '+e+' Ry 时，它进入基组：即倒格子中位于球内的点。其数目随 E<sub>cut</sub><sup>3/2</sup> 和晶胞体积增长。对 Si 在 30 Ry 时，这里得到的正是 Quantum ESPRESSO 的输出：120 Ry 时 5985 个密度矢量（“Smooth grid”），240 Ry 时 16889 个（“Dense grid”）。'}
};
const Q={k:0.3,m:1,delta:1,n2:4,shift:false,cell:0,ecut:30};let W=null,MM=null,MI=null,Z=null,P=null;
const liveW=QC.live('sol.wave'),liveM=QC.live('sol.mesh'),liveZ=QC.live('sol.mesh2d'),liveP=QC.live('sol.pw');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show()};
chips($('mG'),tr(TX.mG),0,i=>{Q.m=[1,2,-1][i];mark($('mG'),i);wave()});
slider('kk',v=>{Q.k=v;wave()},2);
slider('dl',v=>{Q.delta=v;meshes()},1);
chips($('nG'),tr(TX.nG),2,i=>{Q.n2=[2,3,4,6,8][i];mark($('nG'),i);zone()});
chips($('shG'),tr(TX.shG),0,i=>{Q.shift=i===1;mark($('shG'),i);zone()});
chips($('cG'),tr(TX.cG),0,i=>{Q.cell=i;mark($('cG'),i);pws()});
slider('ec',v=>{Q.ecut=v;pws()},0);
async function wave(){try{W=await liveW({k:Q.k,m:Q.m})}catch(e){return}drawWave()}
function drawWave(){if(!W)return;const ac=tok('--accent'),wr=tok('--warn'),ink=tok('--ink');
  let svg=$('bchart');svg.innerHTML='';let [X,Y]=frame(svg,420,260,[46,14,22,38],[-1,1],[-2.3,2.3],[-1,-0.5,0,0.5,1],[-2,-1,0,1,2],'k, π/a','E, |β|');
  el('polyline',{points:W.band.k.map((q,i)=>X(q)+','+Y(W.band.E[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg);
  el('circle',{cx:X(W.k),cy:Y(W.E),r:6,fill:wr},svg);
  svg=$('wchart');svg.innerHTML='';[X,Y]=frame(svg,540,260,[30,10,22,38],[-6,6],[-1.25,1.25],[-6,-4,-2,0,2,4,6],[-1,0,1],'x, a','');
  el('polyline',{points:W.x.map((x,i)=>X(x)+','+Y(W.re[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.2},svg);
  el('polyline',{points:W.x.map((x,i)=>X(x)+','+Y(W.re_g[i])).join(' '),fill:'none',stroke:wr,'stroke-width':1.6,'stroke-dasharray':'5 4'},svg);
  W.sites.forEach(s=>el('circle',{cx:X(s.x),cy:Y(s.re),r:5,fill:ink},svg));
  const lam=Math.abs(W.k)>1e-9?fmt(2/Math.abs(W.k),2)+' a':'∞';
  $('wcards').innerHTML=card(tr(TX.kc),fmt(W.k,2)+' π/a')+card(tr(TX.E),fmt(W.E,3)+' |β|')+card(tr(TX.lam),lam);
  $('wNote').textContent=tr(TX.wNote)(fmt(W.k,2),Q.m)}
async function meshes(){try{[MM,MI]=await Promise.all([liveM({kind:'metal',n:24,delta:Q.delta}),QC.api('sol.mesh',{kind:'insulator',n:24,delta:Q.delta})])}catch(e){return}drawMesh()}
function drawMesh(){if(!MM||!MI)return;const svg=$('mchart');svg.innerHTML='';const lg=v=>Math.log10(Math.max(Math.abs(v),1e-9));
  const [X,Y]=frame(svg,960,280,[56,16,22,40],[1,24],[-9,0.5],[1,4,8,12,16,20,24],[-9,-6,-3,0],tr(TX.nax),tr(TX.err));
  [[MM,tok('--accent')],[MI,tok('--warn')]].forEach(([M,c])=>{const pts=M.rows.map(r=>X(r.n)+','+Y(lg(r.err)));
    el('polyline',{points:pts.join(' '),fill:'none',stroke:c,'stroke-width':2},svg);M.rows.forEach(r=>el('circle',{cx:X(r.n),cy:Y(lg(r.err)),r:3.2,fill:c},svg))});
  [-9,-6,-3,0].forEach(v=>{const t=[...svg.querySelectorAll('text')].find(x=>x.textContent===String(v).replace('-','−'));if(t)t.textContent='10'+SUP(v)});
  const need=M=>{for(let i=0;i<M.rows.length;i++){if(M.rows.slice(i).every(r=>Math.abs(r.err)<1e-3))return M.rows[i].n}return '> 24'};
  const a=need(MI),b=need(MM);
  $('mcards').innerHTML=card(tr(TX.ins),String(a),tr(TX.need))+card(tr(TX.met),String(b),tr(TX.need));
  $('mNote').textContent=tr(TX.mNote)(a,b)}
async function zone(){try{Z=await liveZ({n:Q.n2,shift:Q.shift})}catch(e){return}drawZone()}
function drawZone(){if(!Z)return;const svg=$('zchart');svg.innerHTML='';const S=260,o=20,P=v=>o+(v+0.5)*S,R=v=>o+(0.5-v)*S,ln=tok('--line'),ac=tok('--accent'),mu=tok('--muted');
  el('rect',{x:o,y:o,width:S,height:S,fill:'none',stroke:tok('--ink'),'stroke-width':1.4},svg);
  el('polygon',{points:[[0,0],[0.5,0],[0.5,0.5]].map(p=>P(p[0])+','+R(p[1])).join(' '),fill:tok('--acc-bg'),stroke:'none'},svg);
  el('line',{x1:P(-0.5),x2:P(0.5),y1:R(0),y2:R(0),stroke:ln},svg);el('line',{x1:P(0),x2:P(0),y1:R(-0.5),y2:R(0.5),stroke:ln},svg);
  Z.points.forEach(p=>el('circle',{cx:P(p[0]),cy:R(p[1]),r:3,fill:mu},svg));
  Z.irreducible.forEach(q=>{el('circle',{cx:P(q.k[0]),cy:R(q.k[1]),r:7,fill:ac},svg);el('text',{x:P(q.k[0])+9,y:R(q.k[1])-8,class:'lab'},svg,String(q.w))});
  el('text',{x:P(0)-12,y:R(0)+16,class:'lab'},svg,'Γ');
  $('zcards').innerHTML=card(tr(TX.allk),String(Z.n*Z.n))+card(tr(TX.irr),String(Z.irreducible.length));
  $('zNote').textContent=tr(TX.zNote)(Z.n,Z.irreducible.length)}
async function pws(){try{P=await liveP({cell:TX.cK[Q.cell],ecut:Q.ecut})}catch(e){return}drawPw()}
function drawPw(){if(!P)return;const h=tr(TX.pT);
  $('pcards').innerHTML=card(h[0],String(P.N))+card(h[1],fmt(P.N_est,0))+card(h[2],String(P.N_rho4))+card(h[3],String(P.N_rho8));
  const svg=$('pchart');svg.innerHTML='';const top=P.V*Math.pow(100,1.5)/(6*Math.PI*Math.PI);const yt=[];const st=[100,200,500,1000,2000,5000].find(s=>top/s<=6);for(let v=0;v<=top*1.05;v+=st)yt.push(v);
  const [X,Y]=frame(svg,960,240,[56,16,22,40],[5,100],[0,top*1.08],[10,20,30,40,50,60,70,80,90,100],yt,'Ecut, Ry',tr(TX.pAx));
  const pts=[];for(let e=5;e<=100;e+=1)pts.push(X(e)+','+Y(P.V*Math.pow(e,1.5)/(6*Math.PI*Math.PI)));
  el('polyline',{points:pts.join(' '),fill:'none',stroke:tok('--accent'),'stroke-width':2},svg);
  el('circle',{cx:X(Q.ecut),cy:Y(P.N),r:6,fill:tok('--warn')},svg);
  $('pNote').innerHTML=tr(TX.pNote)(fmt(P.V,1),fmt(Q.ecut,0))}
mark($('mG'),0);mark($('nG'),2);wave();meshes();zone();pws();
onTheme(()=>{drawWave();drawMesh();drawZone();drawPw()});
