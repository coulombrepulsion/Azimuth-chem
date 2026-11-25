/* Compact guided identification and paired symmetry-operation comparison. */
(()=>{
const L={"title": "Как определить точечную группу — пошаговый алгоритм", "intro": "Рассматривайте молекулу целиком в заданной конформации. Операция должна совместить атомы с атомами того же вида. Алгоритм следует вашим ответам и не проверяет геометрию автоматически.", "step": "Шаг", "yes": "Да", "no": "Нет", "back": "Назад", "restart": "Начать заново", "next": "Далее", "n": "Порядок оси n:", "result": "По вашим ответам:", "resultNote": "Проверьте результат на модели: все операции группы должны совмещать молекулу с самой собой. При ошибке вернитесь к предыдущему вопросу.", "compareTitle": "Сравнить операции до и после изменения", "compareIntro": "Одна и та же операция применяется к исходной и изменённой модели. Поверните любую из двух моделей мышью или пальцем — ракурс изменится у обеих.", "filter": "Показать:", "all": "Все операции", "kept": "сохранилась", "lost": "исчезла", "operation": "Операция:", "run": "Выполнить на обеих моделях", "reset": "В начало", "progress": "Ход операции:", "before": "Исходная модель", "after": "После изменения", "keepStatus": "Сохранилась: в конце операции обе модели совпадают сами с собой.", "lostStatus": "Исчезла: исходная модель совпадает сама с собой, изменённая — нет.", "empty": "Таких операций нет. Выберите другой фильтр.", "legend": "Пунктирные контуры — исходные положения атомов. Красная обводка и × в конце операции — атом не совпал с атомом того же вида. Проверяется совпадение в пространстве, а не только на проекции. Анимация показывает математическое преобразование, а не физическое движение атомов.", "atEnd": "В конце операции:", "mismatch": "не совпадут {count} из {total} атомов.", "match": "все атомы совпадут с атомами того же вида.", "axis": "ось", "normal": "нормаль к плоскости", "questions": {"linear": "Молекула линейная?", "inversion": "Есть центр инверсии i?", "high": "Есть несколько различных осей Cₙ с n ≥ 3?", "highN": "Каков наибольший порядок осей вращения?", "mirror": "Есть хотя бы одна плоскость отражения σ?", "axis": "Есть ось собственного вращения Cₙ с n ≥ 2?", "order": "Выберите главную ось Cₙ с наибольшим n.", "perp": "Перпендикулярно главной оси проходят n осей C₂ (n = {n})?", "horizontal": "Есть плоскость σₕ, перпендикулярная главной оси?", "diagonal": "Есть n плоскостей σd (n = {n}), проходящих через главную ось?", "vertical": "Есть плоскости σᵥ, содержащие главную ось?", "improper": "Есть ось S₂ₙ вдоль главной оси Cₙ?"}, "hints": {"linear": "Все ядра лежат на одной прямой. Примеры: CO₂ и HCl. Отдельный атом здесь не рассматривается.", "inversion": "Преобразование (x, y, z) → (−x, −y, −z) относительно выбранного центра должно совместить молекулу с собой.", "high": "Считайте разные направления осей, а не разные повороты вокруг одной оси. Для этой ветви проверяйте все атомы, а не только форму скелета.", "highN": "Для многогранных групп: n = 3 → семейство T; n = 4 → O; n = 5 → I.", "mirror": "Отражение должно совместить атомы одного вида. Плоская молекула всегда имеет плоскость самой молекулы.", "axis": "Поворот на 360°/n должен совместить молекулу с собой. Ось может проходить между атомами.", "order": "Берите наибольший порядок собственного вращения, не Sₙ. При нескольких осях C₂ можно выбрать одну из них главной.", "perp": "Считайте оси, а не атомы. При n = 2 нужны две дополнительные C₂, перпендикулярные выбранной главной оси.", "horizontal": "Индекс h задаётся относительно главной оси: плоскость пересекает её под прямым углом.", "diagonal": "Плоскости σd содержат главную ось и делят пополам углы между соседними перпендикулярными осями C₂.", "vertical": "Индекс v означает, что плоскость содержит главную ось. Для Cₙᵥ таких плоскостей n.", "improper": "Выполните поворот на 360°/(2n), затем отражение в плоскости, перпендикулярной оси. Важно совпадение после всей операции, даже если отдельные действия не являются симметрией."}};
const $=id=>document.getElementById(id);
const wizard=$('sgWizard'), body=$('sgSteps');
let path=[],step='linear',order=2;
const nodes={
 linear:['linear','linI','high'],linI:['inversion','=D∞h','=C∞v'],high:['high','highN','axis'],
 highN:['highN'],highI5:['inversion','=Ih','=I'],highI4:['inversion','=Oh','=O'],highI3:['inversion','=Th','highSigma'],highSigma:['mirror','=Td','=T'],
 axis:['axis','order','lowMirror'],lowMirror:['mirror','=Cs','lowI'],lowI:['inversion','=Ci','=C1'],
 order:['order'],perp:['perp','dH','cH'],dH:['horizontal','=D{n}h','dD'],dD:['diagonal','=D{n}d','=D{n}'],
 cH:['horizontal','=C{n}h','cV'],cV:['vertical','=C{n}v','improper'],improper:['improper','=S{2n}','=C{n}']
};
function advance(next,n){path.push({step,order});if(n)order=n;step=next;renderWizard();}
function btn(label,fn,primary=false){const b=document.createElement('button');b.type='button';b.className='btn'+(primary?' primary':'');b.textContent=label;b.onclick=fn;return b;}
function renderWizard(){body.replaceChildren();const top=document.createElement('p');top.className='hint';top.textContent=L.step+' '+(path.length+1);body.append(top);
 const heading=document.createElement('p');heading.className='sgQuestion';heading.tabIndex=-1;body.append(heading);
 if(step.startsWith('=')){const group=step.slice(1).replace('{2n}',String(2*order)).replace('{n}',String(order));heading.innerHTML=L.result+' '+prettyG(group);const p=document.createElement('p');p.className='hint';p.textContent=L.resultNote;body.append(p);}
 else {const node=nodes[step],key=node[0];heading.innerHTML=L.questions[key].replaceAll('{n}',String(order));const hint=document.createElement('p');hint.className='hint';hint.innerHTML=L.hints[key]||'';body.append(hint);const row=document.createElement('div');row.className='row';body.append(row);
 if(step==='highN'){[3,4,5].forEach(n=>row.append(btn('n = '+n,()=>advance('highI'+n,n))))}
 else if(step==='order'){const lab=document.createElement('label');lab.textContent=L.n+' ';const input=document.createElement('input');input.type='number';input.min='2';input.max='120';input.step='1';input.value=order;input.id='sgN';input.style.width='6em';lab.append(input);row.append(lab,btn(L.next,()=>{const n=Number(input.value);if(!Number.isInteger(n)||n<2||n>120){input.reportValidity();return}advance('perp',n)},true));}
 else row.append(btn(L.yes,()=>advance(node[1]),true),btn(L.no,()=>advance(node[2])));
 }
 const nav=document.createElement('div');nav.className='row sgNav';const back=btn(L.back,()=>{const prev=path.pop();step=prev.step;order=prev.order;renderWizard()});back.disabled=!path.length;nav.append(back,btn(L.restart,()=>{path=[];step='linear';order=2;renderWizard()}));body.append(nav);
 if(wizard.open)heading.focus({preventScroll:true});
}
renderWizard();

const cmp=$('sgCompare'), holder=$('sgCompareBody');
let chosen=null,progress=0,raf=0,yaw=.6,pitch=.38,filter='all',operations=[];
function stopCompare(){if(raf)cancelAnimationFrame(raf);raf=0;}
function opName(M){const f=info(M,S.parentL.id.pa);let name=f.t==='s'?'σ':f.t==='C'||f.t==='S'?f.t+subs(f.n)+(f.k>1?sup(f.k):''):f.t;
 if(f.ax){const coord=f.ax.map(x=>Math.abs(x)<1e-7?0:Math.round(x*100)/100).join(', ');const axis=axLetter(f.ax);name+=' · '+(f.t==='s'?(planeName(f.ax)||L.normal+' ('+coord+')'):(axis||L.axis+' ('+coord+')'));}return name;}
function isKept(M){return invariant(M,S.model.atoms)}
function listOps(){stopCompare();const select=$('sgOp');select.replaceChildren();operations=S.full.filter(M=>filter==='all'||isKept(M)===(filter==='keep'));
 operations.forEach((M,i)=>{const o=document.createElement('option');o.value=i;o.textContent=opName(M)+' — '+(isKept(M)?L.kept:L.lost);select.append(o)});
 if(!operations.some(M=>chosen&&key(M)===key(chosen)))chosen=operations.find(M=>!isKept(M)&&info(M).t==='C'&&info(M).n===4&&info(M).k===1&&axLetter(info(M).ax)==='x')||operations.find(M=>!isKept(M))||operations.find(M=>info(M).t!=='E')||operations[0];
 select.value=String(operations.findIndex(M=>chosen&&key(M)===key(chosen)));select.disabled=!operations.length;$('sgRun').disabled=!operations.length;$('sgProgress').disabled=!operations.length;progress=0;drawCompare();}
function updateCompare(){stopCompare();cmp.hidden=S.desc<0;if(S.desc<0){holder.replaceChildren();return}chosen=null;filter='all';
 holder.innerHTML=`<p class="hint">${L.compareIntro}</p><div class="sgControls"><label>${L.filter} <select id="sgFilter"><option value="all">${L.all}</option><option value="keep">${L.kept}</option><option value="lost">${L.lost}</option></select></label><label class="sgOpLabel">${L.operation} <select id="sgOp"></select></label></div><div class="row"><button type="button" class="btn primary" id="sgRun">${L.run}</button><button type="button" class="btn" id="sgReset">${L.reset}</button><label class="sgSlider">${L.progress} <input type="range" id="sgProgress" min="0" max="100" value="0"><output id="sgPercent">0%</output></label></div><p id="sgStatus" class="sgStatus" role="status"></p><div class="sgPair"><figure><figcaption>${L.before} · ${prettyG(S.parentL.id.name)}</figcaption><svg id="sgBefore" viewBox="0 0 400 340" role="img" aria-label="${L.before}"></svg><p id="sgBeforeNote" class="hint"></p></figure><figure><figcaption>${L.after} · ${prettyG(S.L.id.name)}</figcaption><svg id="sgAfter" viewBox="0 0 400 340" role="img" aria-label="${L.after}"></svg><p id="sgAfterNote" class="hint"></p></figure></div><p class="hint">${L.legend}</p>`;
 $('sgFilter').onchange=e=>{filter=e.target.value;listOps()};$('sgOp').onchange=e=>{stopCompare();chosen=operations[+e.target.value];progress=0;drawCompare()};
 $('sgProgress').oninput=e=>{stopCompare();progress=+e.target.value/100;drawCompare()};$('sgReset').onclick=()=>{stopCompare();progress=0;drawCompare()};
 $('sgRun').onclick=()=>{stopCompare();if(!chosen)return;if(RM.matches){progress=1;drawCompare();return}const start=performance.now();progress=0;const frame=now=>{if(!cmp.open||cmp.hidden){stopCompare();return}progress=Math.min(1,(now-start)/1400);drawCompare();if(progress<1)raf=requestAnimationFrame(frame);else raf=0};raf=requestAnimationFrame(frame)};
 ['sgBefore','sgAfter'].forEach(id=>{const svg=$(id);let last=null;svg.onpointerdown=e=>{last=[e.clientX,e.clientY];svg.setPointerCapture(e.pointerId)};svg.onpointermove=e=>{if(!last)return;yaw+=(e.clientX-last[0])*.01;pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-last[1])*.01));last=[e.clientX,e.clientY];drawCompare()};svg.onpointerup=svg.onpointercancel=()=>last=null});
 listOps();}
