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
/* Conformers page (Atlas v2). The torsion profile, its minima, barriers and Boltzmann fractions,
   and the cost of a grid search come from quas_atlas.core.conformers (conf.profile, conf.cost). */
const TX={
  pre:{ru:['этан, H–C–C–H','бутан, C–C–C–C','свои параметры'],en:['ethane, H–C–C–H','butane, C–C–C–C','own parameters'],zh:['乙烷 H–C–C–H','丁烷 C–C–C–C','自定义参数']},
  kj:{ru:'кДж/моль',en:'kJ/mol',zh:'kJ/mol'},
  axis:{ru:'двугранный угол φ, °',en:'dihedral angle φ, °',zh:'二面角 φ，°'},
  conf:{ru:p=>Math.abs(Math.abs(p)-180)<20?'анти':Math.abs(p)<20?'син':'гош '+(p>0?'+':'−'),en:p=>Math.abs(Math.abs(p)-180)<20?'anti':Math.abs(p)<20?'syn':'gauche '+(p>0?'+':'−'),zh:p=>Math.abs(Math.abs(p)-180)<20?'反式':Math.abs(p)<20?'顺式':'邻位交叉 '+(p>0?'+':'−')},
  pNote:{ru:(n,b)=>'Минимумов (конформеров): <b>'+n+'</b>; самый низкий барьер между ними — <b>'+b+' кДж/моль</b>. Барьер 12–20 кДж/моль при комнатной температуре преодолевается миллиарды раз в секунду: конформеры не выделить, но их можно посчитать по отдельности.',
         en:(n,b)=>'Minima (conformers): <b>'+n+'</b>; the lowest barrier between them is <b>'+b+' kJ/mol</b>. A barrier of 12–20 kJ/mol is crossed billions of times per second at room temperature: the conformers cannot be isolated, but each can be calculated.',
         zh:(n,b)=>'极小点（构象）：<b>'+n+'</b> 个；它们之间最低的能垒为 <b>'+b+' kJ/mol</b>。室温下 12–20 kJ/mol 的能垒每秒被越过数十亿次：构象无法分离，但可以分别计算。'},
  flat:{ru:'Все V = 0: вращение свободное, минимумов нет.',en:'All V = 0: free rotation, no minima.',zh:'所有 V = 0：自由转动，没有极小点。'},
  popNote:{ru:(T,a)=>'При '+T+' K на самый низкий конформер приходится <b>'+a+' %</b> молекул. Свойство, измеряемое в опыте, — среднее по конформерам с этими весами; расчёт одного конформера даёт его лишь отчасти.',
           en:(T,a)=>'At '+T+' K the lowest conformer holds <b>'+a+' %</b> of the molecules. A measured property is the average over the conformers with these weights; one conformer gives only part of it.',
           zh:(T,a)=>T+' K 时最低构象占分子的 <b>'+a+'%</b>。实验测得的性质是按这些权重对构象的平均；只算一个构象只能得到其中一部分。'},
  starts:{ru:'стартовых структур',en:'starting structures',zh:'初始结构'},time:{ru:'время перебора',en:'time of the search',zh:'搜索时间'},
  units:{ru:['мин','ч','сут','лет'],en:['min','h','days','years'],zh:['分钟','小时','天','年']},
  costNote:{ru:'CREST не перебирает сетку: метадинамика (iMTD-GC) «расталкивает» молекулу из уже найденных минимумов и сама находит новые, а CREGEN оставляет конформеры в окне 6 ккал/моль (25 кДж/моль), отбрасывая дубликаты по RMSD 0,125 Å и энергии 0,05 ккал/моль. В «Азимуте»: Компас → «Расчёт → Поиск конформеров».',
            en:'CREST does not walk a grid: metadynamics (iMTD-GC) pushes the molecule out of the minima already found and finds new ones by itself, and CREGEN keeps the conformers within a 6 kcal/mol (25 kJ/mol) window, dropping duplicates by an RMSD of 0.125 Å and an energy of 0.05 kcal/mol. In Azimuth: Compass → «Calculation → Conformer search».',
            zh:'CREST 不做网格遍历：元动力学（iMTD-GC）把分子推离已找到的极小点并自行发现新的极小点，CREGEN 保留 6 kcal/mol（25 kJ/mol）窗口内的构象，并按 RMSD 0.125 Å 和能量 0.05 kcal/mol 去除重复。在 Azimuth 中：罗盘 →“计算 → 构象搜索”。'}
};
const PRE=[[0,0,12.0],[7.2,-2.1,13.8]];
const Q={p:1,T:298.15};
function setV(v){['V1','V2','V3'].forEach((id,i)=>{$(id).value=v[i]})}
chips($('pG'),tr(TX.pre),1,i=>{Q.p=i;mark($('pG'),i);if(i<2)setV(PRE[i]);prof()});
['V1','V2','V3'].forEach(id=>$(id).oninput=()=>{Q.p=2;mark($('pG'),2);prof()});
$('T').oninput=()=>{Q.T=+$('T').value;prof()};
const liveP=QC.live('conf.profile'),liveC=QC.live('conf.cost');
async function prof(){const V1=+$('V1').value,V2=+$('V2').value,V3=+$('V3').value;let Z;try{Z=await liveP({V1,V2,V3,T:Q.T})}catch(e){return}
  $('V1v').textContent=fmt(V1,1);$('V2v').textContent=fmt(V2,1);$('V3v').textContent=fmt(V3,1);$('Tv').textContent=fmt(Q.T,0)+' K';
  const svg=$('pchart');svg.innerHTML='';const W=960,H=300,top=Math.max(5,Math.ceil(Math.max(...Z.E)/5)*5);const yt=[];for(let v=0;v<=top;v+=top>30?10:5)yt.push(v);
  const [X,Y]=frame(svg,W,H,[54,20,16,38],[-180,180],[0,top*1.08],[-180,-120,-60,0,60,120,180],yt,tr(TX.axis),'E, '+tr(TX.kj));
  el('path',{d:Z.phi.map((p,i)=>(i?'L':'M')+X(p).toFixed(1)+' '+Y(Z.E[i]).toFixed(1)).join(''),stroke:tok('--accent'),'stroke-width':2.4,fill:'none'},svg);
  if(!Z.flat)Z.minima.forEach(m=>{const pts=Math.abs(m.phi)>179.5?[-180,180]:[m.phi];pts.forEach(p=>{el('circle',{cx:X(p),cy:Y(m.E),r:6,fill:tok('--accent'),stroke:tok('--panel'),'stroke-width':2},svg);el('text',{x:X(p),y:Y(m.E)-12,'text-anchor':'middle',class:'lab'},svg,tr(TX.conf)(p))})});
  Z.maxima.forEach(m=>el('text',{x:X(m.phi),y:Y(m.E)-8,'text-anchor':'middle'},svg,fmt(m.E,1)));
  const bmin=Z.maxima.length?Math.min(...Z.maxima.map(m=>m.E)):0;
  $('pNote').innerHTML=Z.flat?tr(TX.flat):tr(TX.pNote)(Z.minima.length,fmt(bmin,1));
  const ms=[...Z.minima].sort((a,b)=>a.E-b.E);
  $('bars').innerHTML=Z.flat?'':ms.map(m=>'<div class="bar"><span>'+tr(TX.conf)(m.phi)+' · '+fmt(m.E,1)+' '+tr(TX.kj)+'</span><span class="tr"><span class="fl" style="width:'+(m.p*100).toFixed(1)+'%"></span></span><span class="v">'+fmt(m.p*100,1)+' %</span></div>').join('');
  $('popNote').innerHTML=Z.flat?'':tr(TX.popNote)(fmt(Q.T,0),fmt(ms[0].p*100,0))}
['n','k','mn'].forEach(id=>$(id).oninput=cost);
function human(min){const u=tr(TX.units);if(min<60)return fmt(min,min<10?1:0)+' '+u[0];const h=min/60;if(h<24)return fmt(h,1)+' '+u[1];const d=h/24;if(d<365.25)return fmt(d,d<10?1:0)+' '+u[2];return sci(d/365.25)+' '+u[3]}
async function cost(){const n=+$('n').value,k=+$('k').value,mn=+$('mn').value;let Z;try{Z=await liveC({n,k,minutes:mn})}catch(e){return}
  $('nv').textContent=n;$('kv').textContent=k;$('mnv').textContent=fmt(mn,mn<1?2:mn<10?1:0)+' '+tr(TX.units)[0];
  $('ccards').innerHTML=card(k+'<sup>'+n+'</sup> — '+tr(TX.starts),sci(Z.starts,2))+card(tr(TX.time),human(Z.hours*60));
  $('cNote').textContent=tr(TX.costNote)}
function all(){prof();cost()}
setV(PRE[1]);all();onTheme(all);
