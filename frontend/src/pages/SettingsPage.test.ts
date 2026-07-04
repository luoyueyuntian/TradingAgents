import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SettingsPage from './SettingsPage.vue';

const { apiGet, apiPut } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
}));

vi.mock('../services/api', () => ({
  apiGet,
  apiPut,
}));

const session = {
  apiContext: { value: { tenantId: 'tenant-a' } },
  isAdmin: { value: true },
  canWrite: { value: true },
  canAnalyze: { value: true },
};

vi.mock('../stores/session', () => ({
  useSession: () => session,
}));

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type', 'icon', 'severity'],
  template: `
    <button :type="type || 'button'" :disabled="disabled" @click="$emit('click', $event)">
      {{ label }}<slot />
    </button>
  `,
};

const InputTextStub = {
  props: ['modelValue', 'type', 'placeholder', 'disabled'],
  emits: ['update:modelValue'],
  template: `
    <input
      :type="type || 'text'"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="$emit('update:modelValue', $event.target.value)"
    >
  `,
};

const SelectStub = {
  props: ['modelValue', 'options', 'optionLabel', 'optionValue', 'disabled'],
  emits: ['update:modelValue', 'change'],
  template: `
    <select
      :value="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.value); $emit('change', $event)"
    >
      <option v-for="option in options" :key="option[optionValue || 'value']" :value="option[optionValue || 'value']">
        {{ option[optionLabel || 'label'] }}
      </option>
    </select>
  `,
};

const TextareaStub = {
  props: ['modelValue', 'rows', 'autoResize'],
  emits: ['update:modelValue'],
  template: `
    <textarea
      :value="modelValue"
      :rows="rows"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  `,
};

function mountPage() {
  return mount(SettingsPage, {
    global: {
      stubs: {
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        InputText: InputTextStub,
        Message: { template: '<div><slot /></div>' },
        PageHeader: { template: '<div><slot name="actions" /></div>' },
        Select: SelectStub,
        Textarea: TextareaStub,
      },
    },
  });
}

function llmFields(wrapper: ReturnType<typeof mountPage>) {
  const inputs = wrapper.findAll('input');
  const selects = wrapper.findAll('select');
  return {
    provider: selects[0],
    quick: selects[1],
    deep: selects[2],
    temperature: inputs[0],
    backendUrl: inputs[1],
    apiKey: inputs[2],
  };
}

