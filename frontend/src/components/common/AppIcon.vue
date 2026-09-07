<template><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="icons[name] || icons.file" /></svg></template>
<script setup>
defineProps({ name: String });
const icons = {
  grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  tasks: 'M8 5h13 M8 12h13 M8 19h13 M3 5h.01 M3 12h.01 M3 19h.01',
  file: 'M14 2H5v20h14V7z M14 2v6h5 M8 12h8 M8 16h6',
  book: 'M3 4h6a3 3 0 0 1 3 3v14a4 4 0 0 0-4-2H3z M21 4h-6a3 3 0 0 0-3 3 M21 4v15h-5a4 4 0 0 0-4 2',
  arrow: 'M5 12h14 M14 7l5 5-5 5', plus: 'M12 5v14 M5 12h14',
  upload: 'M12 16V3 M7 8l5-5 5 5 M4 16v5h16v-5',
  search: 'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  refresh: 'M20 7a9 9 0 1 0 1 8 M20 2v6h-6',
  settings: 'M4 7h16 M4 17h16 M8 4v6 M16 14v6',
  chevron: 'M9 5l7 7-7 7', close: 'M6 6l12 12 M6 18L18 6',
  shield: 'M12 2l9 4v6c0 5-9 10-9 10S3 17 3 12V6z M8 12l3 3 5-6',
  clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M12 7v5l3 2',
  check: 'M5 12l4 4L19 6', download: 'M12 3v12 M7 10l5 5 5-5 M4 17v4h16v-4',
  activity: 'M2 12h5l3-8 4 16 3-8h5', menu: 'M4 6h16 M4 12h16 M4 18h16'
};
</script>
