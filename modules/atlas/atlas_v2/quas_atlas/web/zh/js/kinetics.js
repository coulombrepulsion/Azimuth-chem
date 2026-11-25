/* Reaction rate page (Atlas v2).  dG‡, the Eyring rate constant, half-life,
   Arrhenius parameters, the t½(dG‡) line, the isotope effect and the Wigner
   correction come from quas_atlas.core.kinetics (kin.state, kin.custom);
   this script formats and draws. */
// ---------- страница «Скорость реакции: переходное состояние» ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const SUP=s=>String(s).split('').map(c=>c==='-'?'⁻':'⁰¹²³⁴⁵⁶⁷⁸⁹'[+c]).join('');
function sci(x){if(!isFinite(x))return '—';if(x===0)return '0';const e=Math.floor(Math.log10(Math.abs(x)));if(e>=-2&&e<4)return fmt(x,e>=2?0:e>=0?2:3);const m=x/Math.pow(10,e);return fmt(m,2)+'·10'+SUP(e)}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const Q={T:298.15,n:1};
function human(t){if(!isFinite(t))return '—';if(t<1e-3)return sci(t)+' 秒';if(t<1)return fmt(t*1000,t<0.01?2:0)+' ms';if(t<60)return fmt(t,1)+' 秒';if(t<3600)return fmt(t/60,1)+' min';if(t<86400)return fmt(t/3600,1)+' h';if(t<3.156e7)return fmt(t/86400,1)+' 天';return sci(t/3.156e7)+' 年'}
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
chips($('mG'),['单分子，A → P','双分子，A + B → P'],0,i=>{Q.n=i+1;mark($('mG'),i);draw()});
['dH','dS','nu','im'].forEach(id=>$(id).oninput=draw);
$('T').value=298;$('T').oninput=()=>{Q.T=+$('T').value;draw()};$('bT298').textContent=fmt(298.15,2)+' K';$('bT298').onclick=()=>{Q.T=298.15;$('T').value=298;draw()};
const liveK=QC.live('kin.state');
async function draw(){const dH=+$('dH').value,dS=+$('dS').value,T=Q.T,bi=Q.n===2,nu=+$('nu').value,im=+$('im').value;
  let Z;try{Z=await liveK({dH,dS,T,n:Q.n,nu,im})}catch(e){return}const dG=Z.dG,k=Z.k;
  $('dHv').textContent=fmt(dH,1)+' kJ/mol';$('dSv').textContent=fmt(dS,0)+' J/(mol·K)';$('Tv').textContent=fmt(T,T===298.15?2:0)+' K';
  const t=Z.t,Ea=Z.Ea,A=Z.A;
  const card=(a,b,c)=>'<div class="card"><span class="t">'+a+'</span><b>'+b+'</b>'+(c?'<small>'+c+'</small>':'')+'</div>';
  $('cards').innerHTML=card('ΔG<sup>‡</sup> = ΔH<sup>‡</sup> − TΔS<sup>‡</sup>',fmt(dG,1)+' kJ/mol',fmt(dG/4.184,1)+' kcal/mol')+card('速率常数 k',sci(k)+(bi?' L/(mol·s)':' s⁻¹'),bi?'标准态 1 mol/L':'')
    +card('半衰期',human(t),bi?'初始浓度均为 1 mol/L':'')+card('按阿伦尼乌斯',fmt(Ea,1)+' kJ/mol','A = '+sci(A)+(bi?' L/(mol·s)':' s⁻¹'));
  $('eyNote').innerHTML='阿伦尼乌斯活化能 E<sub>a</sub> = ΔH<sup>‡</sup> + RT（适用于单分子反应和溶液中的反应），指前因子 A = (e·k<sub>B</sub>T/h)·exp(ΔS<sup>‡</sup>/R)。负的 ΔS<sup>‡</sup>——有序的过渡态（环状、双分子）——使 A 减小：每 −19 J/(mol·K) 使反应慢 10 倍。';
  chart(dG,T,bi,Z.chart);
  const r=Z.kie.r,nD=Z.kie.nD,kie=Z.kie.kie;$('nuv').textContent=fmt(nu,0);
  $('kie').innerHTML='ν(C–D) = ν(C–H) / √<span class=fr><span>μ<sub>D</sub></span><span>μ<sub>H</sub></span></span> = '+fmt(nu,0)+'/'+fmt(r,3)+' = '+fmt(nD,0)+' cm⁻¹。损失的是量子差值的一半，'+fmt(Z.kie.half,0)+' cm⁻¹ = '+fmt(Z.kie.halfkJ,2)+' kJ/mol。在 '+fmt(T,0)+' K: <b>k<sub>H</sub>/k<sub>D</sub> ≈ '+fmt(kie,1)+'</b>。观测到的一级同位素效应通常为 2–8；室温下明显大于 7–10 的值是隧穿的迹象。';
  const w=Z.tun.w,kap=Z.tun.kap;$('imv').textContent=fmt(im,0)+'i';
  $('tun').innerHTML='hcν<sup>‡</sup>/k<sub>B</sub>T = '+fmt(w,2)+'; <b>κ = '+fmt(kap,2)+'</b>. '+(kap<1.5?'校正很小，此处维格纳估计是合理的。':kap<2.5?'校正已经明显；维格纳估计应该用更精确的模型（埃卡特模型、半经典方法）检验。':'校正很大——超出维格纳估计的适用范围：隧穿很显著，需要埃卡特模型或半经典计算。')}
