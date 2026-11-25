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
/* Properties as derivatives of the energy (Atlas v2): finite differences and the choice of the step, the finite-field
   dipole moment and polarizability, two levels and diffuse functions — quas_atlas.core.derivs (der.steps, der.field,
   der.twolevel). */
const TX={
  hAx:{ru:'шаг h, бор',en:'step h, bohr',zh:'步长 h，bohr'},eAx:{ru:'lg |ошибка|',en:'log₁₀ |error|',zh:'lg |误差|'},
  sLeg:{ru:['разность вперёд','центральная разность','вторая производная','h_опт центральной'],en:['forward difference','central difference','second derivative','h_opt of the central'],zh:['前向差分','中心差分','二阶导数','中心差分 h_opt']},
  sT:{ru:['точная E′(1,6)','лучшая центральная','лучшая вперёд','h_опт = (3δE/|E‴|)^⅓'],en:['exact E′(1.6)','best central','best forward','h_opt = (3δE/|E‴|)^⅓'],zh:['精确 E′(1.6)','最佳中心差分','最佳前向差分','h_opt = (3δE/|E‴|)^⅓']},
  atH:{ru:'при h = ',en:'at h = ',zh:'h = '},
  sNote:{ru:(d)=>'Ошибка формулы растёт с шагом (вперёд — как h, центральная — как h²), а шум округления — при уменьшении шага: δE/h для первой производной и δE/h² для второй. Сумма — кривая с минимумом. '+(d>=13?'Энергии почти точные — чем меньше шаг, тем лучше, пока не кончатся знаки.':'Энергии известны до 10<sup>−'+d+'</sup> хартри: слишком малый шаг так же плох, как слишком большой. При самом малом шаге разность вперёд может оказаться просто нулём — два округлённых числа совпали.')+' Типичный шаг по координатам ядер — около сотой доли ангстрема.',
    en:(d)=>'The error of the formula grows with the step (forward as h, central as h²), and the rounding noise as the step shrinks: δE/h for the first derivative and δE/h² for the second. The sum is a curve with a minimum. '+(d>=13?'The energies are almost exact — the smaller the step the better, until the digits run out.':'The energies are known to 10<sup>−'+d+'</sup> hartree: too small a step is as bad as too large. At the smallest step the forward difference may be plain zero — two rounded numbers coincided.')+' The typical step in the coordinates of the nuclei is about a hundredth of an angstrom.',
    zh:(d)=>'公式误差随步长增大（前向按 h，中心按 h²），而舍入噪声随步长减小而增大：一阶导数为 δE/h，二阶为 δE/h²。两者之和是有极小值的曲线。'+(d>=13?'能量几乎精确——步长越小越好，直到有效数字用完。':'能量精确到 10<sup>−'+d+'</sup> hartree：步长太小和太大同样糟糕。最小步长时前向差分可能直接为零——两个舍入后的数相同。')+'核坐标的典型步长约为百分之一埃。'},
  fAx:{ru:'поле F, а.е.',en:'field F, a.u.',zh:'场 F，a.u.'},
  fLeg:{ru:['α по энергиям','α по диполям','μ по энергиям'],en:['α from the energies','α from the dipoles','μ from the energies'],zh:['由能量得 α','由偶极矩得 α','由能量得 μ']},
  fT:{ru:['μ (истинное 0,728 а.е. = 1,85 Д)','α по энергиям','α по диполям','½αF² — вклад поля'],en:['μ (true 0.728 a.u. = 1.85 D)','α from the energies','α from the dipoles','½αF² — the field term'],zh:['μ（真值 0.728 a.u. = 1.85 D）','由能量得 α','由偶极矩得 α','½αF² ——场项']},
  au:{ru:' а.е.',en:' a.u.',zh:' a.u.'},kj:{ru:' кДж/моль',en:' kJ/mol',zh:' kJ/mol'},
  fNote:{ru:(n1,n2)=>'μ = −(E₊ − E₋)/(2F), α = −(E₊ + E₋ − 2E₀)/F². Поляризуемость — разница почти равных чисел в восьмом знаке: шум энергии делится на F², здесь он даёт ошибку α около '+n1+' а.е. Если программа печатает диполь в поле, α = [μ(F) − μ(−F)]/(2F), и шум делится только на F: около '+n2+' а.е. При большом поле начинают мешать гиперполяризуемости β и γ. Поэтому для конечного поля SCF сходят до 10<sup>−9</sup>–10<sup>−10</sup> и берут F ≈ 10<sup>−3</sup> а.е.',
    en:(n1,n2)=>'μ = −(E₊ − E₋)/(2F), α = −(E₊ + E₋ − 2E₀)/F². The polarizability is a difference of almost equal numbers in the eighth digit: the noise of the energy is divided by F², here it gives an error of α of about '+n1+' a.u. If the program prints the dipole in the field, α = [μ(F) − μ(−F)]/(2F), and the noise is divided only by F: about '+n2+' a.u. At a large field the hyperpolarizabilities β and γ get in the way. This is why for a finite field the SCF is converged to 10<sup>−9</sup>–10<sup>−10</sup> and F ≈ 10<sup>−3</sup> a.u. is taken.',
    zh:(n1,n2)=>'μ = −(E₊ − E₋)/(2F)，α = −(E₊ + E₋ − 2E₀)/F²。极化率是几乎相等的两个数在第八位上的差：能量噪声除以 F²，这里使 α 的误差约为 '+n1+' a.u.。如果程序输出场中的偶极矩，α = [μ(F) − μ(−F)]/(2F)，噪声只除以 F：约 '+n2+' a.u.。场很大时超极化率 β 和 γ 开始干扰。所以有限场计算中 SCF 收敛到 10<sup>−9</sup>–10<sup>−10</sup>，取 F ≈ 10<sup>−3</sup> a.u.。'},
  bAx:{ru:'α воды, а.е.',en:'α of water, a.u.',zh:'水的 α，a.u.'},
  bLeg:{ru:['B3LYP в базисе','опыт','модель двух уровней'],en:['B3LYP in a basis','experiment','two-level model'],zh:['基组中的 B3LYP','实验','二能级模型']},
  twoName:{ru:'2 уровня',en:'2 levels',zh:'二能级'},
  tT:{ru:['α = 2|μ₀₁|²/ΔE','def2-SVP → def2-SVPD','def2-SVP → def2-TZVP'],en:['α = 2|μ₀₁|²/ΔE','def2-SVP → def2-SVPD','def2-SVP → def2-TZVP'],zh:['α = 2|μ₀₁|²/ΔE','def2-SVP → def2-SVPD','def2-SVP → def2-TZVP']},
  tNote:{ru:'Поляризуемость — сумма по возбуждённым состояниям: большой переходный диполь и малая щель дают большую α. Поле тянет электроны наружу, в область, где валентные функции уже затухли. Описать вытянутый хвост плотности могут только диффузные функции с малыми показателями: одна диффузная оболочка (SVP → SVPD) почти удваивает α, а рост ζ без них (SVP → TZVP) почти не помогает. Для поляризуемости, анионов и сродства к электрону диффузные функции обязательны.',
    en:'The polarizability is a sum over the excited states: a large transition dipole and a small gap give a large α. The field pulls the electrons outward, where the valence functions have already died away. Only diffuse functions with small exponents can describe the stretched tail of the density: one diffuse shell (SVP → SVPD) almost doubles α, while a larger ζ without them (SVP → TZVP) hardly helps. For polarizabilities, anions and electron affinities diffuse functions are a must.',
    zh:'极化率是对激发态的求和：大的跃迁偶极和小的能隙给出大的 α。场把电子向外拉，到价函数已经衰减的区域。只有指数小的弥散函数才能描述被拉长的密度尾部：一个弥散壳层（SVP → SVPD）几乎使 α 翻倍，而不加弥散函数增大 ζ（SVP → TZVP）几乎没有帮助。对极化率、阴离子和电子亲和能，弥散函数必不可少。'}
};
const Q={dg:6,lf:-2.7,ld:-8,m:1.2,g:0.3};let S=null,F=null,T=null;
const liveS=QC.live('der.steps'),liveF=QC.live('der.field'),liveT=QC.live('der.twolevel');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show()};
slider('dg',v=>{Q.dg=v;st()},0);slider('lf',v=>{Q.lf=v;fl()},2);slider('ld',v=>{Q.ld=v;fl()},1);slider('m1',v=>{Q.m=v;tl()},2);slider('ge',v=>{Q.g=v;tl()},2);
const lg=Math.log10,cl=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
const legend=(id,names,colors)=>{$(id).innerHTML=names.map((s,j)=>'<span><i class="sw" style="border-color:'+colors[j]+'"></i>'+s+'</span>').join('')};
function logChart(svg,xs,series,xr,yr,xl,yl,mark){svg.innerHTML='';const xt=[],yt=[];for(let v=Math.ceil(xr[0]);v<=xr[1];v++)xt.push(v);for(let v=Math.ceil(yr[0]);v<=yr[1];v+=2)yt.push(v);
  const [X,Y]=frame(svg,960,320,[56,14,22,38],xr,yr,xt,yt,xl,yl);
  series.forEach(([ys,c,w,d])=>el('polyline',{points:xs.map((x,i)=>X(lg(x))+','+Y(cl(lg(Math.max(Math.abs(ys[i]),1e-300)),yr[0],yr[1]))).join(' '),fill:'none',stroke:c,'stroke-width':w,'stroke-dasharray':d||''},svg));
  if(mark!=null)el('line',{x1:X(lg(mark)),x2:X(lg(mark)),y1:Y(yr[0]),y2:Y(yr[1]),stroke:tok('--ink'),'stroke-dasharray':'3 4','stroke-width':1},svg);return [X,Y]}
