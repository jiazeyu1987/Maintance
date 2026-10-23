import { createApp } from 'vue'
import { ElAlert, ElButton, ElInput } from 'element-plus'
import 'element-plus/theme-chalk/base.css'
import 'element-plus/theme-chalk/el-alert.css'
import 'element-plus/theme-chalk/el-button.css'
import 'element-plus/theme-chalk/el-input.css'
import App from './App.vue'
createApp(App).use(ElAlert).use(ElButton).use(ElInput).mount('#app')
