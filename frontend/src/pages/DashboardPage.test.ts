import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
const { apiGet } = vi.hoisted(() => ({ apiGet: vi.fn() }));
vi.mock('../services/api', () => ({ apiGet, buildApiUrl: (path: string) => path }));
vi.mock('../stores/session', () => ({ useSession: () => ({ apiContext: { value: { tenantId: 'a' } } }) }));
import DashboardPage from './DashboardPage.vue';
const analytics = { summary: {total_runs:10,terminal_runs:10,success_rate:0.8}, daily_activity:[{date:'2026-11-14',total_runs:4},{date:'2026-11-15',total_runs:6}], status_breakdown:[{label:'completed',value:8},{label:'failed',value:2}],top_tickers:[{label:'AAPL',value:6},{label:'GOOGL',value:4}] };
function page() { return mount(DashboardPage,{global:{stubs:{
  PageHeader:{template:'<div><slot name="actions"/></div>'},
  MetricGrid:{props:['items'],template:'<div data-testid="metrics"><span v-for="item in items" :key="item.label">{{item.label}} {{item.value}}</span></div>'},
  Card:{template:'<div><slot name="title"/><slot name="content"/></div>'},
  Button:{props:['label'],template:'<button>{{label}}</button>'},
  Message:{template:'<div><slot/></div>'},Tag:{props:['value'],template:'<span>{{value}}</span>'},
  RouterLink:{props:['to'],template:'<a :href="to"><slot/></a>'},
}}}); }
describe('dashboard analysis charts',()=>{
  beforeEach(()=>{
    apiGet.mockReset();apiGet.mockImplementation(async(path:string)=>{
      if(path==='/api/analytics')return analytics;
      if(path==='/api/briefing/daily')return {summary:{headline:'Briefing summary'},recent_runs:[]};
      if(path==='/api/dashboard')return {summary:{watchlist_count:4,portfolio_position_count:2,alert_hit_count:7,bullish_focus_count:8,needs_attention_count:3,pinned_action_count:1},bullish_focus:[{}]};
      throw new Error('Unexpected '+path);
    });
  });
  it('loads only dashboard, briefing and analytics, with no notification panel or requests',async()=>{
    const wrapper=page();await flushPromises();
    expect(apiGet.mock.calls.map(c=>c[0]).sort()).toEqual(['/api/dashboard','/api/briefing/daily','/api/analytics'].sort());
    expect(wrapper.find('select').exists()).toBe(false);
    expect(wrapper.find('[data-testid="activity-chart"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="status-chart"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="ticker-chart"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('80%');expect(wrapper.text()).toContain('Briefing summary');
    expect(wrapper.get('[data-testid="metrics"]').text()).toMatch(/触发提醒 7|Triggered alerts 7/);
    expect(wrapper.text()).toMatch(/看多重点8|Bullish Focus8/);
  });
  it('shows empty states rather than generating invented data',async()=>{
    apiGet.mockImplementation(async(path:string)=>path==='/api/analytics'?{summary:{total_runs:0,terminal_runs:0,success_rate:0},daily_activity:[],status_breakdown:[],top_tickers:[]}:{});
    const wrapper=page();await flushPromises();
    expect(wrapper.find('svg').exists()).toBe(false);
    expect(wrapper.text()).not.toContain('0%');
    expect(wrapper.text()).toMatch(/暂无分析数据|No analysis data yet/);
  });
});