async function st(){try{S=await liveS({digits:Math.round(Q.dg)})}catch(e){return}drawS()}
function drawS(){if(!S)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok');
  logChart($('schart'),S.h,[[S.forward,wr,2.2],[S.central,ac,2.4],[S.second,ok,2.2]],[-5,-0.5],[-12,1],tr(TX.hAx),tr(TX.eAx),S.h_opt);
  legend('sleg',tr(TX.sLeg),[wr,ac,ok,tok('--ink')]);
  const hs=x=>x>=1e-3?fmt(x,Math.max(0,1-Math.floor(Math.log10(x)))):sci(x,1);
  const h=tr(TX.sT),b=S.best,at=tr(TX.atH);
  $('scards').innerHTML=card(h[0],fmt(S.exact.d1,6))+card(h[1],sci(b.central.err,1),at+hs(b.central.h))+card(h[2],sci(b.forward.err,1),at+hs(b.forward.h))+card(h[3],hs(S.h_opt));
  $('sNote').innerHTML=tr(TX.sNote)(Math.round(Q.dg))}
async function fl(){try{F=await liveF({lgF:Q.lf,lgdE:Q.ld})}catch(e){return}drawF()}
function drawF(){if(!F)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok');
  logChart($('fchart'),F.F,[[F.alpha_E_err,wr,2.2],[F.alpha_mu_err,ac,2.4],[F.mu_err,ok,1.8,'5 4']],[-5,-1],[-12,4],tr(TX.fAx),tr(TX.eAx),F.at.F);
  legend('fleg',tr(TX.fLeg),[wr,ac,ok]);
  const h=tr(TX.fT),au=tr(TX.au),a=F.at;
  $('fcards').innerHTML=card(h[0],fmt(a.mu,5)+au)+card(h[1],fmt(a.alpha_E,3)+au)+card(h[2],fmt(a.alpha_mu,3)+au)+card(h[3],sci(a.kj,2)+tr(TX.kj));
  $('fNote').innerHTML=tr(TX.fNote)(sci(a.noise_E,1),sci(a.noise_mu,1))}
