<template>
  <label class="field-row">
    <span class="field-row__label">{{ label }}</span>
    <slot />
  </label>
</template>

<script setup lang="ts">
defineProps<{ label: string }>();
</script>

<style scoped>
.field-row {
  display: grid;
  gap: 8px;
}

.field-row__label {
  color: var(--muted-foreground);
  font: 600 12px/1.2 var(--font-ui);
}
</style>
