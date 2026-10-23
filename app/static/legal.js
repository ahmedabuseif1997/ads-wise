'use strict';
const legalThemeKey='adwise_product_theme';
function applyLegalTheme(theme){
  const selected=theme==='light'?'light':'dark';
  document.documentElement.dataset.productTheme=selected;
  document.querySelectorAll('[data-theme-toggle]').forEach(button=>{
    button.textContent=selected==='dark'?'☀ Light':'☾ Dark';
    button.setAttribute('aria-pressed',String(selected==='light'));
  });
  try{localStorage.setItem(legalThemeKey,selected)}catch{}
}
try{applyLegalTheme(localStorage.getItem(legalThemeKey)||'dark')}catch{applyLegalTheme('dark')}
document.addEventListener('click',event=>{
  if(event.target.closest('[data-theme-toggle]'))applyLegalTheme(document.documentElement.dataset.productTheme==='dark'?'light':'dark');
});
