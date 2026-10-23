<script setup lang="ts">
import { ref, onMounted } from 'vue'
type Entry={id:number;title:string;content:string;updatedAt:string}
type Attachment={id:string;name:string;size:number;sha256:string}
const user=ref<{server:string;releaseTag:string;tenantId:number;tenantName:string;username:string}|null>(null), tenantId=ref(122), username=ref('aoteman'), password=ref(''), error=ref(''), busy=ref(false)
const records=ref<Entry[]>([]), current=ref<Entry|null>(null), title=ref(''), content=ref(''), files=ref<Attachment[]>([]), fileInput=ref<HTMLInputElement>(), editing=ref(false), status=ref('')
async function api(path:string, method='GET', body?:unknown){
 const response=await fetch('/api'+path,{method,credentials:'same-origin',headers:body instanceof FormData?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:body instanceof FormData?body:JSON.stringify(body)})
 const text=await response.text();const data=text?JSON.parse(text):null
 if(!response.ok){if(response.status===401)user.value=null;throw Error(data?.message||`请求失败：${response.status}`)}return data
}
async function run(action:()=>Promise<void>){busy.value=true;error.value='';status.value='';try{await action()}catch(e){error.value=e instanceof Error?e.message:String(e)}finally{busy.value=false}}
async function refresh(){records.value=await api('/records')}
function changeTenant(){username.value=tenantId.value===122?'aoteman':'recovery_tenant123';password.value='';error.value=''}
async function login(){await run(async()=>{await api('/login','POST',{tenantId:tenantId.value,username:username.value,password:password.value});password.value='';user.value=await api('/me');records.value=[];current.value=null;files.value=[];editing.value=false;await refresh()})}
async function select(record:Entry){await run(async()=>{current.value=record;title.value=record.title;content.value=record.content;files.value=await api(`/records/${record.id}/attachments`);editing.value=true})}
function create(){current.value=null;title.value='';content.value='';files.value=[];editing.value=true;error.value='';status.value=''}
async function save(){await run(async()=>{current.value=await api(current.value?`/records/${current.value.id}`:'/records',current.value?'PUT':'POST',{title:title.value,content:content.value});await refresh();status.value='记录已保存'})}
async function remove(){if(!current.value||!confirm('确认删除当前记录？'))return;await run(async()=>{await api(`/records/${current.value!.id}`,'DELETE');current.value=null;editing.value=false;await refresh();status.value='记录已删除'})}
async function upload(){const file=fileInput.value?.files?.[0];if(!file||!current.value)return;await run(async()=>{const form=new FormData();form.append('file',file);await api(`/records/${current.value!.id}/attachments`,'POST',form);files.value=await api(`/records/${current.value!.id}/attachments`);fileInput.value!.value='';status.value='附件已保存'})}
async function deleteFile(file:Attachment){if(!confirm('确认删除此附件？'))return;await run(async()=>{await api(`/attachments/${file.id}`,'DELETE');files.value=await api(`/records/${current.value!.id}/attachments`);status.value='附件已删除'})}
async function logout(){await run(async()=>{await api('/logout','POST');user.value=null;records.value=[];current.value=null;files.value=[];title.value='';content.value='';editing.value=false})}
onMounted(async()=>{try{user.value=await api('/me');await refresh()}catch(e){error.value=e instanceof Error?e.message:String(e)}})
</script>
<template>
 <main>
  <header><div><small>INTRUOYI · 演练环境</small><h1>备份演练小程序</h1></div><div v-if="user" class="identity"><span>{{user.server}} · {{user.tenantName}} / {{user.username}} · 租户 {{user.tenantId}}</span><el-button @click="logout" :disabled="busy">退出登录</el-button></div></header>
  <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon role="alert" />
  <el-alert v-if="status" :title="status" type="success" :closable="false" show-icon role="status" />
  <section v-if="!user" class="login panel"><h2>登录演练租户</h2><p>各租户独立管理记录与附件。</p><form @submit.prevent="login"><label for="tenant">租户</label><select id="tenant" v-model="tenantId" @change="changeTenant" :disabled="busy"><option :value="122">测试租户（122）</option><option :value="123">隔离演练租户（123）</option></select><label for="username">账号</label><el-input id="username" v-model="username" autocomplete="username"/><label for="password">密码</label><el-input id="password" v-model="password" type="password" autocomplete="current-password" show-password/><el-button native-type="submit" type="primary" :loading="busy">登录</el-button></form></section>
  <template v-else>
   <div class="toolbar"><p>记录与附件 <span>· {{records.length}} 条记录</span></p><div><el-button @click="run(refresh)" :disabled="busy">刷新</el-button><el-button type="primary" @click="create" :disabled="busy">新增记录</el-button></div></div>
   <div class="layout"><section class="panel record-list"><p v-if="!records.length">暂无记录，请通过页面新增。</p><button v-for="record in records" :key="record.id" class="record" :class="{selected:current?.id===record.id}" @click="select(record)" :disabled="busy"><strong>{{record.title}}</strong><span>{{record.content}}</span><small>#{{record.id}} · {{record.updatedAt.replace('T',' ')}}</small></button></section>
    <section class="panel editor" v-if="editing"><h2>{{current?'编辑记录':'新增记录'}}</h2><form @submit.prevent="save"><label for="title">标题</label><el-input id="title" v-model="title" maxlength="120" required/><label for="content">内容</label><el-input id="content" v-model="content" type="textarea" :rows="4" maxlength="2000"/><div class="actions"><el-button native-type="submit" type="primary" :disabled="busy||!title.trim()">保存记录</el-button><el-button v-if="current" type="danger" plain @click="remove" :disabled="busy">删除记录</el-button></div></form>
     <div v-if="current" class="attachments"><h3>附件</h3><p>单个附件最大 5 MB，下载时校验完整性。</p><label for="file">选择附件</label><input id="file" type="file" ref="fileInput" :disabled="busy"><el-button @click="upload" :disabled="busy">上传附件</el-button><article v-for="file in files" :key="file.id"><a :href="'/api/attachments/'+file.id" download>{{file.name}}</a><span>{{file.size}} 字节</span><el-button size="small" type="danger" text @click="deleteFile(file)" :disabled="busy">删除附件</el-button><small>SHA-256：{{file.sha256}}</small></article></div>
    </section><section v-else class="panel empty">选择一条记录查看内容和附件，或新增演练数据。</section>
   </div><footer>版本 {{user.releaseTag}} · 三服独立部署 · 仅用于备份与恢复演练</footer>
  </template>
 </main>
