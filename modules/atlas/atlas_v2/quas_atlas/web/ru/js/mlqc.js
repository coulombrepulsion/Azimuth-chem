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
/* Machine learning in quantum chemistry (Atlas v2): Δ-learning with kernel ridge regression and its learning curves,
   the honest test of a model (the MAE and its uncertainty), the convex hull of a screening —
   quas_atlas.core.mlpot (ml.delta, ml.mae, ml.hull). */
const TX={
  U:{ru:{ev:' эВ',ea:' эВ/атом',mev:' мэВ/атом',kj:' кДж/моль'},en:{ev:' eV',ea:' eV/atom',mev:' meV/atom',kj:' kJ/mol'},zh:{ev:' eV',ea:' eV/原子',mev:' meV/原子',kj:' kJ/mol'}},
  xAx:{ru:'координата x',en:'coordinate x',zh:'坐标 x'},EAx:{ru:'E, эВ',en:'E, eV',zh:'E，eV'},
  fLeg:{ru:['дорогой метод','дешёвый метод','модель напрямую','дешёвый + модель Δ','обучающие точки'],en:['expensive method','cheap method','model directly','cheap + model of Δ','training points'],zh:['昂贵方法','廉价方法','直接模型','廉价 + Δ 模型','训练点']},
  nAx:{ru:'число обучающих точек n',en:'number of training points n',zh:'训练点数 n'},mAx:{ru:'lg MAE, эВ',en:'log₁₀ MAE, eV',zh:'lg MAE，eV'},
  lLeg:{ru:['учим энергию','учим поправку Δ'],en:['learning the energy','learning the correction Δ'],zh:['学习能量','学习修正 Δ']},
  dT:{ru:['MAE напрямую','MAE с Δ','наклон a: напрямую / Δ','вдвое меньше ошибка — данных больше в'],en:['MAE directly','MAE with Δ','slope a: direct / Δ','half the error takes more data by'],zh:['直接 MAE','Δ 的 MAE','斜率 a：直接 / Δ','误差减半需数据增加']},
  times:{ru:' раза',en:'×',zh:' 倍'},
  dNote:{ru:(k)=>'Ядерная гребневая регрессия: предсказание — взвешенная сумма «похожестей» на обучающие точки. Энергия дорогого метода меняется сильно, а поправка к дешёвому — мало и плавно: её модель выучивает по тем же данным в '+k+' раз точнее. Кривые обучения — прямые в логарифмических осях, δ = A·n<sup>−a</sup>. Дешёвый расчёт делают всегда; модель только добавляет поправку — если она ошиблась, остаётся результат дешёвого метода, а не выдумка.',
    en:(k)=>'Kernel ridge regression: a prediction is a weighted sum of «similarities» to the training points. The energy of the expensive method varies a lot, the correction to the cheap one little and smoothly: the model learns it from the same data '+k+' times more accurately. The learning curves are straight lines in log axes, δ = A·n<sup>−a</sup>. The cheap calculation is always done; the model only adds the correction — if it errs, the result of the cheap method remains, not an invention.',
    zh:(k)=>'核岭回归：预测是与训练点“相似度”的加权和。昂贵方法的能量变化大，而相对廉价方法的修正变化小且平滑：用同样的数据，模型学修正的精度高 '+k+' 倍。学习曲线在对数坐标中是直线，δ = A·n<sup>−a</sup>。廉价计算总要做；模型只加上修正——即使它出错，剩下的也是廉价方法的结果，而不是编造。'},
  tAx:{ru:'число тестовых молекул',en:'number of test molecules',zh:'测试分子数'},aAx:{ru:'MAE, кДж/моль',en:'MAE, kJ/mol',zh:'MAE，kJ/mol'},
  aLeg:{ru:['модель A','модель B','истинные MAE'],en:['model A','model B','true MAEs'],zh:['模型 A','模型 B','真实 MAE']},
  aT:{ru:['MAE модели A','MAE модели B','относительная погрешность','различимы?'],en:['MAE of model A','MAE of model B','relative uncertainty','distinguishable?'],zh:['模型 A 的 MAE','模型 B 的 MAE','相对不确定度','能区分吗？']},
  yes:{ru:'да',en:'yes',zh:'能'},no:{ru:'нет',en:'no',zh:'不能'},
  aNote:{ru:(r,n)=>'MAE — среднее по тестовым молекулам, и, как любое среднее, известно с погрешностью σ(|e|)/√n ≈ 0,75·MAE/√n. При '+n+' молекулах это ±'+r+' %. Две модели с MAE 10 и 11 на двадцати молекулах не различить: разница меньше погрешности. Поэтому тест берут побольше, а молекулы теста не должны попадать в обучение — даже похожие.',
    en:(r,n)=>'The MAE is a mean over the test molecules and, like any mean, is known within σ(|e|)/√n ≈ 0.75·MAE/√n. With '+n+' molecules that is ±'+r+' %. Two models with MAE 10 and 11 cannot be told apart on twenty molecules: the difference is below the uncertainty. This is why the test set is made larger, and its molecules must not get into the training — not even similar ones.',
    zh:(r,n)=>'MAE 是测试分子的平均值，与任何平均值一样，其不确定度为 σ(|e|)/√n ≈ 0.75·MAE/√n。'+n+' 个分子时为 ±'+r+' %。MAE 为 10 和 11 的两个模型在二十个分子上无法区分：差别小于不确定度。所以测试集要更大，而且测试分子不能进入训练——即使相似的也不行。'},
  hxAx:{ru:'доля B, x',en:'share of B, x',zh:'B 的份额 x'},hyAx:{ru:'энергия образования, эВ/атом',en:'formation energy, eV/atom',zh:'形成能，eV/原子'},
  hLeg:{ru:['выпуклая оболочка','известные фазы','новое соединение'],en:['convex hull','known phases','new compound'],zh:['凸包','已知相','新化合物']},
  hT:{ru:['оболочка при этом x','над оболочкой','вывод'],en:['hull at this x','above the hull','verdict'],zh:['该 x 处的凸包','高于凸包','结论']},
  verdict:{ru:a=>a<0?'устойчиво: новая фаза':a<0.05?'на грани: в пределах ошибки модели':'распадётся на соседние фазы',en:a=>a<0?'stable: a new phase':a<0.05?'borderline: within the error of the model':'decomposes into the neighbouring phases',zh:a=>a<0?'稳定：新相':a<0.05?'临界：在模型误差范围内':'分解为相邻相'},
  hNote:{ru:(a)=>'Соединение устойчиво, если его энергия ниже прямой между соседними фазами — иначе смесь двух соседей того же состава выгоднее. Сейчас оно '+(a<0?'ниже оболочки на '+Math.round(-a*1000)+' мэВ/атом: оболочка перестраивается, и одна из старых фаз может стать неустойчивой.':'выше на '+Math.round(a*1000)+' мэВ/атом.')+' Модели МО ошибаются на 30–50 мэВ/атом, поэтому кандидатов «у оболочки» проверяют DFT, а до синтеза доходят единицы.',
    en:(a)=>'A compound is stable when its energy is below the line between the neighbouring phases — otherwise a mixture of the two neighbours of the same composition is lower. Now it is '+(a<0?Math.round(-a*1000)+' meV/atom below the hull: the hull is rebuilt, and one of the old phases may become unstable.':Math.round(a*1000)+' meV/atom above it.')+' Learned models err by 30–50 meV/atom, so candidates «near the hull» are checked by DFT, and only a few reach a synthesis.',
    zh:(a)=>'化合物的能量若低于相邻两相之间的直线则稳定——否则相同组成的两相混合物更低。现在它'+(a<0?'低于凸包 '+Math.round(-a*1000)+' meV/原子：凸包重建，某个旧相可能变得不稳定。':'高于凸包 '+Math.round(a*1000)+' meV/原子。')+'机器学习模型误差为 30–50 meV/原子，所以“接近凸包”的候选要用 DFT 检验，只有少数能进入合成。'}
};
const Q={n:16,cheap:0.5,sig:0.5,tn:20,ma:10,mb:11,e13:-0.4,e12:-0.5,x:0.4,e:-0.41};let D=null,M=null,H=null;
const liveD=QC.live('ml.delta'),liveM=QC.live('ml.mae'),liveH=QC.live('ml.hull');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show()};
slider('nn',v=>{Q.n=v;dl()},0);slider('cq',v=>{Q.cheap=v;dl()},2);slider('ks',v=>{Q.sig=v;dl()},2);
slider('tn',v=>{Q.tn=v;me()},0);slider('ma',v=>{Q.ma=v;me()},1);slider('mb',v=>{Q.mb=v;me()},1);
slider('e3',v=>{Q.e13=v;hl()},2);slider('e2',v=>{Q.e12=v;hl()},2);slider('xx',v=>{Q.x=v;hl()},2);slider('ee',v=>{Q.e=v;hl()},2);
const ticks=(lo,hi,n)=>{const r=(hi-lo)/n,p=Math.pow(10,Math.floor(Math.log10(r))),s=[1,2,2.5,5,10].map(k=>k*p).find(k=>k>=r);const t=[];for(let v=Math.ceil(lo/s)*s;v<=hi+1e-9;v+=s)t.push(+v.toFixed(6));return t};
const legend=(id,names,colors)=>{$(id).innerHTML=names.map((s,j)=>'<span><i class="sw" style="border-color:'+colors[j]+'"></i>'+s+'</span>').join('')};
const lg=Math.log10;
async function dl(){try{D=await liveD({n:Math.round(Q.n),cheap:Q.cheap,sigma:Q.sig})}catch(e){return}drawD()}
function drawD(){if(!D)return;const ac=tok('--accent'),wr=tok('--warn'),mu=tok('--muted'),ok=tok('--ok'),svg=$('fchart');svg.innerHTML='';
  const all=D.true.concat(D.cheap),lo=Math.min(...all)-0.2,hi=Math.min(5,Math.max(...all)+0.2),cl=v=>Math.max(lo,Math.min(hi,v));
  const [X,Y]=frame(svg,960,260,[56,14,22,38],[D.x[0],D.x[D.x.length-1]],[lo,hi],ticks(D.x[0],D.x[D.x.length-1],7),ticks(lo,hi,4),tr(TX.xAx),tr(TX.EAx));
  const line=(ys,c,w,dash)=>el('polyline',{points:D.x.map((x,i)=>X(x)+','+Y(cl(ys[i]))).join(' '),fill:'none',stroke:c,'stroke-width':w,'stroke-dasharray':dash||''},svg);
  line(D.true,tok('--ink'),2.4);line(D.cheap,mu,1.6,'6 4');line(D.fit_direct,wr,1.8);line(D.fit_delta,ok,1.8);
  D.train.x.forEach((x,i)=>el('circle',{cx:X(x),cy:Y(cl(D.train.E[i])),r:3.5,fill:ac},svg));
  legend('fleg',tr(TX.fLeg),[tok('--ink'),mu,wr,ok,ac]);
  const g=$('lchart');g.innerHTML='';const ys=D.direct.concat(D.delta).map(lg),yl=Math.floor(Math.min(...ys)),yh=Math.ceil(Math.max(...ys));
  const [LX,LY]=frame(g,960,240,[56,14,22,38],[lg(4),lg(128)],[yl,yh],[],ticks(yl,yh,4),tr(TX.nAx),tr(TX.mAx));
  D.ns.forEach(n=>el('text',{x:LX(lg(n)),y:240-38+16,'text-anchor':'middle'},g,String(n)));
  [[D.direct,wr],[D.delta,ok]].forEach(([v,c])=>{el('polyline',{points:D.ns.map((n,i)=>LX(lg(n))+','+LY(lg(v[i]))).join(' '),fill:'none',stroke:c,'stroke-width':2.4},g);D.ns.forEach((n,i)=>el('circle',{cx:LX(lg(n)),cy:LY(lg(v[i])),r:4,fill:c},g))});
  el('line',{x1:LX(lg(D.at.n)),x2:LX(lg(D.at.n)),y1:LY(yl),y2:LY(yh),stroke:tok('--ink'),'stroke-dasharray':'3 4','stroke-width':1},g);
  legend('lleg',tr(TX.lLeg),[wr,ok]);
  const h=tr(TX.dT),U=tr(TX.U);
  $('dcards').innerHTML=card(h[0],sci(D.at.direct,2)+U.ev)+card(h[1],sci(D.at.delta,2)+U.ev)+card(h[2],fmt(D.a_direct,2)+' / '+fmt(D.a_delta,2))+card(h[3],fmt(Math.pow(2,1/D.a_direct),1)+' / '+fmt(Math.pow(2,1/D.a_delta),1)+tr(TX.times));
  $('dNote').innerHTML=tr(TX.dNote)(fmt(D.at.direct/Math.max(1e-12,D.at.delta),1))}
