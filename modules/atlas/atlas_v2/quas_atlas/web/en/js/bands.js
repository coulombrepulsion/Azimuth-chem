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
/* Bands and the density of states (Atlas v2). A chain of two atoms per cell (bands, DOS, PDOS, the Fermi level),
   graphene and a sheet of two different atoms (the Dirac cone and its gap), nearly free electrons in a basis of plane
   waves — quas_atlas.core.solids (sol.pair, sol.graphene, sol.nfe). */
const TX={
  gap:{ru:'запрещённая зона',en:'band gap',zh:'带隙'},ef:{ru:'уровень Ферми',en:'Fermi level',zh:'费米能级'},
  kind:{ru:'вещество',en:'material',zh:'物质'},metal:{ru:'металл',en:'metal',zh:'金属'},ins:{ru:'диэлектрик или полупроводник',en:'insulator or semiconductor',zh:'绝缘体或半导体'},
  shareA:{ru:'доля атома A в нижнем крае верхней зоны',en:'share of atom A at the bottom of the upper band',zh:'上能带底部中原子 A 的份额'},
  dosAx:{ru:'DOS',en:'DOS',zh:'DOS'},kAx:{ru:'k, π/a',en:'k, π/a',zh:'k，π/a'},
  leg:{ru:['всего','атом A','атом B'],en:['total','atom A','atom B'],zh:['总','原子 A','原子 B']},
  pNote:{ru:(m,g,a)=>(m?'Уровень Ферми проходит внутри зоны: есть свободные состояния рядом с занятыми, электроны могут двигаться — металл.':'Уровень Ферми лежит в щели шириной '+g+' |β|: нижняя зона заполнена, верхняя пуста — диэлектрик (при малой щели — полупроводник).')+' Верхняя зона на '+a+' % состоит из орбиталей атома A — так по PDOS расчёта видят, какие атомы дают валентную зону и зону проводимости.',
    en:(m,g,a)=>(m?'The Fermi level runs inside a band: free states are next to the occupied ones, electrons can move — a metal.':'The Fermi level lies in a gap of '+g+' |β|: the lower band is full, the upper one empty — an insulator (a semiconductor when the gap is small).')+' The upper band is '+a+' % made of the orbitals of atom A — this is how the PDOS of a calculation tells which atoms give the valence and the conduction band.',
    zh:(m,g,a)=>(m?'费米能级穿过能带：已占据态旁边有空态，电子可以移动——金属。':'费米能级位于宽度为 '+g+' |β| 的带隙中：下能带全满，上能带全空——绝缘体（带隙小时为半导体）。')+' 上能带中有 '+a+' % 来自原子 A 的轨道——这就是计算的 PDOS 告诉我们价带和导带由哪些原子贡献的方式。'},
  gT:{ru:['запрещённая зона','E в Γ','E в M','E в K'],en:['band gap','E at Γ','E at M','E at K'],zh:['带隙','Γ 点 E','M 点 E','K 点 E']},
  gNote:{ru:d=>d<0.01?'Графен: в точке K зоны касаются друг друга, а около неё E растёт линейно с |k − K| — конус Дирака. Плотность состояний у уровня Ферми равна нулю и растёт линейно: полуметалл. Поэтому для графена нужна густая сетка вокруг K (тема проекта о графене).':'Два разных атома в узлах (как B и N в h-BN) делают позиции неравноценными, и в точке K открывается щель Δ = '+fmt(d,1)+' эВ. В модели одна pz-орбиталь на атом и β = −2,8 эВ.',
    en:d=>d<0.01?'Graphene: at the point K the bands touch, and around it E grows linearly with |k − K| — the Dirac cone. The density of states at the Fermi level is zero and grows linearly: a semimetal. This is why graphene needs a dense mesh around K (the project on graphene).':'Two different atoms on the sites (as B and N in h-BN) make the positions unequal, and a gap Δ = '+fmt(d,1)+' eV opens at K. The model has one pz orbital per atom and β = −2.8 eV.',
    zh:d=>d<0.01?'石墨烯：在 K 点两条能带相接，附近 E 随 |k − K| 线性增长——狄拉克锥。费米能级处的态密度为零并线性增长：半金属。因此石墨烯需要在 K 点附近使用更密的网格（石墨烯项目）。':'格点上两种不同原子（如 h-BN 中的 B 和 N）使位置不再等价，在 K 点打开带隙 Δ = '+fmt(d,1)+' eV。模型中每个原子一个 pz 轨道，β = −2.8 eV。'},
  nT:{ru:['щель 1–2 на границе зоны','2|V| (теория возмущений)','плоских волн в базисе'],en:['gap 1–2 at the zone boundary','2|V| (perturbation theory)','plane waves in the basis'],zh:['布里渊区边界 1–2 带隙','2|V|（微扰理论）','基组中的平面波']},
  nNote:{ru:(n,v)=>'Электрон почти свободен: E = (k + G)², сложенная в первую зону. Слабый потенциал 2V cos(2πx/a) смешивает две волны одной энергии на границе зоны и раздвигает их на 2|V|. Базис здесь — '+n+' плоских волн e<sup>i(k+G)x</sup>: при одной волне щелей нет вовсе, с добавлением волн нижние зоны перестают меняться. Так работает и E<sub>cut</sub> в Quantum ESPRESSO.'+(v>1?' При сильном потенциале теория возмущений уже не годится: щель меньше 2|V|, а электроны почти связаны с атомами.':''),
    en:(n,v)=>'The electron is almost free: E = (k + G)², folded into the first zone. A weak potential 2V cos(2πx/a) mixes two waves of the same energy at the zone boundary and pushes them apart by 2|V|. The basis here is '+n+' plane waves e<sup>i(k+G)x</sup>: with one wave there are no gaps at all, and as waves are added the lower bands stop changing. This is how E<sub>cut</sub> works in Quantum ESPRESSO.'+(v>1?' With a strong potential perturbation theory no longer holds: the gap is below 2|V|, and the electrons are almost bound to the atoms.':''),
    zh:(n,v)=>'电子几乎自由：E = (k + G)²，折叠进第一布里渊区。弱势 2V cos(2πx/a) 在区边界混合两个能量相同的波，并使它们分开 2|V|。这里的基组是 '+n+' 个平面波 e<sup>i(k+G)x</sup>：只有一个波时完全没有带隙，增加波之后下方能带不再变化。Quantum ESPRESSO 中的 E<sub>cut</sub> 也是这样起作用的。'+(v>1?' 势很强时微扰理论不再适用：带隙小于 2|V|，电子几乎束缚在原子上。':'')}
};
const Q={delta:1,b1:-1,b2:-1,e:2,gd:0,V:0.3,M:3};let A=null,G=null,N=null;
const liveA=QC.live('sol.pair'),liveG=QC.live('sol.graphene'),liveN=QC.live('sol.nfe');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show()};
slider('dl',v=>{Q.delta=v;pair()},2);slider('b1',v=>{Q.b1=v;pair()},2);slider('b2',v=>{Q.b2=v;pair()},2);slider('ne',v=>{Q.e=v;pair()},2);
slider('gd',v=>{Q.gd=v;graph()},1);slider('vv',v=>{Q.V=v;nfe()},2);slider('mm',v=>{Q.M=v;nfe()},0);
function dosPlot(svg,E,cur,ymin,ymax,ef){svg.innerHTML='';const mx=Math.max(...cur.map(c=>Math.max(...c[0])))*1.08||1;
  const [X,Y]=frame(svg,300,300,[16,14,22,38],[0,mx],[ymin,ymax],[],[],tr(TX.dosAx),'');
  cur.forEach(([d,c,w])=>el('polyline',{points:E.map((e,i)=>X(d[i])+','+Y(e)).filter((p,i)=>E[i]>=ymin&&E[i]<=ymax).join(' '),fill:'none',stroke:c,'stroke-width':w},svg));
  if(ef!=null)el('line',{x1:X(0),x2:X(mx),y1:Y(ef),y2:Y(ef),stroke:tok('--ink'),'stroke-dasharray':'6 4','stroke-width':1.2},svg)}
