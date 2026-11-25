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
/* The error of a calculation (Atlas v2): errors added in squares, from the mean absolute error to an interval, the
   cancellation of errors (isodesmic reactions, a related reference), conformer shares with their uncertainty —
   quas_atlas.core.errors (err.sum, err.interval, err.isodesmic, err.conformers). */
const TX={
  kj:{ru:' кДж/моль',en:' kJ/mol',zh:' kJ/mol'},
  sNames:{ru:['метод','базис','сходимость','итог (в квадратах)','простая сумма'],en:['method','basis','convergence','total (in squares)','plain sum'],zh:['方法','基组','收敛','总计（平方和）','简单相加']},
  sAx:{ru:'σ, кДж/моль',en:'σ, kJ/mol',zh:'σ，kJ/mol'},
  sT:{ru:['итог √(Σσ²)','без сходимости','доля дисперсии от метода'],en:['total √(Σσ²)','without the convergence','share of the variance from the method'],zh:['总计 √(Σσ²)','不计收敛','方法所占方差比例']},
  sNote:{ru:'Независимые погрешности складываются в квадратах, как дисперсии. Итог определяет самая большая: улучшить сходимость с 1 до 0,01 кДж/моль — итог меняется с 8,6 на 8,5. Зато небрежная сходимость (10 кДж/моль, например грубая k-сетка) делает ошибку почти вдвое больше ошибки метода. Правило: численная погрешность должна быть в несколько раз меньше ошибки метода. Систематические ошибки одного знака складываются сильнее — ближе к простой сумме.',
    en:'Independent errors add in squares, like variances. The largest one decides the total: improving the convergence from 1 to 0.01 kJ/mol moves the total from 8.6 to 8.5. But a careless convergence (10 kJ/mol, e.g. a coarse k-grid) makes the error almost twice the error of the method. The rule: the numerical error should be several times smaller than the error of the method. Systematic errors of one sign add more strongly — closer to the plain sum.',
    zh:'独立误差按平方相加，如同方差。总误差由最大的一项决定：把收敛从 1 改进到 0.01 kJ/mol，总计只从 8.6 变为 8.5。但收敛马虎（10 kJ/mol，例如 k 网格太粗）会使误差几乎是方法误差的两倍。规则：数值误差应比方法误差小数倍。同号的系统误差相加得更多——接近简单相加。'},
  eAx:{ru:'ошибка расчёта, кДж/моль',en:'error of the calculation, kJ/mol',zh:'计算误差，kJ/mol'},
  iLeg:{ru:['распределение ошибок','±MAE','±2σ (95 %)'],en:['distribution of the errors','±MAE','±2σ (95 %)'],zh:['误差分布','±MAE','±2σ（95 %）']},
  iT:{ru:['σ = 1,25·MAE','95 % ошибок в пределах','константа скорости — с точностью до множителя','ошибок больше MAE'],en:['σ = 1.25·MAE','95 % of the errors within','the rate constant — to a factor of','errors larger than MAE'],zh:['σ = 1.25·MAE','95 % 的误差在','速率常数的不确定因子','大于 MAE 的误差']},
  iNote:{ru:'В обзорах пишут среднюю абсолютную ошибку (MAE) на тестовом наборе — для своего типа величины (барьеры, энергии реакций, нековалентные взаимодействия). Но ваша реакция одна, и её ошибка может быть заметно больше средней: при нормальном распределении больше MAE ошибается 42 % реакций, а 5 % — больше 2σ = 2,5·MAE. Это и надо писать: «барьер 85 ± 20 кДж/моль», а не «85». Константа скорости — экспонента от барьера, поэтому расчёт обычно говорит, какой путь быстрее, а не какова скорость. Реальные распределения имеют тяжёлые хвосты — оценка скорее снизу.',
    en:'Reviews give the mean absolute error (MAE) on a test set — take it for your type of quantity (barriers, reaction energies, noncovalent interactions). But your reaction is one, and its error may be well above the mean: with a normal distribution 42 % of the reactions err by more than MAE, and 5 % by more than 2σ = 2.5·MAE. This is what to write: «a barrier of 85 ± 20 kJ/mol», not «85». A rate constant is an exponential of the barrier, so a calculation usually tells which path is faster, not how fast it is. Real distributions have heavy tails — the estimate is rather a lower bound.',
    zh:'综述给出测试集上的平均绝对误差（MAE）——要取与你的量同类的（势垒、反应能、非共价相互作用）。但你的反应只有一个，其误差可能明显大于平均值：正态分布下 42 % 的反应误差大于 MAE，5 % 大于 2σ = 2.5·MAE。应当写成“势垒 85 ± 20 kJ/mol”，而不是“85”。速率常数是势垒的指数函数，所以计算通常只能说明哪条路径更快，而不是速率多大。真实分布有重尾——这一估计偏低。'},
  bNames:{ru:{CH:'C–H',CC:'C–C',CO:'C–O',OH:'O–H'},en:{CH:'C–H',CC:'C–C',CO:'C–O',OH:'O–H'},zh:{CH:'C–H',CC:'C–C',CO:'C–O',OH:'O–H'}},
  paths:{ru:['атомизация C₂H₅OH','реагенты C₂H₅OH + CH₄','продукты CH₃OH + C₂H₆'],en:['atomization of C₂H₅OH','reactants C₂H₅OH + CH₄','products CH₃OH + C₂H₆'],zh:['C₂H₅OH 原子化','反应物 C₂H₅OH + CH₄','产物 CH₃OH + C₂H₆']},
  dAx:{ru:'накопленная ошибка, кДж/моль',en:'accumulated error, kJ/mol',zh:'累积误差，kJ/mol'},
  rAx:{ru:'корреляция ошибок ρ',en:'correlation of the errors ρ',zh:'误差相关系数 ρ'},cAx:{ru:'σ после поправки',en:'σ after the correction',zh:'校正后的 σ'},
  dT:{ru:['через атомизацию','через изодесмическую реакцию','ΔfH(C₂H₅OH), расчёт / опыт','σ после поправки по родственной системе'],en:['through atomization','through the isodesmic reaction','ΔfH(C₂H₅OH), calculation / experiment','σ after a correction by a related system'],zh:['经原子化','经等键反应','ΔfH(C₂H₅OH)，计算 / 实验','经相关体系校正后的 σ']},
  dNote:{ru:'Метод ошибается в основном систематически: у каждой связи своя ошибка. Через энергию атомизации ошибки всех связей копятся; в изодесмической реакции C₂H₅OH + CH₄ → CH₃OH + C₂H₆ связей каждого типа слева и справа поровну, и ошибки сокращаются. Энтальпия образования этанола: ΔfH(CH₃OH) + ΔfH(C₂H₆) − ΔfH(CH₄) − ΔrH = −201,0 − 83,8 + 74,9 − 23,0 = −232,9 кДж/моль при опыте −234 ± 2. Поправка по родственной системе работает так же: σ² = 2σ²(1 − ρ) — похожая реакция (ρ близко к 1) уменьшает ошибку, непохожая (ρ = 0) увеличивает в √2 раз.',
    en:'A method errs mostly systematically: each bond has its own error. Through the atomization energy the errors of all the bonds pile up; in the isodesmic reaction C₂H₅OH + CH₄ → CH₃OH + C₂H₆ there are as many bonds of each type on the left as on the right, and the errors cancel. The enthalpy of formation of ethanol: ΔfH(CH₃OH) + ΔfH(C₂H₆) − ΔfH(CH₄) − ΔrH = −201.0 − 83.8 + 74.9 − 23.0 = −232.9 kJ/mol against the experiment −234 ± 2. A correction by a related system works the same way: σ² = 2σ²(1 − ρ) — a similar reaction (ρ near 1) reduces the error, a dissimilar one (ρ = 0) increases it by √2.',
    zh:'方法的误差主要是系统性的：每种键有自己的误差。经原子化能时所有键的误差累积；在等键反应 C₂H₅OH + CH₄ → CH₃OH + C₂H₆ 中，左右两边每种键的数目相同，误差相互抵消。乙醇的生成焓：ΔfH(CH₃OH) + ΔfH(C₂H₆) − ΔfH(CH₄) − ΔrH = −201.0 − 83.8 + 74.9 − 23.0 = −232.9 kJ/mol，实验为 −234 ± 2。用相关体系校正同理：σ² = 2σ²(1 − ρ)——相似的反应（ρ 接近 1）减小误差，不相似的（ρ = 0）使误差增大 √2 倍。'},
  gAx:{ru:'ΔG = G₂ − G₁, кДж/моль',en:'ΔG = G₂ − G₁, kJ/mol',zh:'ΔG = G₂ − G₁，kJ/mol'},xAx:{ru:'доля конформера 2, %',en:'share of conformer 2, %',zh:'构象 2 的比例，%'},
  cT:{ru:['доля конформера 2','при ΔG ± σ','вывод'],en:['share of conformer 2','at ΔG ± σ','conclusion'],zh:['构象 2 的比例','ΔG ± σ 时','结论']},
  verdict:{ru:['основной — конформер 1','основной — конформер 2','близки, оба присутствуют'],en:['conformer 1 dominates','conformer 2 dominates','close, both present'],zh:['以构象 1 为主','以构象 2 为主','接近，两者都存在']},
  cNote:{ru:'Последнее звено цепочки от энергии к наблюдаемой — экспонента: x₂/x₁ = e^{−ΔG/RT}. Расчёт дал ΔG = 2 кДж/моль — «70 на 30». Но при ошибке метода 4 кДж/моль доля второго конформера — от 8 до 69 %: расчёт не говорит, какой основной. Честный вывод — «близки по энергии, оба присутствуют». Сузить интервал помогает более точный метод для одной разности энергий (DLPNO-CCSD(T)//DFT, σ ≈ 1): 23–40 %.',
    en:'The last link of the chain from the energy to the observable is an exponential: x₂/x₁ = e^{−ΔG/RT}. The calculation gave ΔG = 2 kJ/mol — «70 to 30». But with a method error of 4 kJ/mol the share of the second conformer is from 8 to 69 %: the calculation does not tell which one dominates. The honest conclusion is «close in energy, both present». A more accurate method for one energy difference (DLPNO-CCSD(T)//DFT, σ ≈ 1) narrows the interval: 23–40 %.',
    zh:'从能量到可观测量的链条最后一环是指数：x₂/x₁ = e^{−ΔG/RT}。计算给出 ΔG = 2 kJ/mol——“七比三”。但方法误差为 4 kJ/mol 时，第二个构象的比例在 8 % 到 69 % 之间：计算无法说明哪个为主。诚实的结论是“能量接近，两者都存在”。对单个能量差用更精确的方法（DLPNO-CCSD(T)//DFT，σ ≈ 1）可缩小区间：23–40 %。'}
};
const Q={sm:8,sb:3,sc:1,mae:8,T:298,ch:2,cc:5,co:6,oh:3,sg:8,rh:0.8,dg:2,ss:4,t4:298};let S=null,I=null,D=null,C=null;
const liveS=QC.live('err.sum'),liveI=QC.live('err.interval'),liveD=QC.live('err.isodesmic'),liveC=QC.live('err.conformers');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show()};
slider('sm',v=>{Q.sm=v;su()},1);slider('sb',v=>{Q.sb=v;su()},1);slider('sc',v=>{Q.sc=v;su()},1);
slider('mae',v=>{Q.mae=v;iv()},1);slider('tt',v=>{Q.T=v;iv()},0);
slider('ch',v=>{Q.ch=v;iso()},1);slider('cc',v=>{Q.cc=v;iso()},1);slider('co',v=>{Q.co=v;iso()},1);slider('oh',v=>{Q.oh=v;iso()},1);slider('sg',v=>{Q.sg=v;iso()},1);slider('rh',v=>{Q.rh=v;iso()},2);
slider('dg',v=>{Q.dg=v;cf()},1);slider('ss',v=>{Q.ss=v;cf()},1);slider('t4',v=>{Q.t4=v;cf()},0);
const legend=(id,names,colors,dash)=>{$(id).innerHTML=names.map((s,j)=>'<span><i class="sw" style="border-color:'+colors[j]+(dash&&dash[j]?';border-style:dashed':'')+'"></i>'+s+'</span>').join('')};
const ticks=(a,b,s)=>{const o=[];for(let v=Math.ceil(a/s-1e-9)*s;v<=b+1e-9;v+=s)o.push(+v.toFixed(6));return o};
const nice=v=>v<=10?2:v<=25?5:v<=60?10:20;
async function su(){try{S=await liveS({sm:Q.sm,sb:Q.sb,sc:Q.sc})}catch(e){return}drawS()}
function drawS(){if(!S)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok'),mu=tok('--muted')||'#999',svg=$('schart');svg.innerHTML='';
  const v=[Q.sm,Q.sb,Q.sc,S.total,S.linear],cs=[ac,ac,ac,ok,mu],top=Math.max(10,Math.ceil(1.15*Math.max(...v)/5)*5),nm=tr(TX.sNames);
  const [X,Y]=frame(svg,960,280,[56,14,22,40],[0,5],[0,top],[],ticks(0,top,nice(top)),'',tr(TX.sAx));
  v.forEach((h,i)=>{const x0=X(i+0.2),x1=X(i+0.8);el('rect',{x:x0,y:Y(h),width:x1-x0,height:Y(0)-Y(h),fill:cs[i],opacity:i<3?0.6:0.85},svg);
    el('text',{x:(x0+x1)/2,y:Y(h)-6,'text-anchor':'middle',class:'lab'},svg,fmt(h,1));el('text',{x:(x0+x1)/2,y:280-22,'text-anchor':'middle'},svg,nm[i])});
  const h=tr(TX.sT),kj=tr(TX.kj);
  $('scards').innerHTML=card(h[0],fmt(S.total,1)+kj)+card(h[1],fmt(S.without_conv,1)+kj)+card(h[2],fmt(100*S.share[0],0)+' %');
  $('sNote').textContent=tr(TX.sNote)}
