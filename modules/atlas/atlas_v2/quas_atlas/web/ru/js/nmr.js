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
/* NMR page (Atlas v2). Larmor frequencies, multiplets and shifts from shieldings come from
   quas_atlas.core.nmr (nmr.larmor, nmr.multiplet, nmr.spectrum, nmr.shifts); this script formats and draws. */
const TX={
  ghz:{ru:'МГц',en:'MHz',zh:'MHz'},hz:{ru:'Гц',en:'Hz',zh:'Hz'},
  B:{ru:'Поле B₀',en:'Field B₀',zh:'磁场 B₀'},ppm1:{ru:'1 ppm для ¹H',en:'1 ppm for ¹H',zh:'¹H 的 1 ppm'},
  larmorNote:{ru:'Сдвиги в ppm от поля не зависят, а расстояния в герцах растут вместе с частотой: на 600 МГц 1 ppm ¹H — 600 Гц, на 60 МГц — 60 Гц. Знак γ у ¹⁵N отрицательный: ядро прецессирует в обратную сторону.',en:'Shifts in ppm do not depend on the field, while distances in hertz grow with the frequency: at 600 MHz 1 ppm of ¹H is 600 Hz, at 60 MHz 60 Hz. The γ of ¹⁵N is negative: the nucleus precesses the other way.',zh:'以 ppm 表示的化学位移与磁场无关，而以赫兹表示的间距随频率增大：600 MHz 时 ¹H 的 1 ppm 为 600 Hz，60 MHz 时为 60 Hz。¹⁵N 的 γ 为负：该核反向进动。'},
  names:{ru:['синглет','дублет','триплет','квартет','квинтет','секстет','септет'],en:['singlet','doublet','triplet','quartet','quintet','sextet','septet'],zh:['单峰','二重峰','三重峰','四重峰','五重峰','六重峰','七重峰']},
  mult:{ru:(n,name,ratio,whz,wppm,f)=>n+' '+(n===1?'эквивалентный сосед':n>1&&n<5?'эквивалентных соседа':'эквивалентных соседей')+' → <b>'+name+'</b>, '+(n+1)+' '+(n===0?'линия':n<4?'линии':'линий')+', интенсивности '+ratio+'. Ширина '+whz+' Гц = <b>'+wppm+' ppm</b> на '+f+' МГц.',
        en:(n,name,ratio,whz,wppm,f)=>n+' equivalent neighbour'+(n===1?'':'s')+' → <b>'+name+'</b>, '+(n+1)+' line'+(n===0?'':'s')+', intensities '+ratio+'. Width '+whz+' Hz = <b>'+wppm+' ppm</b> at '+f+' MHz.',
        zh:(n,name,ratio,whz,wppm,f)=>n+' 个等价相邻核 → <b>'+name+'</b>，'+(n+1)+' 条谱线，强度 '+ratio+'。宽度 '+whz+' Hz = '+f+' MHz 下 <b>'+wppm+' ppm</b>。'},
  calcBad:{ru:'Проверьте строки: в каждой — σ (ppm), число ядер, число соседей и J (Гц) через пробел или точку с запятой.',en:'Check the lines: each holds σ (ppm), the number of nuclei, the number of neighbours and J (Hz), separated by spaces or semicolons.',zh:'请检查各行：每行依次为 σ（ppm）、核数、相邻核数和 J（Hz），用空格或分号分隔。'},
  th:{ru:['№','σ, ppm','δ, ppm','ядер','мультиплет'],en:['#','σ, ppm','δ, ppm','nuclei','multiplet'],zh:['序号','σ, ppm','δ, ppm','核数','多重峰']},
  axis:{ru:'δ, ppm',en:'δ, ppm',zh:'δ, ppm'},
  refUsed:{ru:r=>'δ = σ<sub>эт</sub> − σ, σ<sub>эт</sub> = '+r+' ppm (эталон тем же методом и базисом).',en:r=>'δ = σ<sub>ref</sub> − σ, σ<sub>ref</sub> = '+r+' ppm (the reference with the same method and basis).',zh:r=>'δ = σ<sub>参比</sub> − σ，σ<sub>参比</sub> = '+r+' ppm（参比用相同方法和基组计算）。'},
  scaled:{ru:(m,b)=>'Линейное масштабирование: δ = ('+b+' − σ)/'+m+'.',en:(m,b)=>'Linear scaling: δ = ('+b+' − σ)/'+m+'.',zh:(m,b)=>'线性标定：δ = ('+b+' − σ)/'+m+'。'}
};
const NUC=[['1H','¹H'],['13C','¹³C'],['19F','¹⁹F'],['31P','³¹P'],['15N','¹⁵N']];
const Q={B:9.3947,f:300,n:2,J:7.0};
const FREQ=[60,300,400,600,900];
chips($('fG'),FREQ.map(f=>f+' '+tr(TX.ghz)),2,i=>{Q.B=FREQ[i]/42.577478;$('B').value=Q.B;mark($('fG'),i);larmor()});
$('B').oninput=()=>{Q.B=+$('B').value;mark($('fG'),-1);larmor()};
const liveL=QC.live('nmr.larmor'),liveM=QC.live('nmr.multiplet');
async function larmor(){let Z;try{Z=await liveL({B0:Q.B})}catch(e){return}
  $('Bv').textContent=fmt(Q.B,2)+' T';
  $('lcards').innerHTML=NUC.map(([k,n])=>card(n,fmt(Z.nu[k],2)+' '+tr(TX.ghz))).join('')+card(tr(TX.ppm1),fmt(Z.hz_per_ppm['1H'],0)+' '+tr(TX.hz));
  $('lNote').textContent=tr(TX.larmorNote)}
