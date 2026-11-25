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
/* Walsh diagram page (Atlas v2). Orbital energies of AH₂ against the H–A–H angle, the Walsh energy
   for the chosen number of valence electrons and the predicted angle come from quas_atlas.core.walsh
   (walsh.diagram); this script draws them. */
const TX={
  mols:{ru:['BeH₂ (4)','BH₂ (5)','CH₂ (6)','NH₂ (7)','H₂O (8)'],en:['BeH₂ (4)','BH₂ (5)','CH₂ (6)','NH₂ (7)','H₂O (8)'],zh:['BeH₂ (4)','BH₂ (5)','CH₂ (6)','NH₂ (7)','H₂O (8)']},
  axis:{ru:'угол H–A–H, °',en:'H–A–H angle, °',zh:'H–A–H 角，°'},ev:{ru:'ε, эВ',en:'ε, eV',zh:'ε，eV'},
  sum:{ru:'Σ nε, эВ (энергия Уолша)',en:'Σ nε, eV (Walsh energy)',zh:'Σ nε，eV（沃尔什能量）'},
  exp:{ru:['180° (линейная)','131°','102° (синглет), 134° (триплет)','103°','104,5°'],en:['180° (linear)','131°','102° (singlet), 134° (triplet)','103°','104.5°'],zh:['180°（直线形）','131°','102°（单重态）、134°（三重态）','103°','104.5°']},
  cards:{ru:['валентных электронов','угол по модели','угол в опыте','занятые орбитали'],en:['valence electrons','model angle','experimental angle','occupied orbitals'],zh:['价电子数','模型角度','实验角度','占据轨道']},
  note:{ru:(ne,b)=>ne===4?'Четыре электрона занимают 1a₁ и 1b₂. 1b₂ (из σᵤ) при изгибе поднимается — молекула линейна, как BeH₂ в газе.':ne===5?'Пятый электрон попадает на 2a₁ — орбиталь, которая при изгибе сильно опускается (в линейной молекуле это одна из πᵤ, при изгибе к ней подмешивается s). Одного электрона хватает, чтобы молекула изогнулась.':'Пара электронов на 2a₁ изгибает молекулу сильнее; 1b₁ (p ⟂ плоскости) от угла не зависит, поэтому седьмой и восьмой электроны (NH₂, H₂O) угол почти не меняют. Модель даёт '+b+'°; в опыте угол H₂O 104,5° — модель не учитывает отталкивания электронов и считает связи жёсткими.',
        en:(ne,b)=>ne===4?'Four electrons fill 1a₁ and 1b₂. 1b₂ (from σᵤ) rises on bending — the molecule is linear, like gaseous BeH₂.':ne===5?'The fifth electron goes into 2a₁ — the orbital that drops a lot on bending (one of the πᵤ in the linear molecule; on bending it mixes with s). One electron is enough to bend the molecule.':'A pair of electrons in 2a₁ bends the molecule more; 1b₁ (p perpendicular to the plane) does not depend on the angle, so the seventh and eighth electrons (NH₂, H₂O) hardly change it. The model gives '+b+'°; experiment gives 104.5° for H₂O — the model ignores electron repulsion and keeps the bonds rigid.',
        zh:(ne,b)=>ne===4?'四个电子占据 1a₁ 和 1b₂。1b₂（来自 σᵤ）弯曲时升高——分子为直线形，如气态 BeH₂。':ne===5?'第五个电子进入 2a₁——弯曲时大幅下降的轨道（在直线形分子中是 πᵤ 之一，弯曲时与 s 混合）。一个电子就足以使分子弯曲。':'2a₁ 上的一对电子使分子更弯；1b₁（垂直于平面的 p）与角度无关，因此第七、第八个电子（NH₂、H₂O）几乎不改变角度。模型给出 '+b+'°；H₂O 的实验值为 104.5°——模型忽略电子排斥并把键长视为固定。'}
};
const NE=[4,5,6,7,8];let k=4;
const COL={'1a1':'--accent','1b2':'--ok','2a1':'--warn','1b1':'--virt','3a1':'--muted','2b2':'--muted'};
const LAB={'1a1':'1a₁','1b2':'1b₂','2a1':'2a₁','1b1':'1b₁','3a1':'3a₁','2b2':'2b₂'};
chips($('mG'),tr(TX.mols),4,i=>{k=i;mark($('mG'),i);draw()});
const live=QC.live('walsh.diagram');
async function draw(){const ne=NE[k];let Z;try{Z=await live({ne})}catch(e){return}
  const svg=$('wchart');svg.innerHTML='';const W=960,H=380;
  const [X,Y]=frame(svg,W,H,[54,80,18,38],[80,180],[-30,0],[80,100,120,140,160,180],[-30,-25,-20,-15,-10,-5,0],tr(TX.axis),tr(TX.ev));
  const labs=[];for(const [lb,es] of Object.entries(Z.orbitals)){const occ=Z.occ[lb]||0,c=tok(COL[lb]||'--muted');
    el('path',{d:Z.theta.map((t,i)=>(i?'L':'M')+X(t).toFixed(1)+' '+Y(Math.max(-30,Math.min(0,es[i]))).toFixed(1)).join(''),stroke:c,'stroke-width':occ?3:1.4,'stroke-dasharray':occ?'':'5 4',fill:'none'},svg);
    labs.push({y:Y(Math.max(-30,Math.min(0,es[es.length-1])))+4,c,t:LAB[lb]+(occ?' ('+occ+')':'')})}
  labs.sort((a,b)=>a.y-b.y);for(let i=1;i<labs.length;i++)if(labs[i].y-labs[i-1].y<14)labs[i].y=labs[i-1].y+14;
  labs.forEach(l=>el('text',{x:X(180)+6,y:l.y,class:'lab',fill:l.c},svg,l.t));
  el('line',{x1:X(Z.best),x2:X(Z.best),y1:Y(0),y2:Y(-30),stroke:tok('--ink'),'stroke-width':1.2,'stroke-dasharray':'2 3'},svg);
  const s2=$('echart');s2.innerHTML='';const lo=Math.min(...Z.E),hi=Math.max(...Z.E),pad=(hi-lo)*0.08||1;
  const [X2,Y2]=frame(s2,W,200,[54,80,14,38],[80,180],[lo-pad,hi+pad],[80,100,120,140,160,180],[],tr(TX.axis),tr(TX.sum));
  el('path',{d:Z.theta.map((t,i)=>(i?'L':'M')+X2(t).toFixed(1)+' '+Y2(Z.E[i]).toFixed(1)).join(''),stroke:tok('--accent'),'stroke-width':2.4,fill:'none'},s2);
  el('circle',{cx:X2(Z.best),cy:Y2(Math.min(...Z.E)),r:6,fill:tok('--accent'),stroke:tok('--panel'),'stroke-width':2},s2);
  const h=tr(TX.cards),occ=Object.entries(Z.occ).map(([l,n])=>LAB[l]+(n===2?'²':'¹')).join(' ');
  $('wcards').innerHTML=card(h[0],String(ne))+card(h[1],fmt(Z.best,0)+'°')+card(h[2],tr(TX.exp)[k])+card(h[3],occ);
  $('wNote').textContent=tr(TX.note)(ne,fmt(Z.best,0))}
draw();onTheme(draw);