async function iv(){try{I=await liveI({mae:Q.mae,T:Q.T})}catch(e){return}drawI()}
function drawI(){if(!I)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok'),svg=$('ichart');svg.innerHTML='';
  const L=I.x[I.x.length-1],top=Math.max(...I.pdf)*1.1;const st=nice(L);
  const [X,Y]=frame(svg,960,260,[40,14,22,38],[-L,L],[0,top],ticks(-L,L,st),[],tr(TX.eAx),'');
  const s2=I.half95;const band=I.x.map((x,i)=>[x,I.pdf[i]]).filter(([x])=>Math.abs(x)<=s2);
  el('polygon',{points:[[band[0][0],0]].concat(band).concat([[band[band.length-1][0],0]]).map(([x,y])=>X(x)+','+Y(y)).join(' '),fill:ok,opacity:0.18},svg);
  el('polyline',{points:I.x.map((x,i)=>X(x)+','+Y(I.pdf[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.6},svg);
  [-1,1].forEach(k=>{el('line',{x1:X(k*I.mae),x2:X(k*I.mae),y1:Y(0),y2:Y(top),stroke:wr,'stroke-dasharray':'5 4','stroke-width':1.6},svg);
    el('line',{x1:X(k*s2),x2:X(k*s2),y1:Y(0),y2:Y(top),stroke:ok,'stroke-width':1.8},svg)});
  legend('ileg',tr(TX.iLeg),[ac,wr,ok],[0,1,0]);const h=tr(TX.iT),kj=tr(TX.kj);
  $('icards').innerHTML=card(h[0],fmt(I.sigma,1)+kj)+card(h[1],'±'+fmt(I.half95,0)+kj)+card(h[2],sci(I.factor,1))+card(h[3],fmt(100*I.frac_beyond_mae,0)+' %');
  $('iNote').textContent=tr(TX.iNote)}
async function iso(){try{D=await liveD({dch:Q.ch,dcc:Q.cc,dco:Q.co,doh:Q.oh,sigma:Q.sg,rho:Q.rh})}catch(e){return}drawD()}
function drawD(){if(!D)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok'),mu=tok('--muted')||'#999',svg=$('dchart');svg.innerHTML='';
  const B=['CH','CC','CO','OH'],cs=[ac,wr,ok,mu],dv={CH:Q.ch,CC:Q.cc,CO:Q.co,OH:Q.oh},bn=tr(TX.bNames);
  const stacks=[B.map(b=>D.by_bond[b]),B.map(b=>D.left[b]*dv[b]),B.map(b=>D.right[b]*dv[b])];
  const top=Math.max(10,Math.ceil(1.12*Math.max(...stacks.map(s=>s.reduce((a,b)=>a+b,0)))/10)*10),nm=tr(TX.paths);
  const [X,Y]=frame(svg,960,280,[56,14,22,40],[0,3],[0,top],[],ticks(0,top,nice(top)),'',tr(TX.dAx));
  stacks.forEach((st,i)=>{let y=0;const x0=X(i+0.2),x1=X(i+0.8);st.forEach((v,j)=>{if(v>0)el('rect',{x:x0,y:Y(y+v),width:x1-x0,height:Y(y)-Y(y+v),fill:cs[j],opacity:0.75,stroke:tok('--bg')||'#fff','stroke-width':1},svg);y+=v});
    el('text',{x:(x0+x1)/2,y:Y(y)-6,'text-anchor':'middle',class:'lab'},svg,fmt(y,1));el('text',{x:(x0+x1)/2,y:280-22,'text-anchor':'middle'},svg,nm[i])});
  legend('dleg',B.map(b=>bn[b]),cs);
  const sv=$('rchart');sv.innerHTML='';const ct=Math.max(10,Math.ceil(1.1*Math.sqrt(4*Q.sg*Q.sg)/5)*5);
  const [Xr,Yr]=frame(sv,960,220,[56,14,22,38],[-1,1],[0,ct],ticks(-1,1,0.25),ticks(0,ct,nice(ct)),tr(TX.rAx),tr(TX.cAx));
  el('line',{x1:Xr(-1),x2:Xr(1),y1:Yr(Q.sg),y2:Yr(Q.sg),stroke:wr,'stroke-dasharray':'6 4','stroke-width':1.6},sv);
  el('polyline',{points:D.corr_curve.map(([r,s])=>Xr(r)+','+Yr(s)).join(' '),fill:'none',stroke:ac,'stroke-width':2.6},sv);
  el('circle',{cx:Xr(Q.rh),cy:Yr(D.corr),r:6,fill:ac},sv);
  const h=tr(TX.dT),kj=tr(TX.kj);
  $('dcards').innerHTML=card(h[0],fmt(D.atomization,1)+kj)+card(h[1],fmt(D.isodesmic,1)+kj)+card(h[2],fmt(D.dfh,1)+' / '+fmt(D.exp,0)+' ± 2'+kj)+card(h[3],fmt(D.corr,1)+kj);
  $('dNote').textContent=tr(TX.dNote)}
async function cf(){try{C=await liveC({dG:Q.dg,s:Q.ss,T:Q.t4})}catch(e){return}drawC()}
function drawC(){if(!C)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok'),svg=$('cchart');svg.innerHTML='';
  const [X,Y]=frame(svg,960,280,[56,14,22,38],[-20,20],[0,100],ticks(-20,20,5),ticks(0,100,20),tr(TX.gAx),tr(TX.xAx));
  const a=Math.max(-20,Q.dg-Q.ss),b=Math.min(20,Q.dg+Q.ss);el('rect',{x:X(a),y:Y(100),width:X(b)-X(a),height:Y(0)-Y(100),fill:ok,opacity:0.14},svg);
  el('rect',{x:X(-20),y:Y(100*C.hi),width:X(20)-X(-20),height:Math.max(1,Y(100*C.lo)-Y(100*C.hi)),fill:wr,opacity:0.12},svg);
  el('polyline',{points:C.curve.map(([g,x])=>X(g)+','+Y(100*x)).join(' '),fill:'none',stroke:ac,'stroke-width':2.6},svg);
  el('circle',{cx:X(Q.dg),cy:Y(100*C.x2),r:6,fill:ac},svg);
  const h=tr(TX.cT),v=C.hi<0.5?0:C.lo>0.5?1:2;
  $('ccards').innerHTML=card(h[0],fmt(100*C.x2,0)+' %')+card(h[1],fmt(100*C.lo,0)+'–'+fmt(100*C.hi,0)+' %')+card(h[2],tr(TX.verdict)[v]);
  $('cNote').textContent=tr(TX.cNote)}
su();iv();iso();cf();onTheme(()=>{drawS();drawI();drawD();drawC()});
