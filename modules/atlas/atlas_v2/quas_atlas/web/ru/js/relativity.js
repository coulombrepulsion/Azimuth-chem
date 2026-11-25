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
/* Heavy elements page (Atlas v2). The hydrogen-like 1s electron (v/c, γ, contraction, Dirac
   energy), its curve over the periodic table and the def2 ECP cores come from quas_atlas.core.relativity
   (rel.atom, rel.curve). */
const SYM=['H','He','Li','Be','B','C','N','O','F','Ne','Na','Mg','Al','Si','P','S','Cl','Ar','K','Ca','Sc','Ti','V','Cr','Mn','Fe','Co','Ni','Cu','Zn','Ga','Ge','As','Se','Br','Kr','Rb','Sr','Y','Zr','Nb','Mo','Tc','Ru','Rh','Pd','Ag','Cd','In','Sn','Sb','Te','I','Xe','Cs','Ba','La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu','Hf','Ta','W','Re','Os','Ir','Pt','Au','Hg','Tl','Pb','Bi','Po','At','Rn','Fr','Ra','Ac','Th','Pa','U','Np','Pu','Am','Cm','Bk','Cf','Es','Fm','Md','No','Lr','Rf','Db','Sg','Bh','Hs','Mt','Ds','Rg','Cn','Nh','Fl','Mc','Lv','Ts','Og'];
const TX={
  v:{ru:'скорость 1s-электрона v/c',en:'speed of the 1s electron v/c',zh:'1s 电子速度 v/c'},g:{ru:'рост массы γ',en:'mass increase γ',zh:'质量增大 γ'},
  r:{ru:'радиус 1s',en:'1s radius',zh:'1s 半径'},enr:{ru:'E(1s) по Шрёдингеру',en:'E(1s), Schrödinger',zh:'E(1s)，薛定谔'},ed:{ru:'E(1s) по Дираку',en:'E(1s), Dirac',zh:'E(1s)，狄拉克'},
  shr:{ru:'сжатие',en:'contraction',zh:'收缩'},deep:{ru:'глубже',en:'deeper',zh:'更深'},
  aNote:{ru:(s,v,c,d)=>s+': 1s-электрон движется со скоростью '+v+' скорости света, его орбиталь сжата на '+c+' %, а уровень на '+d+' % глубже, чем без релятивизма. Сжимаются и стабилизируются все s- и p<sub>1/2</sub>-оболочки, проникающие к ядру, — у золота это 6s, отсюда его цвет и благородство; d- и f-оболочки, лучше экранированные, расширяются.',
         en:(s,v,c,d)=>s+': the 1s electron moves at '+v+' of the speed of light, its orbital is '+c+' % smaller and its level '+d+' % deeper than without relativity. All s and p<sub>1/2</sub> shells that reach the nucleus contract and are stabilised — for gold this is 6s, hence its colour and nobility; the d and f shells, screened better, expand.',
         zh:(s,v,c,d)=>s+'：1s 电子以光速的 '+v+' 运动，其轨道比非相对论情形小 '+c+'%，能级深 '+d+'%。所有能穿透到核附近的 s 和 p<sub>1/2</sub> 壳层都收缩并被稳定——对金来说是 6s，这正是其颜色和惰性的来源；屏蔽较好的 d、f 壳层则膨胀。'},
  axis:{ru:'заряд ядра Z',en:'nuclear charge Z',zh:'核电荷 Z'},rl:{ru:'r(реляв.)/r(нерел.) для 1s',en:'r(rel.)/r(non-rel.) of 1s',zh:'1s 的 r(相对论)/r(非相对论)'},
  ecpT:{ru:['электронов всего','в остове (ECP)','считаются явно'],en:['electrons in all','in the core (ECP)','treated explicitly'],zh:['电子总数','核芯中（ECP）','显式处理']},
  ecpNote:{ru:(s,k,c)=>k==='ECP'?s+': в базисах def2 внутренние '+c+' электронов заменены псевдопотенциалом Штутгарт–Кёльн. Он подогнан к релятивистским расчётам атома, поэтому скалярные релятивистские эффекты уже учтены — отдельный релятивистский гамильтониан не нужен. ORCA и Gaussian подставляют ECP вместе с базисом def2 сами.':k==='all-electron'?s+': в def2 — все электроны, без псевдопотенциала. Релятивистские эффекты здесь малы (несколько процентов в энергии 1s и меньше в валентных свойствах), для энергий реакций ими обычно пренебрегают.':s+': для лантаноидов def2 не задаёт псевдопотенциал на этой странице — возьмите специальные базисы и ECP (например, с 4f-оболочкой в остове) или релятивистский гамильтониан.',
          en:(s,k,c)=>k==='ECP'?s+': in the def2 basis sets the inner '+c+' electrons are replaced by a Stuttgart–Cologne pseudopotential. It is fitted to relativistic atomic calculations, so the scalar relativistic effects are already included — no separate relativistic Hamiltonian is needed. ORCA and Gaussian add the ECP together with a def2 basis themselves.':k==='all-electron'?s+': def2 keeps all electrons, without a pseudopotential. Relativistic effects are small here (a few per cent of the 1s energy, less in valence properties) and are usually neglected for reaction energies.':s+': for the lanthanides def2 gives no pseudopotential on this page — take special basis sets and ECPs (for example with the 4f shell in the core) or a relativistic Hamiltonian.',
          zh:(s,k,c)=>k==='ECP'?s+'：在 def2 基组中，内层 '+c+' 个电子由 Stuttgart–Cologne 赝势代替。赝势拟合自相对论原子计算，因此已包含标量相对论效应——无需另用相对论哈密顿量。ORCA 和 Gaussian 会随 def2 基组自动加入 ECP。':k==='all-electron'?s+'：def2 保留全部电子，不用赝势。这里相对论效应很小（1s 能量的百分之几，价层性质更小），计算反应能时通常忽略。':s+'：本页不给出 def2 对镧系元素的赝势——请使用专门的基组和 ECP（例如 4f 壳层在核芯中）或相对论哈密顿量。'}
};
const Q={Z:79,E:79};
const PZ=[1,6,26,47,53,79,80,82,118];
chips($('zG'),PZ.map(z=>SYM[z-1]+' '+z),5,i=>{Q.Z=PZ[i];$('Z').value=Q.Z;mark($('zG'),i);atom()});
$('Z').oninput=()=>{Q.Z=+$('Z').value;mark($('zG'),PZ.indexOf(Q.Z));atom()};
const EZ=[19,35,37,47,53,55,74,78,79,82,86];
chips($('eG'),EZ.map(z=>SYM[z-1]),8,i=>{Q.E=EZ[i];mark($('eG'),i);ecp()});
const liveA=QC.live('rel.atom'),liveE=QC.live('rel.atom');let CURVE=null;
async function atom(){let Z;try{Z=await liveA({Z:Q.Z})}catch(e){return}const s=SYM[Q.Z-1]+' (Z = '+Q.Z+')';
  $('Zv').textContent=SYM[Q.Z-1]+' '+Q.Z;
  $('acards').innerHTML=card(tr(TX.v),fmt(Z.v,3))+card(tr(TX.g),fmt(Z.gamma,3))+card(tr(TX.r),fmt(Z.r_ratio,3),tr(TX.shr)+' '+fmt((1-Z.r_ratio)*100,1)+' %')
    +card(tr(TX.enr),fmt(Z.E_nr,Q.Z<10?3:1)+' E<sub>h</sub>')+card(tr(TX.ed),fmt(Z.E_dirac,Q.Z<10?3:1)+' E<sub>h</sub>',tr(TX.deep)+' '+fmt((Z.E_ratio-1)*100,Q.Z<20?3:1)+' %');
  $('aNote').innerHTML=tr(TX.aNote)(s,fmt(Z.v,2),fmt((1-Z.r_ratio)*100,0),fmt((Z.E_ratio-1)*100,0));chart(Z)}
