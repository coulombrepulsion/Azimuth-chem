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
/* Molecular dynamics and learned potentials (Atlas v2): the velocity Verlet integrator and the time step, a committee
   of learned models and where to trust it, the fluctuations of the temperature and the rare events a trajectory sees —
   quas_atlas.core.mlpot (ml.verlet, ml.committee, ml.events). */
const TX={
  U:{ru:{fs:' фс',mev:' мэВ',ps:' пс',h:' ч',d:' сут',s:' с⁻¹',K:' K'},en:{fs:' fs',mev:' meV',ps:' ps',h:' h',d:' days',s:' s⁻¹',K:' K'},zh:{fs:' fs',mev:' meV',ps:' ps',h:' 小时',d:' 天',s:' s⁻¹',K:' K'}},
  sys:{ru:['O–H','O–D','Si (оптический фонон)'],en:['O–H','O–D','Si (optical phonon)'],zh:['O–H','O–D','Si（光学声子）']},sysKeys:['oh','od','si'],
  ints:{ru:['Верле','Эйлер'],en:['Verlet','Euler'],zh:['Verlet','Euler']},intKeys:['verlet','euler'],
  tAx:{ru:'t, фс',en:'t, fs',zh:'t，fs'},eAx:{ru:'ΔE, мэВ',en:'ΔE, meV',zh:'ΔE，meV'},
  vT:{ru:['период колебания τ','Δt / τ','наибольшее |ΔE|','ΔE в конце'],en:['period of the vibration τ','Δt / τ','largest |ΔE|','ΔE at the end'],zh:['振动周期 τ','Δt / τ','最大 |ΔE|','结束时 ΔE']},
  blown:{ru:'разлетелось',en:'blew up',zh:'发散'},
  vNote:{ru:(m,r,b)=>(b?'Интегрирование разлетелось: шаг больше примерно четверти периода, и схема неустойчива. ':m==='euler'?'Метод Эйлера не сохраняет энергию: ошибка каждого шага одного знака, и энергия растёт без конца. Так за тысячу шагов кристалл «нагреется» на сотни кельвинов. ':'Скоростной Верле обратим во времени: ошибка энергии не копится, а колеблется около нуля и растёт как Δt². ')+'Сейчас Δt = '+r+' периода. Правило — десятая–двадцатая часть периода самого быстрого колебания: для связи O–H (9 фс) — 0,5 фс, для фононов кремния (64 фс) — 1–3 фс. Замена водорода дейтерием удлиняет период в √2 раз.',
    en:(m,r,b)=>(b?'The integration blew up: the step is more than about a quarter of the period, and the scheme is unstable. ':m==='euler'?'The Euler method does not keep the energy: the error of every step has the same sign, and the energy grows without end. In a thousand steps a crystal «heats up» by hundreds of kelvins. ':'Velocity Verlet is reversible in time: the error of the energy does not pile up but oscillates around zero and grows as Δt². ')+'Now Δt is '+r+' of the period. The rule is a tenth to a twentieth of the period of the fastest vibration: for an O–H bond (9 fs) 0.5 fs, for the phonons of silicon (64 fs) 1–3 fs. Replacing hydrogen by deuterium makes the period √2 longer.',
    zh:(m,r,b)=>(b?'积分发散：步长超过周期的约四分之一，格式不稳定。':m==='euler'?'Euler 方法不守恒能量：每一步误差同号，能量无限增长。一千步后晶体会“升温”数百开尔文。':'速度 Verlet 时间可逆：能量误差不累积，而是在零附近振荡，随 Δt² 增大。')+'现在 Δt 为周期的 '+r+'。规则是最快振动周期的十分之一到二十分之一：O–H 键（9 fs）取 0.5 fs，硅的声子（64 fs）取 1–3 fs。用氘代替氢使周期增大 √2 倍。'},
  rAx:{ru:'r, Å',en:'r, Å',zh:'r，Å'},EAx:{ru:'E, эВ',en:'E, eV',zh:'E，eV'},
  cLeg:{ru:['«DFT» (истинная кривая)','среднее комитета','± 3σ комитета','обучающие точки','σ > 3σ<sub>обуч</sub>: считать DFT'],en:['«DFT» (the true curve)','mean of the committee','± 3σ of the committee','training points','σ > 3σ<sub>train</sub>: compute with DFT'],zh:['“DFT”（真实曲线）','委员会平均','委员会 ± 3σ','训练点','σ > 3σ<sub>train</sub>：用 DFT 计算']},
  cT:{ru:['ошибка в области обучения','разброс там же','ошибка при r = 1,85 Å','разброс там же'],en:['error inside the training range','spread there','error at r = 1.85 Å','spread there'],zh:['训练范围内误差','该处离散','r = 1.85 Å 处误差','该处离散']},
  cNote:{ru:(k)=>'Пять моделей обучены на разных случайных 70 % одних и тех же точек. Там, где данные есть, они согласны и почти не ошибаются. Сожмите связь за пределы выборки — каждая модель экстраполирует по-своему: ошибка в '+k+' раз больше, и разброс комитета растёт вместе с ней. Модель сама не скажет, что выдумывает силы; разброс скажет. Где он втрое больше обычного, структуру отправляют на расчёт DFT и доучивают модель — это активное обучение.',
    en:(k)=>'Five models are trained on different random 70 % of the same points. Where there are data they agree and hardly err. Compress the bond beyond the training set — each model extrapolates in its own way: the error is '+k+' times larger, and the spread of the committee grows with it. A model will not tell that it invents forces; the spread will. Where it is three times the usual, the structure goes to a DFT calculation and the model is retrained — active learning.',
    zh:(k)=>'五个模型在同一组点的不同随机 70 % 上训练。在有数据的地方它们一致，几乎没有误差。把键压缩到训练范围之外——每个模型以自己的方式外推：误差大 '+k+' 倍，委员会离散随之增大。模型自己不会说它在编造力，而离散会。离散超过平常三倍的结构送去 DFT 计算并重新训练模型——这就是主动学习。'},
  bAx:{ru:'барьер ΔG, эВ',en:'barrier ΔG, eV',zh:'势垒 ΔG，eV'},wAx:{ru:'lg (время ожидания, пс)',en:'log₁₀ (waiting time, ps)',zh:'lg（等待时间，ps）'},
  eLeg:{ru:['среднее время до события','длина траектории'],en:['mean time to an event','length of the trajectory'],zh:['事件平均等待时间','轨迹长度']},
  eT:{ru:['флуктуация T','частота событий k','среднее ожидание','событий за траекторию','с потенциалом МО','с DFT'],en:['fluctuation of T','rate of events k','mean waiting time','events in the trajectory','with a learned potential','with DFT'],zh:['T 的涨落','事件速率 k','平均等待','轨迹中的事件数','机器学习势','DFT']},
  eNote:{ru:(r,n)=>'Мгновенная температура — сумма 3N квадратов скоростей, её разброс ±'+r+' %: в малой ячейке это свойство системы, а не ошибка термостата. '+(n>=10?'Событие с таким барьером траектория увидит много раз — можно считать частоту прямо.':n>=1?'Событие попадёт в траекторию раз-другой: для частоты мало.':'Событие в траекторию не попадёт: за наносекунду при комнатной температуре проходят барьеры не выше 0,2–0,25 эВ (20–25 кДж/моль), а у реакции с барьером 80 кДж/моль (0,83 эВ) — одно событие за 10 секунд. Для более высоких нужны методы редких событий — NEB, метадинамика.')+' Шаг 1 фс; потенциал МО — 30 мс на шаг, DFT — 3 минуты на шаг для 64 атомов.',
    en:(r,n)=>'The instantaneous temperature is a sum of 3N squares of velocities, its spread is ±'+r+' %: in a small cell this is a property of the system, not an error of the thermostat. '+(n>=10?'The trajectory will see an event with this barrier many times — the rate can be counted directly.':n>=1?'The event comes into the trajectory once or twice: too few for a rate.':'The event will not come into the trajectory: in a nanosecond at room temperature only barriers up to 0.2–0.25 eV (20–25 kJ/mol) are crossed, and a reaction with a barrier of 80 kJ/mol (0.83 eV) happens once in 10 seconds. Higher ones need methods of rare events — NEB, metadynamics.')+' A step of 1 fs; a learned potential takes 30 ms a step, DFT 3 minutes a step for 64 atoms.',
    zh:(r,n)=>'瞬时温度是 3N 个速度平方之和，其离散为 ±'+r+' %：在小晶胞中这是体系本身的性质，而不是恒温器的误差。'+(n>=10?'轨迹会多次看到这一势垒的事件——可以直接计算速率。':n>=1?'事件在轨迹中只出现一两次：不足以求速率。':'事件不会出现在轨迹中：室温下一纳秒内只能越过不高于 0.2–0.25 eV（20–25 kJ/mol）的势垒，而势垒为 80 kJ/mol（0.83 eV）的反应每 10 秒才发生一次。更高的势垒需要稀有事件方法——NEB、元动力学。')+'步长 1 fs；机器学习势每步 30 ms，DFT 对 64 个原子每步 3 分钟。'}
};
const Q={sys:0,int:0,dt:0.5,E0:0.3,n:16,hi:2.9,lgN:1.806,T:300,bar:0.8,lgL:2};let V=null,C=null,E=null;
const liveV=QC.live('ml.verlet'),liveC=QC.live('ml.committee'),liveE=QC.live('ml.events');
const slider=(id,f,d,show2)=>{const s=$(id);const show=()=>{$(id+'v').textContent=show2?show2(+s.value):fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show()};
chips($('sysG'),tr(TX.sys),Q.sys,i=>{Q.sys=i;mark($('sysG'),i);ver()});chips($('intG'),tr(TX.ints),Q.int,i=>{Q.int=i;mark($('intG'),i);ver()});
slider('dt',v=>{Q.dt=v;ver()},2);slider('e0',v=>{Q.E0=v;ver()},2);
slider('nn',v=>{Q.n=v;com()},0);slider('hi',v=>{Q.hi=v;com()},2);
const big=v=>{const x=Math.pow(10,v);return x>=100?String(Math.round(x)).replace(/\B(?=(\d{3})+(?!\d))/g,' '):fmt(x,x<10?1:0)};
slider('na',v=>{Q.lgN=v;evt()},0,big);slider('tk',v=>{Q.T=v;evt()},0);slider('bb',v=>{Q.bar=v;evt()},2);slider('ll',v=>{Q.lgL=v;evt()},0,v=>big(v)+tr(TX.U).ps);
const ticks=(lo,hi,n)=>{const r=(hi-lo)/n,p=Math.pow(10,Math.floor(Math.log10(r))),s=[1,2,2.5,5,10].map(k=>k*p).find(k=>k>=r);const t=[];for(let v=Math.ceil(lo/s)*s;v<=hi+1e-9;v+=s)t.push(+v.toFixed(6));return t};
const legend=(id,names,colors)=>{$(id).innerHTML=names.map((s,j)=>'<span><i class="sw" style="border-color:'+colors[j]+'"></i>'+s+'</span>').join('')};
async function ver(){try{V=await liveV({system:TX.sysKeys[Q.sys],method:TX.intKeys[Q.int],dt:Q.dt,E0:Q.E0})}catch(e){return}drawVer()}
function drawVer(){if(!V)return;const ac=tok('--accent'),svg=$('vchart');svg.innerHTML='';const ok=V.dE.filter(x=>isFinite(x)),m=Math.max(1e-3,...ok.map(Math.abs))*1.1;
  const [X,Y]=frame(svg,960,300,[64,14,22,38],[0,200],[-m,m],ticks(0,200,8),ticks(-m,m,4),tr(TX.tAx),tr(TX.eAx));
  el('line',{x1:X(0),x2:X(200),y1:Y(0),y2:Y(0),stroke:tok('--muted'),'stroke-width':1},svg);
  el('polyline',{points:V.t.map((t,i)=>[t,V.dE[i]]).filter(p=>isFinite(p[1])).map(p=>X(p[0])+','+Y(p[1])).join(' '),fill:'none',stroke:Q.int?tok('--warn'):ac,'stroke-width':2},svg);
  const h=tr(TX.vT),U=tr(TX.U);
  $('vcards').innerHTML=card(h[0],fmt(V.period,1)+U.fs)+card(h[1],fmt(V.ratio,3))+card(h[2],V.blown?tr(TX.blown):sci(V.max,2)+U.mev)+card(h[3],V.blown?tr(TX.blown):sci(V.drift,2)+U.mev);
  $('vNote').innerHTML=tr(TX.vNote)(TX.intKeys[Q.int],fmt(V.ratio,3),V.blown)}
async function com(){try{C=await liveC({n:Math.round(Q.n),hi:Q.hi})}catch(e){return}drawCom()}
function drawCom(){if(!C)return;const ac=tok('--accent'),mu=tok('--muted'),wr=tok('--warn'),svg=$('cchart');svg.innerHTML='';const lo=-2.6,hi=1.6,cl=v=>Math.max(lo,Math.min(hi,v));
  const [X,Y]=frame(svg,960,300,[56,14,22,38],[C.r[0],C.r[C.r.length-1]],[lo,hi],ticks(C.r[0],C.r[C.r.length-1],7),ticks(lo,hi,4),tr(TX.rAx),tr(TX.EAx));
  let start=null;C.r.forEach((r,i)=>{if(C.flag[i]&&start==null)start=r;if((!C.flag[i]||i===C.r.length-1)&&start!=null){const end=C.flag[i]?r:C.r[i-1];el('rect',{x:X(start),y:Y(hi),width:Math.max(1,X(end)-X(start)),height:Y(lo)-Y(hi),fill:wr,opacity:.1},svg);start=null}});
  el('polygon',{points:C.r.map((r,i)=>X(r)+','+Y(cl(C.mean[i]+3*C.spread[i]))).concat(C.r.slice().reverse().map((r,j)=>{const i=C.r.length-1-j;return X(r)+','+Y(cl(C.mean[i]-3*C.spread[i]))})).join(' '),fill:ac,opacity:.18},svg);
  el('polyline',{points:C.r.map((r,i)=>X(r)+','+Y(cl(C.true[i]))).join(' '),fill:'none',stroke:mu,'stroke-width':1.6,'stroke-dasharray':'6 4'},svg);
  el('polyline',{points:C.r.map((r,i)=>X(r)+','+Y(cl(C.mean[i]))).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg);
  C.train.r.forEach((r,i)=>el('circle',{cx:X(r),cy:Y(C.train.E[i]),r:4,fill:tok('--ink')},svg));
  legend('cleg',tr(TX.cLeg),[mu,ac,ac,tok('--ink'),wr]);
  const h=tr(TX.cT),U=tr(TX.U);
  $('ccards').innerHTML=card(h[0],sci(C.err_in*1000,2)+U.mev)+card(h[1],sci(C.sigma_in*1000,2)+U.mev)+card(h[2],sci(C.at.err*1000,2)+U.mev)+card(h[3],sci(C.at.sigma*1000,2)+U.mev);
  $('cNote').innerHTML=tr(TX.cNote)(sci(C.err_out/C.err_in,1))}
async function evt(){try{E=await liveE({N:Math.round(Math.pow(10,Q.lgN)),T:Q.T,barrier:Q.bar,length:Math.pow(10,Q.lgL)})}catch(e){return}drawEvt()}
function drawEvt(){if(!E)return;const ac=tok('--accent'),wr=tok('--warn'),svg=$('echart');svg.innerHTML='';const ws=E.curve.wait_ps.map(w=>Math.log10(w)),lo=Math.max(-2,Math.floor(Math.min(...ws))),hi=Math.min(40,Math.ceil(Math.max(...ws)));
  const [X,Y]=frame(svg,960,300,[56,14,22,38],[0.1,2],[lo,hi],ticks(0.1,2,8),ticks(lo,hi,5),tr(TX.bAx),tr(TX.wAx));
  el('polyline',{points:E.curve.barrier.map((b,i)=>X(b)+','+Y(Math.max(lo,Math.min(hi,ws[i])))).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg);
  el('line',{x1:X(0.1),x2:X(2),y1:Y(Q.lgL),y2:Y(Q.lgL),stroke:wr,'stroke-width':1.6,'stroke-dasharray':'6 4'},svg);
  const yw=Math.log10(E.wait_ps);if(yw>=lo&&yw<=hi)el('circle',{cx:X(Q.bar),cy:Y(yw),r:6,fill:ac},svg);
  legend('eleg',tr(TX.eLeg),[ac,wr]);
  const h=tr(TX.eT),U=tr(TX.U);
  $('ecards').innerHTML=card(h[0],'±'+fmt(E.dT,0)+U.K+' ('+fmt(100*E.rel,1)+' %)')+card(h[1],sci(E.rate,2)+U.s)+card(h[2],sci(E.wait_ps,2)+U.ps)+card(h[3],sci(E.events,2))
    +card(h[4],sci(E.ml_hours,2)+U.h)+card(h[5],sci(E.dft_days,2)+U.d);
  $('eNote').innerHTML=tr(TX.eNote)(fmt(100*E.rel,1),E.events)}
ver();com();evt();onTheme(()=>{drawVer();drawCom();drawEvt()});
