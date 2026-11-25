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
/* Crystals page (Atlas v2). Cell volume and density, allowed reflections with Bragg angles and
   cubic packings come from quas_atlas.core.crystals (cr.presets, cr.cell, cr.pattern, cr.packing). */
const TX={
  pre:{ru:['NaCl','медь Cu','железо α-Fe','кремний Si','алмаз C','полоний α-Po','лёд Ih'],en:['NaCl','copper Cu','iron α-Fe','silicon Si','diamond C','polonium α-Po','ice Ih'],zh:['NaCl','铜 Cu','α-铁 Fe','硅 Si','金刚石 C','α-钋 Po','冰 Ih']},
  keys:['nacl','cu','fe','si','diamond','po','ice'],
  exp:{nacl:2.165,cu:8.96,fe:7.87,si:2.329,diamond:3.51,po:9.20,ice:0.917},
  cent:{ru:{P:'примитивная P',I:'объёмноцентрированная I',F:'гранецентрированная F',D:'алмаз (F + базис из двух атомов)',H:'гексагональная плотнейшая (hcp)'},en:{P:'primitive P',I:'body-centred I',F:'face-centred F',D:'diamond (F + a two-atom basis)',H:'hexagonal close packing (hcp)'},zh:{P:'简单 P',I:'体心 I',F:'面心 F',D:'金刚石（F + 双原子基元）',H:'六方密堆积（hcp）'}},
  V:{ru:'объём ячейки',en:'cell volume',zh:'晶胞体积'},rho:{ru:'плотность',en:'density',zh:'密度'},expT:{ru:'опыт',en:'experiment',zh:'实验'},
  cNote:{ru:(z,m)=>'В ячейке Z = '+z+' формульных единиц массой '+m+' г/моль: ρ = Z·M/(N<sub>A</sub>·V). По этой формуле проверяют расшифрованную структуру: если плотность не сходится с измеренной, ошибка в Z или в составе.',en:(z,m)=>'The cell holds Z = '+z+' formula units of '+m+' g/mol: ρ = Z·M/(N<sub>A</sub>·V). This is how a solved structure is checked: if the density disagrees with the measured one, Z or the composition is wrong.',zh:(z,m)=>'晶胞含 Z = '+z+' 个摩尔质量为 '+m+' g/mol 的式单元：ρ = Z·M/(N<sub>A</sub>·V)。解析出的结构就用此式检验：若密度与实测不符，则 Z 或组成有误。'},
  bad:{ru:'Проверьте параметры: длины 0,5–100 Å, углы 20–160°, Z ≥ 1, M > 0.',en:'Check the parameters: lengths 0.5–100 Å, angles 20–160°, Z ≥ 1, M > 0.',zh:'请检查参数：边长 0.5–100 Å，角度 20–160°，Z ≥ 1，M > 0。'},
  th:{ru:['hkl','d, Å','2θ, °','кратность'],en:['hkl','d, Å','2θ, °','multiplicity'],zh:['hkl','d, Å','2θ, °','多重性']},
  axis:{ru:'2θ, °',en:'2θ, °',zh:'2θ, °'},
  lam:{ru:['Cu Kα₁, 1,5406 Å','Mo Kα₁, 0,7093 Å'],en:['Cu Kα₁, 1.5406 Å','Mo Kα₁, 0.7093 Å'],zh:['Cu Kα₁，1.5406 Å','Mo Kα₁，0.7093 Å']},
  pNote:{ru:c=>'Решётка: '+c+'. Высота палочки — кратность (число плоскостей с тем же d); настоящие интенсивности зависят ещё от атомов и их положений (структурный фактор). Погасания центрированной решётки убирают целые серии отражений — по ним определяют тип решётки.',en:c=>'Lattice: '+c+'. The height of a stick is the multiplicity (the number of planes with the same d); real intensities also depend on the atoms and their positions (the structure factor). The extinctions of a centred lattice remove whole series of reflections — they tell the lattice type.',zh:c=>'晶格：'+c+'。竖线高度为多重性（d 相同的晶面数）；实际强度还取决于原子及其位置（结构因子）。有心晶格的系统消光会去掉整组衍射，据此判断晶格类型。'},
  pk:{ru:['простая (sc)','объёмноцентрированная (bcc)','гранецентрированная (fcc)','алмаз'],en:['simple (sc)','body-centred (bcc)','face-centred (fcc)','diamond'],zh:['简单（sc）','体心（bcc）','面心（fcc）','金刚石']},
  pkT:{ru:['атомов на ячейку','координационное число','заполнение объёма','a / r'],en:['atoms per cell','coordination number','space filling','a / r'],zh:['每晶胞原子数','配位数','空间占有率','a / r']},
  pkNote:{ru:['Простая кубическая — редкость: так устроен лишь α-полоний.','ОЦК: щелочные металлы, α-Fe, Cr, W — каждый атом касается восьми соседей по диагонали куба.','ГЦК (кубическая плотнейшая): Cu, Ag, Au, Al, Ni — 74 % объёма, как у гексагональной плотнейшей упаковки.','Алмаз: C, Si, Ge — тетраэдрическая координация, заполнено лишь 34 % объёма.'],en:['Simple cubic is rare: only α-polonium is built this way.','bcc: alkali metals, α-Fe, Cr, W — every atom touches eight neighbours along the cube diagonal.','fcc (cubic close packing): Cu, Ag, Au, Al, Ni — 74 % of the volume, as in the hexagonal close packing.','Diamond: C, Si, Ge — tetrahedral coordination, only 34 % of the volume filled.'],zh:['简单立方很少见：只有 α-钋是这样。','体心立方：碱金属、α-Fe、Cr、W——每个原子沿体对角线与八个近邻接触。','面心立方（立方密堆积）：Cu、Ag、Au、Al、Ni——占体积 74%，与六方密堆积相同。','金刚石：C、Si、Ge——四面体配位，仅占体积 34%。']}
};
const GCM=LG==='ru'?' г/см³':' g/cm³';let PRE=null;const Q={p:1,lam:1.540593,pk:2};
const IDS=['a','b','c','al','be','ga','Z','M'];
function setCell(c){IDS.forEach(k=>{$('c'+k).value=String(c[k]).replace('.',DEC)});$('cent').value=c.cent}
chips($('pG'),tr(TX.pre),1,i=>{Q.p=i;mark($('pG'),i);setCell(PRE[TX.keys[i]]);upd()});
IDS.forEach(k=>$('c'+k).oninput=()=>{Q.p=-1;mark($('pG'),-1);upd()});$('cent').onchange=upd;
chips($('lG'),tr(TX.lam),0,i=>{Q.lam=[1.540593,0.70930][i];mark($('lG'),i);upd()});
chips($('kG'),tr(TX.pk),2,i=>{Q.pk=i;mark($('kG'),i);pack()});
const liveC=QC.live('cr.cell'),liveP=QC.live('cr.pattern'),liveK=QC.live('cr.packing');
function cellVals(){const v={};for(const k of IDS){v[k]=num($('c'+k).value)}return v}
/* the limits are checked here, the wrong field is outlined (the server answered in English) */
const RNG={a:[0.5,100],b:[0.5,100],c:[0.5,100],al:[20,160],be:[20,160],ga:[20,160],Z:[1,1000],M:[0.001,1e5]};
async function upd(){const v=cellVals(),out=IDS.filter(k=>!(isFinite(v[k])&&v[k]>=RNG[k][0]&&v[k]<=RNG[k][1]));
  IDS.forEach(k=>$('c'+k).classList.toggle('bad',out.includes(k)));
  if(out.length){$('ccards').innerHTML='';$('cNote').textContent=tr(TX.bad);return}
  let C,P;try{C=await liveC({a:v.a,b:v.b,c:v.c,al:v.al,be:v.be,ga:v.ga,Z:Math.round(v.Z),M:v.M});P=await liveP({a:v.a,b:v.b,c:v.c,al:v.al,be:v.be,ga:v.ga,cent:$('cent').value,lam:Q.lam,n:14})}catch(e){if(e&&e.message&&!/stale/i.test(e.message)){$('ccards').innerHTML='';$('cNote').textContent=tr(TX.bad)}return}
  const k=Q.p>=0?TX.keys[Q.p]:null;
  $('ccards').innerHTML=card(tr(TX.V),fmt(C.V,2)+' Å³')+card(tr(TX.rho),fmt(C.rho,3)+GCM,k?tr(TX.expT)+': '+fmt(TX.exp[k],3)+GCM:'');
  $('cNote').innerHTML=tr(TX.cNote)(Math.round(v.Z),fmt(v.M,3));
  const L=P.lines,h=tr(TX.th);
  $('ptab').innerHTML='<tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr>'+L.map(l=>'<tr><td>('+l.hkl.map(x=>x<0?'<span style="text-decoration:overline">'+(-x)+'</span>':x).join('')+')</td><td>'+fmt(l.d,4)+'</td><td>'+fmt(l.tt,2)+'</td><td>'+l.mult+'</td></tr>').join('');
  const svg=$('xchart');svg.innerHTML='';const W=960,H=240,mx=Math.max(1,...L.map(l=>l.mult));
  /* the axis 2θ follows the lines (it always went 10…120°, and the lines crowded at the left with
     their labels on top of each other); labels of close lines are lifted in turn */
  const tts=L.map(l=>l.tt).filter(v=>v<=150),lo=tts.length?Math.max(0,Math.floor((Math.min(...tts)-6)/5)*5):10,hi=tts.length?Math.min(150,Math.ceil((Math.max(...tts)+6)/5)*5):120;
  const span=hi-lo,step=[2,5,10,20].find(s=>span/s<=12)||20,xt=[];for(let v=Math.ceil(lo/step)*step;v<=hi;v+=step)xt.push(v);
  const [X,Y]=frame(svg,W,H,[30,20,26,38],[lo,hi],[0,mx*1.45],xt,[],tr(TX.axis),'');
  let lastX=-1e9,lift=0;
  L.forEach(l=>{if(l.tt>hi||l.tt<lo)return;const x=X(l.tt);lift=x-lastX<34?(lift+1)%3:0;lastX=x;
    el('line',{x1:x,x2:x,y1:Y(0),y2:Y(l.mult),stroke:tok('--accent'),'stroke-width':3,'stroke-linecap':'round'},svg);
    el('text',{x,y:Y(l.mult)-6-lift*14,'text-anchor':'middle',class:'lab'},svg,l.hkl.map(x=>x<0?'−'+(-x):x).join(''))});
  $('pNote').textContent=tr(TX.pNote)(tr(TX.cent)[$('cent').value])}
