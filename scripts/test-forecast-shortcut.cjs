const {chromium}=require('../.local/ui-qa/node_modules/playwright-core');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const baseline=process.argv.includes('--baseline');
const overview=JSON.parse(fs.readFileSync('android/app/src/androidTest/assets/layout-overview.json','utf8'));
const forecast=JSON.parse(fs.readFileSync('android/app/src/androidTest/assets/forecast-shortcut.json','utf8'));
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});
 try{for(const width of [1280,390])for(const delay of [0,250,1600]){
  const page=await browser.newPage({viewport:{width,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://greenmine.test/**',async route=>{const url=new URL(route.request().url());
   if(url.pathname==='/api/auth')return route.fulfill({json:{user:{id:-1,email:'shortcut-test@example.org'},auth_email_available:true}});
   if(url.pathname==='/api/engine'){const body=route.request().postDataJSON();if(body.action==='forecast'&&delay)await new Promise(r=>setTimeout(r,delay));return route.fulfill({json:body.action==='forecast'?forecast:overview});}
   let file=baseline?path.join('.local/shortcut-baseline',url.pathname==='/dashboard'?'_pages/dashboard.html':url.pathname):url.pathname==='/dashboard'?'.next/server/app/dashboard.html':url.pathname.startsWith('/_next/static/')?path.join('.next/static',url.pathname.slice('/_next/static/'.length)):path.join('public',url.pathname);
   if(!fs.existsSync(file))return route.fulfill({status:404,body:''});
   const ext=path.extname(file);return route.fulfill({body:fs.readFileSync(file),contentType:({'.html':'text/html','.js':'application/javascript','.css':'text/css','.png':'image/png','.woff':'font/woff','.svg':'image/svg+xml'})[ext]||'application/octet-stream'});
  });
  await page.goto('http://greenmine.test/dashboard');
  const button=page.locator('.forecast-prompt button');await button.waitFor();
  await page.waitForFunction(()=>!document.querySelector('.forecast-prompt button').disabled);
  for(let i=0;i<3;i++){
   if(i){await page.locator('[role=tab][id$=trigger-overview]').click();await button.waitFor();}
   await button.click();
   await page.locator('[data-panel=forecast] .forecast-stats').waitFor({state:'visible',timeout:10000});
   const stats=page.locator('.forecast-stats');await stats.scrollIntoViewIfNeeded();
   await page.waitForFunction(()=>[...document.querySelectorAll('.forecast-stats [data-animated-card]')].every(el=>Number(getComputedStyle(el).opacity)>.9),{},{timeout:5000});
   assert.equal(await page.locator('[role=tab][id$=trigger-forecast]').getAttribute('data-state'),'active');
  }
  assert.deepEqual(errors,[]);console.log(`PASS ${baseline?'baseline':'fixed'} ${width}px / ${delay}ms API delay / three shortcut visits`);
  await page.close();
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
