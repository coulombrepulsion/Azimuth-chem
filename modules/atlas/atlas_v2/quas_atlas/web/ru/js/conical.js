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
/* Conical intersections and biradicals (Atlas v2): the non-crossing rule, the double cone and the branching plane,
   the two-centre model of a biradical, broken symmetry and the Yamaguchi formula — quas_atlas.core.conical
   (cone.cross, cone.cone, cone.twosite, cone.yamaguchi). */
const TX={
  sym:{ru:['одной симметрии','разной симметрии'],en:['the same symmetry','different symmetry'],zh:['相同对称性','不同对称性']},
  meth:{ru:['CASSCF (связь h ≠ 0)','TD-DFT (связь S₀–S₁ = 0)'],en:['CASSCF (coupling h ≠ 0)','TD-DFT (S₀–S₁ coupling = 0)'],zh:['CASSCF（耦合 h ≠ 0）','TD-DFT（S₀–S₁ 耦合 = 0）']},
  rAx:{ru:'координата R',en:'coordinate R',zh:'坐标 R'},eAx:{ru:'энергия',en:'energy',zh:'能量'},
  xLeg:{ru:['диабатические','нижнее адиабатическое','верхнее адиабатическое'],en:['diabatic','lower adiabatic','upper adiabatic'],zh:['非绝热（透热）态','下绝热态','上绝热态']},
  xT:{ru:['щель в точке R = 0','условий для пересечения','кривые'],en:['gap at R = 0','conditions to cross','the curves'],zh:['R = 0 处的能隙','相交所需条件','曲线']},
  cond:{ru:['два: Δ = 0 и H₁₂ = 0','одно: Δ = 0 (H₁₂ ≡ 0)'],en:['two: Δ = 0 and H₁₂ = 0','one: Δ = 0 (H₁₂ ≡ 0)'],zh:['两个：Δ = 0 且 H₁₂ = 0','一个：Δ = 0（H₁₂ ≡ 0）']},
  cv:{ru:['избегают пересечения','пересекаются'],en:['avoid crossing','cross'],zh:['避免相交','相交']},
  xNote:{ru:(s)=>s?'Состояния разной симметрии: H₁₂ равен нулю тождественно, и остаётся одно условие Δ(R) = 0 — одной координаты для него хватает. Кривые пересекаются.':'Одна координата и два условия, Δ(R) = 0 и H₁₂(R) = 0: в общем случае их нельзя выполнить вместе. Адиабатические кривые сближаются на 2|H₁₂| и расходятся, меняясь характером: левая ветвь нижней кривой похожа на одно диабатическое состояние, правая — на другое. Это правило непересечения для двухатомной молекулы.',
    en:(s)=>s?'States of different symmetry: H₁₂ is identically zero, and one condition Δ(R) = 0 is left — one coordinate is enough for it. The curves cross.':'One coordinate and two conditions, Δ(R) = 0 and H₁₂(R) = 0: in general they cannot hold together. The adiabatic curves come within 2|H₁₂| and part, exchanging their character: the left branch of the lower curve looks like one diabatic state, the right one like the other. This is the non-crossing rule for a diatomic.',
    zh:(s)=>s?'不同对称性的态：H₁₂ 恒为零，只剩一个条件 Δ(R) = 0——一个坐标就够了。曲线相交。':'一个坐标、两个条件 Δ(R) = 0 和 H₁₂(R) = 0：一般无法同时满足。绝热曲线接近到 2|H₁₂| 又分开，并交换特征：下曲线左支像一个透热态，右支像另一个。这就是双原子分子的不相交规则。'},
  mapAx:{ru:['x (вдоль g)','y (вдоль h)'],en:['x (along g)','y (along h)'],zh:['x（沿 g）','y（沿 h）']},
  cLeg:{ru:['щель E₊ − E₋ (темнее — меньше)','сечение y = 0','сечение y = y₀'],en:['gap E₊ − E₋ (darker is smaller)','section y = 0','section y = y₀'],zh:['能隙 E₊ − E₋（越深越小）','截面 y = 0','截面 y = y₀']},
  cT:{ru:['щель при x = 0, y = y₀','внутренних координат','размерность шва','шов в TD-DFT'],en:['gap at x = 0, y = y₀','internal coordinates','dimension of the seam','seam in TD-DFT'],zh:['x = 0、y = y₀ 处能隙','内坐标数','交叉缝的维数','TD-DFT 中的交叉缝']},
  none:{ru:'нет',en:'none',zh:'无'},
  cNote:{ru:(td,n,s)=>(td?'В TD-DFT связь основного и возбуждённого состояния равна нулю: остаётся одно условие, и вырождение держится на целой линии x = 0 — шов на единицу шире, конуса нет. Если S₁ и S₀ ближе 0,5 эВ, TD-DFT не верьте.':'Δ ≈ g·x, H₁₂ ≈ h·y: E± = Ē ± √(g²x² + h²y²) — двойной конус. Сечение y = 0 проходит через вершину; любое другое — избегаемое пересечение со щелью 2|h·y₀|. Двухатомная молекула видит одно сечение, многоатомная может обойти конус и попасть в вершину.')+' У молекулы из '+n+' атомов шов имеет размерность '+s+'.',
    en:(td,n,s)=>(td?'In TD-DFT the coupling of the ground and the excited state is zero: one condition is left, and the degeneracy holds along the whole line x = 0 — the seam is one dimension wider, there is no cone. If S₁ and S₀ are closer than 0.5 eV, do not trust TD-DFT.':'Δ ≈ g·x, H₁₂ ≈ h·y: E± = Ē ± √(g²x² + h²y²) — a double cone. The section y = 0 passes through the tip; any other is an avoided crossing with the gap 2|h·y₀|. A diatomic sees one section; a polyatomic can go round the cone and reach the tip.')+' For a molecule of '+n+' atoms the seam has the dimension '+s+'.',
    zh:(td,n,s)=>(td?'TD-DFT 中基态与激发态的耦合为零：只剩一个条件，简并沿整条线 x = 0 保持——交叉缝多一维，没有圆锥。若 S₁ 与 S₀ 相距小于 0.5 eV，不要相信 TD-DFT。':'Δ ≈ g·x，H₁₂ ≈ h·y：E± = Ē ± √(g²x² + h²y²)——双圆锥。截面 y = 0 穿过顶点；其他截面都是能隙为 2|h·y₀| 的避免交叉。双原子分子只看到一个截面，多原子分子可以绕过圆锥到达顶点。')+n+' 个原子的分子，交叉缝维数为 '+s+'。'},
  tAx:{ru:'перескок t, эВ',en:'hopping t, eV',zh:'跃迁 t，eV'},dAx:{ru:'ΔE(T − S), кДж/моль',en:'ΔE(T − S), kJ/mol',zh:'ΔE(T − S)，kJ/mol'},
  bLeg:{ru:['точно (2 × 2)','4t²/U − 2K','опыт для бензинов'],en:['exact (2 × 2)','4t²/U − 2K','experiment for the benzynes'],zh:['精确（2 × 2）','4t²/U − 2K','苯炔实验值']},
  bz:{ru:{o:'о-',m:'м-',p:'п-'},en:{o:'o-',m:'m-',p:'p-'},zh:{o:'邻',m:'间',p:'对'}},
  bT:{ru:['ΔE(T − S) точно','по теории возмущений','основное состояние','t для о- / м- / п-бензина'],en:['ΔE(T − S) exact','by perturbation theory','ground state','t of o- / m- / p-benzyne'],zh:['ΔE(T − S) 精确','微扰理论','基态','邻 / 间 / 对苯炔的 t']},
  gs:{ru:['синглет','триплет'],en:['singlet','triplet'],zh:['单重态','三重态']},
  kj:{ru:' кДж/моль',en:' kJ/mol',zh:' kJ/mol'},ev:{ru:' эВ',en:' eV',zh:' eV'},
  bNote:{ru:(sp)=>'Без перескоков триплет ниже на 2K — правило Хунда. Перескок связывает ковалентный синглет с ионным (2t), и синглет опускается на ≈ 4t²/U: кинетический обмен. Расщепление связывающей и разрыхляющей орбиталей 2|t| = '+sp+' эВ: большое — закрытая оболочка, малое — бирадикал. Опыт для бензинов (157, 88, 16 кДж/моль) идёт в том же порядке, что и t: центры рядом, через атом, напротив. CASSCF(2,2) даёт 123 / 48 / 2, NEVPT2 — 164 / 74 / 10: динамическая корреляция стабилизирует ионную часть синглета.',
    en:(sp)=>'Without hopping the triplet is lower by 2K — the Hund rule. Hopping couples the covalent singlet with the ionic one (2t), and the singlet goes down by ≈ 4t²/U: the kinetic exchange. The splitting of the bonding and antibonding orbitals 2|t| = '+sp+' eV: large — a closed shell, small — a biradical. The experiment for the benzynes (157, 88, 16 kJ/mol) goes in the same order as t: the centres side by side, across an atom, opposite. CASSCF(2,2) gives 123 / 48 / 2, NEVPT2 164 / 74 / 10: the dynamic correlation stabilizes the ionic part of the singlet.',
    zh:(sp)=>'没有跃迁时三重态低 2K——洪德规则。跃迁把共价单重态与离子单重态耦合（2t），单重态下降约 4t²/U：动力学交换。成键与反键轨道的分裂 2|t| = '+sp+' eV：大——闭壳层，小——双自由基。苯炔的实验值（157、88、16 kJ/mol）与 t 的顺序相同：两个中心相邻、隔一个原子、相对。CASSCF(2,2) 给出 123 / 48 / 2，NEVPT2 给出 164 / 74 / 10：动态相关稳定了单重态的离子部分。'},
  yAx:{ru:'ΔE(T − S) п-бензина, кДж/моль',en:'ΔE(T − S) of p-benzyne, kJ/mol',zh:'对苯炔的 ΔE(T − S)，kJ/mol'},
  yNames:{ru:['RKS','E_T − E_BS','Ямагучи','CASSCF','NEVPT2'],en:['RKS','E_T − E_BS','Yamaguchi','CASSCF','NEVPT2'],zh:['RKS','E_T − E_BS','Yamaguchi','CASSCF','NEVPT2']},
  yLeg:{ru:['DFT','многоконфигурационные','опыт (адиабатически)'],en:['DFT','multiconfigurational','experiment (adiabatic)'],zh:['DFT','多组态','实验（绝热）']},
  yT:{ru:['ΔE(T − S) по Ямагучи','вес синглета w = 1 − ⟨S²⟩/2','правило сумм Циглера 2(E_T − E_BS)'],en:['ΔE(T − S) by Yamaguchi','weight of the singlet w = 1 − ⟨S²⟩/2','Ziegler sum rule 2(E_T − E_BS)'],zh:['Yamaguchi 公式 ΔE(T − S)','单重态权重 w = 1 − ⟨S²⟩/2','Ziegler 求和规则 2(E_T − E_BS)']},
  yNote:{ru:'Ограниченный Кон–Шэм для п-бензина даёт синглет выше триплета на 90 кДж/моль — неверный знак. Решение с нарушенной симметрией (α на одном центре, β на другом) ниже триплета, но это смесь синглета и триплета: E_BS ≈ wE_S + (1 − w)E_T, ⟨S²⟩_BS = 2(1 − w). Отсюда формула Ямагучи ΔE = 2(E_T − E_BS)/(⟨S²⟩_T − ⟨S²⟩_BS). При ⟨S²⟩_BS = 1 — правило сумм Циглера. Это вертикальная оценка в одной геометрии с одним функционалом; при малой бирадикальности (⟨S²⟩_BS → 0) формула теряет смысл.',
    en:'Restricted Kohn–Sham for p-benzyne puts the singlet 90 kJ/mol above the triplet — the wrong sign. The broken-symmetry solution (α on one centre, β on the other) lies below the triplet, but it is a mixture of the singlet and the triplet: E_BS ≈ wE_S + (1 − w)E_T, ⟨S²⟩_BS = 2(1 − w). Hence the Yamaguchi formula ΔE = 2(E_T − E_BS)/(⟨S²⟩_T − ⟨S²⟩_BS). At ⟨S²⟩_BS = 1 it is the Ziegler sum rule. It is a vertical estimate at one geometry with one functional; at a small biradical character (⟨S²⟩_BS → 0) the formula loses its meaning.',
    zh:'对苯炔的限制性 Kohn–Sham 计算使单重态比三重态高 90 kJ/mol——符号错误。破缺对称解（α 在一个中心，β 在另一个中心）低于三重态，但它是单重态与三重态的混合：E_BS ≈ wE_S + (1 − w)E_T，⟨S²⟩_BS = 2(1 − w)。由此得到 Yamaguchi 公式 ΔE = 2(E_T − E_BS)/(⟨S²⟩_T − ⟨S²⟩_BS)。⟨S²⟩_BS = 1 时即 Ziegler 求和规则。这是一个几何、一个泛函下的垂直估计；双自由基性很小时（⟨S²⟩_BS → 0）公式失去意义。'}
};
const Q={c:0.1,sym:0,g:1,h:0.6,y0:0.3,tl:0,td:0,na:6,t:0.5,U:4,K:0.02,de:10.3,s2:1};let X=null,C=null,B=null,Y=null;
const liveX=QC.live('cone.cross'),liveC=QC.live('cone.cone'),liveB=QC.live('cone.twosite'),liveY=QC.live('cone.yamaguchi');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show()};
slider('cc',v=>{Q.c=v;xr()},2);chips($('sG'),tr(TX.sym),Q.sym,i=>{Q.sym=i;mark($('sG'),i);xr()});
slider('gg',v=>{Q.g=v;cn()},2);slider('hh',v=>{Q.h=v;cn()},2);slider('yy',v=>{Q.y0=v;cn()},2);slider('tl',v=>{Q.tl=v;cn()},2);slider('na',v=>{Q.na=v;cn()},0);
chips($('dG'),tr(TX.meth),Q.td,i=>{Q.td=i;mark($('dG'),i);cn()});
slider('tt',v=>{Q.t=v;bi()},2);slider('uu',v=>{Q.U=v;bi()},1);slider('kk',v=>{Q.K=v;bi()},2);
slider('de',v=>{Q.de=v;ya()},1);slider('s2',v=>{Q.s2=v;ya()},2);
const cl=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
const legend=(id,names,colors,dash)=>{$(id).innerHTML=names.map((s,j)=>'<span><i class="sw" style="border-color:'+colors[j]+(dash&&dash[j]?';border-style:dashed':'')+'"></i>'+s+'</span>').join('')};
const ticks=(a,b,s)=>{const o=[];for(let v=Math.ceil(a/s-1e-9)*s;v<=b+1e-9;v+=s)o.push(+v.toFixed(6));return o};
function lines(svg,H,xr,yr,xs,ys,xl,yl,series){svg.innerHTML='';const [Xf,Yf]=frame(svg,960,H,[60,14,22,38],xr,yr,ticks(xr[0],xr[1],xs),ticks(yr[0],yr[1],ys),xl,yl);
  series.forEach(([px,py,c,w,d])=>{let seg=[];const put=()=>{if(seg.length>1)el('polyline',{points:seg.join(' '),fill:'none',stroke:c,'stroke-width':w,'stroke-dasharray':d||''},svg);seg=[]};
    px.forEach((x,i)=>{if(py[i]>=yr[0]-1e-9&&py[i]<=yr[1]+1e-9)seg.push(Xf(x)+','+Yf(py[i]));else put()});put()});return [Xf,Yf]}
