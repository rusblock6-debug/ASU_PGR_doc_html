export default {
  plugins: {
    'postcss-mixins': {
      mixinsFiles: ['./src/app/styles/mixins/*.css'],
    },
    'postcss-nesting': {},
    'postcss-preset-mantine': {},
    'postcss-simple-vars': {
      variables: {
        'mantine-breakpoint-xs': '36em',
        'mantine-breakpoint-sm': '48em',
        'mantine-breakpoint-md': '62em',
        'mantine-breakpoint-lg': '75em',
        'mantine-breakpoint-xl': '88em',
        'breakpoint-sm': '640px',
        'breakpoint-md': '768px',
        'breakpoint-lg': '1024px',
        'breakpoint-xl': '1280px',
        'breakpoint-xxl': '1440px',
      },
    },
  },
};