function drawCompare(){if(S.desc<0||!$('sgBefore'))return;const M=chosen||I3;
 $('sgProgress').value=String(Math.round(progress*100));$('sgPercent').textContent=Math.round(progress*100)+'%';
 const status=$('sgStatus');status.textContent=chosen?(isKept(M)?L.keepStatus:L.lostStatus):L.empty;status.dataset.kind=chosen&&isKept(M)?'keep':'lost';
 const maxR=Math.max(.8,...S.base.atoms.map(a=>Math.hypot(...a.p)),...S.model.atoms.map(a=>Math.hypot(...a.p))),scale=108/maxR;
 const project=p=>{const x=p[0]*Math.cos(yaw)-p[1]*Math.sin(yaw),y=p[0]*Math.sin(yaw)+p[1]*Math.cos(yaw);return {x:200+x*scale,y:170-(p[2]*Math.cos(pitch)+y*Math.sin(pitch))*scale,z:y*Math.cos(pitch)-p[2]*Math.sin(pitch)}};
 const unmatched=(model)=>model.atoms.filter(a=>{const q=mv(M,a.p);return !model.atoms.some(b=>b.t===a.t&&Math.hypot(...q.map((v,k)=>v-b.p[k]))<2e-3)}).length;
 for(const [id,model,note] of [['sgBefore',S.base,'sgBeforeNote'],['sgAfter',S.model,'sgAfterNote']]){const svg=$(id);svg.replaceChildren();const ink=tok('--ink'),mut=tok('--muted'),accent=tok('--accent');
 const line=(a,b,attr={})=>el(svg,'line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:mut,'stroke-width':1,...attr});
 const label=(p,s,color=ink)=>{const t=el(svg,'text',{x:p.x,y:p.y,'text-anchor':'middle','font-size':13,fill:color});t.textContent=s};
 for(const [axis,v,color] of [['x',[1,0,0],'--ax-x'],['y',[0,1,0],'--ax-y'],['z',[0,0,1],'--ax-z']]){line(project(v.map(x=>-x*maxR*1.18)),project(v.map(x=>x*maxR*1.25)),{stroke:tok(color),opacity:.6});label(project(v.map(x=>x*maxR*1.4)),axis,tok(color));}
 const f=info(M,S.parentL.id.pa);if(f.t==='s'){const ps=planePoly(f.ax,maxR*1.15).map(project);el(svg,'polygon',{points:ps.map(p=>p.x+','+p.y).join(' '),fill:accent,'fill-opacity':.10,stroke:accent,'stroke-width':1})}else if(f.ax){line(project(f.ax.map(x=>-x*maxR*1.23)),project(f.ax.map(x=>x*maxR*1.23)),{stroke:accent,'stroke-width':3,'stroke-dasharray':'5 3'})}else if(f.t==='i'){el(svg,'circle',{cx:200,cy:170,r:6,fill:'none',stroke:accent,'stroke-width':2})}
 const initial=model.atoms.map(a=>project(a.p));
 const atoms=model.atoms.map((a,i)=>{const q=applyM(M,a.p,progress);const match=model.atoms.some(b=>b.t===a.t&&Math.hypot(...q.map((v,k)=>v-b.p[k]))<2e-3);return {...a,i,q:project(q),match}});
 /* the starting positions as in Compass, balls and sticks with a per-pixel depth test (assets/js/ballstick.js) */
 BallStick.ghost(svg,initial,atoms.map(a=>a.q),model.atoms.map(a=>elSt(a.t)[0]),model.atoms.map(()=>11),model.bonds,mut);
 const bs=BallStick.scene(atoms.map(a=>({x:a.q.x,y:a.q.y,z:-a.q.z*scale,r:11,c:elSt(a.t)[0]})),model.bonds,{rho:3});
 const seen=BallStick.draw(svg,bs.spheres,bs.rods,{fast:progress>0&&progress<1}).visible;
 atoms.forEach(a=>{const color=elSt(a.t),bad=progress>=.999&&!a.match;if(bad)el(svg,'circle',{cx:a.q.x,cy:a.q.y,r:11,fill:'none',stroke:'#cf443f','stroke-width':3});if(seen.has(a.i)||bad)label({x:a.q.x,y:a.q.y+4},color[3],color[1]);if(bad)label({x:a.q.x+17,y:a.q.y-12},'×','#cf443f');});
 const count=unmatched(model);$(note).textContent=L.atEnd+' '+(count?L.mismatch.replace('{count}',count).replace('{total}',model.atoms.length):L.match);
 }
}
const originalSetDesc=setDesc;
setDesc=function(i,animate){return Promise.resolve(originalSetDesc(i,animate)).then(updateCompare)};
cmp.addEventListener('toggle',()=>{if(!cmp.open)stopCompare();else drawCompare()});
new MutationObserver(()=>{if(cmp.open)drawCompare()}).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(cmp.open)drawCompare()});
updateCompare();
})();
