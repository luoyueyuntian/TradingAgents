<template>
  <div class="uno-mb-4 uno-flex uno-items-start uno-justify-between uno-gap-4">
    <div>
      <p class="uno-m-0 uno-text-xs uno-font-700 uno-uppercase uno-text-[#6f8183]">{{ eyebrow }}</p>
      <h1 class="uno-mb-[0.3rem] uno-mt-[0.15rem] uno-text-[1.7rem] uno-tracking-normal">{{ title }}</h1>
      <p class="uno-m-0 uno-max-w-[760px] uno-text-[#6f8183]">{{ description }}</p>
    </div>
    <div class="uno-flex uno-gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  eyebrow: string;
  title: string;
  description: string;
}>();
</script>
