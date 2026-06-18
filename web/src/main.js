import '@unocss/reset/tailwind.css'
import 'virtual:uno.css'
import './style.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router.js'

createApp(App).use(router).mount('#app')