describe('SettingsPage', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPut.mockReset();
  });

  it('shows provider-supported model dropdowns and resets them when the provider changes', async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path === '/api/settings') {
        return {
          api_keys: {
            openai: '***',
            mimo: '',
            ollama: '',
          },
          llm: {
            provider: 'openai',
            quick_think_model: 'gpt-5.4-mini',
            deep_think_model: 'gpt-5.5',
            backend_url: 'https://saved.example/v1',
            temperature: 0.2,
          },
          analysis: {},
          data: {},
          security: {},
          integrations: {},
        };
      }
      if (path === '/api/providers') {
        return [
          {
            provider: 'openai',
            display_name: 'OpenAI',
            quick_models: [{ label: 'GPT-5.4 Mini', value: 'gpt-5.4-mini' }],
            deep_models: [{ label: 'GPT-5.5', value: 'gpt-5.5' }],
            backend_url: null,
            api_key_env: 'OPENAI_API_KEY',
          },
          {
            provider: 'mimo',
            display_name: 'Xiaomi MiMo',
            quick_models: [{ label: 'MiMo 2.5', value: 'mimo-v2.5' }],
            deep_models: [{ label: 'MiMo 2.5 Pro', value: 'mimo-v2.5-pro' }],
            backend_url: 'https://api.xiaomimimo.com/v1',
            api_key_env: 'MIMO_API_KEY',
          },
          {
            provider: 'ollama',
            display_name: 'Ollama',
            quick_models: [{ label: 'llama3.1', value: 'llama3.1' }],
            deep_models: [{ label: 'llama3.1', value: 'llama3.1' }],
            backend_url: 'http://localhost:11434/v1',
            api_key_env: null,
          },
          {
            provider: 'kimi',
            display_name: 'Kimi',
            quick_models: [{ label: 'Custom model ID', value: 'custom' }],
            deep_models: [{ label: 'Custom model ID', value: 'custom' }],
            backend_url: 'https://api.moonshot.ai/v1',
            api_key_env: 'MOONSHOT_API_KEY',
          },
        ];
      }
      throw new Error(`Unexpected apiGet path: ${path}`);
    });

    const wrapper = mountPage();
    await flushPromises();

    const fields = llmFields(wrapper);

    expect(fields.provider?.element.value).toBe('openai');
    expect(fields.quick?.element.value).toBe('gpt-5.4-mini');
    expect(fields.deep?.element.value).toBe('gpt-5.5');
    expect(fields.backendUrl?.element.value).toBe('https://saved.example/v1');
    expect(fields.quick?.findAll('option').map((option) => option.text())).toEqual(['GPT-5.4 Mini']);
    expect(fields.deep?.findAll('option').map((option) => option.text())).toEqual(['GPT-5.5']);
    expect(wrapper.get('[data-testid="provider-api-key-field"]').text()).toContain('OPENAI_API_KEY');
    expect(fields.apiKey?.element.value).toBe('***');

    await fields.provider?.setValue('mimo');

    expect(fields.quick?.element.value).toBe('mimo-v2.5');
    expect(fields.deep?.element.value).toBe('mimo-v2.5-pro');
    expect(fields.backendUrl?.element.value).toBe('https://api.xiaomimimo.com/v1');
    expect(fields.quick?.findAll('option').map((option) => option.text())).toEqual(['MiMo 2.5']);
    expect(fields.deep?.findAll('option').map((option) => option.text())).toEqual(['MiMo 2.5 Pro']);
    expect(wrapper.get('[data-testid="provider-api-key-field"]').text()).toContain('MIMO_API_KEY');
    expect(fields.apiKey?.element.value).toBe('');

    await fields.provider?.setValue('openai');

    expect(fields.quick?.element.value).toBe('gpt-5.4-mini');
    expect(fields.deep?.element.value).toBe('gpt-5.5');
    expect(fields.backendUrl?.element.value).toBe('');
    expect(wrapper.get('[data-testid="provider-api-key-field"]').text()).toContain('OPENAI_API_KEY');

    await fields.provider?.setValue('ollama');

    expect(fields.quick?.element.value).toBe('llama3.1');
    expect(fields.deep?.element.value).toBe('llama3.1');

    expect(wrapper.find('[data-testid="provider-api-key-field"]').exists()).toBe(false);

    await fields.provider?.setValue('kimi');

    expect(fields.quick?.element.value).toBe('custom');
    expect(fields.deep?.element.value).toBe('custom');
    expect(wrapper.find('[data-testid="settings-quick-custom-model-input"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="settings-deep-custom-model-input"]').exists()).toBe(true);
  });

  it('saves the workspace default UI language from settings', async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path === '/api/settings') {
        return {
          api_keys: {},
          llm: {},
          analysis: {},
          workspace: {
            default_home_view: 'auto',
            default_ui_language: 'zh-CN',
          },
          data: {},
          security: {},
          integrations: {},
        };
      }
      if (path === '/api/providers') {
        return [
          {
            provider: 'openai',
            display_name: 'OpenAI',
            quick_models: [{ label: 'GPT-5.4 Mini', value: 'gpt-5.4-mini' }],
            deep_models: [{ label: 'GPT-5.5', value: 'gpt-5.5' }],
            backend_url: null,
          },
        ];
      }
      throw new Error(`Unexpected apiGet path: ${path}`);
    });
    apiPut.mockResolvedValue({});

    const wrapper = mountPage();
    await flushPromises();

    const selects = wrapper.findAll('select');
    await selects[3]?.setValue('en');
    await wrapper.findAll('button')[1]?.trigger('click');

    expect(apiPut).toHaveBeenCalledWith(
      '/api/settings',
      expect.objectContaining({
        workspace: expect.objectContaining({
          default_ui_language: 'en',
        }),
      }),
      session.apiContext.value,
    );
  });
});
