<template>
  <button class="base-button" :class="[`base-button--${variant}`, { 'is-icon': iconOnly }]" :type="type">
    <slot />
  </button>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: "primary" | "secondary" | "ghost" | "danger";
    type?: "button" | "submit";
    iconOnly?: boolean;
  }>(),
  {
    variant: "secondary",
    type: "button",
    iconOnly: false
  }
);
</script>

<style scoped>
.base-button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 0 14px;
  font: 600 13px/1 var(--font-ui);
  color: var(--foreground);
  cursor: pointer;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, background 180ms ease;
}

.base-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.base-button:not(:disabled):hover {
  transform: translateY(-1px);
}

.base-button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.base-button--primary {
  border-color: transparent;
  background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
  color: white;
  box-shadow: var(--shadow-accent);
}

.base-button--secondary {
  border-color: var(--border);
  background: white;
  color: var(--foreground);
}

.base-button--secondary:hover {
  border-color: rgba(0, 82, 255, 0.3);
  box-shadow: var(--shadow-sm);
}

.base-button--ghost {
  background: transparent;
  color: var(--muted-foreground);
}

.base-button--ghost:hover {
  background: var(--muted);
  color: var(--foreground);
}

.base-button--danger {
  border-color: rgba(220, 38, 38, 0.16);
  background: rgba(220, 38, 38, 0.08);
  color: #b91c1c;
}

.is-icon {
  width: 40px;
  padding: 0;
}
</style>
