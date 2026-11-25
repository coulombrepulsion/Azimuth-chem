/* Compact guided identification and paired symmetry-operation comparison. */
(()=>{
const L={"title": "如何确定点群——逐步指南", "intro": "考察固定构象下的整个分子。对称操作必须使同种原子重合。本指南根据你的回答给出结果，不会自动检查几何结构。", "step": "步骤", "yes": "是", "no": "否", "back": "上一步", "restart": "重新开始", "next": "下一步", "n": "旋转轴阶数 n：", "result": "根据你的回答：", "resultNote": "请在模型上验证：该群的每个操作都必须使分子与自身重合。如需修改回答，请返回上一步。", "compareTitle": "比较结构变化前后的对称操作", "compareIntro": "对原始模型和变化后的模型施加同一个操作。用鼠标或手指拖动任一模型，可同时旋转两个视图。", "filter": "显示：", "all": "全部操作", "kept": "保留", "lost": "消失", "operation": "操作：", "run": "同时对两个模型执行", "reset": "回到起点", "progress": "操作进度：", "before": "原始模型", "after": "变化后的模型", "keepStatus": "保留：操作结束时，两个模型都与自身重合。", "lostStatus": "消失：只有原始模型与自身重合，变化后的模型不重合。", "empty": "此筛选条件下没有操作，请更改筛选条件。", "legend": "虚线轮廓表示原子的初始位置。操作结束时，红色轮廓和 × 表示未能与同种原子重合。重合判断在三维空间中进行，不仅依据投影。动画表示数学变换，并非原子的实际运动。", "atEnd": "操作结束时：", "mismatch": "{total} 个原子中有 {count} 个不重合。", "match": "所有原子均与同种原子重合。", "axis": "轴", "normal": "平面法向量", "questions": {"linear": "分子是线性的吗？", "inversion": "是否有反演中心 i？", "high": "是否有多条不同方向的 Cₙ 轴，且 n ≥ 3？", "highN": "正常旋转轴的最高阶数是多少？", "mirror": "是否存在镜面 σ？", "axis": "是否存在 n ≥ 2 的正常旋转轴 Cₙ？", "order": "选择阶数 n 最大的 Cₙ 轴作为主轴。", "perp": "是否有 {n} 条 C₂ 轴垂直于主轴 Cₙ？", "horizontal": "是否有垂直于主轴的 σₕ 平面？", "diagonal": "是否有 n 个（n = {n}）包含主轴的 σd 平面？", "vertical": "是否有包含主轴的 σᵥ 平面？", "improper": "是否有与主轴 Cₙ 同方向的 S₂ₙ 轴？"}, "hints": {"linear": "所有原子核位于同一直线上，例如 CO₂ 或 HCl。本指南不讨论单个原子。", "inversion": "相对于选定中心，(x, y, z) → (−x, −y, −z) 应使分子与自身重合。", "high": "计算不同方向的轴，不是同一条轴上的不同转动。检查所有原子，而不仅是骨架形状。", "highN": "多面体点群：n = 3 → T 类；n = 4 → O 类；n = 5 → I 类。", "mirror": "反射必须使同种原子重合。平面分子的分子平面一定是镜面。", "axis": "转动 360°/n 后分子必须与自身重合。旋转轴可以穿过原子之间。", "order": "选择正常旋转轴的最高阶数，而不是 Sₙ 的阶数。若有多条 C₂ 轴，可选其中一条作为主轴。", "perp": "计算轴的数量，而不是原子的数量。n = 2 时，需要另外两条垂直于主轴的 C₂ 轴。", "horizontal": "下标 h 相对于主轴定义：平面与主轴垂直。", "diagonal": "σd 平面包含主轴，并平分相邻的、垂直于主轴的 C₂ 轴之间的夹角。", "vertical": "垂直镜面包含主轴。Cₙᵥ 群中有 n 个这样的平面。", "improper": "先转动 360°/(2n)，再关于垂直于轴的平面反射。应检查整个组合操作，即使每个单独步骤并非对称操作。"}};
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