const MF=[60,300,600];
chips($('mfG'),MF.map(f=>f+' '+tr(TX.ghz)),1,i=>{Q.f=MF[i];mark($('mfG'),i);multi()});
$('n').oninput=()=>{Q.n=+$('n').value;multi()};$('J').oninput=()=>{Q.J=+$('J').value;multi()};
function binom(n){const r=[1];for(let k=1;k<=n;k++)r.push(r[k-1]*(n-k+1)/k);return r}
async function multi(){let Z;try{Z=await liveM({n:Q.n,J:Q.J,nu0:Q.f,delta:0})}catch(e){return}
  $('nv').textContent=Q.n;$('Jv').textContent=fmt(Q.J,1)+' '+tr(TX.hz);
  const svg=$('mchart');svg.innerHTML='';const W=960,H=240,span=0.12;
  const [X,Y]=frame(svg,W,H,[50,20,14,38],[-span,span],[0,1],[-0.1,-0.05,0,0.05,0.1],[],tr(TX.axis),'',true);
  const top=Math.max(...Z.lines.map(l=>l[1]));
  Z.lines.forEach(([x,w])=>{if(Math.abs(x)<=span)el('line',{x1:X(x),x2:X(x),y1:Y(0),y2:Y(w/top*0.9),stroke:tok('--accent'),'stroke-width':3,'stroke-linecap':'round'},svg)});
  const names=tr(TX.names),name=names[Q.n]||(LG==='ru'?(Q.n+1)+' линий':LG==='en'?(Q.n+1)+' lines':(Q.n+1)+' 重峰');
  $('mNote').innerHTML=tr(TX.mult)(Q.n,name,binom(Q.n).join(':'),fmt(Z.width_hz,1),fmt(Z.width_ppm,3),Q.f)}