async function xr(){try{X=await liveX({c:Q.c,sym:Q.sym})}catch(e){return}drawX()}
function drawX(){if(!X)return;const ac=tok('--accent'),wr=tok('--warn'),ink=tok('--ink');
  lines($('xchart'),300,[-2,2],[-0.5,3],0.5,0.5,tr(TX.rAx),tr(TX.eAx),[[X.x,X.d1,ink,1.2,'5 4'],[X.x,X.d2,ink,1.2,'5 4'],[X.x,X.lo,ac,2.6],[X.x,X.hi,wr,2.6]]);
  legend('xleg',tr(TX.xLeg),[ink,ac,wr],[1,0,0]);const h=tr(TX.xT),s=X.crossing?1:0;
  $('xcards').innerHTML=card(h[0],fmt(X.gap,2))+card(h[1],tr(TX.cond)[Q.sym])+card(h[2],tr(TX.cv)[s]);
  $('xNote').textContent=tr(TX.xNote)(Q.sym)}
async function cn(){try{C=await liveC({g:Q.g,h:Q.h,y0:Q.y0,tilt:Q.tl,tddft:Q.td,atoms:Math.round(Q.na)})}catch(e){return}drawC()}
function drawC(){if(!C)return;const ac=tok('--accent'),wr=tok('--warn'),ink=tok('--ink'),svg=$('cmap');svg.innerHTML='';
  const ax=tr(TX.mapAx),[Xf,Yf]=frame(svg,960,300,[60,14,22,38],[-1,1],[-1,1],ticks(-1,1,0.5),ticks(-1,1,0.5),ax[0],ax[1]);
  const top=Math.max(...C.gap.map(r=>Math.max(...r)))||1,dx=(Xf(1)-Xf(-1))/40,dy=(Yf(-1)-Yf(1))/40,g=el('g',{'shape-rendering':'crispEdges'},svg);
  C.gap.forEach((row,j)=>row.forEach((v,i)=>{const q=Math.floor(16*Math.min(1,v/top))/16;el('rect',{x:Xf(C.x[i])-dx/2,y:Yf(C.y[j])-dy/2,width:dx,height:dy,fill:ac,opacity:(0.85*Math.pow(1-q,2)).toFixed(3)},g)}));
  el('line',{x1:Xf(-1),x2:Xf(1),y1:Yf(0),y2:Yf(0),stroke:ink,'stroke-dasharray':'5 4','stroke-width':1.4},svg);
  el('line',{x1:Xf(-1),x2:Xf(1),y1:Yf(Q.y0),y2:Yf(Q.y0),stroke:wr,'stroke-width':2},svg);
  const all=C.sec0.hi.concat(C.sec.hi).concat(C.sec0.lo).concat(C.sec.lo),m=Math.max(1,...all.map(Math.abs));const yr=[-Math.ceil(m*2)/2,Math.ceil(m*2)/2];
  lines($('csec'),280,[-1,1],yr,0.5,yr[1]>2?1:0.5,ax[0],tr(TX.eAx),[[C.sx,C.sec0.lo,ink,1.4,'5 4'],[C.sx,C.sec0.hi,ink,1.4,'5 4'],[C.sx,C.sec.lo,wr,2.6],[C.sx,C.sec.hi,wr,2.6]]);
  legend('cleg',tr(TX.cLeg),[ac,ink,wr],[0,1,0]);const h=tr(TX.cT),sd=v=>v<0?tr(TX.none):String(v);
  $('ccards').innerHTML=card(h[0],fmt(C.gap_y0,2))+card(h[1],String(C.n_int))+card(h[2],sd(C.seam))+card(h[3],sd(C.seam_tddft));
  $('cNote').textContent=tr(TX.cNote)(Q.td,Math.round(Q.na),sd(Q.td?C.seam_tddft:C.seam))}
