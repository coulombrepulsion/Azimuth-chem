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
/* The bond through orbitals (Atlas v2): localization as a rotation, hybridization from the angle, the NBO donor–acceptor
   energy E(2), the NCI reduced density gradient — quas_atlas.core.bonding (bond.rotate, bond.hybrid, bond.e2,
   bond.nci). */
const TX={
  xAx:{ru:'x, бор',en:'x, bohr',zh:'x，bohr'},
  oLeg:{ru:['φ₁′','φ₂′','плотность ρ (не меняется)'],en:['φ₁′','φ₂′','density ρ (unchanged)'],zh:['φ₁′','φ₂′','密度 ρ（不变）']},
  thAx:{ru:'угол поворота θ, °',en:'rotation angle θ, °',zh:'旋转角 θ，°'},spAx:{ru:'Σ протяжённость',en:'Σ spread',zh:'Σ 弥散度'},
  oT:{ru:['наибольшее изменение ρ','⟨φ₁′|F|φ₂′⟩, хартри','⟨φ₁′|F|φ₁′⟩ / ⟨φ₂′|F|φ₂′⟩','Σ(⟨x²⟩ − ⟨x⟩²) — критерий Бойса'],en:['largest change of ρ','⟨φ₁′|F|φ₂′⟩, hartree','⟨φ₁′|F|φ₁′⟩ / ⟨φ₂′|F|φ₂′⟩','Σ(⟨x²⟩ − ⟨x⟩²) — the Boys criterion'],zh:['ρ 的最大变化','⟨φ₁′|F|φ₂′⟩，hartree','⟨φ₁′|F|φ₁′⟩ / ⟨φ₂′|F|φ₂′⟩','Σ(⟨x²⟩ − ⟨x⟩²)——Boys 判据']},
  oNote:{ru:(t)=>'Поворот пары занятых орбиталей умножает определитель на cos²θ + sin²θ = 1: энергия и плотность не меняются (кривая ρ стоит на месте), меняется только вид орбиталей. При θ = 0 — канонические орбитали: размазаны по обеим связям, диагонализуют оператор Фока, у них есть энергии ε. '+(Math.abs(Math.abs(t)-45)<2?'При θ = ±45° каждая орбиталь сидит на своей связи, протяжённость минимальна — это локализованные орбитали Бойса.':'При θ = ±45° орбитали сядут каждая на свою связь — минимум протяжённости, локализованные орбитали Бойса.')+' Плата: локализованные орбитали — не собственные функции F (недиагональный элемент не ноль), орбитальных энергий у них нет.',
    en:(t)=>'A rotation of a pair of occupied orbitals multiplies the determinant by cos²θ + sin²θ = 1: the energy and the density do not change (the ρ curve stays put), only the look of the orbitals does. At θ = 0 — the canonical orbitals: spread over both bonds, diagonalizing the Fock operator, with energies ε. '+(Math.abs(Math.abs(t)-45)<2?'At θ = ±45° each orbital sits on its own bond, the spread is the smallest — these are the Boys localized orbitals.':'At θ = ±45° the orbitals will sit each on its own bond — the minimum of the spread, the Boys localized orbitals.')+' The price: localized orbitals are not eigenfunctions of F (the off-diagonal element is not zero), they have no orbital energies.',
    zh:(t)=>'旋转一对占据轨道使行列式乘以 cos²θ + sin²θ = 1：能量和密度不变（ρ 曲线不动），只有轨道的样子改变。θ = 0 时为正则轨道：分布在两根键上，使 Fock 算符对角化，有轨道能 ε。'+(Math.abs(Math.abs(t)-45)<2?'θ = ±45° 时每个轨道各在一根键上，弥散度最小——这就是 Boys 定域轨道。':'θ = ±45° 时轨道将各自位于一根键上——弥散度最小，即 Boys 定域轨道。')+'代价：定域轨道不是 F 的本征函数（非对角元不为零），没有轨道能。'},
  nb:{ru:['2 связи + 2 пары (H₂O)','3 связи + 1 пара (NH₃)'],en:['2 bonds + 2 pairs (H₂O)','3 bonds + 1 pair (NH₃)'],zh:['2 键 + 2 对（H₂O）','3 键 + 1 对（NH₃）']},
  aAx:{ru:'валентный угол θ, °',en:'bond angle θ, °',zh:'键角 θ，°'},hAx:{ru:'доля s, %',en:'s share, %',zh:'s 成分，%'},
  hLeg:{ru:['гибрид связи','неподелённая пара'],en:['bond hybrid','lone pair'],zh:['成键杂化轨道','孤对']},
  hT:{ru:['гибрид связи','s в связи','s в неподелённой паре','неподелённая пара'],en:['bond hybrid','s in a bond','s in a lone pair','lone pair'],zh:['成键杂化','键中 s','孤对中 s','孤对']},
  hNote:{ru:'Два одинаковых гибрида s + λp под углом θ ортогональны, если 1 + λ²cosθ = 0, то есть λ² = −1/cosθ. Тетраэдр — sp³, 120° — sp², 180° — sp. У воды (104,5°) гибриды связей — sp⁴, 20 % s; на две неподелённые пары остаётся 60 % s, по 30 % — sp²·³. Кислород в воде не sp³: связи и пары гибридизованы по-разному. Чем меньше угол, тем больше p в связях и s в парах; NBO находит такие дробные показатели из матрицы плотности (у связей O–H обычно sp³·³–sp⁴).',
    en:'Two equal hybrids s + λp at an angle θ are orthogonal if 1 + λ²cosθ = 0, that is λ² = −1/cosθ. A tetrahedron — sp³, 120° — sp², 180° — sp. In water (104.5°) the bond hybrids are sp⁴, 20 % s; 60 % s is left for the two lone pairs, 30 % each — sp²·³. Oxygen in water is not sp³: the bonds and the pairs are hybridized differently. The smaller the angle, the more p in the bonds and s in the pairs; NBO finds such fractional exponents from the density matrix (usually sp³·³–sp⁴ for O–H).',
    zh:'两个相同的杂化轨道 s + λp 夹角为 θ 时，若 1 + λ²cosθ = 0（即 λ² = −1/cosθ）则正交。四面体——sp³，120°——sp²，180°——sp。水（104.5°）中成键杂化为 sp⁴，s 占 20 %；两个孤对共剩 60 % s，各 30 %——sp²·³。水中的氧不是 sp³：键和孤对的杂化不同。角越小，键中 p 越多、孤对中 s 越多；NBO 从密度矩阵求出这样的分数指数（O–H 通常为 sp³·³–sp⁴）。'},
  fAx:{ru:'F_ij, хартри',en:'F_ij, hartree',zh:'F_ij，hartree'},eAx:{ru:'стабилизация, кДж/моль',en:'stabilization, kJ/mol',zh:'稳定化能，kJ/mol'},
  eLeg:{ru:['E(2) = n·F²/Δε','точно (задача 2 × 2)'],en:['E(2) = n·F²/Δε','exact (the 2 × 2 problem)'],zh:['E(2) = n·F²/Δε','精确（2 × 2 问题）']},
  eT:{ru:['E(2)','точно','расхождение'],en:['E(2)','exact','difference'],zh:['E(2)','精确','差别']},
  eNote:{ru:'Заполненная орбиталь i и пустая j* связаны недиагональным элементом оператора Фока; нижний уровень опускается на ≈ F²/(ε_j* − ε_i), умножаем на заселённость. Примеры: в заторможенном этане σ(C–H) → σ*(C–H) напротив (шесть пар — одно из объяснений барьера вращения); в димере воды n(O) → σ*(O–H) соседа — связь O–H удлиняется, частота падает. Пока F ≪ Δε, формула близка к точной. Красный флажок: E(2) не складываются в «энергию сопряжения» и зависят от выбранной опорной структуры Льюиса — это язык объяснения, а не разложение наблюдаемой энергии.',
    en:'A filled orbital i and an empty j* are coupled by an off-diagonal element of the Fock operator; the lower level goes down by ≈ F²/(ε_j* − ε_i), times the occupation. Examples: in staggered ethane σ(C–H) → σ*(C–H) opposite (six pairs — one explanation of the rotational barrier); in the water dimer n(O) → σ*(O–H) of the neighbour — the O–H bond lengthens, its frequency drops. As long as F ≪ Δε the formula is close to the exact one. A red flag: the E(2) do not add up to a «conjugation energy» and depend on the reference Lewis structure chosen — a language of explanation, not a decomposition of an observable energy.',
    zh:'占据轨道 i 与空轨道 j* 通过 Fock 算符的非对角元耦合；低能级下降约 F²/(ε_j* − ε_i)，再乘以占据数。例子：交叉式乙烷中 σ(C–H) → 对位 σ*(C–H)（六对——旋转势垒的一种解释）；水二聚体中 n(O) → 邻分子 σ*(O–H)——O–H 键变长、频率降低。只要 F ≪ Δε，公式接近精确值。警示：E(2) 不能相加成“共轭能”，并且依赖所选的参考 Lewis 结构——这是解释的语言，而不是可观测能量的分解。'},
  kinds:{ru:['один фрагмент','димер','кольцо из шести'],en:['one fragment','a dimer','a ring of six'],zh:['单个片段','二聚体','六元环']},
  nAx:{ru:'sign(λ₂)·ρ, а.е.',en:'sign(λ₂)·ρ, a.u.',zh:'sign(λ₂)·ρ，a.u.'},sAx:{ru:'s',en:'s',zh:'s'},
  nT:{ru:['ρ в точке контакта','ρ в центре кольца','шип'],en:['ρ at the contact','ρ at the ring centre','spike'],zh:['接触点 ρ','环中心 ρ','尖峰']},
  spike:{ru:['нет','притяжение (λ₂ < 0)','притяжение и отталкивание'],en:['none','attraction (λ₂ < 0)','attraction and repulsion'],zh:['无','吸引（λ₂ < 0）','吸引与排斥']},
  nNote:{ru:'s = |∇ρ|/(2(3π²)^⅓ρ^{4/3}) безразмерна (та же величина, что в градиентных функционалах). В хвосте одной молекулы ρ ~ e^{−ar}, и s растёт без предела — малых ρ с малым s нет. Между двумя молекулами хвосты перекрываются, в критической точке ∇ρ = 0 и s падает до нуля при малой ρ — шип. Знак второй кривизны отличает точку связи (λ₂ < 0, притяжение, шип слева) от точки цикла (λ₂ > 0, отталкивание, шип справа, как в центре кольца). Положение шипа — плотность в контакте, грубая мера прочности: левее −0,02 — водородная связь, у нуля — ван-дер-ваальсов контакт.',
    en:'s = |∇ρ|/(2(3π²)^⅓ρ^{4/3}) is dimensionless (the same quantity as in gradient functionals). In the tail of one molecule ρ ~ e^{−ar}, and s grows without bound — there are no small ρ with a small s. Between two molecules the tails overlap, at the critical point ∇ρ = 0 and s drops to zero at a small ρ — a spike. The sign of the second curvature tells a bond point (λ₂ < 0, attraction, a spike on the left) from a ring point (λ₂ > 0, repulsion, a spike on the right, as at the centre of a ring). The position of the spike is the density at the contact, a rough measure of the strength: left of −0.02 — a hydrogen bond, near zero — a van der Waals contact.',
    zh:'s = |∇ρ|/(2(3π²)^⅓ρ^{4/3}) 无量纲（与梯度泛函中的量相同）。在单个分子的尾部 ρ ~ e^{−ar}，s 无限增大——不存在 ρ 小而 s 也小的点。两个分子之间尾部重叠，在临界点 ∇ρ = 0，s 在小 ρ 处降到零——出现尖峰。第二曲率的符号区分键点（λ₂ < 0，吸引，尖峰在左）与环点（λ₂ > 0，排斥，尖峰在右，如环中心）。尖峰位置即接触处的密度，是强度的粗略量度：−0.02 以左——氢键，零附近——范德华接触。'},
  kj:{ru:' кДж/моль',en:' kJ/mol',zh:' kJ/mol'}
};
const Q={th:0,nb:0,an:104.5,F:0.05,g:0.6,n:2,k:1,d:4};let O=null,H=null,E=null,N=null;
const liveO=QC.live('bond.rotate'),liveH=QC.live('bond.hybrid'),liveE=QC.live('bond.e2'),liveN=QC.live('bond.nci');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show();return show};
slider('th',v=>{Q.th=v;ro()},0);const anShow=slider('an',v=>{Q.an=v;hy()},1);
chips($('nG'),tr(TX.nb),Q.nb,i=>{Q.nb=i;mark($('nG'),i);const s=$('an');s.max=i?120:180;Q.an=i?106.7:104.5;s.value=Q.an;anShow();hy()});
slider('ff',v=>{Q.F=v;e2()},3);slider('gp',v=>{Q.g=v;e2()},2);slider('nn',v=>{Q.n=v;e2()},2);
chips($('kG'),tr(TX.kinds),Q.k,i=>{Q.k=i;mark($('kG'),i);nc()});slider('dd',v=>{Q.d=v;nc()},1);
const legend=(id,names,colors,dash)=>{$(id).innerHTML=names.map((s,j)=>'<span><i class="sw" style="border-color:'+colors[j]+(dash&&dash[j]?';border-style:dashed':'')+'"></i>'+s+'</span>').join('')};
const ticks=(a,b,s)=>{const o=[];for(let v=Math.ceil(a/s-1e-9)*s;v<=b+1e-9;v+=s)o.push(+v.toFixed(6));return o};
function lines(svg,H,box,xr,yr,xs,ys,xl,yl,series){svg.innerHTML='';const [Xf,Yf]=frame(svg,960,H,box,xr,yr,ticks(xr[0],xr[1],xs),ticks(yr[0],yr[1],ys),xl,yl);
  series.forEach(([px,py,c,w,d])=>{let seg=[];const put=()=>{if(seg.length>1)el('polyline',{points:seg.join(' '),fill:'none',stroke:c,'stroke-width':w,'stroke-dasharray':d||''},svg);seg=[]};
    px.forEach((x,i)=>{const y=py[i];if(y!=null&&y>=yr[0]-1e-9&&y<=yr[1]+1e-9)seg.push(Xf(x)+','+Yf(y));else put()});put()});return [Xf,Yf]}