// ---------- own calculation ----------
const EX={ru:'30.66 3 2 7.0\n28.19 2 3 7.0\n29.27 1 0 0',en:'30.66 3 2 7.0\n28.19 2 3 7.0\n29.27 1 0 0',zh:'30.66 3 2 7.0\n28.19 2 3 7.0\n29.27 1 0 0'};
$('bEx').onclick=()=>{$('cRows').value=tr(EX);$('cRef').value='31.88';$('cScale').checked=false;$('cF').value='400';calc()};
$('bCalc').onclick=calc;
async function calc(){const msg=$('cMsg');const rows=$('cRows').value.split('\n').map(s=>s.trim()).filter(Boolean).map(s=>s.split(/[\s;]+/).map(num));
  const ok=rows.length&&rows.every(r=>r.length>=1&&r.every(isFinite));if(!ok){msg.textContent=tr(TX.calcBad);return}
  const ref=num($('cRef').value),sc=$('cScale').checked,m=num($('cM').value),b=num($('cB').value),f=num($('cF').value);
  if(!isFinite(ref)||!(f>0)||(sc&&(!isFinite(m)||!isFinite(b)||m===0))){msg.textContent=tr(TX.calcBad);return}
  let S,P;try{S=await QC.api('nmr.shifts',{sigmas:rows.map(r=>r[0]),ref,slope:sc?m:-1,intercept:sc?b:null})}catch(e){msg.textContent=String(e.message||e);return}
  const peaks=rows.map((r,i)=>({delta:S.delta[i],count:r[1]>0?r[1]:1,n:Math.round(r[2]||0),J:r[3]||0}));
  const ds=S.delta,lo=Math.min(-0.5,Math.floor(Math.min(...ds)-0.5)),hi=Math.max(10,Math.ceil(Math.max(...ds)+0.5));
  try{P=await QC.api('nmr.spectrum',{peaks,nu0:f,fwhm:1.2,lo,hi,N:2400})}catch(e){msg.textContent=String(e.message||e);return}
  const names=tr(TX.names),h=tr(TX.th);
  msg.innerHTML=(sc?tr(TX.scaled)(fmt(-m,3),fmt(b,2)):tr(TX.refUsed)(fmt(ref,2)))+'<table class="tbl" style="margin-top:6px"><tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr>'+peaks.map((p,i)=>'<tr><td>'+(i+1)+'</td><td>'+fmt(rows[i][0],2)+'</td><td><b>'+fmt(p.delta,2)+'</b></td><td>'+p.count+'</td><td>'+(names[p.n]||p.n+1)+(p.n?', J = '+fmt(p.J,1)+' '+tr(TX.hz):'')+'</td></tr>').join('')+'</table>';
  const svg=$('schart');svg.innerHTML='';svg.hidden=false;const W=960,H=260,step=hi-lo>14?2:1,xt=[];for(let v=Math.ceil(lo);v<=hi;v+=step)xt.push(v);
  const [X,Y]=frame(svg,W,H,[30,20,14,38],[lo,hi],[0,1.05],xt,[],tr(TX.axis),'',true);
  el('path',{d:P.x.map((x,i)=>(i?'L':'M')+X(x).toFixed(1)+' '+Y(P.y[i]).toFixed(1)).join(''),stroke:tok('--accent'),'stroke-width':1.6,fill:'none'},svg)}
function all(){larmor();multi();if($('schart').hidden===false)calc()}
$('B').value=Q.B;all();calc();onTheme(all);  // the example spectrum is shown at once (no empty chart under the form)

