<template>
  <Dialog
    :visible="visible"
    modal
    :header="title"
    :style="{ width: 'min(560px, 94vw)' }"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="uno-grid uno-gap-4">
      <p class="uno-text-sm uno-text-[#4c6265]">{{ description }}</p>
      <code data-testid="password-result" class="uno-rounded-lg uno-bg-[#f4f7f7] uno-px-3 uno-py-2 uno-font-mono">
        {{ password }}
      </code>
    </div>

    <template #footer>
      <div class="uno-flex uno-justify-end uno-gap-2">
        <Button data-testid="copy-password" :label="t('users.copyPassword')" severity="secondary" @click="copyPassword" />
        <Button :label="t('common.cancel')" @click="emit('update:visible', false)" />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';

import { useI18n } from '../i18n';

const props = withDefaults(defineProps<{
  visible: boolean;
  password: string;
  title?: string;
  description?: string;
}>(), {
  title: '',
  description: '',
});

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
}>();

const { t } = useI18n();

async function copyPassword() {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(props.password);
  }
}
</script>