async function ro(){try{O=await liveO({theta:Q.th})}catch(e){return}drawO()}
function drawO(){if(!O)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok'),ink=tok('--ink');
  lines($('ochart'),280,[56,14,22,38],[-5,5],[-1.2,1.2],1,0.4,tr(TX.xAx),'',[[O.x,O.rho.map(v=>v/2),ok,2,'6 4'],[O.x,O.phi1,ac,2.6],[O.x,O.phi2,wr,2.6]]);
  legend('oleg',tr(TX.oLeg),[ac,wr,ok],[0,0,1]);
  const sp=$('pchart'),[X,Y]=lines(sp,200,[56,14,22,38],[-90,90],[0,6],30,1,tr(TX.thAx),tr(TX.spAx),[[O.spread.map(p=>p[0]),O.spread.map(p=>p[1]),ac,2.4]]);
  el('circle',{cx:X(Q.th),cy:Y(Math.min(6,O.at.spread)),r:6,fill:wr},sp);
  const h=tr(TX.oT),a=O.at;
  $('ocards').innerHTML=card(h[0],sci(a.drho,1))+card(h[1],fmt(a.f12,3))+card(h[2],fmt(a.e1,3)+' / '+fmt(a.e2,3))+card(h[3],fmt(a.spread,2));
  $('oNote').textContent=tr(TX.oNote)(Q.th)}