function cube(svg,kind){svg.innerHTML='';const s=150,ox=60,oy=40,dx=60,dy=-36;const P=(x,y,z)=>[ox+x*s+z*dx,oy+s+36-y*s+z*dy];const ln=tok('--line'),ac=tok('--accent'),mu=tok('--muted');
  const E=[[0,0,0,1,0,0],[0,0,0,0,1,0],[0,0,0,0,0,1],[1,1,1,0,1,1],[1,1,1,1,0,1],[1,1,1,1,1,0],[1,0,0,1,1,0],[1,0,0,1,0,1],[0,1,0,1,1,0],[0,1,0,0,1,1],[0,0,1,1,0,1],[0,0,1,0,1,1]];
  E.forEach(e=>{const a=P(e[0],e[1],e[2]),b=P(e[3],e[4],e[5]);el('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:mu,'stroke-width':1.2},svg)});
  const at=[];for(const x of [0,1])for(const y of [0,1])for(const z of [0,1])at.push([x,y,z,'c']);
  if(kind===1)at.push([.5,.5,.5,'b']);
  if(kind===2||kind===3){[[.5,.5,0],[.5,.5,1],[.5,0,.5],[.5,1,.5],[0,.5,.5],[1,.5,.5]].forEach(p=>at.push([...p,'f']))}
  if(kind===3){[[.25,.25,.25],[.75,.75,.25],[.75,.25,.75],[.25,.75,.75]].forEach(p=>at.push([...p,'i']))}
  at.sort((p,q)=>q[2]-p[2]).forEach(([x,y,z,t])=>{const [u,v]=P(x,y,z);el('circle',{cx:u,cy:v,r:t==='i'?9:11,fill:t==='i'?mu:ac,stroke:tok('--panel'),'stroke-width':2,opacity:t==='c'?0.85:1},svg)})}
async function pack(){const kinds=['sc','bcc','fcc','diamond'];let Z;try{Z=await liveK({kind:kinds[Q.pk]})}catch(e){return}const h=tr(TX.pkT);
  $('kcards').innerHTML=card(h[0],String(Z.Z))+card(h[1],String(Z.cn))+card(h[2],fmt(Z.pf*100,1)+' %')+card(h[3],fmt(Z.a_over_r,3));
  $('kNote').textContent=tr(TX.pkNote)[Q.pk];cube($('kcube'),Q.pk)}
async function start(){try{PRE=await QC.api('cr.presets',{})}catch(e){return}setCell(PRE.cu);upd();pack()}
start();onTheme(()=>{if(PRE){upd();pack()}});