async function pair(){try{A=await liveA({delta:Q.delta,b1:Q.b1,b2:Q.b2,e:Q.e,sigma:0.08})}catch(e){return}drawPair()}
function drawPair(){if(!A)return;const top=Math.max(...A.upper)+0.4,ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok');
  const yt=[];for(let v=Math.ceil(-top);v<=top;v++)yt.push(v);
  let svg=$('achart');svg.innerHTML='';const [X,Y]=frame(svg,620,300,[46,14,22,38],[-1,1],[-top,top],[-1,-0.5,0,0.5,1],yt,tr(TX.kAx),'E, |β|');
  [A.lower,A.upper].forEach(b=>el('polyline',{points:A.k.map((q,i)=>X(q)+','+Y(b[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg));
  el('line',{x1:X(-1),x2:X(1),y1:Y(A.ef),y2:Y(A.ef),stroke:tok('--ink'),'stroke-dasharray':'6 4','stroke-width':1.2},svg);
  el('text',{x:X(1)-4,y:Y(A.ef)-6,'text-anchor':'end',class:'lab'},svg).innerHTML='E<tspan baseline-shift="sub" font-size="75%">F</tspan>';
  dosPlot($('adchart'),A.E,[[A.dos,ac,2.2],[A.pdos_a,wr,1.6],[A.pdos_b,ok,1.6]],-top,top,A.ef);
  const i=A.E.findIndex(e=>e>=A.cbm+0.05),tot=A.dos[i]||1,share=Math.round(100*(A.pdos_a[i]||0)/tot);
  $('acards').innerHTML=card(tr(TX.gap),fmt(A.gap,2)+' |β|')+card(tr(TX.ef),fmt(A.ef,2)+' |β|')+card(tr(TX.kind),A.metal?tr(TX.metal):tr(TX.ins));
  $('aleg').innerHTML=tr(TX.leg).map((t,j)=>'<span><i class="sw" style="border-color:'+[ac,wr,ok][j]+'"></i>'+t+'</span>').join('');
  $('aNote').textContent=tr(TX.pNote)(A.metal,fmt(A.gap,2),share)}
async function graph(){try{G=await liveG({delta:Q.gd,sigma:0.15})}catch(e){return}drawGraph()}
function drawGraph(){if(!G)return;const ac=tok('--accent'),top=Math.max(...G.upper)+0.6;const yt=[];for(let v=-8;v<=8;v+=2)if(Math.abs(v)<=top)yt.push(v);
  const svg=$('gchart');svg.innerHTML='';const L=G.ticks[G.ticks.length-1];const [X,Y]=frame(svg,620,300,[46,14,22,38],[0,L],[-top,top],[],yt,'','E, eV');
  G.ticks.forEach((t,j)=>{el('line',{x1:X(t),x2:X(t),y1:Y(top),y2:Y(-top),stroke:tok('--line')},svg);el('text',{x:X(t),y:Y(-top)+16,'text-anchor':'middle'},svg,G.labels[j])});
  [G.lower,G.upper].forEach(b=>el('polyline',{points:G.x.map((x,i)=>X(x)+','+Y(b[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg));
  el('line',{x1:X(0),x2:X(L),y1:Y(0),y2:Y(0),stroke:tok('--ink'),'stroke-dasharray':'6 4','stroke-width':1.2},svg);
  dosPlot($('gdchart'),G.E,[[G.dos,ac,2.2]],-top,top,0);
  const at=x=>G.x.reduce((b,v,i)=>Math.abs(v-x)<Math.abs(G.x[b]-x)?i:b,0),h=tr(TX.gT);
  const iM=at(G.ticks[1]),iK=at(G.ticks[2]);
  $('gcards').innerHTML=card(h[0],fmt(G.gap,1)+' eV')+card(h[1],'±'+fmt(G.upper[0],1)+' eV')+card(h[2],'±'+fmt(G.upper[iM],1)+' eV')+card(h[3],'±'+fmt(G.upper[iK],1)+' eV');
  $('gNote').textContent=tr(TX.gNote)(Q.gd)}
async function nfe(){try{N=await liveN({V:Q.V,M:Math.round(Q.M)})}catch(e){return}drawNfe()}
function drawNfe(){if(!N)return;const ac=tok('--accent'),mu=tok('--muted'),top=Math.min(Math.max(...N.bands[N.bands.length-1])+2,45);
  const svg=$('nchart');svg.innerHTML='';const yt=[0,10,20,30,40].filter(v=>v<=top);
  const [X,Y]=frame(svg,960,300,[46,14,22,38],[-1,1],[Math.min(0,Math.min(...N.bands[0]))-1,top],[-1,-0.5,0,0.5,1],yt,tr(TX.kAx),'E');
  const free=[];for(let m=-3;m<=3;m++){const pts=N.k.map(q=>[X(q),Y(Math.pow(Math.PI*(q+2*m),2))]).filter(p=>p[1]>=14);if(pts.length>1)el('polyline',{points:pts.map(p=>p.join(',')).join(' '),fill:'none',stroke:mu,'stroke-width':1,'stroke-dasharray':'3 4'},svg)}
  N.bands.forEach(b=>{const pts=N.k.map((q,i)=>[X(q),Y(b[i])]).filter(p=>p[1]>=14);el('polyline',{points:pts.map(p=>p.join(',')).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg)});
  const g=N.gaps.find(x=>x.between[0]===1),h=tr(TX.nT);
  $('ncards').innerHTML=card(h[0],g?fmt(g.gap,3):'—')+card(h[1],fmt(2*Math.abs(N.V),3))+card(h[2],String(2*N.M+1));
  $('nNote').innerHTML=tr(TX.nNote)(2*N.M+1,N.V)}
pair();graph();nfe();onTheme(()=>{drawPair();drawGraph();drawNfe()});
