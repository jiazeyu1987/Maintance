// Real existing Spug login and read-only business UI. Never submit, execute, or activate a task.
import {createRequire} from 'node:module';
import {readFile, writeFile} from 'node:fs/promises';
const require=createRequire('E:/IntRuoyi/IntRuoyiFronted/package.json');
const {chromium}=require('playwright');
const privateName=process.argv[2];
if(!privateName || !/^[A-Za-z0-9_.-]+\.private\.json$/.test(privateName))
  throw new Error('EXPLICIT_PRIVATE_LOGIN_REQUIRED');
const login=JSON.parse(await readFile('E:/Int/CacheData/IntRuoyi/spug-integration-20261010/'+privateName,'utf8'));
const destination='doc/tasks/20261010-spug-integration';
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000}});
const page=await context.newPage();
page.setDefaultTimeout(12000);
const mutations=[], pageErrors=[], selections=[];
page.on('request',request=>{
  if(request.method()==='POST' && !request.url().endsWith('/api/account/login/'))
    mutations.push(new URL(request.url()).pathname);
});
page.on('pageerror',()=>pageErrors.push('PAGE_SCRIPT_ERROR'));
page.on('response',async response=>{
  if(response.url().endsWith('/backup-entry-api/selections')){
    try{
      const body=await response.json();
      selections.push({status:response.status(),errorCode:body.errorCode || null,
        applications:(body.applications || []).map(app=>({applicationId:app.applicationId,
          registrationSha256:app.registrationSha256,engineSelectionRef:app.engineSelectionRef,
          fullReady:app.validated?.fullReady===true,readinessError:app.readinessError || null})),
        registrationVersions:body.registrationVersions || null});
    }catch(error){selections.push({status:response.status(),errorCode:'SELECTION_RESPONSE_NOT_JSON'});}
  }
});
function need(condition,code){if(!condition)throw new Error(code);}
try{
  await page.goto('http://127.0.0.1:18080/',{waitUntil:'domcontentloaded'});
  await page.getByPlaceholder('请输入账户').fill(login.username);
  await page.getByPlaceholder('请输入密码').fill(login.password);
  const logged=page.waitForResponse(r=>r.url().endsWith('/api/account/login/') && r.request().method()==='POST');
  await page.getByRole('button',{name:'登 录'}).click();
  need(!(await (await logged).json()).error,'SPUG_REAL_LOGIN_REJECTED');
  const warning=page.getByRole('button',{name:'知道了'});
  await warning.waitFor({state:'visible'});
  await warning.click();await warning.waitFor({state:'hidden'});
  await page.getByText('工作台',{exact:true}).first().waitFor();
  const selected=page.waitForResponse(r=>r.url().endsWith('/backup-entry-api/selections'));
  await page.goto('http://127.0.0.1:18080/backup-restore/',{waitUntil:'domcontentloaded'});
  await selected;
  await page.waitForFunction(()=>!document.querySelector('#refresh').disabled &&
    (document.querySelector('#problem').textContent || document.querySelector('#application').options.length));
  const tabs=[];
  for(const [action,label] of [['FULL','全量备份'],['INCREMENTAL','增量备份'],['RESTORE','恢复']]){
    await page.getByRole('tab',{name:label,exact:true}).click();
    const state=await page.evaluate(()=>({
      action:document.querySelector('[aria-selected=true]').dataset.action,
      submitDisabled:document.querySelector('#submit').disabled,
      problem:document.querySelector('#problem').textContent,
      blockedReason:document.querySelector('#blocked-reason').textContent,
      incrementalVisible:!document.querySelector('#incremental-fields').hidden,
      restoreVisible:!document.querySelector('#restore-fields').hidden,
      applicationOptions:Array.from(document.querySelector('#application').options).map(o=>({value:o.value,label:o.text})),
      registeredVersion:document.querySelector('#selected-version').textContent,
      sourceOptions:Array.from(document.querySelector('#source').options).map(o=>o.value).filter(Boolean),
      parentOptions:Array.from(document.querySelector('#parent').options).map(o=>o.value).filter(Boolean),
      pointOptions:Array.from(document.querySelector('#point').options).map(o=>o.value).filter(Boolean),
      targetOptions:Array.from(document.querySelector('#target').options).map(o=>o.value).filter(Boolean),
      documentOverflow:document.documentElement.scrollWidth>innerWidth,
    }));
    need(state.action===action && state.incrementalVisible===(action==='INCREMENTAL') &&
      state.restoreVisible===(action==='RESTORE'),'BUSINESS_TAB_VISIBILITY_FAILED');
    need(state.submitDisabled,'UNAUTHORIZED_BUSINESS_SUBMIT_ENABLED');
    need(!state.documentOverflow,'DESKTOP_DOCUMENT_OVERFLOW');
    tabs.push(state);
    await page.screenshot({path:destination+'/smallapp-business-'+action.toLowerCase()+'-20261014.png',fullPage:true});
  }
  await page.getByRole('tab',{name:'全量备份',exact:true}).click();
  need((await page.locator('#action-note').textContent()).includes('首次全量备份无需等待增量链或恢复目标'),
    'FIRST_FULL_FUTURE_DEPENDENCY_ADDED');
  await page.setViewportSize({width:390,height:844});
  need(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'MOBILE_DOCUMENT_OVERFLOW');
  await page.screenshot({path:destination+'/smallapp-business-mobile-20261014.png',fullPage:true});
  need(pageErrors.length===0,'BUSINESS_PAGE_SCRIPT_ERROR');
  need(mutations.length===0,'UNEXPECTED_BUSINESS_OR_SCHEDULE_MUTATION');
  // Final independent API verification follows the actual frontend path.
  const anonymous=await browser.newContext();
  const refused=await anonymous.request.get('http://127.0.0.1:18080/backup-entry-api/selections');
  const refusal=await refused.json();
  need(refused.status()===401 && refusal.errorCode==='SPUG_LOGIN_REQUIRED','ANONYMOUS_ENTRY_NOT_REFUSED');
  await anonymous.close();
  const evidence={at:new Date().toISOString(),status:'REAL_LOGIN_AND_READONLY_REFUSAL_UI_VERIFIED',
    entry:'http://127.0.0.1:18080/backup-restore/',realLogin:true,officialPrivateIpWarningDismissed:true,
    selections,tabs,mobileNoDocumentOverflow:true,anonymousApiStatus:refused.status(),
    pageScriptErrors:pageErrors.length,nonLoginPosts:mutations.length,businessActionsTriggered:0,
    schedulesActivated:0,actualApplicationSelectionAcceptance:tabs.some(t=>t.applicationOptions.length>0),
    actualFullIncrementalRestoreAcceptance:false};
  await writeFile(destination+'/smallapp-business-ui-20261014.json',JSON.stringify(evidence,null,2),'utf8');
  console.log(JSON.stringify(evidence));
}catch(error){
  console.log(JSON.stringify({errorCode:/^[A-Z0-9_]+$/.test(error.message)?error.message:'BUSINESS_READONLY_UI_VERIFICATION_FAILED'}));
  throw new Error('BUSINESS_READONLY_UI_NOT_ACCEPTED');
}finally{await browser.close();}