async function hy(){try{H=await liveH({angle:Q.an,nb:Q.nb?3:2})}catch(e){return}drawH()}
const spx=l=>{if(l==null)return '—';const t=Math.abs(l-Math.round(l))<0.05?String(Math.round(l)):l.toFixed(1);return 'sp'+t.split('').map(c=>c==='.'?'·':'⁰¹²³⁴⁵⁶⁷⁸⁹'[+c]).join('')};
function drawH(){if(!H)return;const ac=tok('--accent'),wr=tok('--warn'),ink=tok('--ink'),hi=H.nb===2?180:120,svg=$('hchart');
  const pc=a=>a.map(v=>v==null?null:100*v);
  const [X,Y]=lines(svg,300,[56,14,22,38],[90,hi],[0,60],H.nb===2?10:5,10,tr(TX.aAx),tr(TX.hAx),[[H.angle,pc(H.s_bond),ac,2.6],[H.angle,pc(H.s_lp),wr,2.6]]);
  H.marks.forEach(([n,t])=>{el('line',{x1:X(t),x2:X(t),y1:Y(0),y2:Y(60),stroke:tok('--line'),'stroke-width':1.4},svg);el('text',{x:X(t)+4,y:Y(56),class:'lab'},svg,n)});
  el('line',{x1:X(Q.an),x2:X(Q.an),y1:Y(0),y2:Y(60),stroke:ink,'stroke-dasharray':'3 4','stroke-width':1},svg);
  legend('hleg',tr(TX.hLeg),[ac,wr]);const h=tr(TX.hT),a=H.at;
  $('hcards').innerHTML=card(h[0],spx(a.lam2))+card(h[1],a.s_bond==null?'—':fmt(100*a.s_bond,1)+' %')+card(h[2],a.s_lp==null?'—':fmt(100*a.s_lp,1)+' %')+card(h[3],a.s_lp!=null&&a.s_lp>=0.999?'s':spx(a.lam2_lp));
  $('hNote').textContent=tr(TX.hNote)}
