<script setup>
defineProps({
  label: { type: String, required: true },
  /** 'top' | 'bottom' */
  placement: { type: String, default: 'bottom' },
});
</script>

<template>
  <button type="button" class="ui-icon-tip group relative inline-flex items-center justify-center">
    <slot />
    <span
      class="ui-icon-tip__label"
      :class="placement === 'top' ? 'ui-icon-tip__label--top' : 'ui-icon-tip__label--bottom'"
    >{{ label }}</span>
  </button>
</template>