async function chart(Z){if(!CURVE){try{CURVE=await QC.api('rel.curve',{})}catch(e){return}}
  const svg=$('rchart');svg.innerHTML='';const W=960,H=280;
  const [X,Y]=frame(svg,W,H,[54,20,22,38],[1,118],[0.5,1.02],[1,20,40,60,80,100,118],[0.5,0.6,0.7,0.8,0.9,1],tr(TX.axis),tr(TX.rl));
  el('path',{d:CURVE.map((c,i)=>(i?'L':'M')+X(c[0]).toFixed(1)+' '+Y(c[1]).toFixed(1)).join(''),stroke:tok('--accent'),'stroke-width':2.4,fill:'none'},svg);
  el('circle',{cx:X(Q.Z),cy:Y(Z.r_ratio),r:6,fill:tok('--accent'),stroke:tok('--panel'),'stroke-width':2},svg);
  [[55,'Cs'],[79,'Au'],[86,'Rn']].forEach(([z,s])=>el('text',{x:X(z),y:Y(CURVE[z-1][1])-10,'text-anchor':'middle',class:'lab'},svg,s))}
async function ecp(){let Z;try{Z=await liveE({Z:Q.E})}catch(e){return}const e=Z.ecp,s=SYM[Q.E-1]+' (Z = '+Q.E+')',h=tr(TX.ecpT);
  $('ecards').innerHTML=card(h[0],String(Q.E))+card(h[1],e.core==null?'—':String(e.core))+card(h[2],e.valence==null?'—':String(e.valence));
  $('eNote').innerHTML=tr(TX.ecpNote)(s,e.kind,e.core)}
function all(){atom();ecp()}
$('Z').value=Q.Z;all();onTheme(all);