/* EPR and NICS panels (2026-11-24): the Fermi contact of hydrogen in Gaussian bases and the field of a π ring current —
   quas_atlas.core.magnetic (nmr.fermi, nmr.ring). */
{
const T2={
  bases:{ru:['одна гауссиана','STO-3G','STO-6G'],en:['one Gaussian','STO-3G','STO-6G'],zh:['单个高斯','STO-3G','STO-6G']},
  rAx:{ru:'r, бор',en:'r, bohr',zh:'r，bohr'},
  fLeg:{ru:['точная 1s: e^{−r}/√π','гауссово приближение'],en:['exact 1s: e^{−r}/√π','Gaussian approximation'],zh:['精确 1s：e^{−r}/√π','高斯近似']},
  fT:{ru:['|ψ(0)|² / точная','A_iso, МГц (точная 1s — ','энергия, хартри (точная −0,5)'],en:['|ψ(0)|² / exact','A_iso, MHz (exact 1s — ','energy, hartree (exact −0.5)'],zh:['|ψ(0)|² / 精确值','A_iso，MHz（精确 1s 为 ','能量，hartree（精确 −0.5）']},
  fNote:{ru:(e)=>'Изотропная сверхтонкая константа — контакт Ферми — пропорциональна спиновой плотности прямо на ядре, значению функции в одной точке. Для точной 1s водорода она около 1423 МГц (опыт 1420,4 МГц — линия 21 см). У гауссовой функции нет каспа: на ядре она слишком плоская. Энергия ошибается всего на '+e+' %, а плотность на ядре — в разы. Поэтому для ЭПР и контактного вклада в J нужны базисы с жёсткими несжатыми s-функциями: EPR-II/III, pcJ. Каждое свойство «смотрит» на свою часть функции: поляризуемость — на хвост, сверхтонкие константы — на точку ядра.',
    en:(e)=>'The isotropic hyperfine constant — the Fermi contact — is proportional to the spin density right at the nucleus, the value of the function at one point. For the exact hydrogen 1s it is about 1423 MHz (experiment 1420.4 MHz — the 21 cm line). A Gaussian has no cusp: it is too flat at the nucleus. The energy is off by only '+e+' %, the density at the nucleus by a factor. Hence EPR and the contact part of J need bases with tight uncontracted s functions: EPR-II/III, pcJ. Each property «looks» at its own part of the function: the polarizability at the tail, hyperfine constants at the nucleus.',
    zh:(e)=>'各向同性超精细常数——费米接触——正比于原子核处的自旋密度，即函数在一点的值。精确氢 1s 约为 1423 MHz（实验 1420.4 MHz——21 cm 谱线）。高斯函数没有尖点：在核处太平。能量误差只有 '+e+' %，而核处密度相差数倍。因此 EPR 和 J 的接触项需要含紧致、未收缩 s 函数的基组：EPR-II/III、pcJ。每种性质“看”函数的不同部分：极化率看尾部，超精细常数看核处。'},
  rings:{ru:['бензол (4n + 2)','циклобутадиен (4n)'],en:['benzene (4n + 2)','cyclobutadiene (4n)'],zh:['苯（4n + 2）','环丁二烯（4n）']},
  dAx:{ru:'расстояние от центра кольца, Å',en:'distance from the ring centre, Å',zh:'离环中心的距离，Å'},nAx:{ru:'NICS, ppm',en:'NICS, ppm',zh:'NICS，ppm'},
  rLeg:{ru:['вдоль оси (над кольцом)','в плоскости кольца'],en:['along the axis (above the ring)','in the plane of the ring'],zh:['沿轴（环上方）','环平面内']},
  rT:{ru:['NICS(0)','NICS(1) — на 1 Å над центром','сдвиг протона кольца от тока','ток'],en:['NICS(0)','NICS(1) — 1 Å above the centre','shift of a ring proton from the current','current'],zh:['NICS(0)','NICS(1)——中心上方 1 Å','环电流引起的环质子位移','电流']},
  cur:{ru:['диатропный — ароматичность','паратропный — антиароматичность','нет'],en:['diatropic — aromaticity','paratropic — antiaromaticity','none'],zh:['抗磁环流——芳香性','顺磁环流——反芳香性','无']},
  rNote:{ru:'Поле, перпендикулярное кольцу, наводит в замкнутой системе π-электронов кольцевой ток, как в витке провода. Его поле внутри кольца и над ним направлено против внешнего — там σ > 0 и NICS = −σ < 0; снаружи в плоскости — по внешнему, и протоны кольца дезэкранированы (у бензола сдвиг 7,3 ppm против 5,3 у этилена). Для 4n электронов ток паратропный, знаки обратные. В [18]аннулене внутренние протоны — около −3 ppm, внешние — +9,3. В центре кольца мешают σ-связи, поэтому чаще берут NICS(1); и одно число — не мера ароматичности: сравнивают в ряду похожих молекул на одном уровне теории.',
    en:'A field perpendicular to the ring induces a ring current in the closed π system, like in a wire loop. Its field inside the ring and above it opposes the external one — there σ > 0 and NICS = −σ < 0; outside, in the plane, it adds to it, and the ring protons are deshielded (benzene 7.3 ppm against 5.3 for ethylene). For 4n electrons the current is paratropic and the signs are reversed. In [18]annulene the inner protons are at about −3 ppm, the outer at +9.3. At the centre of a ring the σ bonds interfere, so NICS(1) is used more often; and one number is not a measure of aromaticity: compare within a series of similar molecules at one level of theory.',
    zh:'垂直于环的磁场在闭合的 π 体系中感生环电流，如同导线圈。其磁场在环内和环上方与外场相反——那里 σ > 0，NICS = −σ < 0；在环外平面内与外场同向，环上质子被去屏蔽（苯 7.3 ppm，乙烯 5.3）。4n 个电子时电流为顺磁性，符号相反。[18]轮烯内侧质子约 −3 ppm，外侧 +9.3。环中心受 σ 键干扰，因此更常用 NICS(1)；单个数值不是芳香性的量度：应在同一理论水平下比较一系列相似分子。'}
};
const Q2={b:1,n:-10,R:1.39,ring:0};let F2=null,R2=null;
const liveF2=QC.live('nmr.fermi'),liveR2=QC.live('nmr.ring');
const sl2=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show();return show};
const lg2=(id,names,colors,dash)=>{$(id).innerHTML=names.map((s,j)=>'<span><i class="sw" style="border-color:'+colors[j]+(dash&&dash[j]?';border-style:dashed':'')+'"></i>'+s+'</span>').join('')};
const tk2=(a,b,s)=>{const o=[];for(let v=Math.ceil(a/s-1e-9)*s;v<=b+1e-9;v+=s)o.push(+v.toFixed(6));return o};
chips($('fG'),tr(T2.bases),Q2.b,i=>{Q2.b=i;mark($('fG'),i);fe()});
const niShow=sl2('ni',v=>{Q2.n=v;ri()},1),rrShow=sl2('rr',v=>{Q2.R=v;ri()},2);
const PRE=[[-10,1.39],[27,1.0]];
chips($('rG'),tr(T2.rings),Q2.ring,i=>{Q2.ring=i;mark($('rG'),i);[Q2.n,Q2.R]=PRE[i];$('ni').value=Q2.n;$('rr').value=Q2.R;niShow();rrShow();ri()});
async function fe(){try{F2=await liveF2({basis:['g1','sto3g','sto6g'][Q2.b]})}catch(e){return}drawF2()}
function drawF2(){if(!F2)return;const ac=tok('--accent'),wr=tok('--warn'),svg=$('fchart');svg.innerHTML='';
  const [X,Y]=frame(svg,960,280,[56,14,22,38],[0,3],[0,0.6],tk2(0,3,0.5),tk2(0,0.6,0.1),tr(T2.rAx),'ψ(r)');
  el('polyline',{points:F2.r.map((r,i)=>X(r)+','+Y(F2.exact[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.6},svg);
  el('polyline',{points:F2.r.map((r,i)=>X(r)+','+Y(F2.approx[i])).join(' '),fill:'none',stroke:wr,'stroke-width':2.4,'stroke-dasharray':'7 4'},svg);
  lg2('fleg',tr(T2.fLeg),[ac,wr],[0,1]);const h=tr(T2.fT);
  $('fcards').innerHTML=card(h[0],fmt(F2.ratio,2))+card(h[1]+fmt(F2.a_exact,0)+(LG==='zh'?'）':')'),fmt(F2.a_iso,0))+card(h[2],fmt(F2.energy,4));
  $('fNote').textContent=tr(T2.fNote)(fmt(100*(F2.energy+0.5)/0.5,1))}
async function ri(){try{R2=await liveR2({nics0:Q2.n,R:Q2.R})}catch(e){return}drawR2()}
function drawR2(){if(!R2)return;const ac=tok('--accent'),wr=tok('--warn'),ink=tok('--ink'),svg=$('rchart');svg.innerHTML='';
  const m=Math.max(5,Math.ceil(Math.abs(R2.nics0)*1.1/5)*5),yr=[-m,m];
  const [X,Y]=frame(svg,960,300,[56,14,22,38],[0,4],yr,tk2(0,4,0.5),tk2(-m,m,m>20?10:5),tr(T2.dAx),tr(T2.nAx));
  el('line',{x1:X(0),x2:X(4),y1:Y(0),y2:Y(0),stroke:ink,'stroke-width':1},svg);
  el('polyline',{points:R2.z.map((z,i)=>X(z)+','+Y(R2.axis[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.6},svg);
  let seg=[];const put=()=>{if(seg.length>1)el('polyline',{points:seg.join(' '),fill:'none',stroke:wr,'stroke-width':2.6},svg);seg=[]};
  R2.rho.forEach((r,i)=>{const v=R2.plane[i];if(v==null||v<yr[0]||v>yr[1])put();else seg.push(X(r)+','+Y(v))});put();
  [[R2.R,'R'],[R2.proton.rho,'H']].forEach(([x,t])=>{el('line',{x1:X(x),x2:X(x),y1:Y(yr[0]),y2:Y(yr[1]),stroke:tok('--line'),'stroke-width':1.4,'stroke-dasharray':'3 4'},svg);el('text',{x:X(x)+4,y:Y(yr[1])+14,class:'lab'},svg,t)});
  lg2('rleg',tr(T2.rLeg),[ac,wr]);const h=tr(T2.rT),c=R2.nics0<0?0:R2.nics0>0?1:2;
  $('rcards').innerHTML=card(h[0],fmt(R2.nics0,1)+' ppm')+card(h[1],fmt(R2.nics1,1)+' ppm')+card(h[2],(R2.proton.dshift>0?'+':'')+fmt(R2.proton.dshift,1)+' ppm')+card(h[3],tr(T2.cur)[c]);
  $('rNote').textContent=tr(T2.rNote)}
fe();ri();onTheme(()=>{drawF2();drawR2()});
}