</template>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f6f9;color:#243247;font:14px/1.6 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1180px;margin:auto;padding:36px 24px}header,.toolbar,.identity,.actions{display:flex;align-items:center;justify-content:space-between;gap:16px}header{margin-bottom:24px}h1{font-size:26px;margin:4px 0}h2{font-size:19px;margin:0 0 16px}h3{font-size:16px}small,footer,.toolbar span{color:#6c7b90}header small{letter-spacing:2px}label{display:block;margin:14px 0 6px}.panel{background:white;border:1px solid #dde3ed;border-radius:8px;padding:24px}.login{max-width:420px;margin:64px auto}.login button{margin-top:24px;width:100%}.layout{display:grid;grid-template-columns:340px 1fr;gap:20px}.toolbar{margin:20px 0}.record-list{padding:10px;max-height:700px;overflow:auto}.record{background:white;border:0;border-bottom:1px solid #e9edf3;text-align:left;display:flex;flex-direction:column;gap:6px;width:100%;padding:16px;cursor:pointer;color:inherit}.record.selected{background:#edf4ff}.record span{max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.actions{justify-content:flex-start;margin-top:18px}.attachments{margin-top:30px;border-top:1px solid #e9edf3;padding-top:12px}.attachments article{margin-top:16px;padding:12px;background:#f7f9fc}.attachments article small{display:block;overflow-wrap:anywhere}.attachments span{margin:0 12px}input[type=file]{max-width:100%;margin-bottom:10px}footer{margin-top:24px;font-size:12px}.empty{color:#6c7b90;align-content:center}.el-alert{margin-bottom:12px}@media(max-width:760px){main{padding:20px 12px}.layout{grid-template-columns:1fr}header,.identity{align-items:flex-start;flex-direction:column}.record-list{max-height:300px}}
</style>