async function me(){try{M=await liveM({n:Math.round(Q.tn),a:Q.ma,b:Q.mb})}catch(e){return}drawM()}
function drawM(){if(!M)return;const ac=tok('--accent'),wr=tok('--warn'),mu=tok('--muted'),svg=$('achart');svg.innerHTML='';
  const vals=M.a.lo.concat(M.a.hi,M.b.lo,M.b.hi,[Q.ma,Q.mb]),lo=Math.max(0,Math.min(...vals)*0.9),hi=Math.max(...vals)*1.05;
  const [X,Y]=frame(svg,960,280,[56,14,22,38],[lg(4),lg(400)],[lo,hi],[],ticks(lo,hi,5),tr(TX.tAx),tr(TX.aAx));
  M.ns.forEach(n=>el('text',{x:X(lg(n)),y:280-38+16,'text-anchor':'middle'},svg,String(n)));
  [[Q.ma,ac],[Q.mb,wr]].forEach(([v,c])=>el('line',{x1:X(lg(4)),x2:X(lg(400)),y1:Y(v),y2:Y(v),stroke:c,'stroke-dasharray':'6 4','stroke-width':1.2,opacity:.7},svg));
  [[M.a,ac,-0.012],[M.b,wr,0.012]].forEach(([s,c,dx])=>M.ns.forEach((n,i)=>{const x=X(lg(n)+dx);el('line',{x1:x,x2:x,y1:Y(s.lo[i]),y2:Y(s.hi[i]),stroke:c,'stroke-width':2},svg);el('circle',{cx:x,cy:Y(s.mean[i]),r:4.5,fill:c},svg)}));
  el('line',{x1:X(lg(M.n)),x2:X(lg(M.n)),y1:Y(lo),y2:Y(hi),stroke:tok('--ink'),'stroke-dasharray':'3 4','stroke-width':1},svg);
  legend('mleg',tr(TX.aLeg),[ac,wr,mu]);
  const h=tr(TX.aT),U=tr(TX.U),a=M.a.at,b=M.b.at,apart=Math.abs(a.mae-b.mae)>2*Math.hypot(a.err,b.err);
  $('mcards').innerHTML=card(h[0],fmt(a.mae,1)+' ± '+fmt(a.err,1)+U.kj)+card(h[1],fmt(b.mae,1)+' ± '+fmt(b.err,1)+U.kj)+card(h[2],'±'+fmt(100*M.rel,0)+' %')+card(h[3],apart?tr(TX.yes):tr(TX.no));
  $('mNote').innerHTML=tr(TX.aNote)(fmt(100*M.rel,0),M.n)}
