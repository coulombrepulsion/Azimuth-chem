(function(){const R=document.documentElement;let on=false;
  function scale(){document.querySelectorAll('svg [stroke-width]').forEach(e=>{if(e.dataset.pw)return;const w=parseFloat(e.getAttribute('stroke-width'));if(isNaN(w))return;e.dataset.pw=w;e.setAttribute('stroke-width',(w*1.7).toFixed(2))})}
  const mo=new MutationObserver(()=>{if(on)scale()});
  function set(v){on=!!v;R.classList.toggle('proj',on);if(on){scale();mo.observe(document.body,{childList:true,subtree:true})}
    else{mo.disconnect();document.querySelectorAll('[data-pw]').forEach(e=>{e.setAttribute('stroke-width',e.dataset.pw);delete e.dataset.pw})}}
  addEventListener('message',e=>{if(e.data&&typeof e.data.proj==='boolean')set(e.data.proj)});
  if(/[?&]proj=1/.test(location.search))addEventListener('DOMContentLoaded',()=>set(true));
})();