async function e2(){try{E=await liveE({F:Q.F,gap:Q.g,n:Q.n})}catch(e){return}drawE()}
function drawE(){if(!E)return;const ac=tok('--accent'),wr=tok('--warn'),ink=tok('--ink'),top=Math.max(20,Math.ceil(1.1*E.exact[E.exact.length-1]/20)*20),svg=$('echart');
  const [X,Y]=lines(svg,300,[60,14,22,38],[0,0.3],[0,top],0.05,top>200?50:top>80?20:5,tr(TX.fAx),tr(TX.eAx),[[E.F,E.pt,wr,2.2,'6 4'],[E.F,E.exact,ac,2.6]]);
  el('line',{x1:X(Q.F),x2:X(Q.F),y1:Y(0),y2:Y(top),stroke:ink,'stroke-dasharray':'3 4','stroke-width':1},svg);
  legend('eleg',tr(TX.eLeg),[wr,ac],[1,0]);const h=tr(TX.eT),a=E.at,kj=tr(TX.kj);
  $('ecards').innerHTML=card(h[0],fmt(a.pt,1)+kj)+card(h[1],fmt(a.exact,1)+kj)+card(h[2],a.exact>0?fmt(100*(a.pt-a.exact)/a.exact,1)+' %':'—');
  $('eNote').textContent=tr(TX.eNote)}
