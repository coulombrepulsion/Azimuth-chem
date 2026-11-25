/* Normal-vibrations page (Atlas v2).  Force field, Hessian, normal modes, their
   symmetry species and activities, the reduction of Gamma_3N and the quiz
   answers come from quas_atlas.core.vibrations (vib.list, vib.mol); this
   script draws and animates. */
const ruN=(n,a,b,c)=>{n=Math.abs(Math.round(n));const m=n%10,h=n%100;return m===1&&h!==11?a:m>=2&&m<=4&&(h<12||h>14)?b:c};
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const nf=x=>{const r=Math.round(x*1000)/1000;return (Math.abs(r)<1e-9?'0':String(r)).replace('.',',').replace('-','−')};
const FR=(a,b)=>'<span class=fr><span>'+a+'</span><span>'+b+'</span></span>';
function tex2h(t){return t.replace(/\\,/g,' ').replace(/\\sigma/g,'σ').replace(/'/g,'′').replace(/\^(\d)/g,'<sup>$1</sup>').replace(/_([0-9a-z]+)/g,'<sub>$1</sub>').replace(/\(=/g,'(= ')}
const SUB=n=>String(n).replace(/\d/g,d=>'₀₁₂₃₄₅₆₇₈₉'[d]);
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const CORR={D2h:'A<sub>g</sub> → Σ<sub>g</sub><sup>+</sup>; B<sub>1u</sub> → Σ<sub>u</sub><sup>+</sup>; B<sub>2u</sub> + B<sub>3u</sub> → Π<sub>u</sub>; B<sub>2g</sub> + B<sub>3g</sub> → Π<sub>g</sub>',
  C2v:'A<sub>1</sub> → Σ<sup>+</sup>; B<sub>1</sub> + B<sub>2</sub> → Π'};
const GNAME={Dinfh:'D<sub>∞h</sub>',Cinfv:'C<sub>∞v</sub>',C2v:'C<sub>2v</sub>',C3v:'C<sub>3v</sub>',D3h:'D<sub>3h</sub>',Td:'T<sub>d</sub>',Oh:'O<sub>h</sub>',D2h:'D<sub>2h</sub>'};
function act(M,md){return md.act}
const VIEW={h2o:[90,12],h2co:[90,12],nh3:[30,18],bf3:[20,55],ch4:[25,18],sf6:[28,20],co2:[0,12,1],hcn:[0,12,1],c2h2:[0,12,1]};
let MOLS=[],MM=null,mol=0,modes=[],sel=0,cmp=0,play=!RM,amp=0.22,arrows=true,yaw=0,pitch=0,roll=0,ph=0;
const liveM=QC.live('vib.mol');
async function setMol(i){let Z;try{Z=await liveM({m:i})}catch(e){return}mol=i;MM=Z;const M=Z.M;modes=Z.modes;sel=0;cmp=0;const v=VIEW[M.id]||[30,15];yaw=v[0];pitch=v[1];roll=v[2]?90:0;
  [...$('molG').children].forEach((b,k)=>b.setAttribute('aria-pressed',k===i));table();gamma();spec();frame()}
function table(){const M=MM.M;
  $('modeTab').innerHTML='<table class="mtab"><thead><tr><th>№</th><th>ν̃, см⁻¹ (эксп.)</th><th>симметрия</th><th>кратность</th><th>ИК</th><th>КР</th></tr></thead><tbody>'+
    modes.map((md,k)=>{const a=act(M,md);return '<tr class="pick'+(k===sel?' sel':'')+'" data-k="'+k+'" tabindex="0"><td>ν<sub>'+(k+1)+'</sub></td><td>'+(md.nu||'—')+'</td><td>'+md.lab+'</td><td>'+md.deg+'</td><td class="'+(a.ir?'yes':'no')+'">'+(a.ir?'да':'нет')+'</td><td class="'+(a.ra?'yes':'no')+'">'+(a.ra?'да':'нет')+'</td></tr>'}).join('')+'</tbody></table>';
  $('modeTab').querySelectorAll('tr.pick').forEach(tr=>{const f=()=>{sel=+tr.dataset.k;cmp=0;table();frame()};tr.onclick=f;tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();f()}}});
  const md=modes[sel],a=act(M,md);
  $('cmpRow').hidden=md.deg===1;const cg=$('cmpG');cg.innerHTML='';for(let q=0;q<md.deg;q++){const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=q+1;b.setAttribute('aria-pressed',q===cmp);b.onclick=()=>{cmp=q;table();frame()};cg.appendChild(b)}
  let why='';if(M.lin)why=a.ir&&a.ra?'Для C<sub>∞v</sub> типы Σ<sup>+</sup> и Π содержат и компоненты дипольного момента, и квадратичные функции.':a.ir?'Тип '+md.lab+' совпадает с типом '+(md.lab.startsWith('Π')?'(x, y)':'z')+'.':a.ra?'Тип '+md.lab+' совпадает с типом квадратичных функций, но не x, y, z.':'Тип '+md.lab+' не совпадает ни с x, y, z, ни с квадратичными функциями.';
  else{const ir=md.irrep;const L=ir.lin.split('; ').filter(s=>/(^|[^R])[xyz]/.test(s));why=(L.length?'Тип '+md.lab+' преобразуется как '+L.join(', ').replace(/R(?=[xyz])/g,'')+' → ИК-активно. ':'Тип '+md.lab+' не совпадает с x, y, z → в ИК неактивно. ')+(ir.quad?'Ему отвечают квадратичные функции '+ir.quad.replace(/(\w)2/g,'$1²')+' → активно в КР.':'Квадратичных функций этого типа нет → в КР неактивно.')}
  $('st1').innerHTML='<b>ν<sub>'+(sel+1)+'</sub> = '+(md.nu||'—')+' см⁻¹, тип '+md.lab+'</b>'+(md.deg>1?' (вырождено '+(md.deg===2?'дважды':'трижды')+': '+md.deg+' независимых формы с одной частотой)':'')+'. '+why+(M.id==='nh3'&&md.nu===950?' Полоса «зонтичного» колебания NH₃ расщеплена на 932 и 968 см⁻¹ из-за инверсии молекулы.':'')}
function rotM(){const r=Math.PI/180,cy=Math.cos(yaw*r),sy=Math.sin(yaw*r),cp=Math.cos(pitch*r),sp=Math.sin(pitch*r);
  // линейные молекулы: ось z кладём горизонтально; затем yaw вокруг z и pitch вокруг x
  return p=>{let [x,y,z]=p;if(roll)[x,z]=[z,-x];[x,y]=[x*cy-y*sy,x*sy+y*cy];[y,z]=[y*cp-z*sp,y*sp+z*cp];return [x,y,z]}}
const RAD={H:0.20,B:0.30,C:0.30,N:0.30,O:0.31,F:0.30,S:0.40};
function frame(){if(!MM)return;const M=MM.M,sv=$('mv');sv.innerHTML='';const md=modes[sel],v=md.vc[Math.min(cmp,md.vc.length-1)];
  let mx=0;for(let a=0;a<M.at.length;a++)mx=Math.max(mx,Math.hypot(v[3*a],v[3*a+1],v[3*a+2]));const sc=amp/mx;const c=Math.cos(ph);
  const R=rotM();let ext=0;M.at.forEach(a=>ext=Math.max(ext,Math.hypot(a[1],a[2],a[3])));const S=Math.min(190,135/Math.max(ext,0.6)),cx=220,cy=170;
  const P=M.at.map((a,k)=>{const q=[a[1]+sc*c*v[3*k],a[2]+sc*c*v[3*k+1],a[3]+sc*c*v[3*k+2]];const r=R(q);return {x:cx+S*r[0],y:cy-S*r[2],z:r[1],el:a[0],k}});
  const D=M.at.map((a,k)=>{const r0=R([a[1],a[2],a[3]]),r1=R([a[1]+sc*v[3*k],a[2]+sc*v[3*k+1],a[3]+sc*v[3*k+2]]);return [S*(r1[0]-r0[0]),-S*(r1[2]-r0[2])]});
  const ink=tok('--ink'),acc=tok('--warn');
  /* the molecule drawn as in Compass — balls and rods with depth and light (assets/js/ballstick.js,
     the port of Compass's renderer): the bonds show where they go, so the turn of the molecule is clear */
  const lum=c=>{const m=/^#?([0-9a-f]{6})$/i.exec(String(c).trim());if(!m)return 0.5;const n=parseInt(m[1],16);return (0.299*(n>>16)+0.587*(n>>8&255)+0.114*(n&255))/255};
  const R0=P.map(p=>S*RAD[p.el]*(1-0.08*p.z/Math.max(ext,1)));
  let seen=null;if(window.BallStick){const bs=BallStick.scene(P.map((p,i)=>({x:p.x,y:p.y,z:-p.z*S,r:R0[i],c:tok('--a'+p.el)})),M.bonds,{rho:Math.max(2.2,S*0.05)});seen=BallStick.draw(sv,bs.spheres,bs.rods,{fast:play}).visible}
  else{for(const [i,j] of M.bonds){el('line',{x1:P[i].x,y1:P[i].y,x2:P[j].x,y2:P[j].y,stroke:tok('--muted'),'stroke-width':5,'stroke-linecap':'round'},sv)}
    [...P].sort((a,b)=>b.z-a.z).forEach(p=>el('circle',{cx:p.x,cy:p.y,r:R0[p.k],fill:tok('--a'+p.el),stroke:ink,'stroke-width':1.2},sv))}
  P.forEach((p,i)=>{if(seen&&!seen.has(i))return;const r=R0[i],f=tok('--a'+p.el);el('text',{x:p.x,y:p.y+Math.min(15,r*0.95)*0.36,'text-anchor':'middle','font-size':Math.max(9,Math.min(15,r*0.95)),'font-weight':600,fill:lum(f)>0.6?'#1b2230':'#ffffff','pointer-events':'none'},sv,p.el)});
  /* the atom moves both ways — two heads; shorter (the whole displacement there and back) */
  const head=(x,y,ux,uy)=>el('path',{d:`M${x+ux*6},${y+uy*6} L${x-uy*4.5},${y+ux*4.5} L${x+uy*4.5},${y-ux*4.5} Z`,fill:acc},sv);
  P.forEach(p=>{if(arrows){const [dx,dy]=D[p.k];const L=Math.hypot(dx,dy);if(L>4){const ex=p.x+dx*0.9,ey=p.y+dy*0.9,bx=p.x-dx*0.9,by=p.y-dy*0.9,ux=dx/L,uy=dy/L;
      el('line',{x1:bx,y1:by,x2:ex,y2:ey,stroke:acc,'stroke-width':2.4},sv);head(ex,ey,ux,uy);head(bx,by,-ux,-uy)}}});
  el('text',{x:10,y:22,'font-size':15,fill:ink,'font-family':'var(--f-display)'},sv,M.name+'  ·  ν'+SUB(sel+1)+' = '+(md.nu||'—')+' см⁻¹');
  el('text',{x:430,y:332,'text-anchor':'end','font-size':12,fill:tok('--muted')},sv).innerHTML='группа '+GNAME[M.grp].replace(/<sub>/g,'<tspan baseline-shift="sub" font-size="9">').replace(/<\/sub>/g,'</tspan>')}
let last=0;function loop(t){if(play){ph+=(t-last)/1000*2*Math.PI/1.3;frame()}last=t;requestAnimationFrame(loop)}
// сводная таблица Γ3N и приведение
function gamma(){const M=MM.M,gk=MM.gam.gk,G=MM.G;const n=M.at.length;
  const {un,pa,g3,gt,gr}=MM.gam,gv=MM.gam.gv.slice();
  const row=(lab,a,cls)=>'<tr'+(cls?' class="'+cls+'"':'')+'><td>'+lab+'</td>'+a.map(x=>'<td>'+nf(x)+'</td>').join('')+'</tr>';
  $('g3nTab').innerHTML=(M.lin?'<p class="small" style="margin-bottom:6px">Группа '+GNAME[M.grp]+' бесконечна, поэтому считаем в подгруппе '+GNAME[gk]+' (ось z — ось молекулы), а затем переходим к '+GNAME[M.grp]+' по корреляции. Для линейной молекулы вращение вокруг оси молекулы не является степенью свободы, поэтому колебаний 3N − 5.</p>':'')+
    '<table class="mtab g3"><thead><tr><th>'+GNAME[gk]+'</th>'+G.classes.map(c=>'<th>'+(c.n>1?c.n:'')+tex2h(c.tex)+'</th>').join('')+'</tr></thead><tbody>'+
    row('атомов на месте N<sub>R</sub>',un)+row('вклад одного атома χ',pa)+row('Γ<sub>3N</sub> = N<sub>R</sub> · χ',g3)+row('Γ<sub>трансл</sub> (x, y, z)',gt)+row('Γ<sub>вращ</sub> (R<sub>x</sub>, R<sub>y</sub>, R<sub>z</sub>)',M.lin?gr.map(()=>NaN):gr)+row('Γ<sub>кол</sub>',M.lin?gv.map(()=>NaN):gv,'vib')+'</tbody></table>';
  if(M.lin){// для линейной: вращения только вокруг x и y
    const grl=MM.gam.grl,gvl=MM.gam.gvl;
    $('g3nTab').querySelector('tbody').innerHTML=row('атомов на месте N<sub>R</sub>',un)+row('вклад одного атома χ',pa)+row('Γ<sub>3N</sub> = N<sub>R</sub> · χ',g3)+row('Γ<sub>трансл</sub> (x, y, z)',gt)+row('Γ<sub>вращ</sub> (R<sub>x</sub>, R<sub>y</sub>)',grl)+row('Γ<sub>кол</sub>',gvl,'vib');gv.splice(0,gv.length,...gvl)}
  const lines=G.irreps.map((ir,i)=>{const terms=G.classes.map((c,k)=>(c.n>1?c.n+'·':'')+'('+nf(gv[k])+')·('+nf(ir.chi[k])+')');const v=MM.gam.nred[i];
    return 'n('+ir.lab+') = '+FR(1,G.h)+' [ '+terms.join(' + ')+' ] = <b>'+v+'</b>'});
  const res=G.irreps.map((ir,i)=>[MM.gam.nred[i],ir.lab]).filter(x=>x[0]>0).map(x=>(x[0]>1?x[0]:'')+x[1]).join(' + ');
  const nv=MM.gam.nv;
  $('redBox').innerHTML=lines.join('<br>')+'<br><span class="res">Γ<sub>кол</sub> = '+res+'</span> — всего '+nv+' '+ruN(nv,'колебание','колебания','колебаний')+' (3 · '+n+' − '+(M.lin?5:6)+')'+(M.lin?'<br><span class="res">Корреляция '+GNAME[gk]+' → '+GNAME[M.grp]+': '+CORR[gk]+'.</span> Итог: Γ<sub>кол</sub> = '+linSum()+'.':'')}
function linSum(){const c={};modes.forEach(m=>c[m.lab]=(c[m.lab]||0)+1);return Object.entries(c).map(([k,v])=>(v>1?v:'')+k).join(' + ')}
function spec(){if(!MM)return;const M=MM.M,sv=$('spec');sv.innerHTML='';const W=1100,L=70,R=16,x0=0,x1=4000/* as wide as the panel, the labels no longer scaled up twice */,sx=x=>L+(x1-x)/(x1-x0)*(W-L-R);
  const rows=[['ИК',62,'ir'],['КР',132,'ra']];
  for(let x=0;x<=4000;x+=500){el('line',{x1:sx(x),y1:20,x2:sx(x),y2:150,stroke:tok('--line'),'stroke-dasharray':'2 4'},sv);el('text',{x:sx(x),y:170,'text-anchor':'middle','font-size':11,fill:tok('--muted')},sv,String(x))}
  el('text',{x:W-R,y:186,'text-anchor':'end','font-size':11.5,fill:tok('--muted')},sv,'ν̃, см⁻¹');
  let nI=0,nR=0,both=0;
  rows.forEach(([lab,y,key])=>{el('text',{x:8,y:y+4,'font-size':13,fill:tok('--ink')},sv,lab);el('line',{x1:L,y1:y+24,x2:W-R,y2:y+24,stroke:tok('--muted')},sv);
    modes.forEach((md,k)=>{const a=act(M,md);if(!a[key]||!md.nu)return;const h=12+8*md.deg;el('line',{x1:sx(md.nu),y1:y+24,x2:sx(md.nu),y2:y+24-h-12,stroke:k===sel?tok('--warn'):tok('--accent'),'stroke-width':k===sel?3.5:2.5},sv);
      const t=el('text',{x:sx(md.nu),y:y+24-h-16,'text-anchor':'middle','font-size':10.5,fill:tok('--muted')},sv);t.innerHTML='ν'+'<tspan baseline-shift="sub" font-size="8">'+(k+1)+'</tspan>'})});
  modes.forEach(md=>{const a=act(M,md);if(a.ir)nI++;if(a.ra)nR++;if(a.ir&&a.ra)both++});
  const cen=['co2','c2h2','sf6'].includes(M.id);
  $('st3').innerHTML='Полос в ИК: <b>'+nI+'</b>, линий в КР: <b>'+nR+'</b>, совпадающих по частоте: <b>'+both+'</b>. '+(cen?'У '+M.name+' есть центр инверсии: g-колебания видны только в КР, u-колебания — только в ИК (альтернативный запрет).':'Центра инверсии нет, поэтому одно и то же колебание может проявляться и в ИК, и в КР.')+(modes.some(m=>!act(M,m).ir&&!act(M,m).ra)?' Есть «немые» колебания, неактивные в обоих спектрах: '+modes.filter(m=>!act(M,m).ir&&!act(M,m).ra).map(m=>'ν<sub>'+(modes.indexOf(m)+1)+'</sub> ('+m.lab+')').join(', ')+'.':'')}
// тренажёр
let qz=null;
async function newQ(){let k;do{k=Math.floor(Math.random()*MOLS.length)}while(qz&&k===qz.k&&MOLS.length>1);let Z;try{Z=await QC.api('vib.mol',{m:k})}catch(e){return}const M=Z.M,md=Z.modes;
  const ans=Z.ans;
  qz={k,ans,md,M};$('qMol').innerHTML=M.name+' ('+GNAME[M.grp]+')';
  for(let q=0;q<4;q++){$('q'+q).value='';$('q'+q).className=''}$('qRes').textContent='Введите числа и нажмите «Проверить».'}
$('qNew').onclick=newQ;
// «Проверьте себя» с выбором ответа (assets/js/try.*.js, initSelf): правильные ответы для вариантов
window.qcSelf=()=>qz.ans.slice(0,4).map(String);
$('qChk').onclick=()=>{let ok=0;for(let q=0;q<4;q++){const s=$('q'+q).value.trim();const good=s!==''&&+s===qz.ans[q];$('q'+q).className=s===''?'':good?'ok':'bad';if(good)ok++}
  $('qRes').innerHTML=ok===4?'<b>Всё верно!</b>':'Верно '+ok+' из 4. Подсказка: Γ<sub>кол</sub> можно получить в разделе 2, а активность — по столбцам x, y, z и квадратичных функций.'};
$('qShow').onclick=()=>{const M=qz.M;for(let q=0;q<4;q++){$('q'+q).value=qz.ans[q];$('q'+q).className='ok'}
  const c={};qz.md.forEach(m=>c[m.lab]=(c[m.lab]||0)+1);
  $('qRes').innerHTML='Γ<sub>кол</sub> = '+Object.entries(c).map(([k,v])=>(v>1?v:'')+k).join(' + ')+'. Колебаний '+qz.ans[0]+' (3 · '+M.at.length+' − '+(M.lin?5:6)+'), разных частот '+qz.ans[1]+'. ИК: '+(qz.md.filter(m=>act(M,m).ir).map(m=>m.lab).join(', ')||'нет')+'; КР: '+(qz.md.filter(m=>act(M,m).ra).map(m=>m.lab).join(', ')||'нет')+'.'};
// управление
$('bPlay').onclick=()=>{play=!play;$('bPlay').textContent=play?'❚❚ Пауза':'▶ Пуск';if(!play){ph=0;frame()}};
$('amp').value=amp;$('amp').oninput=e=>{amp=+e.target.value;frame()};
$('arr').onchange=e=>{arrows=e.target.checked;frame()};
(()=>{const sv=$('mv');let drag=null;sv.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY,yaw,pitch];sv.setPointerCapture(e.pointerId)});
  sv.addEventListener('pointermove',e=>{if(!drag)return;yaw=drag[2]+(e.clientX-drag[0])*0.6;pitch=Math.max(-89,Math.min(89,drag[3]+(e.clientY-drag[1])*0.6));frame()});
  sv.addEventListener('pointerup',()=>drag=null);sv.addEventListener('pointercancel',()=>drag=null)})();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{frame();spec()});
if(!play)$('bPlay').textContent='▶ Пуск';
(async()=>{try{MOLS=await QC.api('vib.list',{})}catch(e){return}
  MOLS.forEach((M,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.textContent=M.name;b.onclick=()=>setMol(i);$('molG').appendChild(b)});
  await setMol(0);newQ()})();requestAnimationFrame(loop);

/* «стрелки смещений» — an icon toggle (a double arrow) instead of a checkbox with words */
(()=>{const box=document.getElementById('arr'),lab=box&&box.closest('label');if(!lab)return;const name=lab.textContent.trim();
  const b=document.createElement('button');b.type='button';b.className='btn icoB';b.title=name;b.setAttribute('aria-label',name);
  b.innerHTML='<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M4 12h16M7.5 8.5L4 12l3.5 3.5M16.5 8.5L20 12l-3.5 3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const sync=()=>{b.setAttribute('aria-pressed',String(box.checked));b.classList.toggle('primary',box.checked)};
  b.onclick=()=>{box.checked=!box.checked;box.dispatchEvent(new Event('change',{bubbles:true}));sync()};
  lab.hidden=true;lab.after(b);sync()})();
