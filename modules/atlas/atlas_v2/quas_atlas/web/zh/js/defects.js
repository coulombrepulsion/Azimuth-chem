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
/* Defects and surfaces (Atlas v2): the vacancy and its concentration, charged defects and their transition levels,
   the correction of a charged supercell, the surface energy of a slab — quas_atlas.core.defects (def.vacancy,
   def.charged, def.slab). */
const TX={
  U:{ru:{ev:' эВ',j:' Дж/м²',cm:' см⁻³',mev:' мэВ'},en:{ev:' eV',j:' J/m²',cm:' cm⁻³',mev:' meV'},zh:{ev:' eV',j:' J/m²',cm:' cm⁻³',mev:' meV'}},
  tAx:{ru:'T, K',en:'T, K',zh:'T，K'},cAx:{ru:'lg c',en:'log₁₀ c',zh:'lg c'},
  vT:{ru:['доля вакансий c','одна вакансия на','вакансий в 1 см³','ошибка E<sub>f</sub> на 0,3 эВ меняет c в'],en:['share of vacancies c','one vacancy per','vacancies per cm³','an error of 0.3 eV in E<sub>f</sub> changes c by'],zh:['空位份额 c','每多少个原子一个空位','每 cm³ 空位数','E<sub>f</sub> 误差 0.3 eV 使 c 变化']},
  atoms:{ru:' атомов',en:' atoms',zh:' 个原子'},times:{ru:' раз',en:'×',zh:' 倍'},
  vLeg:{ru:['E<sub>f</sub>','E<sub>f</sub> ± 0,3 эВ','текущая T'],en:['E<sub>f</sub>','E<sub>f</sub> ± 0.3 eV','this T'],zh:['E<sub>f</sub>','E<sub>f</sub> ± 0.3 eV','当前 T']},
  vNote:{ru:(x,t)=>'Вакансия стоит E<sub>f</sub>, но её можно поставить в любой узел: в равновесии c = e^(−E<sub>f</sub>/kT), здесь E<sub>f</sub>/kT = '+x+'. '+(t<700?'При такой температуре равновесных вакансий практически нет: всё, что есть в кристалле, — от выращивания и облучения.':'Чем ближе к плавлению (кремний — 1687 K), тем больше вакансий; от них зависит скорость диффузии.')+' Ошибка расчёта в десятые доли электронвольта меняет концентрацию на порядки — поэтому расчёт отвечает на вопрос «какой дефект преобладает», а не «сколько его».',
    en:(x,t)=>'A vacancy costs E<sub>f</sub> but can sit on any site: at equilibrium c = e^(−E<sub>f</sub>/kT); here E<sub>f</sub>/kT = '+x+'. '+(t<700?'At this temperature there are practically no equilibrium vacancies: whatever the crystal has comes from its growth and irradiation.':'The closer to melting (silicon: 1687 K), the more vacancies; the speed of diffusion depends on them.')+' An error of tenths of an electronvolt changes the concentration by orders of magnitude — this is why a calculation answers «which defect prevails», not «how many there are».',
    zh:(x,t)=>'空位需要 E<sub>f</sub> 的能量，但可以占据任何格点：平衡时 c = e^(−E<sub>f</sub>/kT)，此处 E<sub>f</sub>/kT = '+x+'。'+(t<700?'在这个温度下几乎没有平衡空位：晶体中的空位都来自生长和辐照。':'越接近熔点（硅为 1687 K），空位越多；扩散速度取决于它们。')+'计算误差为零点几 eV 就会使浓度变化几个数量级——因此计算回答的是“哪种缺陷占优”，而不是“有多少”。'},
  fAx:{ru:'уровень Ферми, эВ',en:'Fermi level, eV',zh:'费米能级，eV'},eAx:{ru:'энергия образования, эВ',en:'formation energy, eV',zh:'形成能，eV'},
  cLeg:{ru:['заряд +1','заряд 0','заряд −1','самый выгодный'],en:['charge +1','charge 0','charge −1','the lowest'],zh:['电荷 +1','电荷 0','电荷 −1','最低者']},
  cT:{ru:['ε(+/0)','ε(0/−)','на середине щели'],en:['ε(+/0)','ε(0/−)','in the middle of the gap'],zh:['ε(+/0)','ε(0/−)','带隙中央']},
  none:{ru:'нет в щели',en:'not in the gap',zh:'不在带隙中'},
  cNote:{ru:(s,neg)=>'Заряд дефекта при данном уровне Ферми — тот, чья прямая ниже: '+s+'. Уровень перехода — разность полных энергий двух зарядовых состояний, а не энергия орбитали. Его и измеряют спектроскопией глубоких уровней.'+(neg?' Нейтральное состояние здесь не бывает самым выгодным: дефект сразу переходит из + в − («отрицательное U»).':''),
    en:(s,neg)=>'The charge of the defect at a given Fermi level is the one whose line is lowest: '+s+'. A transition level is a difference of the total energies of two charge states, not an orbital energy. It is what deep-level spectroscopy measures.'+(neg?' The neutral state is never the lowest here: the defect goes from + straight to − («negative U»).':''),
    zh:(s,neg)=>'在给定费米能级下，缺陷的电荷取直线最低者：'+s+'。跃迁能级是两个电荷态总能量之差，而不是轨道能量。深能级谱测量的正是它。'+(neg?'这里中性态从来不是最低的：缺陷直接从 + 变为 −（“负 U”）。':'')},
  from:{ru:(a,b,q)=>'от '+a+' до '+b+' эВ — '+q,en:(a,b,q)=>q+' from '+a+' to '+b+' eV',zh:(a,b,q)=>a+'–'+b+' eV 为 '+q},
  sNote:{ru:(q,e)=>'Поправка к энергии заряженной сверхъячейки (первый член Макова–Пейна) q²α/(2εL), q = '+q+', ε = '+e+'. Убывает как 1/L, то есть медленно: даже 1728 атомов не делают её пренебрежимой. Без неё заряженные дефекты считать нельзя.',
    en:(q,e)=>'The correction of the energy of a charged supercell (the first Makov–Payne term) q²α/(2εL), q = '+q+', ε = '+e+'. It falls as 1/L, that is slowly: even 1728 atoms do not make it negligible. Charged defects cannot be computed without it.',
    zh:(q,e)=>'带电超胞能量的修正（Makov–Payne 第一项）q²α/(2εL)，q = '+q+'，ε = '+e+'。它按 1/L 下降，即很慢：即使 1728 个原子也不能忽略它。不加修正无法计算带电缺陷。'},
  faces:{ru:['(111)','(100)','(100), димеры'],en:['(111)','(100)','(100), dimers'],zh:['(111)','(100)','(100)，二聚体']},
  faceKeys:['111','100','100r'],
  nAx:{ru:'число слоёв N',en:'number of layers N',zh:'层数 N'},gAx:{ru:'γ, Дж/м²',en:'γ, J/m²',zh:'γ，J/m²'},
  sLeg:{ru:['γ с энергией объёма «со стороны»','γ из прямой E<sub>слэб</sub>(N)','истинная γ'],en:['γ with the bulk energy «from elsewhere»','γ from the line E<sub>slab</sub>(N)','the true γ'],zh:['用“外部”体相能量的 γ','由直线 E<sub>slab</sub>(N) 得到的 γ','真实 γ']},
  gT:{ru:['γ (модель)','из прямой, N = 16','со стороны, N = 16','ошибка Nδ/(2A), N = 16'],en:['γ (model)','from the line, N = 16','from elsewhere, N = 16','error Nδ/(2A), N = 16'],zh:['γ（模型）','直线，N = 16','外部，N = 16','误差 Nδ/(2A)，N = 16']},
  gNote:{ru:(b,r)=>(r?'После оптимизации поверхностные атомы (100) сходятся попарно — димеры: каждая пара замыкает по одной оборванной связи друг на друга, период вдоль поверхности удваивается, и γ падает с 2,36 до 1,44 Дж/м². Чтобы найти это, нужна ячейка больше 1 × 1 и нарушенная симметрия.':'На поверхности оборвано '+b+(b>1?' связи':' связь')+' на атом, каждая — половина энергии связи ε на поверхность: γ ≈ n·(ε/2)/A. Грань (111) почти вдвое дешевле (100) — поэтому кремний раскалывается по (111).')+' Если брать энергию объёма из отдельного расчёта с ошибкой δ, ошибка γ растёт с толщиной как Nδ/(2A) — сходимости нет. Наклон прямой E<sub>слэб</sub>(N) даёт энергию объёма, согласованную со слэбами.',
    en:(b,r)=>(r?'After the optimization the atoms of the (100) surface pair up — dimers: each pair closes one broken bond of each atom on the other, the period along the surface doubles, and γ drops from 2.36 to 1.44 J/m². Finding this takes a cell larger than 1 × 1 and a broken symmetry.':b+' broken bond'+(b>1?'s':'')+' per surface atom, each giving half the bond energy ε to the surface: γ ≈ n·(ε/2)/A. The (111) face is almost half as costly as (100) — this is why silicon cleaves along (111).')+' With the bulk energy taken from a separate calculation with an error δ, the error of γ grows with the thickness as Nδ/(2A) — there is no convergence. The slope of the line E<sub>slab</sub>(N) gives a bulk energy consistent with the slabs.',
    zh:(b,r)=>(r?'优化后 (100) 表面原子两两靠拢——形成二聚体：每对原子把各自的一个悬挂键闭合在一起，沿表面的周期加倍，γ 由 2.36 降至 1.44 J/m²。要找到它，需要大于 1 × 1 的晶胞并破坏对称性。':'表面每个原子断开 '+b+' 个键，每个键给每个表面一半键能 ε：γ ≈ n·(ε/2)/A。(111) 面的代价几乎只有 (100) 的一半——所以硅沿 (111) 解理。')+'如果体相能量取自误差为 δ 的单独计算，γ 的误差随厚度按 Nδ/(2A) 增长——不收敛。直线 E<sub>slab</sub>(N) 的斜率给出与表面板一致的体相能量。'}
};
const Q={ef:3.6,T:1687,ep:2.9,e0:3.4,em:4.3,gap:1.17,q:1,eps:11.7,face:0,delta:10,noise:1};let V=null,C=null,S=null;
const liveV=QC.live('def.vacancy'),liveC=QC.live('def.charged'),liveS=QC.live('def.slab');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show()};
slider('ef',v=>{Q.ef=v;vac()},2);slider('tt',v=>{Q.T=v;vac()},0);
slider('ep',v=>{Q.ep=v;chg()},2);slider('e0',v=>{Q.e0=v;chg()},2);slider('em',v=>{Q.em=v;chg()},2);slider('gp',v=>{Q.gap=v;chg()},2);slider('ee',v=>{Q.eps=v;chg()},1);
chips($('qG'),['1','2','3'],Q.q-1,i=>{Q.q=i+1;mark($('qG'),i);chg()});
slider('dd',v=>{Q.delta=v;slb()},1);slider('nz',v=>{Q.noise=v;slb()},1);
chips($('fG'),tr(TX.faces),Q.face,i=>{Q.face=i;mark($('fG'),i);slb()});
const ticks=(lo,hi,n)=>{const r=(hi-lo)/n,p=Math.pow(10,Math.floor(Math.log10(r))),s=[1,2,2.5,5,10].map(k=>k*p).find(k=>k>=r);const t=[];for(let v=Math.ceil(lo/s)*s;v<=hi+1e-9;v+=s)t.push(+v.toFixed(6));return t};
const legend=(id,names,colors)=>{$(id).innerHTML=names.map((s,j)=>'<span><i class="sw" style="border-color:'+colors[j]+'"></i>'+s+'</span>').join('')};
async function vac(){try{V=await liveV({ef:Q.ef,T:Q.T})}catch(e){return}drawVac()}
function drawVac(){if(!V)return;const ac=tok('--accent'),mu=tok('--muted'),svg=$('vchart');svg.innerHTML='';const cv=V.curve,lo=Math.max(-40,Math.floor(Math.min(...cv.hi))),hi=Math.min(0,Math.ceil(Math.max(...cv.lo))+1);
  const [X,Y]=frame(svg,960,300,[56,14,22,38],[300,2000],[lo,hi],ticks(300,2000,8),ticks(lo,hi,5),tr(TX.tAx),tr(TX.cAx));
  const cl=v=>Math.max(lo,Math.min(hi,v));
  el('polygon',{points:cv.T.map((t,i)=>X(t)+','+Y(cl(cv.lo[i]))).concat(cv.T.slice().reverse().map((t,i)=>X(t)+','+Y(cl(cv.hi[cv.T.length-1-i])))).join(' '),fill:mu,opacity:.18},svg);
  el('polyline',{points:cv.T.map((t,i)=>X(t)+','+Y(cl(cv.log10c[i]))).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg);
  if(V.log10c>=lo){el('line',{x1:X(Q.T),x2:X(Q.T),y1:Y(lo),y2:Y(hi),stroke:tok('--ink'),'stroke-width':1},svg);el('circle',{cx:X(Q.T),cy:Y(V.log10c),r:5,fill:ac},svg)}
  const h=tr(TX.vT),U=tr(TX.U);
  $('vcards').innerHTML=card(h[0],V.log10c<-300?'—':sci(V.c,1))+card(h[1],(V.log10c<-300?'—':sci(V.one_in,1))+tr(TX.atoms))+card(h[2],sci(V.per_cm3,1)+U.cm)+card(h[3],fmt(V.factor,1)+tr(TX.times));
  legend('vleg',tr(TX.vLeg),[ac,mu,tok('--ink')]);
  $('vNote').innerHTML=tr(TX.vNote)(fmt(V.x,1),Q.T)}
async function chg(){try{C=await liveC({ep:Q.ep,e0:Q.e0,em:Q.em,gap:Q.gap,q:Q.q,eps:Q.eps})}catch(e){return}drawChg()}
function drawChg(){if(!C)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok'),mu=tok('--muted'),svg=$('cchart');svg.innerHTML='';
  const all=[].concat(C.lines['+'],C.lines['0'],C.lines['−']),lo=Math.floor(Math.min(...all)),hi=Math.ceil(Math.max(...all));
  const [X,Y]=frame(svg,960,300,[56,14,22,38],[0,C.ef[C.ef.length-1]],[lo,hi],ticks(0,C.ef[C.ef.length-1],6),ticks(lo,hi,5),tr(TX.fAx),tr(TX.eAx));
  [['+',wr],['0',mu],['−',ok]].forEach(([k,c])=>el('polyline',{points:C.ef.map((x,i)=>X(x)+','+Y(C.lines[k][i])).join(' '),fill:'none',stroke:c,'stroke-width':1.4,'stroke-dasharray':'6 4'},svg));
  el('polyline',{points:C.ef.map((x,i)=>X(x)+','+Y(C.lowest[i])).join(' '),fill:'none',stroke:ac,'stroke-width':3},svg);
  C.levels.forEach(l=>{el('line',{x1:X(l.at),x2:X(l.at),y1:Y(lo),y2:Y(hi),stroke:tok('--ink'),'stroke-dasharray':'3 4','stroke-width':1},svg);el('text',{x:X(l.at)+4,y:Y(hi)+14,class:'lab'},svg,l.label)});
  legend('cleg',tr(TX.cLeg),[wr,mu,ok,ac]);
  const h=tr(TX.cT),U=tr(TX.U),g=C.ef[C.ef.length-1],inGap=x=>x>0&&x<g?fmt(x,2)+U.ev:tr(TX.none),mid=C.stable.find(s=>s.from<=g/2&&g/2<=s.to);
  $('ccards').innerHTML=card(h[0],inGap(C.pairs['+/0']))+card(h[1],inGap(C.pairs['0/−']))+card(h[2],mid?mid.q:'—');
  const neg=C.pairs['+/0']>C.pairs['0/−']&&C.pairs['0/−']>0&&C.pairs['+/0']<g;
  $('cNote').innerHTML=tr(TX.cNote)(C.stable.map(s=>tr(TX.from)(fmt(s.from,2),fmt(s.to,2),s.q)).join('; '),neg);
  $('scards').innerHTML=C.supercell.map(r=>card(r.atoms+tr(TX.atoms)+' (L = '+fmt(r.L,1)+' Å)',fmt(r.dE,2)+U.ev)).join('');
  $('sNote').textContent=tr(TX.sNote)(Q.q,fmt(Q.eps,1))}
async function slb(){try{S=await liveS({face:TX.faceKeys[Q.face],delta:Q.delta,noise:Q.noise})}catch(e){return}drawSlb()}
function drawSlb(){if(!S)return;const ac=tok('--accent'),wr=tok('--warn'),mu=tok('--muted'),svg=$('schart');svg.innerHTML='';
  const vals=S.ext.concat(S.fit.filter(v=>v!=null),[S.gamma]),lo=Math.min(...vals),hi=Math.max(...vals),pad=Math.max(0.05,(hi-lo)*0.15);
  const [X,Y]=frame(svg,960,300,[56,14,22,38],[2,S.N[S.N.length-1]],[lo-pad,hi+pad],S.N.filter(n=>n%2===0),ticks(lo-pad,hi+pad,5),tr(TX.nAx),tr(TX.gAx));
  el('line',{x1:X(2),x2:X(S.N[S.N.length-1]),y1:Y(S.gamma),y2:Y(S.gamma),stroke:mu,'stroke-dasharray':'6 4','stroke-width':1.4},svg);
  el('polyline',{points:S.N.map((n,i)=>X(n)+','+Y(S.ext[i])).join(' '),fill:'none',stroke:wr,'stroke-width':2.4},svg);
  S.N.forEach((n,i)=>el('circle',{cx:X(n),cy:Y(S.ext[i]),r:3.5,fill:wr},svg));
  const fp=S.N.map((n,i)=>[n,S.fit[i]]).filter(p=>p[1]!=null);
  el('polyline',{points:fp.map(p=>X(p[0])+','+Y(p[1])).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg);
  fp.forEach(p=>el('circle',{cx:X(p[0]),cy:Y(p[1]),r:3.5,fill:ac},svg));
  legend('sleg',tr(TX.sLeg),[wr,ac,mu]);
  const h=tr(TX.gT),U=tr(TX.U),last=S.N.length-1;
  $('gcards').innerHTML=card(h[0],fmt(S.gamma,2)+U.j)+card(h[1],fmt(S.fit[last],2)+U.j)+card(h[2],fmt(S.ext[last],2)+U.j)+card(h[3],fmt(S.err_formula[last],3)+U.j);
  $('gNote').innerHTML=tr(TX.gNote)(S.bonds,Q.face===2)}
vac();chg();slb();onTheme(()=>{drawVac();drawChg();drawSlb()});
