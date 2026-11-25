/* Atomic terms page (Atlas v2).  Configurations, microstates, the
   (M_L, M_S) table, term extraction, Hund's rules and the ground terms of
   H-Kr come from quas_atlas.core.terms (terms.analyze, terms.element);
   this script builds the tables and texts. */
// ---------- страница «Термы атомов» ----------
const $=id=>document.getElementById(id);
const LL='SPDFGHIKLMNOQ',LN='spdf';
const SUP=s=>String(s).replace(/\d/g,c=>'⁰¹²³⁴⁵⁶⁷⁸⁹'[c]);
const half=x2=>x2%2===0?String(x2/2):'<span class=fr><span>'+x2+'</span><span>2</span></span>';
const halfT=x2=>x2%2===0?String(x2/2):x2+'/2';
const termH=(L,S2,J2)=>'<sup>'+(S2+1)+'</sup>'+LL[L]+(J2!=null?'<sub>'+halfT(J2)+'</sub>':'');
// ---------- configuration analysis: terms.analyze ----------
const ERRT={bad_token:a=>'无法识别“'+a[0]+'”。请写成 d3、p2、2p1 3p1 的形式。',count:a=>''+a[0]+' 亚层中可有 1 到 '+a[1]+' 个电子。',empty:'请输入组态。',duplicate:'相同的亚层请合并书写：例如写 p2，而不是 p1 p1。不同的壳层请注明主量子数：2p1 3p1。',too_many:'微观状态太多——请取不超过 8 个电子。'};
function errText(r){const t=ERRT[r.err];return typeof t==='function'?t(r.a):(t||r.err)}
const cfgName=sh=>sh.map(x=>(x.n||'')+LN[x.l]+SUP(x.N)).join(' ');
// ---------- раздел 1 ----------
let SH=null,MS=null,TB=null,TERMS=[],shown=0,AN=null;
const PRE=['p1','p2','p3','p4','d1','d2','d3','d5','d8','s1 p1','2p1 3p1','s1 d1'];
async function setCfg(s){let r;try{r=await QC.api('terms.analyze',{cfg:s})}catch(e){return false}$('cfgErr').textContent=r.err?errText(r):'';if(r.err)return false;
  SH=r.sh;$('cfgIn').value=s;AN=r;MS={length:r.nmicro};TB={T:r.T,Lm:r.Lm,Sm:r.Sm};TERMS=r.terms;shown=0;
  [...$('cfgG').children].forEach(b=>b.setAttribute('aria-pressed',b.dataset.c===s));render1();return true}
function render1(){const hl=shown>0?new Set(TERMS[shown-1].cells):new Set();const rem=Object.assign({},TB.T);for(let i=0;i<shown-1;i++)TERMS[i].cells.forEach(c=>rem[c]--);
  const S=[];for(let s=TB.Sm;s>=-TB.Sm;s-=2)S.push(s);
  $('tabT').innerHTML='给定 M<sub>L</sub> 和 M<sub>S</sub> 的微观状态数'+(shown?'（已减去 '+(shown-1)+' 个光谱项'+(shown-1===1?'':'')+'；标出的是 '+termH(TERMS[shown-1].L,TERMS[shown-1].S2)+')':'');
  $('mlmsTab').innerHTML='<table class="mtab mlms"><thead><tr><th class="rh">M<sub>L</sub> \\ M<sub>S</sub></th>'+S.map(s=>'<th>'+(s>0?'+':s<0?'−':'')+half(Math.abs(s))+'</th>').join('')+'</tr></thead><tbody>'+
    Array.from({length:2*TB.Lm+1},(_,i)=>TB.Lm-i).map(ml=>'<tr><th class="rh">'+(ml>0?'+':ml<0?'−':'')+Math.abs(ml)+'</th>'+S.map(s=>{const k=ml+'|'+s,v=rem[k]||0;return '<td class="'+(hl.has(k)?'hl':v?'':'z')+'">'+v+'</td>'}).join('')+'</tr>').join('')+'</tbody></table>';
  const parts=SH.map((x,i)=>'C('+2*(2*x.l+1)+', '+x.N+') = '+AN.binom[i]);
  $('nMicro').innerHTML='<span>组态 <b>'+cfgName(SH)+'</b></span><span>微观状态：<b>'+MS.length+'</b>'+(SH.length>1?' = '+AN.binom.join(' × '):'')+'</span><span class="hint">'+parts.join('; ')+'</span>';
  const gr=AN.ground,single=SH.length===1;
  const gi=AN.gi;
  $('termList').innerHTML=TERMS.slice(0,shown).map((t,i)=>{const J=t.J2;
    return '<span class="t'+(i===gi?' g':'')+'">'+termH(t.L,t.S2)+'<small>'+t.mult+' 个微观状态；J = '+J.map(halfT).join(', ')+'</small></span>'}).join('');
  const sum=TERMS.slice(0,shown).reduce((a,t)=>a+t.mult,0);
  $('st1').innerHTML=shown===0?'请点击“标出下一个光谱项”：取最大的 M<sub>L</sub>，并在此条件下取最大的 M<sub>S</sub>——它们就是下一个光谱项的 L 和 S。该光谱项从每个满足 |M<sub>L</sub>| ≤ L 且 |M<sub>S</sub>| ≤ S 的格子中各取走一个微观状态。':
    shown<TERMS.length?'光谱项 '+termH(TERMS[shown-1].L,TERMS[shown-1].S2)+': L = '+TERMS[shown-1].L+', S = '+half(TERMS[shown-1].S2)+'，它取走 (2L + 1)(2S + 1) = '+TERMS[shown-1].mult+' 个微观状态。已计入 '+sum+' / '+MS.length+'.':
    '<b>所有微观状态都已分配：'+sum+' = '+MS.length+'.</b> '+(single?'按洪特规则，基态光谱项为 '+termH(gr.L,gr.S2,gr.J2)+'（绿色标出）。其余光谱项的顺序洪特规则并不能可靠预测。':'对于非等价电子，L 和 S 的所有组合都是允许的。');
  $('bStep').disabled=shown>=TERMS.length}
