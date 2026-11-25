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
/* Spin states of transition-metal complexes in DFT (Atlas v2): the spin gap against the share of exact exchange,
   spin contamination, the geometry that depends on the spin — quas_atlas.core.spinstates (spin.gap, spin.contam,
   spin.geom). */
const TX={
  names:{ru:{water:'[Fe(H₂O)₆]²⁺',nch:'[Fe(NCH)₆]²⁺',co:'[Fe(CO)₆]²⁺'},en:{water:'[Fe(H₂O)₆]²⁺',nch:'[Fe(NCH)₆]²⁺',co:'[Fe(CO)₆]²⁺'},zh:{water:'[Fe(H₂O)₆]²⁺',nch:'[Fe(NCH)₆]²⁺',co:'[Fe(CO)₆]²⁺'}},
  aAx:{ru:'доля точного обмена a, %',en:'share of exact exchange a, %',zh:'精确交换比例 a，%'},gAx:{ru:'E(ВС) − E(НС), кДж/моль',en:'E(HS) − E(LS), kJ/mol',zh:'E(高自旋) − E(低自旋)，kJ/mol'},
  hs:{ru:'ВС',en:'HS',zh:'高自旋'},ls:{ru:'НС',en:'LS',zh:'低自旋'},
  zero:{ru:'знак меняется при ',en:'sign changes at ',zh:'变号于 '},nozero:{ru:'знак не меняется',en:'no sign change',zh:'不变号'},
  slope:{ru:' кДж/моль на 1 %',en:' kJ/mol per 1 %',zh:' kJ/mol / 1 %'},
  gNote:{ru:(a)=>'Обмен даёт −K на каждую пару параллельных спинов: в высокоспиновом d⁶ (5α + 1β) таких пар 10, в низкоспиновом (3α + 3β) — 6. Хартри–Фок с точным обменом и без корреляции занижает высокий спин, чистый GGA переоценивает делокализацию — низкий. Гибрид с долей a: ΔE(a) ≈ ΔE(0) − k·a, и наклон k тем больше, чем ковалентнее связь металл–лиганд. При a = '+a+' % — см. карточки. Для [Fe(NCH)₆]²⁺ BP86 говорит «низкий спин», B3LYP — «высокий»: вывод по одному функционалу делать нельзя. Разумно 10–15 % (TPSSh, B3LYP*), и всегда сверка двумя-тремя функционалами.',
    en:(a)=>'Exchange gives −K for every pair of parallel spins: in high-spin d⁶ (5α + 1β) there are 10 such pairs, in low-spin (3α + 3β) 6. Hartree–Fock with exact exchange and no correlation puts the high spin too low, a pure GGA overestimates delocalization — the low spin. A hybrid with the share a: ΔE(a) ≈ ΔE(0) − k·a, and the slope k is the larger the more covalent the metal–ligand bond. At a = '+a+' % — see the cards. For [Fe(NCH)₆]²⁺ BP86 says «low spin», B3LYP «high»: one functional is not enough for a conclusion. 10–15 % is reasonable (TPSSh, B3LYP*), always checked with two or three functionals.',
    zh:(a)=>'每对平行自旋给出交换 −K：高自旋 d⁶（5α + 1β）有 10 对，低自旋（3α + 3β）有 6 对。有精确交换而无相关的 Hartree–Fock 使高自旋过低，纯 GGA 高估离域——使低自旋过低。比例为 a 的杂化泛函：ΔE(a) ≈ ΔE(0) − k·a，金属–配体键越共价，斜率 k 越大。a = '+a+' % 时见卡片。对 [Fe(NCH)₆]²⁺，BP86 给出“低自旋”，B3LYP 给出“高自旋”：不能只凭一个泛函下结论。10–15 % 较合理（TPSSh、B3LYP*），并总要用两三个泛函核对。'},
  mult:{ru:['синглет','дублет','триплет','квартет','квинтет','секстет'],en:['singlet','doublet','triplet','quartet','quintet','sextet'],zh:['单重态','二重态','三重态','四重态','五重态','六重态']},
  sept:{ru:'септет',en:'septet',zh:'七重态'},sAx:{ru:'⟨S²⟩',en:'⟨S²⟩',zh:'⟨S²⟩'},
  cT:{ru:['должно быть S(S + 1)','избыток','примесь состояния S + 1','вердикт'],en:['should be S(S + 1)','excess','admixture of S + 1','verdict'],zh:['应为 S(S + 1)','超出','S + 1 态的混入','结论']},
  ok:{ru:['чисто','терпимо','не доверять'],en:['clean','tolerable','do not trust'],zh:['干净','可接受','不可信']},
  cNote:{ru:'Неограниченный определитель — не собственная функция Ŝ²: ⟨S²⟩ = S(S + 1) + N_β − Σ|⟨φ_i^α|φ_j^β⟩|². Если каждая β-орбиталь совпадает с какой-то α-орбиталью, добавка ноль; разошлись — положительна. Избыток делят на расстояние до следующего состояния и получают долю примеси. Не путайте ⟨S²⟩ с числом неспаренных электронов: у квинтета их четыре, а ⟨S²⟩ = 6. Ещё две проверки: спиновая заселённость на металле (для высокоспинового Fe(II) около 3,6–3,9) и заселённости d-орбиталей.',
    en:'An unrestricted determinant is not an eigenfunction of Ŝ²: ⟨S²⟩ = S(S + 1) + N_β − Σ|⟨φ_i^α|φ_j^β⟩|². If every β orbital coincides with some α orbital the addition is zero; if they part, it is positive. The excess divided by the distance to the next state gives the share of the admixture. Do not confuse ⟨S²⟩ with the number of unpaired electrons: a quintet has four of them and ⟨S²⟩ = 6. Two more checks: the spin population on the metal (about 3.6–3.9 for high-spin Fe(II)) and the populations of the d orbitals.',
    zh:'非限制性行列式不是 Ŝ² 的本征函数：⟨S²⟩ = S(S + 1) + N_β − Σ|⟨φ_i^α|φ_j^β⟩|²。若每个 β 轨道都与某个 α 轨道重合，附加项为零；若分开，则为正。把超出量除以到下一个态的距离，就得到混入比例。不要把 ⟨S²⟩ 与未成对电子数混淆：五重态有四个未成对电子，而 ⟨S²⟩ = 6。另外两项检查：金属上的自旋布居（高自旋 Fe(II) 约 3.6–3.9）和 d 轨道布居。'},
  rAx:{ru:'Fe–L, Å',en:'Fe–L, Å',zh:'Fe–L，Å'},
  rLeg:{ru:['квинтет: две короткие и четыре длинные','синглет: все шесть равны'],en:['quintet: two short and four long','singlet: all six equal'],zh:['五重态：两短四长','单重态：六根相等']},
  rT:{ru:['квинтет, короткие / длинные','синглет','квинтет длиннее на'],en:['quintet, short / long','singlet','quintet longer by'],zh:['五重态，短 / 长','单重态','五重态长出']},
  rNote:{ru:'В высокоспиновом состоянии два электрона сидят на e_g* — разрыхляющих орбиталях металл–лиганд: все шесть связей длиннее на 0,1–0,4 Å, тем сильнее, чем прочнее связь. Типичная ошибка DFT в длине связи — 0,02 Å. Поэтому оба состояния оптимизируют отдельно, каждое со своей мультиплетностью, и сравнивают энергии в минимумах (адиабатическая разность). Две связи квинтета короче четырёх: t₂g⁴ вырождена, и октаэдр слегка искажается (Ян–Теллер) — не навязывайте комплексу симметрию.',
    en:'In the high-spin state two electrons sit on e_g* — the metal–ligand antibonding orbitals: all six bonds are 0.1–0.4 Å longer, the more so the stronger the bond. A typical DFT error in a bond length is 0.02 Å. So both states are optimized separately, each with its own multiplicity, and the energies are compared at the minima (the adiabatic difference). Two bonds of the quintet are shorter than four: t₂g⁴ is degenerate and the octahedron distorts slightly (Jahn–Teller) — do not impose a symmetry on the complex.',
    zh:'高自旋态中有两个电子位于 e_g*——金属–配体反键轨道：六根键都长 0.1–0.4 Å，键越强伸长越多。DFT 键长的典型误差为 0.02 Å。因此两个态分别以各自的多重度优化，并在各自极小点比较能量（绝热差）。五重态中两根键比另四根短：t₂g⁴ 简并，八面体略有畸变（Jahn–Teller）——不要强加对称性。'},
  ang:{ru:' Å',en:' Å',zh:' Å'},kj:{ru:' кДж/моль',en:' kJ/mol',zh:' kJ/mol'}
};
const KEYS=['water','nch','co'],SV=[0,0.5,1,1.5,2,2.5];
const Q={a:20,m:4,s2:6.9,k:0};let G=null,C=null,R=null;
const liveG=QC.live('spin.gap'),liveC=QC.live('spin.contam'),liveR=QC.live('spin.geom');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show()};
slider('ax',v=>{Q.a=v;gp()},0);slider('s2',v=>{Q.s2=v;ct()},2);
chips($('mG'),tr(TX.mult),Q.m,i=>{Q.m=i;mark($('mG'),i);ct()});
chips($('kG'),KEYS.map(k=>tr(TX.names)[k]),Q.k,i=>{Q.k=i;mark($('kG'),i);gm()});
const legend=(id,names,colors,dash)=>{$(id).innerHTML=names.map((s,j)=>'<span><i class="sw" style="border-color:'+colors[j]+(dash&&dash[j]?';border-style:dashed':'')+'"></i>'+s+'</span>').join('')};
const ticks=(a,b,s)=>{const o=[];for(let v=Math.ceil(a/s-1e-9)*s;v<=b+1e-9;v+=s)o.push(+v.toFixed(6));return o};
const cols=()=>[tok('--accent'),tok('--ok'),tok('--warn')];
async function gp(){try{G=await liveG({a:Q.a})}catch(e){return}drawG()}
function drawG(){if(!G)return;const svg=$('gchart');svg.innerHTML='';const c=cols(),ink=tok('--ink'),nm=tr(TX.names);
  const [X,Y]=frame(svg,960,340,[64,14,26,40],[0,60],[-250,390],ticks(0,60,10),ticks(-200,300,100),tr(TX.aAx),tr(TX.gAx));
  el('line',{x1:X(0),x2:X(60),y1:Y(0),y2:Y(0),stroke:ink,'stroke-width':1.2},svg);
  el('text',{x:X(60)-6,y:Y(0)-8,'text-anchor':'end',class:'lab'},svg,'↑ '+tr(TX.ls)+' · '+tr(TX.hs)+' ↓');
  G.functionals.forEach(([n,a])=>el('text',{x:X(a),y:Y(390)+12,'text-anchor':'middle',class:'lab'},svg,n));
  G.complexes.forEach((k,j)=>{el('line',{x1:X(0),x2:X(60),y1:Y(k.icept),y2:Y(k.icept+60*k.slope),stroke:c[j],'stroke-width':2,'stroke-dasharray':'6 4'},svg);
    k.points.forEach(([a,v])=>el('circle',{cx:X(a),cy:Y(v),r:5,fill:c[j]},svg));
    el('circle',{cx:X(Q.a),cy:Y(Math.max(-250,Math.min(390,k.at))),r:6,fill:'none',stroke:c[j],'stroke-width':2.4},svg)});
  el('line',{x1:X(Q.a),x2:X(Q.a),y1:Y(-250),y2:Y(390),stroke:ink,'stroke-dasharray':'3 4','stroke-width':1},svg);
  legend('gleg',KEYS.map(k=>nm[k]),c);
  $('gcards').innerHTML=G.complexes.map(k=>card(nm[k.key],fmt(k.at,0)+tr(TX.kj)+' ('+(k.at<0?tr(TX.hs):tr(TX.ls))+')',fmt(k.slope,2)+tr(TX.slope)+' · '+(k.zero!=null?tr(TX.zero)+fmt(k.zero,1)+' %':tr(TX.nozero)))).join('');
  $('gNote').textContent=tr(TX.gNote)(fmt(Q.a,0))}