async function bi(){try{B=await liveB({t:Q.t,U:Q.U,K:Q.K})}catch(e){return}drawB()}
function drawB(){if(!B)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok'),ink=tok('--ink'),svg=$('bchart');
  const [Xf,Yf]=lines(svg,320,[0,2],[-50,300],0.25,50,tr(TX.tAx),tr(TX.dAx),[[B.t,B.exact,ac,2.6],[B.t,B.approx,wr,2,'6 4']]);
  const bz=tr(TX.bz);B.benzynes.forEach(b=>{el('line',{x1:Xf(0),x2:Xf(2),y1:Yf(b.exp),y2:Yf(b.exp),stroke:ok,'stroke-dasharray':'2 4','stroke-width':1.6},svg);
    el('text',{x:Xf(2)-6,y:Yf(b.exp)-5,'text-anchor':'end',class:'lab'},svg,bz[b.name]+' '+fmt(b.exp,0));
    if(b.t_fit!=null)el('circle',{cx:Xf(b.t_fit),cy:Yf(b.exp),r:4,fill:ok},svg)});
  el('line',{x1:Xf(Q.t),x2:Xf(Q.t),y1:Yf(-50),y2:Yf(300),stroke:ink,'stroke-dasharray':'3 4','stroke-width':1},svg);
  el('circle',{cx:Xf(Q.t),cy:Yf(cl(B.at.exact,-50,300)),r:5,fill:ac},svg);
  legend('bleg',tr(TX.bLeg),[ac,wr,ok],[0,1,1]);const h=tr(TX.bT),a=B.at,kj=tr(TX.kj);
  const tf=B.benzynes.map(b=>b.t_fit==null?'—':fmt(b.t_fit,2)).join(' / ');
  $('bcards').innerHTML=card(h[0],fmt(a.exact,1)+kj)+card(h[1],fmt(a.approx,1)+kj)+card(h[2],tr(TX.gs)[a.exact>=0?0:1])+card(h[3],tf+tr(TX.ev));
  $('bNote').textContent=tr(TX.bNote)(fmt(a.split,2))}