$('bStep').onclick=()=>{if(shown<TERMS.length){shown++;render1()}};
$('bAll').onclick=()=>{shown=TERMS.length;render1()};
$('bReset').onclick=()=>{shown=0;render1()};
$('cfgGo').onclick=()=>setCfg($('cfgIn').value);$('cfgIn').addEventListener('keydown',e=>{if(e.key==='Enter')setCfg($('cfgIn').value)});
PRE.forEach(c=>{const b=document.createElement('button');b.type='button';b.className='chip';b.dataset.c=c;b.innerHTML=c.split(' ').map(p=>{const m=p.match(/^(\d?)([spdf])(\d+)$/);return m[1]+m[2]+'<sup>'+m[3]+'</sup>'}).join(' ');b.onclick=()=>setCfg(c);$('cfgG').appendChild(b)});
// ---------- раздел 2: элементы H–Kr ----------
const EL='H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr'.split(' ');
function cfgStr(E){return (E.core?'['+E.core+']':'')+E.rest.map(x=>x.n+LN[x.l]+'<sup>'+x.N+'</sup>').join('')}
const liveE=QC.live('terms.element');
let Zsel=26;
async function render2(){const Z=Zsel;let E;try{E=await liveE({Z})}catch(e){return}const op=E.open,g=E.ground;
  [...$('ptab').querySelectorAll('button')].forEach(b=>b.setAttribute('aria-pressed',+b.dataset.z===Z));
  $('elCfg').innerHTML='<span><b>'+EL[Z-1]+'</b> (Z = '+Z+')</span><span>'+cfgStr(E)+'</span>'+(op.length?'<span class="hint">未满亚层：'+op.map(x=>x.n+LN[x.l]+SUP(x.N)).join(', ')+'</span>':'');
  $('boxes').innerHTML=g.closed?'<span class="hint">所有亚层都已填满。</span>':g.boxes.map(b=>{const n=2*b.x.l+1;return '<div class="shell"><div class="row">'+b.occ.map((o,k)=>'<span class="bx">'+(o===2?'↑↓':o===1?'↑':'')+'</span>').join('')+'</div><div class="row">'+Array.from({length:n},(_,k)=>'<span class="ml">'+(b.x.l-k>0?'+':b.x.l-k<0?'−':'')+Math.abs(b.x.l-k)+'</span>').join('')+'</div><div class="hint">'+b.x.n+LN[b.x.l]+SUP(b.x.N)+' · m<sub>l</sub></div></div>'}).join('');
  if(g.closed){$('st2').innerHTML='闭壳层：S = 0，L = 0，J = 0 → <span class="big">'+termH(0,0,0)+'</span>';return}
  const Ssum=g.boxes.map(b=>'('+b.up+' − '+b.dn+')·½').join(' + ');const Ml=g.boxes.map(b=>b.ml).join(' + ');
  $('st2').innerHTML='S = '+Ssum+' = '+half(g.S2)+' → 2S + 1 = <b>'+(g.S2+1)+'</b><br>L = |Σm<sub>l</sub>| = |'+Ml.replace(/-/g,'−')+'| = <b>'+g.L+'</b> ('+LL[g.L]+')<br>J = '+(g.L===0||g.S2===0?'L + S':g.less?'|L − S|，亚层不到半满':g.more?'L + S，亚层超过半满':'S')+' = <b>'+half(g.J2)+'</b><br>基态光谱项：<span class="big">'+termH(g.L,g.S2,g.J2)+'</span>'}