async function ct(){try{C=await liveC({S:SV[Q.m],s2:Q.s2})}catch(e){return}drawC()}
function drawC(){if(!C)return;const svg=$('cchart');svg.innerHTML='';const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok'),line=tok('--line');
  const [X,Y]=frame(svg,960,200,[40,14,20,36],[0,16],[-0.1,1],ticks(0,16,2),[],tr(TX.sAx),'');
  const mult=tr(TX.mult);C.ladder.forEach(([s,v],i)=>{if(v>16)return;const me=Math.abs(s-C.S)<1e-9;el('line',{x1:X(v),x2:X(v),y1:Y(0.15),y2:Y(0.85),stroke:me?ok:line,'stroke-width':me?3:1.6},svg);
    if(i<7)el('text',{x:X(v),y:Y(i%2?0.02:0.92)+(i%2?0:0),'text-anchor':'middle',class:'lab'},svg,i<6?mult[i]:tr(TX.sept))});
  el('line',{x1:X(C.exact),x2:X(Math.min(16,C.s2)),y1:Y(0.5),y2:Y(0.5),stroke:wr,'stroke-width':4,opacity:0.6},svg);
  el('circle',{cx:X(Math.min(16,C.s2)),cy:Y(0.5),r:7,fill:ac},svg);
  const v=C.admix<0.03?0:C.admix<0.1?1:2,h=tr(TX.cT);
  $('ccards').innerHTML=card(h[0],fmt(C.exact,2))+card(h[1],fmt(C.excess,2))+card(h[2],C.admix<0?'—':fmt(100*C.admix,0)+' %')+card(h[3],C.excess<-1e-9?'⟨S²⟩ < S(S + 1)?':tr(TX.ok)[v]);
  $('cNote').textContent=tr(TX.cNote)}
