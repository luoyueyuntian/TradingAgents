<template>
  <Dialog
    :visible="visible"
    modal
    :header="title"
    :style="{ width: 'min(720px, 94vw)' }"
    @update:visible="emit('update:visible', $event)"
  >
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <div class="uno-grid uno-gap-4">
      <slot />
    </div>
    <template #footer>
      <div class="uno-flex uno-justify-end uno-gap-2">
        <Button :label="cancelLabel" severity="secondary" text @click="emit('update:visible', false)" />
        <Button :label="saveLabel" :loading="loading" :disabled="disabled" @click="emit('submit')" />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import Message from 'primevue/message';

withDefaults(defineProps<{
  visible: boolean;
  title: string;
  saveLabel: string;
  cancelLabel?: string;
  loading?: boolean;
  disabled?: boolean;
  error?: string;
}>(), {
  cancelLabel: 'Cancel',
  loading: false,
  disabled: false,
  error: '',
});

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'submit'): void;
}>();
</script>
