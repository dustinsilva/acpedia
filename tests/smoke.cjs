const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{createRequire}=require('node:module');
const loader=process.env.ACPEDIA_NODE_MODULES?createRequire(path.join(process.env.ACPEDIA_NODE_MODULES,'_test.cjs')):require;
const {chromium}=loader('playwright');
const base=(process.env.ACPEDIA_URL||'http://127.0.0.1:8770').replace(/\/$/,'');
(async()=>{const browser=await chromium.launch({headless:true,channel:process.env.ACPEDIA_BROWSER_CHANNEL||'msedge'});try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 async function api(params){const r=await page.request.get(base+'/api.php',{params:{format:'json',...params}});assert.equal(r.status(),200);const json=await r.json();assert(!json.error,JSON.stringify(json.error));return json;}
 let response=await page.goto(base+'/wiki/Home',{waitUntil:'networkidle',timeout:60000});assert.equal(response.status(),200);
 await page.locator('#mw-content-text').getByText("Welcome to the Asheron's Call Community Wiki,",{exact:true}).waitFor();
 const homeImages=await page.locator('#mw-content-text img').evaluateAll(img=>({count:img.length,broken:img.filter(x=>!x.complete||!x.naturalWidth).map(x=>x.src)}));assert(homeImages.count>=25);assert.deepEqual(homeImages.broken,[]);
 assert(await page.locator('.acpedia-menu').count());const menu=page.locator('.acpedia-menu>li').first();await menu.hover();assert(await menu.locator('ul').first().isVisible());
 await page.screenshot({path:'.data/home-restoration.png',fullPage:true});
 for(const title of ['Holtburg Dungeon','Sword of Lost Light Quest','Olthoi Legionary']){
  await page.goto(base+'/wiki/'+encodeURIComponent(title.replaceAll(' ','_')),{waitUntil:'networkidle',timeout:60000});
  assert((await page.locator('h1').innerText()).includes(title));assert(!(await page.locator('#mw-content-text').innerText()).includes('Internal error'));
 }
 const revisions=await api({action:'query',prop:'revisions',titles:'Sword of Lost Light Quest',rvlimit:'3',rvprop:'timestamp|user'});const record=Object.values(revisions.query.pages)[0];assert.equal(record.revisions.length,3,'original history missing');
 const search=await api({action:'query',list:'search',srsearch:'Holtburg'});assert(search.query.search.length>0,'search index empty');
 const categories=await api({action:'query',prop:'categories',titles:'Sword of Lost Light Quest',cllimit:'max'});assert(Object.values(categories.query.pages)[0].categories?.length>0,'categories not rebuilt');
 const map=await api({action:'query',titles:'File:01F6.gif',prop:'imageinfo',iiprop:'url|size',iiurlwidth:'200'});const image=Object.values(map.query.pages)[0].imageinfo?.[0];assert(image,'dungeon map unavailable');const media=await page.request.get(image.thumburl||image.url);assert.equal(media.status(),200);
 for(const secret of ['/.data/admin-password.txt','/LocalSettings.php','/maintenance/run.php']){const r=await page.request.get(base+secret);assert.equal(r.status(),404,secret+' exposed');}
 await page.goto(base+'/wiki/Home',{waitUntil:'networkidle'});await page.setViewportSize({width:390,height:844});await page.screenshot({path:'.data/home-mobile.png',fullPage:true});
 // Legacy Vector intentionally retains the original wide tables on small screens.
 assert.deepEqual(errors,[]);console.log('PASS: original home/images/menu, quest/dungeon/creature pages, histories, search, categories, dungeon map, secret-path denial; no page errors.');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
