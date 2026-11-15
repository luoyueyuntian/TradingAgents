import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';
import { interfaceColors, palette } from './palette';

export const tradingAgentsPreset = definePreset(Aura, {
  primitive: interfaceColors,
  semantic: {
    primary: palette.brand,
    focusRing: { color: '{primary.600}', width: '2px', style: 'solid', offset: '2px' },
    colorScheme: {
      light: {
        surface: palette.neutral,
        primary: { color: '{primary.600}', contrastColor: '#ffffff', hoverColor: '{primary.700}', activeColor: '{primary.800}' },
        highlight: { background: '{primary.50}', focusBackground: '{primary.100}', color: '{primary.700}', focusColor: '{primary.800}' },
      },
    },
  },
});