async function tl(){try{T=await liveT({mu01:Q.m,dE:Q.g})}catch(e){return}drawT()}
function drawT(){if(!T)return;const ac=tok('--accent'),wr=tok('--warn'),ok=tok('--ok'),svg=$('tchart');svg.innerHTML='';const rows=T.basis.concat([{name:tr(TX.twoName),alpha:T.alpha,two:true}]),top=Math.max(12,...rows.map(r=>r.alpha))*1.1;
  const [X,Y]=frame(svg,960,300,[56,14,22,40],[0,rows.length],[0,top],[],[0,2,4,6,8,10,12,14,16,18,20].filter(v=>v<=top),'',tr(TX.bAx));
  rows.forEach((r,i)=>{const x0=X(i+0.18),x1=X(i+0.82);el('rect',{x:x0,y:Y(r.alpha),width:x1-x0,height:Y(0)-Y(r.alpha),fill:r.two?ok:ac,opacity:r.two?0.8:0.75},svg);
    el('text',{x:(x0+x1)/2,y:300-22,'text-anchor':'middle'},svg,r.name);el('text',{x:(x0+x1)/2,y:Y(r.alpha)-6,'text-anchor':'middle',class:'lab'},svg,fmt(r.alpha,2))});
  el('line',{x1:X(0),x2:X(rows.length),y1:Y(T.exp),y2:Y(T.exp),stroke:wr,'stroke-dasharray':'6 4','stroke-width':1.6},svg);
  legend('tleg',tr(TX.bLeg),[ac,wr,ok]);
  const h=tr(TX.tT),b=T.basis;
  $('tcards').innerHTML=card(h[0],fmt(T.alpha,2)+tr(TX.au))+card(h[1],fmt(b[0].alpha,2)+' → '+fmt(b[2].alpha,2))+card(h[2],fmt(b[0].alpha,2)+' → '+fmt(b[1].alpha,2));
  $('tNote').textContent=tr(TX.tNote)}
st();fl();tl();onTheme(()=>{drawS();drawF();drawT()});