async function gm(){try{R=await liveR({key:KEYS[Q.k]})}catch(e){return}drawR()}
function drawR(){if(!R)return;const svg=$('rchart');svg.innerHTML='';const ac=tok('--accent'),ok=tok('--ok'),nm=tr(TX.names);
  const [X,Y]=frame(svg,960,300,[64,14,22,40],[0,3],[1.8,2.4],[],ticks(1.8,2.4,0.1),'',tr(TX.rAx));
  KEYS.forEach((k,i)=>{const a=R.all[k],sel=i===Q.k,op=sel?0.85:0.35;const x0=X(i+0.15),xm=X(i+0.5),x1=X(i+0.85);
    el('rect',{x:x0,y:Y(a.mean_q),width:xm-x0-4,height:Y(1.8)-Y(a.mean_q),fill:ac,opacity:op},svg);
    el('rect',{x:xm+4,y:Y(a.mean_s),width:x1-xm-4,height:Y(1.8)-Y(a.mean_s),fill:ok,opacity:op},svg);
    el('text',{x:(x0+xm)/2,y:Y(a.mean_q)-6,'text-anchor':'middle',class:'lab'},svg,fmt(a.mean_q,3));
    el('text',{x:(xm+x1)/2,y:Y(a.mean_s)-6,'text-anchor':'middle',class:'lab'},svg,fmt(a.mean_s,3));
    el('text',{x:xm,y:300-22,'text-anchor':'middle'},svg,nm[k])});
  const i=Q.k,x0=X(i+0.15),xm=X(i+0.5);[R.quintet[0],R.quintet[2]].forEach(r=>el('line',{x1:x0,x2:xm-4,y1:Y(r),y2:Y(r),stroke:tok('--ink'),'stroke-width':1.6,'stroke-dasharray':'4 3'},svg));
  legend('rleg',tr(TX.rLeg),[ac,ok]);const h=tr(TX.rT),A=tr(TX.ang);
  $('rcards').innerHTML=card(h[0],fmt(R.quintet[0],3)+' / '+fmt(R.quintet[2],3)+A)+card(h[1],fmt(R.mean_s,3)+A)+card(h[2],fmt(R.dr,3)+A);
  $('rNote').textContent=tr(TX.rNote)}
gp();ct();gm();onTheme(()=>{drawG();drawC();drawR()});
