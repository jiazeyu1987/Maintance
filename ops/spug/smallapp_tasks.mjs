// Configure only the three existing inactive tasks; never Execute/activate them.
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
const require=createRequire('E:/IntRuoyi/IntRuoyiFronted/package.json');
const {chromium}=require('playwright');
const loginPrivateName=process.argv[2];
if(!loginPrivateName || !/^[A-Za-z0-9_.-]+\.private\.json$/.test(loginPrivateName))throw new Error('EXPLICIT_PRIVATE_LOGIN_REQUIRED');
const admin=JSON.parse(await readFile('E:/Int/CacheData/IntRuoyi/spug-integration-20261010/'+loginPrivateName,'utf8'));
const output='doc/tasks/20261010-spug-integration';
const original=JSON.parse(await readFile(output+'/smallapp-manual-tasks-20261014.json','utf8')).results;
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
page.setDefaultTimeout(12000);
let headers;
page.on('request',r=>{if(r.url().endsWith('/api/schedule/')&&r.method()==='GET')headers=r.headers();});
try{
  await page.goto('http://127.0.0.1:18080/',{waitUntil:'domcontentloaded'});
  await page.getByPlaceholder('请输入账户').fill(admin.username);
  await page.getByPlaceholder('请输入密码').fill(admin.password);
  const response=page.waitForResponse(r=>r.url().includes('/api/account/login/')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登 录'}).click();
  if((await(await response).json()).error)throw new Error('SPUG_UI_LOGIN_REJECTED');
  const warning=page.getByRole('button',{name:'知道了'});
  await warning.waitFor({state:'visible'});await warning.click();await warning.waitFor({state:'hidden'});
  await page.getByText('工作台',{exact:true}).first().waitFor();
  const initial=page.waitForResponse(r=>r.url().endsWith('/api/schedule/')&&r.request().method()==='GET');
  await page.getByText('任务计划',{exact:true}).first().click();
  const tasks=(await(await initial).json()).data.tasks;
  const results=[];
  const observed=[];
  for(const old of original){
    const task=tasks.find(t=>t.id===old.taskId);
    const command='python3 /opt/intruoyi-spug/smallapp_adapter.py --business-action '+old.action;
    const row=page.getByRole('row').filter({has:page.getByText(old.name,{exact:true})});
    if(task)await row.waitFor();
    observed.push({taskId:old.taskId,found:!!task,nameMatches:task?.name===old.name,
      isActive:task?.is_active,targetsLocal:JSON.stringify(task?.targets)==='["local"]',
      commandMatchesOriginal:task?.command===old.command,commandMatchesBusinessTemplate:task?.command===command,
      uiStatus:task?((await row.innerText()).includes('未激活')?'未激活':(await row.innerText()).includes('已激活')?'已激活':'状态标签待核'):null});
  }
  const conflict=observed.some(r=>!r.found || !r.nameMatches || r.isActive!==false || !r.targetsLocal ||
    (!r.commandMatchesOriginal && !r.commandMatchesBusinessTemplate));
  if(conflict){
    const evidence={at:new Date().toISOString(),status:'OWN_TEMPLATE_BASELINE_CHANGED',observed,
      tasksModified:0,businessActionsTriggered:0,schedulesActivated:0};
    await writeFile(output+'/smallapp-template-conflict-20261014.json',JSON.stringify(evidence,null,2),'utf8');
    await page.screenshot({path:output+'/smallapp-template-conflict-20261014.png',fullPage:true});
    console.log(JSON.stringify(evidence));
    throw new Error('OWN_TEMPLATE_BASELINE_CHANGED');
  }
  for(const old of original){
    const task=tasks.find(t=>t.id===old.taskId);
    const command='python3 /opt/intruoyi-spug/smallapp_adapter.py --business-action '+old.action;
    const desc='仅手动。业务入口 http://127.0.0.1:18080/backup-restore/；页面选择已登记应用/源、实际已接受父链或恢复点、全新目标，无需修改命令。请从业务入口执行；直接运行此模板缺页面参数会拒绝。结果保留本任务执行历史；不得激活定时。';
    if(!task || task.name!==old.name || task.is_active || JSON.stringify(task.targets)!=='["local"]' ||
       ![old.command,command].includes(task.command)){
      console.log(JSON.stringify({taskId:old.taskId,found:!!task,nameMatches:task?.name===old.name,
        inactive:task?.is_active===false,activeValue:task?.is_active,activeType:typeof task?.is_active,
        targetsLocal:JSON.stringify(task?.targets)==='["local"]',
        commandMatchesOriginal:task?.command===old.command,commandMatchesBusinessTemplate:task?.command===command}));
      throw new Error('OWN_TEMPLATE_BASELINE_CHANGED');
    }
    const row=page.getByRole('row').filter({has:page.getByText(old.name,{exact:true})});
    await row.getByText('未激活',{exact:true}).waitFor();
    await row.getByText('编辑',{exact:true}).click();
    const edit=page.getByRole('dialog',{name:'编辑任务'});
    const current=await edit.locator('.ace_editor').evaluate(e=>e.env.editor.getValue());
    if(current!==task.command)throw new Error('OWN_TEMPLATE_LIVE_CONFLICT');
    if(current!==command || task.desc!==desc){
      await edit.locator('.ace_content').click();await page.keyboard.press('Control+A');await page.keyboard.insertText(command);
      await edit.getByPlaceholder('请输入模板备注信息').fill(desc);
      await edit.getByRole('button',{name:'下一步',exact:true}).click();
      await edit.getByRole('button',{name:'下一步',exact:true}).click();
      const saving=page.waitForResponse(r=>r.url().endsWith('/api/schedule/')&&r.request().method()==='POST');
      await edit.getByRole('button',{name:/提\s*交/}).click();
      if((await(await saving).json()).error)throw new Error('OWN_TEMPLATE_SAVE_REJECTED');
      await edit.waitFor({state:'hidden'});
      await row.getByText('编辑',{exact:true}).click();
    }
    const readback=page.getByRole('dialog',{name:'编辑任务'});
    if(await readback.locator('.ace_editor').evaluate(e=>e.env.editor.getValue())!==command)throw new Error('OWN_TEMPLATE_READBACK_FAILED');
    await readback.locator('.ant-modal-close').click();await readback.waitFor({state:'hidden'});
    results.push({taskId:old.taskId,name:old.name,action:old.action,command,inactiveUiReadback:true,businessActionsTriggered:0});
  }
  const final=await page.request.get('http://127.0.0.1:18080/api/schedule/',{headers});
  const saved=(await final.json()).data.tasks;
  for(const result of results){
    const task=saved.find(t=>t.id===result.taskId);
    if(!task || task.command!==result.command || task.is_active || JSON.stringify(task.targets)!=='["local"]' || task.interpreter!=='sh')
      throw new Error('OWN_TEMPLATE_FINAL_READBACK_FAILED');
  }
  const evidence={at:new Date().toISOString(),loginCredentialRef:loginPrivateName,businessEntry:'http://127.0.0.1:18080/backup-restore/',
    scope:'Existing task IDs 7/8/9 only; no other task audit or mutation',realUiSavedReadback:true,businessActionsTriggered:0,schedulesActivated:0,results};
  await page.screenshot({path:output+'/smallapp-business-templates-20261014.png',fullPage:true});
  await writeFile(output+'/smallapp-business-templates-20261014.json',JSON.stringify(evidence,null,2),'utf8');
  console.log(JSON.stringify(evidence));
}catch(error){
  console.log(JSON.stringify({errorCode:/^[A-Z0-9_]+$/.test(error.message)?error.message:'SPUG_TEMPLATE_UI_FAILED'}));
  throw new Error('SPUG_TEMPLATE_CONFIGURATION_NOT_ACCEPTED');
}finally{await browser.close();}
