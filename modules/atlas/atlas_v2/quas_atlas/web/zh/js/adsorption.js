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
/* Adsorption and magnetism (Atlas v2): an adsorbate level on a d band (Newns–Anderson, the d-band model of Hammer and
   Nørskov), the Stoner criterion of ferromagnetism, the Hubbard dimer and the DFT+U penalty —
   quas_atlas.core.adsorption (ads.chem, ads.stoner, ads.hubbard). */
const TX={
  U:{ru:{ev:' эВ',mev:' мэВ',mu:' μB'},en:{ev:' eV',mev:' meV',mu:' μB'},zh:{ev:' eV',mev:' meV',mu:' μB'}},
  metals:['Ni','Pd','Pt','Cu','Au','Ag'],mEd:[-1.29,-1.83,-2.25,-2.67,-3.56,-4.30],mW:[4.0,4.5,6.5,3.0,6.0,3.5],
  eAx:{ru:'энергия от уровня Ферми, эВ',en:'energy from the Fermi level, eV',zh:'相对费米能级的能量，eV'},dAx:{ru:'плотность состояний',en:'density of states',zh:'态密度'},
  aLeg:{ru:['d-зона металла','на адсорбате','уровень Ферми','уровни задачи 2 × 2'],en:['d band of the metal','on the adsorbate','Fermi level','levels of the 2 × 2 problem'],zh:['金属 d 带','吸附物上','费米能级','2 × 2 问题的能级']},
  aT:{ru:['энергия связи ΔE','гибридизация с d-зоной','отталкивание Паули','разрыхляющие заполнены на'],en:['bond energy ΔE','hybridization with the d band','Pauli repulsion','antibonding states filled'],zh:['键能 ΔE','与 d 带杂化','泡利排斥','反键态占据']},
  tAx:{ru:'ΔE, эВ',en:'ΔE, eV',zh:'ΔE，eV'},
  aNote:{ru:(f,d)=>'Уровень адсорбата смешивается с d-зоной, как две орбитали в молекуле: снизу — связывающие состояния, сверху — разрыхляющие. Разница с молекулой — число электронов: их задаёт уровень Ферми. Сейчас разрыхляющие заполнены на '+f+' %. '+(d<0?'Связь выгодна: часть разрыхляющих состояний выше уровня Ферми и пуста.':'Связи нет: d-зона глубоко, разрыхляющие состояния заполнены, остаётся отталкивание. Поэтому золото и серебро «благородны».')+' Чем выше центр d-зоны, тем прочнее адсорбция — правило Хаммера и Нёрскова (нижний график). Это корреляция внутри ряда похожих металлов, а не закон природы.',
    en:(f,d)=>'The adsorbate level mixes with the d band like two orbitals of a molecule: bonding states below, antibonding ones above. The difference from a molecule is the number of electrons: the Fermi level sets it. Now the antibonding states are '+f+' % filled. '+(d<0?'The bond pays: part of the antibonding states lies above the Fermi level and is empty.':'There is no bond: the d band is deep, the antibonding states are filled, the repulsion remains. This is why gold and silver are «noble».')+' The higher the centre of the d band, the stronger the adsorption — the rule of Hammer and Nørskov (the lower chart). It is a correlation within a row of similar metals, not a law of nature.',
    zh:(f,d)=>'吸附物能级与 d 带混合，如同分子中的两个轨道：下方为成键态，上方为反键态。与分子的区别在于电子数：由费米能级决定。现在反键态占据 '+f+' %。'+(d<0?'成键有利：部分反键态位于费米能级之上且为空。':'没有成键：d 带很深，反键态被占满，只剩排斥。所以金和银是“惰性的”。')+'d 带中心越高，吸附越强——Hammer–Nørskov 规则（下图）。这是同类金属之间的相关性，而不是自然规律。'},
  sMetals:['Fe','Ni','Pd','Cu'],sPre:[[7.4,4.0,0.93],[9.4,3.2,1.0],[9.5,4.6,0.7],[10,3.0,0.9]],
  mAx:{ru:'магнитный момент m, μB',en:'magnetic moment m, μB',zh:'磁矩 m，μB'},sAx:{ru:'ΔE, мэВ на атом',en:'ΔE, meV per atom',zh:'ΔE，meV/原子'},
  sT:{ru:['N(E<sub>F</sub>) на спин','I·N(E<sub>F</sub>)','момент m','выигрыш энергии'],en:['N(E<sub>F</sub>) per spin','I·N(E<sub>F</sub>)','moment m','energy gained'],zh:['每自旋 N(E<sub>F</sub>)','I·N(E<sub>F</sub>)','磁矩 m','能量降低']},
  per:{ru:' на эВ',en:' per eV',zh:' /eV'},
  sNote:{ru:(p,m,on)=>'Перевернуть спин у части электронов стоит кинетической энергии (им приходится подниматься по зоне), но даёт обменный выигрыш −I m²/4. Ферромагнетизм выгоден, если I·N(E<sub>F</sub>) > 1. Сейчас I·N(E<sub>F</sub>) = '+p+(on?': минимум E(m) не в нуле — металл магнитен, момент '+m+' μB.':': минимум в нуле — металл не магнитен.')+' Велика N(E<sub>F</sub>) у узких зон с уровнем Ферми внутри: так у железа, кобальта, никеля. Палладий «почти» ферромагнетик. В расчёте магнитное решение получают, только задав начальные моменты: немагнитное есть всегда.',
    en:(p,m,on)=>'Turning the spin of some electrons costs kinetic energy (they have to climb the band) but gains the exchange −I m²/4. Ferromagnetism pays when I·N(E<sub>F</sub>) > 1. Now I·N(E<sub>F</sub>) = '+p+(on?': the minimum of E(m) is not at zero — the metal is magnetic, the moment is '+m+' μB.':': the minimum is at zero — the metal is not magnetic.')+' N(E<sub>F</sub>) is large for narrow bands with the Fermi level inside: so it is for iron, cobalt, nickel. Palladium is «almost» a ferromagnet. A calculation finds the magnetic solution only from given starting moments: the non-magnetic one always exists.',
    zh:(p,m,on)=>'翻转部分电子的自旋要付出动能（它们须在能带中上移），但获得交换能 −I m²/4。当 I·N(E<sub>F</sub>) > 1 时铁磁有利。现在 I·N(E<sub>F</sub>) = '+p+(on?'：E(m) 的极小值不在零处——金属是磁性的，磁矩 '+m+' μB。':'：极小值在零处——金属无磁性。')+'费米能级位于其中的窄能带 N(E<sub>F</sub>) 大：铁、钴、镍就是如此。钯“几乎”是铁磁体。计算中只有给定初始磁矩才能得到磁性解：非磁性解总是存在。'},
  uAx:{ru:'U / t',en:'U / t',zh:'U / t'},hAx:{ru:'E / t',en:'E / t',zh:'E / t'},nAx:{ru:'заселённость n',en:'occupation n',zh:'占据数 n'},
  hLeg:{ru:['синглет','триплет','−4t²/U'],en:['singlet','triplet','−4t²/U'],zh:['单重态','三重态','−4t²/U']},
  hT:{ru:['E синглета','J = E<sub>T</sub> − E<sub>S</sub>','4t²/U','доля ионного состояния','E<sub>U</sub> при n = ½','сдвиг занятой / пустой'],en:['E of the singlet','J = E<sub>T</sub> − E<sub>S</sub>','4t²/U','share of the ionic state','E<sub>U</sub> at n = ½','shift of filled / empty'],zh:['单重态 E','J = E<sub>T</sub> − E<sub>S</sub>','4t²/U','离子态份额','n = ½ 时 E<sub>U</sub>','占据 / 空轨道移动']},
  hNote:{ru:(u)=>(u<1?'Малое U: оба электрона на связывающей орбитали, E ≈ −2t — молекула водорода у равновесия. ':u>8?'Большое U: электроны сидят каждый на своём атоме, энергия понижается только виртуальными перескоками, J ≈ 4t²/U — антиферромагнитный обмен, как в растянутой H₂ и в NiO. ':'Промежуточное U: ковалентное и ионное состояния смешаны. ')+'PBE занижает U (ошибка самодействия размазывает электрон), поэтому для оксидов переходных металлов он даёт малую щель или металл. DFT+U возвращает штраф (U/2)·n(1 − n) за дробные заселённости: занятая орбиталь опускается на U/2, пустая поднимается на U/2, щель растёт на U. Энергии с разными U сравнивать нельзя — это разные функционалы.',
    en:(u)=>(u<1?'Small U: both electrons on the bonding orbital, E ≈ −2t — the hydrogen molecule at equilibrium. ':u>8?'Large U: each electron sits on its own atom, the energy goes down only by virtual hops, J ≈ 4t²/U — the antiferromagnetic exchange, as in stretched H₂ and in NiO. ':'A middle U: the covalent and the ionic states are mixed. ')+'PBE underestimates U (the self-interaction error spreads the electron), so for oxides of transition metals it gives a small gap or a metal. DFT+U brings back a penalty (U/2)·n(1 − n) for fractional occupations: a filled orbital goes down by U/2, an empty one up by U/2, the gap grows by U. Energies with different U cannot be compared — they are different functionals.',
    zh:(u)=>(u<1?'U 小：两个电子都在成键轨道上，E ≈ −2t——平衡时的氢分子。':u>8?'U 大：每个电子待在各自原子上，能量只靠虚跃迁降低，J ≈ 4t²/U——反铁磁交换，如拉伸的 H₂ 和 NiO。':'中等 U：共价态与离子态混合。')+'PBE 低估 U（自相互作用误差使电子弥散），所以对过渡金属氧化物给出小带隙或金属。DFT+U 对分数占据加回惩罚 (U/2)·n(1 − n)：占据轨道下移 U/2，空轨道上移 U/2，带隙增大 U。不同 U 的能量不能比较——它们是不同的泛函。'}
};
const Q={metal:2,ea:-2,ed:-2.25,W:6.5,V:2,sm:0,n:7.4,sw:4,I:0.93,U:4,Ue:5};let A=null,S=null,H=null;
const liveA=QC.live('ads.chem'),liveS=QC.live('ads.stoner'),liveH=QC.live('ads.hubbard');
const slider=(id,f,d)=>{const s=$(id);const show=()=>{$(id+'v').textContent=fmt(+s.value,d)};s.oninput=()=>{show();f(+s.value)};show();return v=>{s.value=v;show()}};
const setEa=slider('ea',v=>{Q.ea=v;chem()},2),setEd=slider('ed',v=>{Q.ed=v;chem()},2),setW=slider('ww',v=>{Q.W=v;chem()},1),setV=slider('vv',v=>{Q.V=v;chem()},2);
chips($('mG'),TX.metals,Q.metal,i=>{Q.metal=i;mark($('mG'),i);Q.ed=TX.mEd[i];Q.W=TX.mW[i];setEd(Q.ed);setW(Q.W);chem()});
const setN=slider('nn',v=>{Q.n=v;ston()},1),setSw=slider('sw',v=>{Q.sw=v;ston()},1),setI=slider('si',v=>{Q.I=v;ston()},2);
chips($('sG'),TX.sMetals,Q.sm,i=>{Q.sm=i;mark($('sG'),i);[Q.n,Q.sw,Q.I]=TX.sPre[i];setN(Q.n);setSw(Q.sw);setI(Q.I);ston()});
slider('uu',v=>{Q.U=v;hub()},1);slider('ue',v=>{Q.Ue=v;hub()},1);
const ticks=(lo,hi,n)=>{const r=(hi-lo)/n,p=Math.pow(10,Math.floor(Math.log10(r))),s=[1,2,2.5,5,10].map(k=>k*p).find(k=>k>=r);const t=[];for(let v=Math.ceil(lo/s)*s;v<=hi+1e-9;v+=s)t.push(+v.toFixed(6));return t};
const legend=(id,names,colors)=>{$(id).innerHTML=names.map((s,j)=>'<span><i class="sw" style="border-color:'+colors[j]+'"></i>'+s+'</span>').join('')};
async function chem(){try{A=await liveA({ea:Q.ea,ed:Q.ed,W:Q.W,V:Q.V})}catch(e){return}drawChem()}
function drawChem(){if(!A)return;const ac=tok('--accent'),mu=tok('--muted'),wr=tok('--warn'),svg=$('achart');svg.innerHTML='';
  const top=Math.max(Math.max(...A.pdos),Math.max(...A.band))*1.1||1,lo=A.E[0],hi=A.E[A.E.length-1];
  const [X,Y]=frame(svg,960,300,[56,14,22,38],[lo,hi],[0,top],ticks(lo,hi,7),[],tr(TX.eAx),tr(TX.dAx));
  el('polygon',{points:[X(lo)+','+Y(0)].concat(A.E.map((e,i)=>X(e)+','+Y(A.band[i])),[X(hi)+','+Y(0)]).join(' '),fill:mu,opacity:.22},svg);
  el('polyline',{points:A.E.map((e,i)=>X(e)+','+Y(A.pdos[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg);
  el('line',{x1:X(0),x2:X(0),y1:Y(0),y2:Y(top),stroke:tok('--ink'),'stroke-dasharray':'6 4','stroke-width':1.2},svg);
  el('text',{x:X(0)+4,y:Y(top)+14,class:'lab'},svg).innerHTML='E<tspan baseline-shift="sub" font-size="75%">F</tspan>';
  [A.two.lower,A.two.upper].forEach(e=>{if(e>=lo&&e<=hi)el('line',{x1:X(e),x2:X(e),y1:Y(0),y2:Y(top*0.12),stroke:wr,'stroke-width':3},svg)});
  legend('aleg',tr(TX.aLeg),[mu,ac,tok('--ink'),wr]);
  const h=tr(TX.aT),U=tr(TX.U);
  $('acards').innerHTML=card(h[0],fmt(A.dE,2)+U.ev)+card(h[1],fmt(A.hyb,2)+U.ev)+card(h[2],'+'+fmt(A.pauli,2)+U.ev)+card(h[3],Math.round(100*A.filled_anti)+' %');
  const t=$('tchart');t.innerHTML='';const vals=A.trend.map(m=>m.dE),tl=Math.min(-0.2,...vals)*1.15,th=Math.max(0.2,...vals)*1.15;
  const [TXx,TY]=frame(t,960,200,[56,14,14,30],[0,A.trend.length],[tl,th],[],ticks(tl,th,4),'',tr(TX.tAx));
  A.trend.forEach((m,i)=>{const x0=TXx(i+0.2),x1=TXx(i+0.8),y0=TY(0),y1=TY(m.dE);el('rect',{x:x0,y:Math.min(y0,y1),width:x1-x0,height:Math.abs(y1-y0),fill:m.dE<0?ac:wr,opacity:i===Q.metal&&Math.abs(Q.ed-m.ed)<1e-6?1:.6},t);el('text',{x:(x0+x1)/2,y:200-12,'text-anchor':'middle'},t,m.name)});
  el('line',{x1:TXx(0),x2:TXx(A.trend.length),y1:TY(0),y2:TY(0),stroke:tok('--ink'),'stroke-width':1},t);
  $('aNote').innerHTML=tr(TX.aNote)(Math.round(100*A.filled_anti),A.dE)}
async function ston(){try{S=await liveS({n:Q.n,W:Q.sw,I:Q.I})}catch(e){return}drawSton()}
function drawSton(){if(!S)return;const ac=tok('--accent'),svg=$('schart');svg.innerHTML='';const es=S.E.map(e=>e*1000),lo=Math.min(...es,-1),hi=Math.max(...es,1),mx=S.m[S.m.length-1]||1;
  const [X,Y]=frame(svg,960,300,[64,14,22,38],[0,mx],[lo-(hi-lo)*0.05,hi+(hi-lo)*0.05],ticks(0,mx,6),ticks(lo,hi,5),tr(TX.mAx),tr(TX.sAx));
  el('line',{x1:X(0),x2:X(mx),y1:Y(0),y2:Y(0),stroke:tok('--muted'),'stroke-width':1},svg);
  el('polyline',{points:S.m.map((m,i)=>X(m)+','+Y(es[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg);
  el('circle',{cx:X(S.moment),cy:Y(S.E_min*1000),r:6,fill:tok('--warn')},svg);
  const h=tr(TX.sT),U=tr(TX.U);
  $('scards').innerHTML=card(h[0],fmt(S.N_EF,2)+tr(TX.per))+card(h[1],fmt(S.product,2))+card(h[2],fmt(S.moment,2)+U.mu)+card(h[3],fmt(-S.E_min*1000,0)+U.mev);
  $('sNote').innerHTML=tr(TX.sNote)(fmt(S.product,2),fmt(S.moment,2),S.moment>0.01)}
async function hub(){try{H=await liveH({U:Q.U,Ueff:Q.Ue})}catch(e){return}drawHub()}
function drawHub(){if(!H)return;const ac=tok('--accent'),wr=tok('--warn'),mu=tok('--muted'),svg=$('hchart');svg.innerHTML='';
  const [X,Y]=frame(svg,620,300,[48,14,22,38],[0,20],[-2.2,0.4],[0,5,10,15,20],[-2,-1.5,-1,-0.5,0],tr(TX.uAx),tr(TX.hAx));
  el('polyline',{points:H.U.map((u,i)=>X(u)+','+Y(H.singlet[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},svg);
  el('polyline',{points:H.U.map((u,i)=>X(u)+','+Y(0)).join(' '),fill:'none',stroke:wr,'stroke-width':2.4},svg);
  const asym=H.U.filter(u=>u>=1.8).map(u=>X(u)+','+Y(Math.max(-2.2,-4/u)));el('polyline',{points:asym.join(' '),fill:'none',stroke:mu,'stroke-width':1.4,'stroke-dasharray':'5 4'},svg);
  el('circle',{cx:X(H.at.U),cy:Y(H.at.E_S),r:6,fill:ac},svg);
  legend('hleg',tr(TX.hLeg),[ac,wr,mu]);
  const p=H.plus_u,g=$('pchart');g.innerHTML='';const top=Math.max(0.1,p.half*1.25);
  const [PX,PY]=frame(g,300,300,[40,14,22,38],[0,1],[0,top],[0,0.5,1],ticks(0,top,4),tr(TX.nAx),'');
  el('text',{x:4,y:10},g).innerHTML='E<tspan baseline-shift="sub" font-size="75%">U</tspan>, '+(LG==='ru'?'эВ':'eV');
  el('polyline',{points:p.n.map((n,i)=>PX(n)+','+PY(p.E_U[i])).join(' '),fill:'none',stroke:ac,'stroke-width':2.4},g);
  const h=tr(TX.hT),U=tr(TX.U);
  $('hcards').innerHTML=card(h[0],fmt(H.at.E_S,3)+' t')+card(h[1],fmt(H.at.J,3)+' t')+card(h[2],H.at.J_large_U==null?'—':fmt(H.at.J_large_U,3)+' t')+card(h[3],Math.round(100*H.at.ionic)+' %')
    +card(h[4],fmt(p.half,2)+U.ev)+card(h[5],fmt(p.shift_filled,1)+' / +'+fmt(p.shift_empty,1)+U.ev);
  $('hNote').innerHTML=tr(TX.hNote)(H.at.U)}
chem();ston();hub();onTheme(()=>{drawChem();drawSton();drawHub()});
