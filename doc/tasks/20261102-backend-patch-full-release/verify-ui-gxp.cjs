'use strict';
// Reuse the established real-login, read-only GxP acceptance path.
const fs=require('node:fs');const path=require('node:path');
fs.mkdirSync('C:/SpugHandoff/release/private/acceptance/backend-full-20261102',{recursive:true});
const source=path.join(__dirname,'../20261101-three-server-schema-consistency/verify-target-gxp.cjs');
let code=fs.readFileSync(source,'utf8');
code=code.replace("path.join(__dirname,'target-gxp-'+environment+'-'+(expectedTag||'local')+'.json')",
    "path.join(__dirname,'ui-gxp-'+(process.env.RELEASE_VERIFY_PHASE||'before')+'-'+environment+'.json')");
code=code.replaceAll('schema-20261101','backend-full-20261102');
// Login redirects to the configuration page. Let its initial responses finish
// before the explicit second navigation, so their bodies cannot be discarded.
code=code.replace("phase = 'read-gxp-configuration-from-real-page';",
    "await page.waitForLoadState('networkidle',{timeout:30000});\n    phase = 'read-gxp-configuration-from-real-page';");
code=code.replace("assert(info.releaseTag===expectedTag,'Frontend release tag differs');report.releaseTag=info.releaseTag;",
    "assert((info.baseReleaseTag||info.releaseTag)===expectedTag,'Frontend main release differs');report.releaseTag=info.baseReleaseTag||info.releaseTag;report.frontendPatchTag=info.frontendPatchTag||null;");
code=code.replace("report.status = 'PASS';",`
    if(environment!=='local'){
      phase='real-version-dialog';
      const version=page.getByTestId('release-info-dock').getByRole('button');
      await version.waitFor({state:'visible',timeout:30000});
      report.visibleFrontendTag=(await version.innerText()).trim();
      assert(report.visibleFrontendTag===(report.frontendPatchTag||expectedTag),'Visible version differs');
      await version.click();
      const dialog=page.getByRole('dialog',{name:'版本变更说明'});
      await dialog.waitFor({state:'visible',timeout:15000});
      report.versionChangeItems=await dialog.locator('li').allTextContents();
      report.versionNotesAvailable=report.versionChangeItems.length>0;
      if((process.env.RELEASE_VERIFY_PHASE||'').startsWith('full')){
        assert(report.versionNotesAvailable,'Full release version change notes missing');
        assert(report.versionChangeItems.some(item=>item.includes('启动')&&item.includes('日志')),'Startup-log change note missing');
      }
      await page.screenshot({path:report.privateScreenshotPath.replace('.png','-version.png'),fullPage:false,mask:[page.locator('input')]});
      await page.keyboard.press('Escape');
      await dialog.waitFor({state:'hidden',timeout:15000});
      report.realVersionDialog=true;
    }
    report.status = 'PASS';`);
require('node:vm').runInThisContext('(function(require,__dirname){'+code+'\n})',{filename:source})(require,__dirname);
