/** Three chromatic families; every other interface color is neutral. */
export const palette = {
  brand: { 50: '#fff0eb', 100: '#fbe4dc', 200: '#f6cabc', 300: '#eda990', 400: '#e08162', 500: '#d65a3a', 600: '#b94328', 700: '#92351f', 800: '#742c1d', 900: '#5a241b', 950: '#32130e' },
  info: { 50: '#f0f4f7', 100: '#e2eaf0', 200: '#c7d6e1', 300: '#a2b8c9', 400: '#7895ad', 500: '#4b6680', 600: '#3d556c', 700: '#314558', 800: '#283847', 900: '#222e39', 950: '#121920' },
  success: { 50: '#f0f5f1', 100: '#e4ece6', 200: '#cbdacd', 300: '#abc2af', 400: '#829f89', 500: '#526c59', 600: '#415846', 700: '#344638', 800: '#2a392e', 900: '#232e26', 950: '#121a14' },
  neutral: { 0: '#ffffff', 50: '#fafafa', 100: '#f5f5f5', 200: '#e5e5e5', 300: '#d4d4d4', 400: '#a3a3a3', 500: '#737373', 600: '#525252', 700: '#404040', 800: '#262626', 900: '#171717', 950: '#0a0a0a' },
};
// White button labels need a darker red than the logo's brand swatch.
export const statusRed = { ...palette.brand, 500: palette.brand[600], 600: palette.brand[700], 700: palette.brand[800] };
export const interfaceColors = {
  red: statusRed, orange: statusRed, amber: statusRed, yellow: statusRed, rose: statusRed, pink: statusRed,
  blue: palette.info, sky: palette.info, cyan: palette.info, indigo: palette.info, violet: palette.info, purple: palette.info, fuchsia: palette.info,
  green: palette.success, emerald: palette.success, lime: palette.success, teal: palette.success,
  slate: palette.neutral, gray: palette.neutral, zinc: palette.neutral, neutral: palette.neutral, stone: palette.neutral,
};