async function hl(){try{H=await liveH({e13:Q.e13,e12:Q.e12,x:Q.x,e:Q.e})}catch(e){return}drawH()}
function drawH(){if(!H)return;const ac=tok('--accent'),wr=tok('--warn'),mu=tok('--muted'),svg=$('hchart');svg.innerHTML='';
  const es=H.phases.map(p=>p.E).concat([H.e]),lo=Math.min(-0.1,...es)-0.1,hi=Math.max(0.1,...es)+0.1;
  const [X,Y]=frame(svg,960,300,[64,14,30,38],[0,1],[lo,hi],[0,0.25,1/3,0.5,0.75,1].map(v=>+v.toFixed(3)),ticks(lo,hi,5),tr(TX.hxAx),tr(TX.hyAx));
  el('line',{x1:X(0),x2:X(1),y1:Y(0),y2:Y(0),stroke:mu,'stroke-width':1},svg);
  el('polyline',{points:H.hull.x.map((x,i)=>X(x)+','+Y(H.hull.E[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg);
  if(H.above<0)el('polyline',{points:H.new_hull.x.map((x,i)=>X(x)+','+Y(H.new_hull.E[i])).join(' '),fill:'none',stroke:wr,'stroke-width':1.4,'stroke-dasharray':'6 4'},svg);
  H.phases.forEach(p=>el('circle',{cx:X(p.x),cy:Y(p.E),r:6,fill:p.on?ac:'none',stroke:ac,'stroke-width':2},svg));
  el('line',{x1:X(H.x),x2:X(H.x),y1:Y(H.at_hull),y2:Y(H.e),stroke:wr,'stroke-width':1.4,'stroke-dasharray':'2 3'},svg);
  el('rect',{x:X(H.x)-6,y:Y(H.e)-6,width:12,height:12,fill:wr,transform:'rotate(45 '+X(H.x)+' '+Y(H.e)+')'},svg);
  legend('hleg',tr(TX.hLeg),[ac,ac,wr]);
  const h=tr(TX.hT),U=tr(TX.U);
  $('hcards').innerHTML=card(h[0],fmt(H.at_hull,3)+U.ea)+card(h[1],fmt(H.above*1000,0)+U.mev)+card(h[2],tr(TX.verdict)(H.above));
  $('hNote').innerHTML=tr(TX.hNote)(H.above)}
dl();me();hl();onTheme(()=>{drawD();drawM();drawH()});
