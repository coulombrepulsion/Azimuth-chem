(() => {
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
/* Panels added to the Hückel page: global reactivity indices χ, η, ω from I and A, Fukui functions
   by finite differences in the Hückel model (react.atoms, react.global, react.fukui); semi-empirical levels and the
   number of two-electron integrals (semi.count). */
const TX={
  th:{ru:['атом','I, эВ','A, эВ','χ, эВ','η, эВ','ω, эВ'],en:['atom','I, eV','A, eV','χ, eV','η, eV','ω, eV'],zh:['原子','I，eV','A，eV','χ，eV','η，eV','ω，eV']},
  gNote:{ru:(c,e,w)=>'χ = (I + A)/2 = <b>'+c+' эВ</b> — электроотрицательность по Малликену, химический потенциал μ = −χ; жёсткость η = (I − A)/2 = <b>'+e+' эВ</b>, мягкость S = 1/(2η); индекс электрофильности ω = χ²/(2η) = <b>'+w+' эВ</b>. Электроны перетекают от низкой χ к высокой, пока химические потенциалы не сравняются; принцип ЖМКО: жёсткие кислоты предпочитают жёсткие основания, мягкие — мягкие.',
         en:(c,e,w)=>'χ = (I + A)/2 = <b>'+c+' eV</b> — the Mulliken electronegativity, chemical potential μ = −χ; hardness η = (I − A)/2 = <b>'+e+' eV</b>, softness S = 1/(2η); electrophilicity index ω = χ²/(2η) = <b>'+w+' eV</b>. Electrons flow from low χ to high χ until the chemical potentials are equal; HSAB principle: hard acids prefer hard bases, soft acids soft bases.',
         zh:(c,e,w)=>'χ = (I + A)/2 = <b>'+c+' eV</b>——马利肯电负性，化学势 μ = −χ；硬度 η = (I − A)/2 = <b>'+e+' eV</b>，软度 S = 1/(2η)；亲电指数 ω = χ²/(2η) = <b>'+w+' eV</b>。电子从 χ 低处流向 χ 高处，直到化学势相等；软硬酸碱原理：硬酸喜硬碱，软酸喜软碱。'},
  bad:{ru:'Нужно I > A, оба в эВ.',en:'I > A is needed, both in eV.',zh:'需要 I > A，单位 eV。'},
  mols:{ru:['бутадиен','акролеин (C=C–C=O)','бензол','пиридин','пиррол','стирол'],en:['butadiene','acrolein (C=C–C=O)','benzene','pyridine','pyrrole','styrene'],zh:['丁二烯','丙烯醛（C=C–C=O）','苯','吡啶','吡咯','苯乙烯']},
  fth:{ru:['атом','f⁺ (нуклеофил)','f⁻ (электрофил)','f⁰ (радикал)','c²(НСМО)','c²(ВЗМО)'],en:['atom','f⁺ (nucleophile)','f⁻ (electrophile)','f⁰ (radical)','c²(LUMO)','c²(HOMO)'],zh:['原子','f⁺（亲核）','f⁻（亲电）','f⁰（自由基）','c²(LUMO)','c²(HOMO)']},
  fNote:{ru:'f⁺ = ρ(N+1) − ρ(N) и f⁻ = ρ(N) − ρ(N−1) здесь посчитаны «честно» — решением для аниона и катиона — и совпадают с плотностями НСМО и ВЗМО: в методе Хюккеля орбитали не перестраиваются при изменении числа электронов. В DFT и HF это уже не так — функции Фукуи учитывают релаксацию. Выделен атом с наибольшим значением в каждом столбце.',
         en:'f⁺ = ρ(N+1) − ρ(N) and f⁻ = ρ(N) − ρ(N−1) are computed “honestly” here, by solving for the anion and the cation, and coincide with the LUMO and HOMO densities: in the Hückel model the orbitals do not change with the number of electrons. In DFT and HF this no longer holds — the Fukui functions include relaxation. The atom with the largest value in each column is highlighted.',
         zh:'这里的 f⁺ = ρ(N+1) − ρ(N) 和 f⁻ = ρ(N) − ρ(N−1) 是“如实”求解阴离子和阳离子得到的，与 LUMO、HOMO 密度相同：休克尔方法中轨道不随电子数变化。在 DFT 和 HF 中情况不同——福井函数包含弛豫。每列最大值所在原子已高亮。'},
  cth:{ru:['уровень','базисных функций','двухэлектронных интегралов'],en:['level','basis functions','two-electron integrals'],zh:['方法层次','基函数','双电子积分']},
  lv:{ru:['ab initio, 6-31G*','ab initio, STO-3G','NDDO (MNDO, AM1, PM3, PM7)','INDO','CNDO','расширенный Хюккель, xtb','Хюккель (π)'],en:['ab initio, 6-31G*','ab initio, STO-3G','NDDO (MNDO, AM1, PM3, PM7)','INDO','CNDO','extended Hückel, xtb','Hückel (π)'],zh:['从头算，6-31G*','从头算，STO-3G','NDDO（MNDO、AM1、PM3、PM7）','INDO','CNDO','扩展休克尔、xtb','休克尔（π）']},
  none:{ru:'нет (параметры)',en:'none (parameters)',zh:'无（参数）'},
  xtb:{ru:'нет явных; заряды и мультиполи',en:'none explicit; charges and multipoles',zh:'无显式积分；电荷与多极'},
  cNote:{ru:'Ab initio-интегралов ∝ N⁴, полуэмпирических — порядка числа пар атомов. NDDO отбрасывает интегралы с произведением функций разных атомов (нулевое дифференциальное перекрывание), а оставшиеся заменяет параметрами, подогнанными под опыт. Поэтому AM1/PM7 и xtb в тысячи раз быстрее DFT и годятся для предоптимизации, поиска конформеров (CREST) и больших систем, но их ошибки непредсказуемы вне обучающего набора.',
         en:'Ab initio integrals grow as N⁴, semi-empirical ones as the number of atom pairs. NDDO drops the integrals with products of functions on different atoms (neglect of diatomic differential overlap) and replaces the rest by parameters fitted to experiment. Hence AM1/PM7 and xtb are thousands of times faster than DFT and suit pre-optimisation, conformer searches (CREST) and large systems, but their errors are unpredictable outside the training set.',
         zh:'从头算积分随 N⁴ 增长，半经验积分约与原子对数成正比。NDDO 舍弃不同原子上函数乘积的积分（忽略双原子微分重叠），其余用拟合实验的参数代替。因此 AM1/PM7 和 xtb 比 DFT 快数千倍，适合预优化、构象搜索（CREST）和大体系，但在训练集之外误差难以预料。'},
  ex:{ru:['бензол C₆H₆','глюкоза C₆H₁₂O₆','холестерин C₂₇H₄₆O','белок, 1000 тяжёлых атомов'],en:['benzene C₆H₆','glucose C₆H₁₂O₆','cholesterol C₂₇H₄₆O','a protein, 1000 heavy atoms'],zh:['苯 C₆H₆','葡萄糖 C₆H₁₂O₆','胆固醇 C₂₇H₄₆O','蛋白质，1000 个重原子']}
};
// ---- global indices ----
let ATOMS=null;
async function glob(){if(!ATOMS){try{ATOMS=await QC.api('react.atoms',{})}catch(e){return}}
  const h=tr(TX.th);let rows='<tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr>';
  for(const [s,I,A] of ATOMS){let g;try{g=await QC.api('react.global',{I,A})}catch(e){continue}
    rows+='<tr><td>'+s+'</td><td class="mono">'+fmt(I,2)+'</td><td class="mono">'+fmt(A,2)+'</td><td class="mono">'+fmt(g.chi,2)+'</td><td class="mono">'+fmt(g.eta,2)+'</td><td class="mono">'+fmt(g.omega,2)+'</td></tr>'}
  $('gTab').innerHTML=rows;own()}
['gI','gA'].forEach(id=>$(id).oninput=own);
async function own(){const I=num($('gI').value),A=num($('gA').value);if(!(isFinite(I)&&isFinite(A)&&I>A)){$('gNote').textContent=tr(TX.bad);return}
  let g;try{g=await QC.api('react.global',{I,A})}catch(e){$('gNote').textContent=tr(TX.bad);return}
  $('gNote').innerHTML=tr(TX.gNote)(fmt(g.chi,2),fmt(g.eta,2),fmt(g.omega,2))}
// ---- Fukui ----
const FM=[[['C','C','C','C'],[[0,1],[1,2],[2,3]],['C1','C2','C3','C4']],
 [['C','C','C','O1'],[[0,1],[1,2],[2,3]],['Cβ','Cα','C (C=O)','O']],
 [['C','C','C','C','C','C'],[[0,1],[1,2],[2,3],[3,4],[4,5],[5,0]],['C1','C2','C3','C4','C5','C6']],
 [['N1','C','C','C','C','C'],[[0,1],[1,2],[2,3],[3,4],[4,5],[5,0]],['N1','C2','C3','C4','C5','C6']],
 [['N2','C','C','C','C'],[[0,1],[1,2],[2,3],[3,4],[4,0]],['N1','C2','C3','C4','C5']],
 [['C','C','C','C','C','C','C','C'],[[0,1],[1,2],[2,3],[3,4],[4,5],[5,0],[0,6],[6,7]],['C1 (ипсо)','C2 (орто)','C3 (мета)','C4 (пара)','C5 (мета)','C6 (орто)','Cα','Cβ']]];
let fm=0;chips($('fG'),tr(TX.mols),0,i=>{fm=i;mark($('fG'),i);fuk()});
async function fuk(){const [t,b,lab]=FM[fm];let Z;try{Z=await QC.api('react.fukui',{types:t,bonds:b})}catch(e){return}
  const cols=[Z.fplus,Z.fminus,Z.f0,Z.fL||[],Z.fH||[]],mx=cols.map(c=>c.length?Math.max(...c):null),h=tr(TX.fth);
  const L=LG==='ru'?lab:lab.map(s=>s.replace(' (ипсо)',' (ipso)').replace(' (орто)',' (ortho)').replace(' (мета)',' (meta)').replace(' (пара)',' (para)'));
  $('fTab').innerHTML='<tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr>'+t.map((_,r)=>'<tr><td>'+L[r]+'</td>'+cols.map((c,k)=>'<td class="mono'+(c.length&&Math.abs(c[r]-mx[k])<1e-6&&k<3?' hi':'')+'">'+(c.length?fmt(c[r],3):'—')+'</td>').join('')+'</tr>').join('');
  $('fNote').textContent=tr(TX.fNote)}
// ---- semi-empirical ----
const EXS=[[6,6],[12,12],[28,46],[1000,1000]];
chips($('sG'),tr(TX.ex),0,i=>{mark($('sG'),i);$('sn').value=EXS[i][0];$('sm').value=EXS[i][1];semi()});
['sn','sm'].forEach(id=>$(id).oninput=()=>{mark($('sG'),-1);semi()});
async function semi(){const cl=v=>Math.max(0,Math.min(5000,Math.round(v)||0)),n=cl(num($('sn').value)),m=cl(num($('sm').value));/* within what the server counts */let Z;try{Z=await QC.api('semi.count',{n,m})}catch(e){return}
  const L=tr(TX.lv),h=tr(TX.cth),R=[[L[0],Z.N_631gs,Z.ab_631gs],[L[1],Z.N_sto3g,Z.ab_sto3g],[L[2],Z.N_val,Z.nddo],[L[3],Z.N_val,Z.indo],[L[4],Z.N_val,Z.cndo],[L[5],Z.N_val,null],[L[6],n,null]];
  $('sTab').innerHTML='<tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr>'+R.map((r,i)=>'<tr><td>'+r[0]+'</td><td class="mono">'+r[1]+'</td><td class="mono">'+(r[2]==null?(i===5?tr(TX.xtb):tr(TX.none)):(i>=2&&i<=4?'≈ ':'')+(r[2]<1e5?String(Math.round(r[2])):sci(r[2],2)))+'</td></tr>').join('');
  $('sNote').textContent=tr(TX.cNote)}
glob();fuk();semi();

})();
