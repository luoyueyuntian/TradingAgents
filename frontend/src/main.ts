import 'virtual:uno.css';
import 'primeicons/primeicons.css';
import './theme/global.css';

import PrimeVue from 'primevue/config';
import { createApp } from 'vue';

import App from './App.vue';
import { router } from './router';
import { tradingAgentsPreset } from './theme/preset';

createApp(App)
  .use(router)
  .use(PrimeVue, {
    theme: {
      preset: tradingAgentsPreset,
      options: {
        darkModeSelector: '.ta-dark',
      },
    },
  })
  .mount('#app');

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(() => undefined);
  });
}