(()=>{const pos=Z=>{if(Z===1)return [1,1];if(Z===2)return [1,18];const per=Z<=10?2:Z<=18?3:4;const st=per===2?3:per===3?11:19;const k=Z-st;
    if(per<4){if(k<2)return [per,k+1];return [per,k+11]}return [per,k+1]};
  const grid=$('ptab');const cells={};for(let Z=1;Z<=36;Z++){const [r,c]=pos(Z);cells[r+'|'+c]=Z}
  for(let r=1;r<=4;r++)for(let c=1;c<=18;c++){const Z=cells[r+'|'+c];if(Z){const b=document.createElement('button');b.type='button';b.textContent=EL[Z-1];b.dataset.z=Z;b.title='Z = '+Z;b.onclick=()=>{Zsel=Z;render2()};grid.appendChild(b)}else grid.appendChild(document.createElement('span'))}})();
$('bToCfg').onclick=async()=>{let E;try{E=await QC.api('terms.element',{Z:Zsel})}catch(e){return}const op=E.open;if(!op.length)return;const s=op.map(x=>(op.length>1?x.n:'')+LN[x.l]+x.N).join(' ');if(await setCfg(s)){$('bAll').click();$('h1s').scrollIntoView({behavior:'smooth'})}};
// ---------- тренажёр ----------
let qz=null;
async function newQ(){let Z,E;try{do{Z=1+Math.floor(Math.random()*36);E=await QC.api('terms.element',{Z})}while((qz&&Z===qz.Z)||!E.open.length)}catch(e){return}qz={Z,g:E.ground};
  $('qEl').innerHTML=EL[Z-1]+' <span class="hint" style="font-family:var(--f-body);font-size:14px">'+cfgStr(E)+'</span>';for(let k=0;k<3;k++){$('q'+k).value='';$('q'+k).className=''}$('qRes').textContent='输入答案并点击“检查”。'}
const pj=s=>{s=String(s).trim().replace(',','.').replace(/\s/g,'');if(/^\d+\/2$/.test(s))return +s.split('/')[0];if(s==='')return NaN;return Math.round(+s*2)};
const pL=s=>{s=String(s).trim().toUpperCase();if(/^\d+$/.test(s))return +s;const i=LL.indexOf(s);return s.length===1&&i>=0?i:NaN};
$('qNew').onclick=newQ;
// «Проверьте себя» с выбором ответа (assets/js/try.*.js, initSelf): правильные ответы для вариантов
window.qcSelf=()=>{const g=qz.g;return [String(g.S2+1),LL[g.L],halfT(g.J2)]};
$('qChk').onclick=()=>{const g=qz.g;const r=[+$('q0').value===g.S2+1,pL($('q1').value)===g.L,pj($('q2').value)===g.J2];
  r.forEach((ok,k)=>$('q'+k).className=$('q'+k).value.trim()===''?'':ok?'ok':'bad');
  $('qRes').innerHTML=r.every(Boolean)?'<b>正确！</b> '+termH(g.L,g.S2,g.J2):'还不完全正确。把未满亚层的电子按 m<sub>l</sub> 格子排布（第 2 部分），求出 S、L 和 J。'};
$('qShow').onclick=()=>{const g=qz.g;$('q0').value=g.S2+1;$('q1').value=LL[g.L];$('q2').value=halfT(g.J2);for(let k=0;k<3;k++)$('q'+k).className='ok';
  $('qRes').innerHTML='基态光谱项 '+EL[qz.Z-1]+': <span class="big">'+termH(g.L,g.S2,g.J2)+'</span> — S = '+half(g.S2)+', L = '+g.L+', J = '+half(g.J2)+'.';Zsel=qz.Z;render2()};
setCfg('p2');render2();newQ();