function chart(dG,T,bi,C){const svg=$('chart');svg.innerHTML='';const W=960,Hh=300,L=64,Rr=110,Tp=14,B=38,g0=40,g1=140;
  const y0=C.y0,y1=C.y1;
  const X=g=>L+(g-g0)/(g1-g0)*(W-L-Rr),Y=v=>Tp+(y1-v)/(y1-y0)*(Hh-B-Tp);const ax=tok('--line'),mu=tok('--muted');
  [['1 s',0],['1 min',Math.log10(60)],['1 h',Math.log10(3600)],['1 天',Math.log10(86400)],['1 年',Math.log10(3.156e7)],['1000 年',Math.log10(3.156e10)],['1 μs',-6]].forEach(([n,v])=>{if(v<y0||v>y1)return;el('line',{x1:L,x2:W-Rr,y1:Y(v),y2:Y(v),stroke:ax},svg);el('text',{x:W-Rr+6,y:Y(v)+4},svg,n)});
  for(let g=40;g<=140;g+=20)el('text',{x:X(g),y:Hh-B+16,'text-anchor':'middle'},svg,String(g));
  el('text',{x:(L+W-Rr)/2,y:Hh-4,'text-anchor':'middle'},svg,'ΔG‡，kJ/mol');el('text',{x:8,y:Tp+4},svg,'lg t½');
  for(let v=Math.ceil(y0/5)*5;v<=y1;v+=5)el('text',{x:L-6,y:Y(v)+4,'text-anchor':'end'},svg,String(v).replace('-','−'));
  el('path',{d:[g0,g1].map((g,i)=>(i?'L':'M')+X(g).toFixed(1)+' '+Y([C.lt0,C.lt1][i]).toFixed(1)).join(''),stroke:tok('--accent'),'stroke-width':2.4,fill:'none'},svg);
  if(dG>=g0&&dG<=g1)el('circle',{cx:X(dG),cy:Y(C.ltG),r:6,fill:tok('--accent'),stroke:tok('--panel'),'stroke-width':2},svg)}
// ---------- своя реакция ----------
const num=s=>Number(String(s).trim().replace(',','.').replace('−','-'));
$('bCalc').onclick=async()=>{const msg=$('cMsg'),Gr=num($('cGr').value),Gt=num($('cGt').value),T=num($('cT').value),n=+$('cN').value,sol=$('cSS').value==='sol',ims=$('cIm').value.trim(),im=ims?Math.abs(num(ims)):0;
  if(!isFinite(Gr)||!isFinite(Gt)||!(T>0)||(ims&&!isFinite(im))){msg.textContent='请检查数字：能量以哈特里为单位，温度以开尔文为单位。';return}
  let C;try{C=await QC.api('kin.custom',{Gr,Gt,T,n,sol,im})}catch(e){return}const dG=C.dG,corr=C.corr||0;
  if(dG<=0){msg.textContent='ΔG‡ = '+fmt(dG,1)+' kJ/mol ≤ 0：过渡态并不高于反应物。请检查输入的能量是否正确（方法和基组是否一致）。';return}
  const k=C.k,t=C.t,kap=C.kap;
  msg.innerHTML='ΔG<sup>‡</sup> = <b>'+fmt(dG,1)+' kJ/mol</b>（'+fmt(dG/4.184,1)+' kcal/mol）'+(corr?'；已换算到 1 mol/L：'+fmt(corr,2)+' kJ/mol':'')+'. k = '+sci(k)+(n===2?(sol?' L/(mol·s)':' bar⁻¹·s⁻¹（= '+sci(C.kc)+' L/(mol·s)）'):' s⁻¹')+', t½ ≈ '+human(t)+'.'+(im?' 加维格纳校正（κ = '+fmt(kap,2)+'): k = '+sci(C.kk)+'.'+(kap>2?' κ > 2——估计不可靠。':''):'')+(n===2&&!sol?' 对于溶液中的反应，请选择 1 mol/L 标准态：输出文件中的能量对应 1 bar 的气体。':'')};
draw();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',draw);
