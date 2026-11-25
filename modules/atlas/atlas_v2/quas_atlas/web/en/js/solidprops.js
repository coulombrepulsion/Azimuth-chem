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
/* The properties of crystals (Atlas v2): the equation of state E(V) by Birch–Murnaghan and the bulk modulus, the
   phonons of a chain of two atoms (the acoustic and the optical branch, the gap), the heat capacity by Debye and by
   Einstein — quas_atlas.core.solids (sol.eos, sol.phonons, sol.cv). */
const TX={
  U:{ru:{gpa:' ГПа',mev:' мэВ',cm:' см⁻¹'},en:{gpa:' GPa',mev:' meV',cm:' cm⁻¹'},zh:{gpa:' GPa',mev:' meV',cm:' cm⁻¹'}},
  mats:{ru:['Al','Cu','Si','NaCl','MgO'],en:['Al','Cu','Si','NaCl','MgO'],zh:['Al','Cu','Si','NaCl','MgO']},
  keys:['al','cu','si','nacl','mgo'],
  per:{ru:{atom:'на атом',NaCl:'на NaCl',MgO:'на MgO'},en:{atom:'per atom',NaCl:'per NaCl',MgO:'per MgO'},zh:{atom:'每个原子',NaCl:'每个 NaCl',MgO:'每个 MgO'}},
  vAx:{ru:'V, Å³',en:'V, Å³',zh:'V，Å³'},eAx:{ru:'ΔE, мэВ',en:'ΔE, meV',zh:'ΔE，meV'},
  eT:{ru:['V₀ подгонка (справочное)','B₀ подгонка (справочное)','B₀′ подгонка (справочное)','ΔE на краю диапазона'],en:['V₀ fit (reference)','B₀ fit (reference)','B₀′ fit (reference)','ΔE at the edge of the range'],zh:['V₀ 拟合（参考值）','B₀ 拟合（参考值）','B₀′ 拟合（参考值）','范围边缘的 ΔE']},
  eLeg:{ru:['«расчёты» с шумом','подгонка Бёрча–Мурнагана','справочная кривая'],en:['«calculations» with noise','the Birch–Murnaghan fit','the reference curve'],zh:['带噪声的“计算”','Birch–Murnaghan 拟合','参考曲线']},
  eNote:{ru:(b,p,d)=>b<5&&p<10?'Подгонка восстанавливает и модуль сжатия, и его производную: точки стоят достаточно широко, а энергия на краю ('+d+' мэВ) намного больше шума. Так обрабатывают серию расчётов при разных постоянных решётки (в Quantum ESPRESSO — программа ev.x).':b<10?'Модуль сжатия B₀ найден хорошо, а производная B₀′ — плохо: она определяется тонкой асимметрией кривой, и шум её сбивает. Возьмите шире диапазон или больше точек.':'Подгонка не годится: на краю диапазона энергия меняется всего на '+d+' мэВ, и шум того же порядка. Узкий диапазон объёмов вместе с неплотной сходимостью (мало k-точек, малое E<sub>cut</sub>) — частая причина «странного» модуля сжатия.',
    en:(b,p,d)=>b<5&&p<10?'The fit recovers both the bulk modulus and its derivative: the points are spread widely enough, and the energy at the edge ('+d+' meV) is much larger than the noise. This is how a series of calculations at different lattice constants is treated (in Quantum ESPRESSO, the program ev.x).':b<10?'The bulk modulus B₀ is found well, but its derivative B₀′ badly: it rests on a fine asymmetry of the curve, and the noise throws it off. Take a wider range or more points.':'The fit is no good: at the edge of the range the energy changes by only '+d+' meV, and the noise is of the same order. A narrow range of volumes together with loose convergence (few k-points, a small E<sub>cut</sub>) is a common cause of a «strange» bulk modulus.',
    zh:(b,p,d)=>b<5&&p<10?'拟合同时还原了体模量及其导数：各点分布足够宽，范围边缘的能量（'+d+' meV）远大于噪声。不同晶格常数下的一系列计算就是这样处理的（Quantum ESPRESSO 中为 ev.x 程序）。':b<10?'体模量 B₀ 求得很好，但其导数 B₀′ 很差：它取决于曲线细微的不对称性，噪声会使其偏离。请扩大范围或增加点数。':'拟合不可用：在范围边缘能量只变化 '+d+' meV，与噪声同一量级。体积范围过窄再加上收敛不够（k 点少、E<sub>cut</sub> 小），是体模量“异常”的常见原因。'},
  eBad:{ru:'Точки не дают минимума: шум больше изменения энергии в диапазоне. Расширьте диапазон или уменьшите шум.',en:'The points give no minimum: the noise is larger than the change of energy over the range. Widen the range or lower the noise.',zh:'这些点给不出极小值：噪声大于范围内的能量变化。请扩大范围或减小噪声。'},
  kAx:{ru:'k, π/a',en:'k, π/a',zh:'k，π/a'},wAx:{ru:'ω, см⁻¹',en:'ω, cm⁻¹',zh:'ω，cm⁻¹'},
  pLeg:{ru:['акустическая ветвь','оптическая ветвь','щель'],en:['acoustic branch','optical branch','gap'],zh:['声学支','光学支','带隙']},
  pT:{ru:['верх акустической ветви','низ оптической ветви','оптическая в Γ','щель'],en:['top of the acoustic branch','bottom of the optical branch','optical at Γ','gap'],zh:['声学支顶部','光学支底部','Γ 点光学支','带隙']},
  pNote:{ru:(g,h)=>g<0.5?'Массы равны — щели нет: две ветви сходятся на границе зоны. По сути это одноатомная цепочка, записанная с удвоенной ячейкой: оптическая ветвь — это та же акустическая, сложенная пополам.':'Чем больше разница масс, тем шире щель. На границе зоны в акустической ветви колеблются только тяжёлые атомы ('+h+'), в оптической — только лёгкие. В точке Γ акустическая частота равна нулю — это сдвиг кристалла как целого; оптическая — атомы двух сортов движутся навстречу друг другу. В ионных кристаллах эта мода поглощает инфракрасный свет.',
    en:(g,h)=>g<0.5?'The masses are equal — there is no gap: the two branches meet at the zone boundary. In fact this is a chain of one atom written with a doubled cell: the optical branch is the same acoustic one folded in half.':'The larger the difference of the masses, the wider the gap. At the zone boundary only the heavy atoms move in the acoustic branch ('+h+'), only the light ones in the optical branch. At Γ the acoustic frequency is zero — the crystal shifts as a whole; in the optical mode the two kinds of atoms move against each other. In ionic crystals this mode absorbs infrared light.',
    zh:(g,h)=>g<0.5?'质量相等——没有带隙：两支在布里渊区边界相接。这实际上是用加倍晶胞写出的单原子链：光学支就是对折后的声学支。':'质量差越大，带隙越宽。在区边界，声学支中只有重原子振动（'+h+'），光学支中只有轻原子振动。在 Γ 点声学频率为零——整个晶体平移；光学模中两类原子相向运动。在离子晶体中该模吸收红外光。'},
  heavy:{ru:m=>'масса '+m+' а.е.м.',en:m=>'mass '+m+' amu',zh:m=>'质量 '+m+' amu'},
  cMats:{ru:['Pb','NaCl','Cu','Al','Si','алмаз'],en:['Pb','NaCl','Cu','Al','Si','diamond'],zh:['Pb','NaCl','Cu','Al','Si','金刚石']},
  cKeys:['pb','nacl','cu','al','si','diamond'],
  tAx:{ru:'T, K',en:'T, K',zh:'T，K'},
  cLeg:{ru:['Дебай','Эйнштейн','закон T³','Дюлонг и Пти'],en:['Debye','Einstein','the T³ law','Dulong–Petit'],zh:['德拜','爱因斯坦','T³ 定律','杜隆–珀蒂']},
  cT:{ru:['θ<sub>D</sub>','C<sub>v</sub>/3R по Дебаю','C<sub>v</sub>/3R по Эйнштейну','закон T³'],en:['θ<sub>D</sub>','C<sub>v</sub>/3R by Debye','C<sub>v</sub>/3R by Einstein','the T³ law'],zh:['θ<sub>D</sub>','德拜 C<sub>v</sub>/3R','爱因斯坦 C<sub>v</sub>/3R','T³ 定律']},
  cNote:{ru:r=>(r<0.1?'Низкие температуры (T < θ<sub>D</sub>/10): теплоёмкость растёт как T³ — возбуждаются только длинные акустические волны. У модели Эйнштейна (одна частота) теплоёмкость падает экспоненциально, и это расходится с опытом.':r<0.6?'Промежуточная область: часть колебаний уже возбуждена, часть ещё «заморожена». Здесь результат сильнее всего зависит от формы спектра фононов — поэтому для точной термохимии кристаллов считают фононы.':'Высокие температуры (T ≳ θ<sub>D</sub>): возбуждены все колебания, C<sub>v</sub> → 3R на моль атомов — закон Дюлонга и Пти. Обе модели здесь сходятся.')+' Из спектра фононов, рассчитанного в ph.x и matdyn.x, программы получают теплоёмкость, энтропию и нулевые колебания кристалла.',
    en:r=>(r<0.1?'Low temperatures (T < θ<sub>D</sub>/10): the heat capacity grows as T³ — only the long acoustic waves are excited. In the Einstein model (one frequency) the heat capacity falls exponentially, and this disagrees with the experiment.':r<0.6?'The middle range: some vibrations are excited, others still «frozen». Here the result depends most on the shape of the phonon spectrum — this is why phonons are computed for accurate thermochemistry of crystals.':'High temperatures (T ≳ θ<sub>D</sub>): all vibrations are excited, C<sub>v</sub> → 3R per mole of atoms — the Dulong–Petit law. Both models agree here.')+' From the phonon spectrum computed by ph.x and matdyn.x the programs obtain the heat capacity, the entropy and the zero-point vibrations of the crystal.',
    zh:r=>(r<0.1?'低温（T < θ<sub>D</sub>/10）：热容按 T³ 增长——只有长波声学波被激发。爱因斯坦模型（单一频率）的热容按指数下降，与实验不符。':r<0.6?'中间区域：部分振动已被激发，部分仍“冻结”。这里结果最依赖于声子谱的形状——因此精确的晶体热化学需要计算声子。':'高温（T ≳ θ<sub>D</sub>）：所有振动都被激发，C<sub>v</sub> → 每摩尔原子 3R——杜隆–珀蒂定律。两种模型在此一致。')+' 由 ph.x 和 matdyn.x 计算的声子谱，程序可得到晶体的热容、熵和零点振动。'}
};
const Q={kind:2,span:6,n:7,noise:0,m1:24.3,m2:16,C:60,ck:2,T:300};let E=null,P=null,C=null,eErr=false;
const liveE=QC.live('sol.eos'),liveP=QC.live('sol.phonons'),liveC=QC.live('sol.cv');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show()};
slider('sp',v=>{Q.span=v;eos()},1);slider('np',v=>{Q.n=v;eos()},0);slider('nz',v=>{Q.noise=v;eos()},1);
slider('m1',v=>{Q.m1=v;ph()},1);slider('m2',v=>{Q.m2=v;ph()},1);slider('cc',v=>{Q.C=v;ph()},0);slider('tt',v=>{Q.T=v;cv()},0);
chips($('eG'),tr(TX.mats),Q.kind,i=>{Q.kind=i;mark($('eG'),i);eos()});
chips($('cG'),tr(TX.cMats),Q.ck,i=>{Q.ck=i;mark($('cG'),i);cv()});
const EVA3=160.21766208;
function bm(V,V0,B0,Bp,E0){const b=B0/EVA3,x=Math.pow(V0/V,2/3);return (E0||0)+9*V0*b/16*(Math.pow(x-1,3)*Bp+Math.pow(x-1,2)*(6-4*x))}
const ticks=(lo,hi,n)=>{const r=(hi-lo)/n,p=Math.pow(10,Math.floor(Math.log10(r))),s=[1,2,2.5,5,10].map(k=>k*p).find(k=>k>=r);const t=[];for(let v=Math.ceil(lo/s)*s;v<=hi+1e-9;v+=s)t.push(+v.toFixed(6));return t};
async function eos(){try{E=await liveE({kind:TX.keys[Q.kind],span:Q.span,n:Math.round(Q.n),noise:Q.noise});eErr=false}catch(e){if(e===QC.STALE||!e||!e.status)return;eErr=true}drawEos()}
function drawEos(){const svg=$('echart');svg.innerHTML='';if(eErr){$('ecards').innerHTML='';$('eNote').textContent=tr(TX.eBad);return}if(!E)return;
  const ac=tok('--accent'),wr=tok('--warn'),mu=tok('--muted'),t=E.true,f=E.fit;
  const vs=E.curve.V,emin=Math.min(...E.E);const pts=E.V.map((v,i)=>[v,(E.E[i]-emin)*1000]);
  const ref=vs.map(v=>[v,(bm(v,t.V0,t.B0,t.Bp,0)-emin)*1000]);const top=Math.max(...pts.map(p=>p[1]),...ref.map(p=>p[1]))*1.08||1,bot=Math.min(0,...pts.map(p=>p[1]))-top*0.06;
  const [X,Y]=frame(svg,960,300,[56,14,22,38],[vs[0],vs[vs.length-1]],[bot,top],ticks(vs[0],vs[vs.length-1],8),ticks(bot,top,5),tr(TX.vAx),tr(TX.eAx)+', '+tr(TX.per)[E.per]);
  const inY=p=>p[1]>=bot&&p[1]<=top;
  el('polyline',{points:ref.filter(inY).map(p=>X(p[0])+','+Y(p[1])).join(' '),fill:'none',stroke:mu,'stroke-width':1.4,'stroke-dasharray':'6 4'},svg);
  el('polyline',{points:E.curve.V.map((v,i)=>[v,(E.curve.E[i]-emin)*1000]).filter(inY).map(p=>X(p[0])+','+Y(p[1])).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg);
  pts.forEach(p=>el('circle',{cx:X(p[0]),cy:Y(p[1]),r:5,fill:wr,stroke:tok('--bg'),'stroke-width':1.5},svg));
  const dE=Math.max(...E.V.map(v=>bm(v,t.V0,t.B0,t.Bp,0)))*1000,h=tr(TX.eT),U=tr(TX.U);
  $('ecards').innerHTML=card(h[0],fmt(f.V0,2)+' Å³','('+fmt(t.V0,2)+')')+card(h[1],sci(f.B0,1)+U.gpa,'('+fmt(t.B0,1)+')')+card(h[2],sci(f.Bp,1),'('+fmt(t.Bp,1)+')')+card(h[3],sci(dE,1)+U.mev);
  $('eleg').innerHTML=tr(TX.eLeg).map((s,j)=>'<span><i class="sw" style="border-color:'+[wr,ac,mu][j]+'"></i>'+s+'</span>').join('');
  const rb=100*Math.abs(f.B0-t.B0)/t.B0,rp=100*Math.abs(f.Bp-t.Bp)/t.Bp;$('eNote').innerHTML=tr(TX.eNote)(rb,rp,fmt(dE,1))}
async function ph(){try{P=await liveP({m1:Q.m1,m2:Q.m2,C:Q.C})}catch(e){return}drawPh()}
function drawPh(){if(!P)return;const ac=tok('--accent'),wr=tok('--warn'),svg=$('pchart');svg.innerHTML='';const top=P.optical_top*1.1;
  const [X,Y]=frame(svg,960,300,[56,14,22,38],[-1,1],[0,top],[-1,-0.5,0,0.5,1],ticks(0,top,5),tr(TX.kAx),tr(TX.wAx));
  if(P.gap>0.5)el('rect',{x:X(-1),y:Y(P.optical_bottom),width:X(1)-X(-1),height:Y(P.acoustic_top)-Y(P.optical_bottom),fill:tok('--muted'),opacity:.15},svg);
  [[P.acoustic,ac],[P.optical,wr]].forEach(([b,c])=>el('polyline',{points:P.k.map((q,i)=>X(q)+','+Y(b[i])).join(' '),fill:'none',stroke:c,'stroke-width':2.4},svg));
  const h=tr(TX.pT),u=tr(TX.U).cm;$('pcards').innerHTML=card(h[0],fmt(P.acoustic_top,0)+u)+card(h[1],fmt(P.optical_bottom,0)+u)+card(h[2],fmt(P.optical_top,0)+u)+card(h[3],fmt(P.gap,0)+u);
  $('pleg').innerHTML=tr(TX.pLeg).map((s,j)=>'<span><i class="sw" style="border-color:'+[ac,wr,tok('--muted')][j]+'"></i>'+s+'</span>').join('');
  $('phNote').textContent=tr(TX.pNote)(P.gap,tr(TX.heavy)(fmt(Math.max(Q.m1,Q.m2),1)))}
async function cv(){try{C=await liveC({kind:TX.cKeys[Q.ck],T:Q.T})}catch(e){return}drawCv()}
function drawCv(){if(!C)return;const ac=tok('--accent'),wr=tok('--warn'),mu=tok('--muted'),ok=tok('--ok'),svg=$('cchart');svg.innerHTML='';const tm=C.T[C.T.length-1];
  const [X,Y]=frame(svg,960,300,[56,14,22,38],[0,tm],[0,1.1],ticks(0,tm,8),[0,0.2,0.4,0.6,0.8,1],tr(TX.tAx),'Cv/3R');
  el('line',{x1:X(0),x2:X(tm),y1:Y(1),y2:Y(1),stroke:ok,'stroke-dasharray':'6 4','stroke-width':1.4},svg);
  const t3=C.T.map(t=>[t,4*Math.pow(Math.PI,4)/5*Math.pow(t/C.theta,3)]).filter(p=>p[1]<=1.1);
  el('polyline',{points:[[0,0]].concat(t3).map(p=>X(p[0])+','+Y(p[1])).join(' '),fill:'none',stroke:mu,'stroke-width':1.4,'stroke-dasharray':'2 4'},svg);
  [[C.debye,ac],[C.einstein,wr]].forEach(([b,c])=>el('polyline',{points:[X(0)+','+Y(0)].concat(C.T.map((t,i)=>X(t)+','+Y(b[i]))).join(' '),fill:'none',stroke:c,'stroke-width':2.4},svg));
  el('line',{x1:X(C.at.T),x2:X(C.at.T),y1:Y(0),y2:Y(1.1),stroke:tok('--ink'),'stroke-width':1},svg);
  el('circle',{cx:X(C.at.T),cy:Y(C.at.debye),r:5,fill:ac},svg);el('circle',{cx:X(C.at.T),cy:Y(C.at.einstein),r:5,fill:wr},svg);
  const h=tr(TX.cT);$('ccards').innerHTML=card(h[0],fmt(C.theta,0)+' K')+card(h[1],fmt(C.at.debye,3))+card(h[2],fmt(C.at.einstein,3))+card(h[3],C.at.t3>1.5?'—':fmt(C.at.t3,3));
  $('cleg').innerHTML=tr(TX.cLeg).map((s,j)=>'<span><i class="sw" style="border-color:'+[ac,wr,mu,ok][j]+'"></i>'+s+'</span>').join('');
  $('cNote').innerHTML=tr(TX.cNote)(C.at.T/C.theta)}
eos();ph();cv();onTheme(()=>{drawEos();drawPh();drawCv()});