async function nc(){try{N=await liveN({kind:['one','dimer','ring'][Q.k],d:Q.d})}catch(e){return}drawN()}
function drawN(){if(!N)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok'),svg=$('nchart');svg.innerHTML='';
  const [X,Y]=frame(svg,960,320,[56,14,22,38],[-0.08,0.08],[0,2],ticks(-0.08,0.08,0.02),ticks(0,2,0.5),tr(TX.nAx),tr(TX.sAx));
  el('line',{x1:X(0),x2:X(0),y1:Y(0),y2:Y(2),stroke:tok('--ink'),'stroke-width':1},svg);
  const g=el('g',{},svg);N.pts.forEach(([r,s])=>el('circle',{cx:X(r).toFixed(1),cy:Y(s).toFixed(1),r:1.6,fill:s<0.5?(r<0?ac:wr):tok('--muted')||'#999',opacity:s<0.5?0.9:0.45},g));
  const h=tr(TX.nT),sp=N.kind==='one'?0:N.kind==='dimer'?1:2;
  $('ncards').innerHTML=card(h[0],N.mid==null?'—':'−'+fmt(N.mid,4))+card(h[1],N.ring==null?'—':'+'+fmt(N.ring,4))+card(h[2],tr(TX.spike)[sp]);
  $('nNote').textContent=tr(TX.nNote)}
ro();hy();e2();nc();onTheme(()=>{drawO();drawH();drawE();drawN()});