async function ya(){try{Y=await liveY({dE:Q.de,s2:Q.s2})}catch(e){return}drawY()}
function drawY(){if(!Y)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok'),svg=$('ychart');svg.innerHTML='';const names=tr(TX.yNames),rows=Y.methods;
  const top=Math.max(40,...rows.map(r=>r.value))+10,yr=[-100,Math.ceil(top/20)*20];
  const [Xf,Yf]=frame(svg,960,300,[60,14,34,40],[0,rows.length],yr,[],ticks(yr[0],yr[1],20),'',tr(TX.yAx));
  rows.forEach((r,i)=>{const x0=Xf(i+0.18),x1=Xf(i+0.82),y0=Yf(Math.max(0,r.value)),y1=Yf(Math.min(0,r.value)),multi=i>=3;
    el('rect',{x:x0,y:y0,width:x1-x0,height:Math.max(1,y1-y0),fill:multi?ok:ac,opacity:0.78},svg);
    el('text',{x:(x0+x1)/2,y:300-22,'text-anchor':'middle'},svg,names[i]);
    el('text',{x:(x0+x1)/2,y:r.value>=0?y0-6:y1+16,'text-anchor':'middle',class:'lab'},svg,fmt(r.value,1))});
  el('line',{x1:Xf(0),x2:Xf(rows.length),y1:Yf(0),y2:Yf(0),stroke:tok('--ink'),'stroke-width':1},svg);
  el('line',{x1:Xf(0),x2:Xf(rows.length),y1:Yf(Y.exp),y2:Yf(Y.exp),stroke:wr,'stroke-dasharray':'6 4','stroke-width':1.6},svg);
  legend('yleg',tr(TX.yLeg),[ac,ok,wr],[0,0,1]);const h=tr(TX.yT),a=Y.at,kj=tr(TX.kj);
  $('ycards').innerHTML=card(h[0],fmt(a.dest,1)+kj)+card(h[1],fmt(a.w,2))+card(h[2],fmt(a.ziegler,1)+kj);
  $('yNote').textContent=tr(TX.yNote)}
xr();cn();bi();ya();onTheme(()=>{drawX();drawC();drawB();drawY()});
