<template>
  <section class="uno-grid uno-gap-4">
    <PageHeader
      :eyebrow="t('users.eyebrow')"
      :title="t('users.title')"
      :description="t('users.description')"
    >
      <template #actions>
        <Button
          icon="pi pi-refresh"
          :label="t('common.refresh')"
          severity="secondary"
          @click="refreshUsers"
        />
      </template>
    </PageHeader>

    <AdminUserDirectory
      ref="directory"
      list-path="/api/admin/users"
      create-path="/api/admin/users"
      :update-path="userPath"
      :delete-path="userPath"
    />
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import { ref } from 'vue';

import PageHeader from '../components/PageHeader.vue';
import AdminUserDirectory from '../components/AdminUserDirectory.vue';
import { useI18n } from '../i18n';

const { t } = useI18n();
const directory = ref<{ loadUsers: () => Promise<void> } | null>(null);

function userPath(userId: string) {
  return `/api/admin/users/${encodeURIComponent(userId)}`;
}

function refreshUsers() {
  void directory.value?.loadUsers();
}
</script>
