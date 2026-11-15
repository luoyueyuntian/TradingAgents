import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, nextTick, reactive, type Component } from 'vue';
import { createMemoryHistory, createRouter, RouterView } from 'vue-router';
import App from './App.vue';
const state = reactive({ loading: false, currentUser: null as { must_change_password: boolean } | null });
vi.mock('./stores/session', () => ({ useSession: () => ({ state, mustChangePassword: computed(() => Boolean(state.currentUser?.must_change_password)) }) }));

describe('authentication view transitions', () => {
  beforeEach(() => { state.loading=false; state.currentUser=null; });
  it.each([false,true])('hides the login form as soon as authentication succeeds while the next view loads (password change: %s)', async (changePassword) => {
    let finish!: (view: Component) => void;
    const target=changePassword?'/change-password':'/';
    const router=createRouter({history:createMemoryHistory(),routes:[
      {path:'/login',component:{template:'<form data-testid="login-form"><input /></form>'}},
      {path:target,component:()=>new Promise<Component>(resolve=>{finish=resolve;})},
    ]});
    await router.push('/login');
    const wrapper=mount(App,{global:{plugins:[router],stubs:{AppLayout:{components:{RouterView},template:'<main><RouterView /></main>'}}}});
    expect(wrapper.find('[data-testid="login-form"]').exists()).toBe(true);
    state.currentUser={must_change_password:changePassword};
    const navigation=router.replace(target);await flushPromises();
    expect(wrapper.find('[data-testid="login-form"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="auth-transition"]').exists()).toBe(true);
    finish({template:'<div data-testid="target-view">Ready</div>'});await navigation;await flushPromises();
    expect(wrapper.find('[data-testid="target-view"]').exists()).toBe(true);
    wrapper.unmount();
  });
  it('keeps the form mounted while submitting so failed sign-in does not reset user input',async()=>{
    const router=createRouter({history:createMemoryHistory(),routes:[{path:'/login',component:{template:'<form data-testid="login-form"><input /></form>'}}]});
    await router.push('/login');
    const wrapper=mount(App,{global:{plugins:[router],stubs:{AppLayout:true}}});
    state.loading=true;await nextTick();
    expect(wrapper.find('[data-testid="login-form"]').exists()).toBe(true);
    state.loading=false;await nextTick();wrapper.unmount();
  });
  it('offers recovery if a lazy view fails without bringing the login form back',async()=>{
    let fail!: (error: Error) => void;
    const router=createRouter({history:createMemoryHistory(),routes:[
      {path:'/login',component:{template:'<form data-testid="login-form" />'}},
      {path:'/',component:()=>new Promise<Component>((_resolve,reject)=>{fail=reject;})},
    ]});
    await router.push('/login');
    const wrapper=mount(App,{global:{plugins:[router],stubs:{AppLayout:true,Button:{props:['label'],template:'<button>{{label}}</button>'}}}});
    state.currentUser={must_change_password:false};
    const navigation=router.replace('/').catch(()=>undefined);await flushPromises();
    fail(new Error('chunk unavailable'));await navigation;await flushPromises();
    expect(wrapper.find('[data-testid="login-form"]').exists()).toBe(false);
    expect(wrapper.text()).toMatch(/页面加载失败|Could not load the page/);
    expect(wrapper.find('button').exists()).toBe(true);wrapper.unmount();
  });

});
