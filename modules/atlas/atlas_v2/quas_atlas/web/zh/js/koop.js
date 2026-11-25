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
/* Panel «Орбитальные энергии и теорема Купманса» of the SCF page: −ε₁ against ΔSCF and the full
   CI ionisation energy, −ε₂ as an electron affinity (quas_atlas.core.koopmans, endpoint scf.koopmans). */
const EV=27.211386;
const TX={
  mol:{ru:['H₂','HeH⁺'],en:['H₂','HeH⁺'],zh:['H₂','HeH⁺']},
  R:{ru:'бор',en:'bohr',zh:'bohr'},
  th:{ru:['Величина','Eₕ','эВ','что это'],en:['Quantity','E_h','eV','what it is'],zh:['量','E_h','eV','含义']},
  rows:{ru:[['ε₁ (занятая σ)','орбитальная энергия'],['ε₂ (вакантная σ*)','орбитальная энергия'],['ПИ по Купмансу = −ε₁','орбитали «заморожены»'],['ПИ ΔSCF = E(M⁺) − E(RHF)','орбитали катиона релаксируют'],['ПИ «точный в базисе» = E(M⁺) − E(КВ)','корреляция в нейтральной молекуле учтена'],['СЭ по Купмансу = −ε₂','для HF ненадёжно']],
        en:[['ε₁ (occupied σ)','orbital energy'],['ε₂ (virtual σ*)','orbital energy'],['IP, Koopmans = −ε₁','orbitals “frozen”'],['IP, ΔSCF = E(M⁺) − E(RHF)','the cation’s orbital relaxes'],['IP “exact in the basis” = E(M⁺) − E(CI)','correlation of the neutral included'],['EA, Koopmans = −ε₂','unreliable for HF']],
        zh:[['ε₁（占据 σ）','轨道能'],['ε₂（空 σ*）','轨道能'],['库普曼斯电离能 = −ε₁','轨道“冻结”'],['ΔSCF 电离能 = E(M⁺) − E(RHF)','阳离子轨道弛豫'],['“基组内精确”电离能 = E(M⁺) − E(CI)','计入中性分子的相关'],['库普曼斯电子亲和能 = −ε₂','对 HF 不可靠']]},
  note:{ru:(m,rel,cor)=>(m===0?'У H₂ в минимальном базисе форма σ-орбитали задана симметрией, поэтому релаксации нет: ΔSCF совпадает с оценкой Купманса. ':'У HeH⁺ орбиталь катиона перестраивается: релаксация понижает ПИ на <b>'+rel+' эВ</b>. ')+'Корреляция, которой нет в Хартри–Фоке, повышает ПИ на <b>'+cor+' эВ</b>: в нейтральной молекуле два электрона и есть что коррелировать, в катионе — один. Две ошибки противоположны по знаку и частично гасят друг друга, поэтому −ε<sub>ВЗМО</sub> — неплохая оценка вертикального ПИ. Для H₂ опыт: вертикальный ПИ около 16,0 эВ, адиабатический 15,43 эВ.',
        en:(m,rel,cor)=>(m===0?'For H₂ in a minimal basis the shape of the σ orbital is fixed by symmetry, so there is no relaxation: ΔSCF equals the Koopmans estimate. ':'For HeH⁺ the cation’s orbital rearranges: relaxation lowers the IP by <b>'+rel+' eV</b>. ')+'Correlation, missing in Hartree–Fock, raises the IP by <b>'+cor+' eV</b>: the neutral molecule has two electrons to correlate, the cation one. The two errors have opposite signs and partly cancel, which is why −ε<sub>HOMO</sub> is a fair estimate of the vertical IP. For H₂ experiment gives a vertical IP of about 16.0 eV, an adiabatic one of 15.43 eV.',
        zh:(m,rel,cor)=>(m===0?'最小基下 H₂ 的 σ 轨道形状由对称性决定，因此没有弛豫：ΔSCF 与库普曼斯估计相同。':'HeH⁺ 的阳离子轨道发生重排：弛豫使电离能降低 <b>'+rel+' eV</b>。')+'哈特里–福克中缺失的电子相关使电离能升高 <b>'+cor+' eV</b>：中性分子有两个电子可相关，阳离子只有一个。两种误差符号相反、部分抵消，所以 −ε<sub>HOMO</sub> 是垂直电离能的不错估计。H₂ 的实验值：垂直电离能约 16.0 eV，绝热电离能 15.43 eV。'}
};
const MOL=[['H2',1.24,1.24,1.4],['HeH',2.0925,1.24,1.4632]];let m=0;
chips($('kG'),tr(TX.mol),0,i=>{m=i;mark($('kG'),i);$('kR').value=MOL[i][3];draw()});
$('kR').oninput=draw;
const live=QC.live('scf.koopmans');
async function draw(){const R=+$('kR').value,[mol,za,zb]=MOL[m];let Z;try{Z=await live({mol,R,za,zb})}catch(e){return}
  $('kRv').textContent=fmt(R,2)+' '+tr(TX.R);
  const v=[Z.eps[0],Z.eps[1],Z.ip_koop,Z.ip_dscf,Z.ip_fci,Z.ea_koop],h=tr(TX.th),rw=tr(TX.rows);
  $('kTab').innerHTML='<tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr>'+rw.map(([a,b],i)=>'<tr><td>'+a+'</td><td class="mono">'+fmt(v[i],4)+'</td><td class="mono"'+(i===2||i===4?' style="font-weight:600"':'')+'>'+fmt(v[i]*EV,2)+'</td><td>'+b+'</td></tr>').join('');
  $('kNote').innerHTML=tr(TX.note)(m,fmt(Z.relax*EV,2),fmt(Z.corr*EV,2))}
$('kR').value=1.4;draw();

})();
