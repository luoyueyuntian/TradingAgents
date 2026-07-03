import { defineConfig, presetWind3 } from 'unocss';

export default defineConfig({
  presets: [
    presetWind3({
      // Keep utilities explicit so existing semantic classes are not treated as atoms.
      prefix: 'uno-',
      preflight: true,
    }),
  ],
  theme: {
    fontFamily: {
      sans: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    },
  },
  preflights: [
    {
      getCSS: () => `
*, ::before, ::after {
  box-sizing: border-box;
}

button,
input,
textarea,
select {
  font: inherit;
}
`,
    },
  ],
});
