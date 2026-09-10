export default defineAppConfig({
  ui: {
    colors: {
      primary: 'brand',
      secondary: 'violet',
      success: 'green',
      info: 'sky',
      warning: 'amber',
      error: 'red',
      neutral: 'slate',
    },
    button: {
      defaultVariants: {
        color: 'primary',
        size: 'md',
        variant: 'solid',
      },
    },
    input: {
      defaultVariants: {
        color: 'primary',
        size: 'md',
        variant: 'outline',
      },
    },
    select: {
      defaultVariants: {
        color: 'primary',
        size: 'md',
        variant: 'outline',
      },
    },
    textarea: {
      defaultVariants: {
        color: 'primary',
        size: 'md',
        variant: 'outline',
      },
    },
    formField: {
      defaultVariants: {
        size: 'md',
      },
    },
  },
})
