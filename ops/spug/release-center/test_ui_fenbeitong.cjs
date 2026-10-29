const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const context=vm.createContext({URLSearchParams,location:{search:''},localStorage:{getItem:()=> 'token'},sessionStorage:{getItem:()=>null},document:{addEventListener:()=>{}},setInterval:()=>{},fetch:()=>new Promise(()=>{})});
vm.runInContext(fs.readFileSync(__dirname+'/ui/fenbeitong.js','utf8'),context);
const evaluate=expression=>vm.runInContext(expression,context);
evaluate('const testPackage={releaseTag:"2026-10-27-10-03-10",packageSha256:"one"};const testState={environments:{}};');
assert.equal(evaluate('fbtCanDeploy(testPackage,testState,"test")'),true);
for(const env of ['prod','backup']){
 assert.equal(evaluate(`fbtCanDeploy(testPackage,testState,"${env}")`),false);
 assert.equal(evaluate(`fbtButton("发布","x",fbtCanDeploy(testPackage,testState,"${env}")).includes("disabled")`),true);
}
evaluate('testPackage.accepted={test:{note:"通过"}};');
assert.equal(evaluate('fbtCanDeploy(testPackage,testState,"prod")'),false);
evaluate('testPackage.rehearsal={accepted:true};');
assert.equal(evaluate('fbtCanDeploy(testPackage,testState,"prod")'),true);
evaluate('testPackage.accepted.prod={note:"通过"};testState.environments.prod={packageSha256:"other"};');
assert.equal(evaluate('fbtCanDeploy(testPackage,testState,"backup")'),false);
evaluate('testState.environments.prod.packageSha256="one";');
assert.equal(evaluate('fbtCanDeploy(testPackage,testState,"backup")'),true);
evaluate('testPackage.rejected=true;');
assert.equal(evaluate('fbtCanDeploy(testPackage,testState,"backup")'),false);
console.log('PASS: unaccepted, mismatched and rejected packages keep promotion buttons disabled.');
