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
/* Panel «Приводимое представление и SALC» of the symmetry page: the permutation representation of
   the ligand σ orbitals, the reduction formula with its terms, the SALCs from projection operators
   (quas_atlas.core.salc, endpoint sym.salc). */
const TX={
  mol:{ru:['H₂O · C<sub>2v</sub>','NH₃ · C<sub>3v</sub>','BF₃ · D<sub>3h</sub>','CH₄ · T<sub>d</sub>','[PtCl₄]²⁻ · D<sub>4h</sub>','SF₆ · O<sub>h</sub>']},
  lig:{ru:['1s атомов H','1s атомов H','σ-орбитали F','1s атомов H','σ-орбитали Cl','σ-орбитали F'],en:['1s of the H atoms','1s of the H atoms','σ orbitals of F','1s of the H atoms','σ orbitals of Cl','σ orbitals of F'],zh:['H 原子的 1s','H 原子的 1s','F 的 σ 轨道','H 原子的 1s','Cl 的 σ 轨道','F 的 σ 轨道']},
  gam:{ru:'Γ (лиганды на месте)',en:'Γ (ligands left in place)',zh:'Γ（不动的配体数）'},
  red:{ru:'Формула редукции',en:'Reduction formula',zh:'约化公式'},
  sum:{ru:(g,s)=>'Γ = '+s+' (группа '+g+')',en:(g,s)=>'Γ = '+s+' (group '+g+')',zh:(g,s)=>'Γ = '+s+'（点群 '+g+'）'},
  salc:{ru:'SALC: P̂<sup>Γ</sup>φ₁ = <span class=fr><span>d</span><span>h</span></span> Σ<sub>R</sub> χ(R) R̂φ₁, затем ортонормировка',en:'SALC: P̂<sup>Γ</sup>φ₁ = <span class=fr><span>d</span><span>h</span></span> Σ<sub>R</sub> χ(R) R̂φ₁, then orthonormalisation',zh:'SALC：P̂<sup>Γ</sup>φ₁ = <span class=fr><span>d</span><span>h</span></span> Σ<sub>R</sub> χ(R) R̂φ₁，再正交归一化'},
  note:{ru:(n,l)=>'Базис — '+n+' '+l+' (φ₁…φ'+'₀₁₂₃₄₅₆₇₈₉'[n]+'). Характер Γ для операции — число лигандов, которые она оставляет на месте: орбиталь, переставленная на другой атом, вклада в след матрицы не даёт. Центральный атом может образовать σ-связи только орбиталями тех же неприводимых представлений, что и SALC.',
        en:(n,l)=>'Basis: '+n+' '+l+' (φ₁…φ'+'₀₁₂₃₄₅₆₇₈₉'[n]+'). The character of Γ for an operation is the number of ligands it leaves in place: an orbital moved to another atom adds nothing to the trace. The central atom can form σ bonds only with its orbitals of the same irreducible representations as the SALCs.',
        zh:(n,l)=>'基：'+n+' 个'+l+'（φ₁…φ'+n+'）。某操作下 Γ 的特征标等于该操作不移动的配体数：被移到其他原子上的轨道对矩阵迹没有贡献。中心原子只能用与 SALC 同属一个不可约表示的轨道形成 σ 键。'},
  conv:{ru:'C₂ᵥ: молекула в плоскости yz (ось x перпендикулярна плоскости), поэтому 1s атомов H дают B₂; при молекуле в плоскости xz получится B₁.',en:'C₂ᵥ: the molecule lies in the yz plane (x perpendicular to it), so the H 1s give B₂; with the molecule in the xz plane it would be B₁.',zh:'C₂ᵥ：分子位于 yz 平面（x 轴垂直于分子平面），因此 H 的 1s 给出 B₂；若分子在 xz 平面内则为 B₁。'}
};
const GN={C2v:'C<sub>2v</sub>',C3v:'C<sub>3v</sub>',D3h:'D<sub>3h</sub>',Td:'T<sub>d</sub>',D4h:'D<sub>4h</sub>',Oh:'O<sub>h</sub>'};
const KEYS=['h2o','nh3','bf3','ch4','ptcl4','sf6'];let cur=0;
chips($('salcG'),tr(TX.mol),0,i=>{cur=i;mark($('salcG'),i);draw()});
const SUB='₀₁₂₃₄₅₆₇₈₉';const sub=n=>String(n).split('').map(c=>SUB[+c]).join('');
function coef(c){const v=Math.abs(c),f=[[1,'1'],[1/Math.SQRT2,'1/√2'],[1/Math.sqrt(3),'1/√3'],[0.5,'1/2'],[Math.sqrt(2/3),'√(2/3)'],[1/Math.sqrt(6),'1/√6'],[Math.sqrt(3)/2,'√3/2'],[1/(2*Math.sqrt(3)),'1/(2√3)']].find(([x])=>Math.abs(x-v)<1e-9);return f?f[1]:fmt(v,3)}
async function draw(){let Z;try{Z=await QC.api('sym.salc',{key:KEYS[cur]})}catch(e){return}
  /* in the style of the character table of the page (.ctab): centred numbers with a true minus, the whole row
     of a contained irrep lit, the formulas typeset with fractions and sums as elsewhere in the Atlas */
  const M=x=>String(x).replace('-','−'),FR=(a,b)=>'<span class=fr><span>'+a+'</span><span>'+b+'</span></span>';
  const cls=Z.classes,head='<thead><tr><th class="l">'+GN[Z.group]+'</th>'+cls.map(c=>'<th>'+c.name+'</th>').join('')+'<th>n<sub>i</sub></th></tr></thead>';
  const inG=new Set(Z.reduce.filter(r=>r.n>0).map(r=>r.irrep));
  const rows=Z.table.map(([ir,d,chi])=>'<tr'+(inG.has(ir)?' class="sel"':'')+'><td class="l">'+ir+'</td>'+chi.map(x=>'<td>'+M(x)+'</td>').join('')+'<td><b>'+Z.reduce.find(r=>r.irrep===ir).n+'</b></td></tr>').join('');
  const g='<tr class="gam"><td class="l">'+tr(TX.gam)+'</td>'+Z.gamma.map(x=>'<td>'+M(x)+'</td>').join('')+'<td></td></tr>';
  $('salcTab').innerHTML=head+'<tbody>'+rows+g+'</tbody>';
  const parts=Z.reduce.filter(r=>r.n>0).map(r=>(r.n>1?r.n:'')+r.irrep).join(' + ');
  $('salcRed').innerHTML='<b>'+tr(TX.red)+':</b> n<sub>i</sub> = '+FR(1,'h')+' Σ<sub>c</sub> g<sub>c</sub> χ<sub>Γ</sub>(c) χ<sub>i</sub>(c), h = '+Z.h+'<br>'+Z.reduce.map(r=>'n('+r.irrep+') = '+FR(1,Z.h)+'·('+r.terms.map(M).join(' + ').replace(/\+ −/g,'− ')+') = <b>'+r.n+'</b>').join('<br>')+'<br><b>'+tr(TX.sum)(GN[Z.group],parts)+'</b>';
  const C=c=>{const s=coef(c),m=s.match(/^1\/(.+)$/);return m?FR(1,m[1]):s};
  $('salcList').innerHTML='<b>'+tr(TX.salc)+'</b><br>'+Z.salc.map(s=>{let t='';s.c.forEach((c,k)=>{if(Math.abs(c)<1e-9)return;t+=(t?(c<0?' − ':' + '):(c<0?'−':''))+C(c)+'·φ'+sub(k+1)});return s.irrep+': '+t}).join('<br>');
  $('salcNote').textContent=tr(TX.note)(Z.ligands,tr(TX.lig)[cur])+(cur===0?' '+tr(TX.conv):'');
  pic(Z)}
function pic(Z){const svg=$('salcPic');svg.innerHTML='';const cx=130,cy=100,s=72;const P=Z.positions.map(p=>cur===0?[cx+s*p[1],cy-s*p[2]]:[cx+s*(p[0]-0.42*p[1]),cy-s*(p[2]+0.42*p[1])]);
  const ln=tok('--muted'),ac=tok('--accent');P.forEach(([x,y])=>el('line',{x1:cx,y1:cy,x2:x,y2:y,stroke:ln,'stroke-width':2},svg));
  el('circle',{cx,cy,r:13,fill:tok('--soft'),stroke:ln,'stroke-width':1.5},svg);
  P.forEach(([x,y],k)=>{el('circle',{cx:x,cy:y,r:12,fill:ac},svg);el('text',{x,y:y+4,'text-anchor':'middle',fill:tok('--panel'),'font-size':11,'font-weight':600},svg,String(k+1))})}
draw();onTheme(draw);

})();
