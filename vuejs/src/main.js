import './assets/main.css'
import axios from 'axios'
import { createPinia } from "pinia";
import 'primeicons/primeicons.css'
import Toast from "vue-toastification";
import "vue-toastification/dist/index.css";
import router from './router';
import { VueMasonryPlugin } from "vue-masonry";
import { autoAnimatePlugin } from '@formkit/auto-animate/vue';
import * as lucideIcons from 'lucide-vue-next'
import { installAuthRefreshInterceptor } from '@/api/sessionRefresh'
import { bus } from '@/events/bus'

axios.defaults.withCredentials = true

const readCookie = (name) => {
  const prefix = `${encodeURIComponent(name)}=`
  const entry = document.cookie.split('; ').find((item) => item.startsWith(prefix))
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null
}

axios.interceptors.request.use(async (config) => {
  const method = (config.method || 'get').toLowerCase()
  if (['post', 'put', 'patch', 'delete'].includes(method)) {
    let csrfToken = readCookie('csrf_token')
    if (!csrfToken) {
      const response = await axios.get('/api/users/csrf', { withCredentials: true })
      csrfToken = response.data.csrf_token
    }
    config.headers = config.headers || {}
    config.headers['X-CSRF-Token'] = csrfToken
  }
  return config
})

installAuthRefreshInterceptor(axios)




import { createApp } from 'vue'
import App from './App.vue'
import { i18n, initDocumentLang } from '@/i18n'

const app = createApp(App)

Object.entries(lucideIcons).forEach(([name, component]) => {
  app.component(name, component)
})

app.config.globalProperties.emitter = bus

initDocumentLang()
app.use(createPinia());
app.use(i18n)
app.use(autoAnimatePlugin)
app.use(VueMasonryPlugin)
app.use(router);
app.use(Toast);
app.mount('#app')