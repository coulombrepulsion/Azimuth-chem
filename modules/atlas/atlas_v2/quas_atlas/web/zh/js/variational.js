/* Variational method page (Atlas v2).  Trial-function energies, the linear
   variational method, basis optimisation and the perturbation series come
   from quas_atlas.core.variational (var.trial, var.lvm, var.optimize,
   var.optcurve, var.pt); this script draws. */
// ---------- страница «Вариационный метод и теория возмущений» (ат. ед.) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt=(x,d=4)=>{if(!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const FR=(a,b)=>'<span class=fr><span>'+a+'</span><span>'+b+'</span></span>';
function axes(sv,W,H,L,R,T,B,xs,ys,xl,yl){el('rect',{x:L,y:T,width:W-L-R,height:H-T-B,fill:'none',stroke:tok('--line')},sv);
  xs.forEach(([x,t])=>el('text',{x,y:H-B+16,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,t));
  ys.forEach(([y,t])=>{el('line',{x1:L,y1:y,x2:W-R,y2:y,stroke:tok('--line'),'stroke-dasharray':'2 4'},sv);el('text',{x:L-5,y:y+4,'text-anchor':'end','font-size':11,fill:tok('--muted')},sv,t)});
  el('text',{x:W-R,y:H-3,'text-anchor':'end','font-size':11.5,fill:tok('--muted')},sv,xl);el('text',{x:4,y:T-11,'font-size':11.5,fill:tok('--muted')},sv,yl)}
const pathOf=(pts,clip)=>{let d='',pen=false;pts.forEach(([x,y])=>{const ok=isFinite(y)&&(!clip||(y>=clip[0]&&y<=clip[1]));if(!ok){pen=false;return}d+=(pen?' L':' M')+x.toFixed(1)+','+y.toFixed(1);pen=true});return d};
// ---------- 1. пробная функция ----------
let trial='gauss',par={slater:0.7,gauss:0.1};
const TR={slater:{nm:'斯莱特型 e<sup>−ζr</sup>',p:'ζ',lo:0.2,hi:2.5,log:false,opt:1},
  gauss:{nm:'高斯型 e<sup>−αr²</sup>',p:'α',lo:0.01,hi:3,log:true,opt:8/(9*Math.PI)}};
const liveT=QC.live('var.trial'),liveL=QC.live('var.lvm'),liveP=QC.live('var.pt');
async function sec1(){const T=TR[trial],v=par[trial],sl=$('par');sl.min=T.log?Math.log10(T.lo):T.lo;sl.max=T.log?Math.log10(T.hi):T.hi;sl.step=0.005;sl.value=T.log?Math.log10(v):v;
  $('parL').innerHTML='参数 '+T.p;$('parV').textContent=T.p+' = '+fmt(v,3);[...$('tG').children].forEach(b=>b.setAttribute('aria-pressed',b.dataset.t===trial));
  let Z;try{Z=await liveT({trial,v})}catch(e){return}
  let sv=$('eSvg');sv.innerHTML='';const W=520,H=300,L=56,R=14,Tm=30,B=34,pw=W-L-R,ph=H-Tm-B,y0=-0.55,y1=Math.max(0.3,Z.E+0.12*(Z.E-y0));// the range grows with E, so the point stays inside
  const xf=p=>T.log?(Math.log10(p)-Math.log10(T.lo))/(Math.log10(T.hi)-Math.log10(T.lo)):(p-T.lo)/(T.hi-T.lo);const sx=p=>L+xf(p)*pw,sy=e=>Tm+ph*(y1-e)/(y1-y0);
  const xt=T.log?[0.01,0.03,0.1,0.3,1,3]:[0.5,1,1.5,2,2.5];
  axes(sv,W,H,L,R,Tm,B,xt.map(x=>[sx(x),fmt(x,x<0.1?2:1).replace(/,0$/,'')]),(y1>0.9?[-0.5,0,0.5,1,1.5,2].filter(e=>e<=y1):y1>0.5?[-0.5,-0.25,0,0.25,0.5,0.75].filter(e=>e<=y1):[-0.5,-0.4,-0.2,0,0.2]).map(e=>[sy(e),fmt(e,e%0.5&&y1>0.5?2:1)]),T.p,'E, Eₕ');
  el('line',{x1:L,y1:sy(-0.5),x2:L+pw,y2:sy(-0.5),stroke:tok('--ok'),'stroke-width':1.6,'stroke-dasharray':'6 4'},sv);el('text',{x:L+pw-4,y:sy(-0.5)-5,'text-anchor':'end','font-size':11.5,fill:tok('--ok')},sv,'精确：−0.5');
  const pts=Z.curve.map(([p,e])=>[sx(p),sy(e)]);
  el('path',{d:pathOf(pts,[Tm,Tm+ph]),fill:'none',stroke:tok('--accent'),'stroke-width':2.4},sv);
  el('circle',{cx:sx(T.opt),cy:sy(Z.Eopt),r:4,fill:'none',stroke:tok('--accent'),'stroke-width':1.5},sv);
  el('circle',{cx:sx(v),cy:sy(Z.E),r:6,fill:tok('--warn')},sv);
  // плотности
  sv=$('fSvg');sv.innerHTML='';/* the top of the axis follows the curve continuously (it jumped to the next round value), as on the left plot */
  const rx=6,dm=Math.max(...Z.dens,...Z.exact),ym=Math.max(1,dm*1.05),ys=[0.25,0.5,1,2,5].find(s=>ym/s<=5)||5,NT=Math.floor(ym/ys+1e-9);const sx2=r=>L+r/rx*pw,sy2=d=>Tm+ph*(1-d/ym);
  axes(sv,W,H,L,R,Tm,B,[0,1,2,3,4,5,6].map(r=>[sx2(r),String(r)]),Array.from({length:NT+1},(_,k)=>[sy2(k*ys),fmt(k*ys,2)]),'r, a₀','r²φ²·4π');
  const rr=Z.r;
  el('path',{d:pathOf(rr.map((r,i)=>[sx2(r),sy2(Z.exact[i])])),fill:'none',stroke:tok('--ok'),'stroke-width':2,'stroke-dasharray':'6 4'},sv);
  el('path',{d:pathOf(rr.map((r,i)=>[sx2(r),sy2(Z.dens[i])])),fill:'none',stroke:tok('--accent'),'stroke-width':2.4},sv);
  const E=Z.E;
  $('st1').innerHTML='E('+T.p+' = '+fmt(v,3)+') = <b>'+fmt(E,4)+' E<sub>h</sub></b>——比精确值高 '+fmt(Z.dE,4)+' E<sub>h</sub>。比值 −V/T = '+fmt(Z.ratio,3)+'（按维里定理，在极小处它等于 2）。'+
    (trial==='slater'?'ζ = 1 处的极小给出<b>精确</b>能量 −0.5：试探函数与真实 1s 一致。':'最优值 α = '+FR(8,'9π')+' ≈ 0.283 给出 E = −'+FR(4,'3π')+' ≈ −0.4244 E<sub>h</sub>，比精确值高 15 %：高斯函数在核处没有尖峰，在大 r 处又衰减得太快。因此基组中同时使用多个高斯函数（第 2 部分）。')}
// ---------- 2. линейный вариационный метод ----------
let NB=3,A0=0.1,BE=4;
async function sec2(){let res,O;try{res=await liveL({N:NB,a0:A0,be:BE});O=await QC.api('var.optcurve',{})}catch(e){return}[...$('nG').children].forEach((b,k)=>b.setAttribute('aria-pressed',k+1===NB));$('a0').value=Math.log10(A0);$('a0V').textContent='α₀ = '+fmt(A0,3);$('be').value=BE;$('beV').textContent='β = '+fmt(BE,2);
  const Es=res.Es;
  let sv=$('nSvg');sv.innerHTML='';const W=520,H=280,L=60,R=14,T=30,B=34,pw=W-L-R,ph=H-T-B;const lo=-7,hi=0;
  const sx=k=>L+(k-0.5)/10*pw,sy=e=>{const v=Math.log10(Math.max(1e-7,e+0.5));return T+ph*(hi-v)/(hi-lo)};
  axes(sv,W,H,L,R,T,B,Array.from({length:10},(_,k)=>[sx(k+1),String(k+1)]),[0,-1,-2,-3,-4,-5,-6,-7].map(v=>[T+ph*(hi-v)/(hi-lo),'10'+String(v).replace('-','⁻').replace(/\d/,d=>'⁰¹²³⁴⁵⁶⁷⁸⁹'[d])]),'N','E − E₀, Eₕ');
  el('line',{x1:L,y1:sy(-0.5+0.0016),x2:L+pw,y2:sy(-0.5+0.0016),stroke:tok('--ok'),'stroke-dasharray':'6 4','stroke-width':1.4},sv);el('text',{x:L+pw-4,y:sy(-0.5+0.0016)-5,'text-anchor':'end','font-size':11,fill:tok('--ok')},sv,'1 kcal/mol');
  el('path',{d:pathOf(Es.map((e,k)=>[sx(k+1),sy(e)])),fill:'none',stroke:tok('--accent'),'stroke-width':1.8},sv);
  Es.forEach((e,k)=>el('circle',{cx:sx(k+1),cy:sy(e),r:k+1===NB?6:3.5,fill:k+1===NB?tok('--warn'):tok('--accent')},sv));
  el('path',{d:pathOf(O.map((o,k)=>[sx(k+1),sy(o.E)])),fill:'none',stroke:tok('--ok'),'stroke-width':1.6,'stroke-dasharray':'4 3'},sv);O.forEach((o,k)=>el('rect',{x:sx(k+1)-3,y:sy(o.E)-3,width:6,height:6,fill:tok('--ok')},sv));
  // функция
  sv=$('wSvg');sv.innerHTML='';const rx=4,ym=Math.max(0.62,Math.max(...res.phi)*1.05);const sx2=r=>L+r/rx*pw,sy2=v=>T+ph*(1-v/ym);
  axes(sv,W,H,L,R,T,B,[0,1,2,3,4].map(r=>[sx2(r),String(r)]),(()=>{const st=ym>1.6?0.5:0.2,a=[];for(let v=0;v<=ym+1e-9;v+=st)a.push(+v.toFixed(2));return a})().map(v=>[sy2(v),fmt(v,1)])/* the ticks follow the top of the axis */,'r, a₀','φ');
  const rr=res.r;
  el('path',{d:pathOf(rr.map((r,i)=>[sx2(r),sy2(res.exact[i])])),fill:'none',stroke:tok('--ok'),'stroke-width':2,'stroke-dasharray':'6 4'},sv);
  el('path',{d:pathOf(rr.map((r,i)=>[sx2(r),sy2(res.phi[i])])),fill:'none',stroke:tok('--accent'),'stroke-width':2.4},sv);
  const ex=res.exn;
  $('rootTab').innerHTML='<table class="mtab"><thead><tr><th class="l">根</th><th>E（基组），E<sub>h</sub></th><th>精确（ns 能级）</th><th>差值</th></tr></thead><tbody>'+
    res.E.slice(0,Math.min(4,res.E.length)).map((e,k)=>'<tr><td class="l">'+(k+1)+'</td><td>'+fmt(e,5)+'</td><td>'+fmt(ex[k],5)+' ('+(k+1)+'s)</td><td>'+(res.diff[k]>-1e-9?'+':'')+fmt(res.diff[k],5)+'</td></tr>').join('')+'</tbody></table>';
  const err=res.err;
  $('st2').innerHTML='N = '+NB+': E = <b>'+fmt(res.E[0],5)+' E<sub>h</sub></b>，误差 '+fmt(res.errm,2)+' mE<sub>h</sub>（'+fmt(res.errk,2)+' kcal/mol）。'+
    '随着 N 增大，能量只会降低，并从上方逼近 −0.5。在核附近 φ 仍是光滑的：精确函数的“尖峰”（尖点）无法用高斯函数再现，只能用越来越窄的函数去逼近。'+
    (res.dropped?' <b>基组近乎线性相关</b>：舍去了 '+res.dropped+' 个函数组合。':'')+(res.E.length>1&&res.E[1]<0?' 只有当基组中含有足够弥散的函数（小 α）时，第二个根才近似 2s 能级。':'')}
async function optimize(){let r;try{r=await QC.api('var.optimize',{N:NB,a0:A0,be:BE})}catch(e){return}A0=r.a0;BE=r.be;sec2()}
// ---------- 3. теория возмущений ----------
let lvl=0,lam=0.1;
async function sec3(){let P;try{P=await liveP({lam,n:lvl})}catch(e){return}[...$('lvG').children].forEach((b,k)=>b.setAttribute('aria-pressed',k===lvl));$('lam').value=lam;$('lamV').textContent='λ = '+fmt(lam,3);const n=lvl;
  $('ptF').innerHTML='E<sup>(0)</sup> = n + ½ = '+fmt(n+0.5,1)+'&nbsp;&nbsp;·&nbsp;&nbsp;E<sup>(1)</sup> = λ⟨n|x⁴|n⟩ = '+FR('3λ',4)+'(2n² + 2n + 1) = '+fmt(P.E1,2)+'λ&nbsp;&nbsp;·&nbsp;&nbsp;E<sup>(2)</sup> = −Σ<sub>k≠n</sub>'+FR('λ²|⟨k|x⁴|n⟩|²','E<sub>k</sub> − E<sub>n</sub>')+' = −'+FR('λ²',8)+'(34n³ + 51n² + 59n + 21) = '+fmt(P.E2,3)+'λ²';
  let sv=$('ptSvg');sv.innerHTML='';const W=520,H=300,L=50,R=14,T=30,B=34,pw=W-L-R,ph=H-T-B;const lmax=0.5;
  const ls=P.ls,ex=P.ex,p1=P.p1,p2=P.p2;
  const lo=n+0.5-0.1*(n+1),hi=Math.max(...p1)*1.02;const sx=l=>L+l/lmax*pw,sy=e=>T+ph*(hi-e)/(hi-lo);
  const yt=[];const st=(hi-lo)>3?1:(hi-lo)>1.5?0.5:0.25;for(let e=Math.ceil(lo/st)*st;e<=hi;e+=st)yt.push([sy(e),fmt(e,2)]);
  axes(sv,W,H,L,R,T,B,[0,0.1,0.2,0.3,0.4,0.5].map(l=>[sx(l),fmt(l,1)]),yt,'λ','E');
  el('path',{d:pathOf(ls.map((l,i)=>[sx(l),sy(p1[i])]),[T,T+ph]),fill:'none',stroke:tok('--accent'),'stroke-width':2,'stroke-dasharray':'6 4'},sv);
  el('path',{d:pathOf(ls.map((l,i)=>[sx(l),sy(p2[i])]),[T,T+ph]),fill:'none',stroke:tok('--warn'),'stroke-width':2.2},sv);
  el('path',{d:pathOf(ls.map((l,i)=>[sx(l),sy(ex[i])]),[T,T+ph]),fill:'none',stroke:tok('--ink'),'stroke-width':2.4},sv);
  el('line',{x1:sx(lam),y1:T,x2:sx(lam),y2:T+ph,stroke:tok('--muted'),'stroke-dasharray':'3 3'},sv);
  // потенциал
  sv=$('vSvg');sv.innerHTML='';const xr=3.5,vmax=6;const sx2=x=>L+(x+xr)/(2*xr)*pw,sy2=v=>T+ph*(1-v/vmax);
  axes(sv,W,H,L,R,T,B,[-3,-2,-1,0,1,2,3].map(x=>[sx2(x),String(x).replace('-','−')]),[0,2,4,6].map(v=>[sy2(v),String(v)]),'x','E');
  const xs=P.xs;
  el('path',{d:pathOf(xs.map((x,i)=>[sx2(x),sy2(P.V0[i])]),[T,T+ph]),fill:'none',stroke:tok('--muted'),'stroke-width':1.4,'stroke-dasharray':'5 4'},sv);
  el('path',{d:pathOf(xs.map((x,i)=>[sx2(x),sy2(P.V[i])]),[T,T+ph]),fill:'none',stroke:tok('--accent'),'stroke-width':2.4},sv);
  for(let k=0;k<P.lev.length;k++){const [e,xt]=P.lev[k];
    el('line',{x1:sx2(-xt),y1:sy2(e),x2:sx2(xt),y2:sy2(e),stroke:k===n?tok('--warn'):tok('--ink'),'stroke-width':k===n?2.6:1.4},sv);el('text',{x:sx2(xt)+6,y:sy2(e)+4,'font-size':11,fill:tok('--muted')},sv,'n = '+k)}
  const e=P.e,q1=P.q1,q2=P.q2;
  $('ptTab').innerHTML='<table class="mtab"><thead><tr><th class="l">量</th><th>数值</th><th>误差</th></tr></thead><tbody>'+
    '<tr><td class="l">E<sup>(0)</sup></td><td>'+fmt(n+0.5,5)+'</td><td>'+fmt(P.d0,5)+'</td></tr>'+
    '<tr><td class="l">E<sup>(0)</sup> + E<sup>(1)</sup></td><td>'+fmt(q1,5)+'</td><td>'+fmt(P.d1,5)+'</td></tr>'+
    '<tr><td class="l">E<sup>(0)</sup> + E<sup>(1)</sup> + E<sup>(2)</sup></td><td>'+fmt(q2,5)+'</td><td>'+fmt(P.d2,5)+'</td></tr>'+
    '<tr><td class="l">精确（对角化）</td><td>'+fmt(e,5)+'</td><td>—</td></tr></tbody></table>';
  const r1=P.r1,r2=P.r2;
  $('st3').innerHTML=(lam===0?'λ = 0 时所有修正均为零。':r2<r1?'二阶改善了结果：误差 '+fmt(r2,5)+' 对比 '+fmt(r1,5)+'（一阶）。':'<b>二阶已经比一阶更差</b>：在这样的 λ 下修正不再是小量，微扰级数发散。')+
    '一阶修正就是微扰在未微扰态中的平均值。基态的二阶修正总是负的。MP2 方法也是这样构造的：Ĥ₀ 是 Fock 算符之和，微扰是精确电子间排斥与其平均场之差，而 E<sup>(2)</sup> 给出关联能。'}
// ---------- управление ----------
Object.entries(TR).forEach(([k,T])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.dataset.t=k;b.innerHTML=T.nm;b.onclick=()=>{trial=k;sec1()};$('tG').appendChild(b)});
$('par').oninput=e=>{const T=TR[trial];par[trial]=T.log?Math.pow(10,+e.target.value):+e.target.value;sec1()};
$('bOpt').onclick=()=>{par[trial]=TR[trial].opt;sec1()};
for(let k=1;k<=10;k++){const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=k;b.onclick=()=>{NB=k;sec2()};$('nG').appendChild(b)}
$('a0').oninput=e=>{A0=Math.pow(10,+e.target.value);sec2()};$('be').oninput=e=>{BE=+e.target.value;sec2()};$('bOpt2').onclick=optimize;
for(let k=0;k<4;k++){const b=document.createElement('button');b.type='button';b.className='chip';b.textContent='n = '+k;b.onclick=()=>{lvl=k;sec3()};$('lvG').appendChild(b)}
$('lam').oninput=e=>{lam=+e.target.value;sec3()};
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{sec1();sec2();sec3()});
sec1();sec2();sec3();
