import uniHelper from '@uni-helper/eslint-config'
import prettierConfig from 'eslint-config-prettier'
import prettierPlugin from 'eslint-plugin-prettier'
import stylistic from '@stylistic/eslint-plugin'

export default uniHelper(
  {
    unocss: true,
    vue: true,
    markdown: false,
    stylistic: false,
    ignores: [
      // 忽略uni_modules目录
      '**/uni_modules/',
      // 忽略原生插件目录
      '**/nativeplugins/',
      'dist',
      // unplugin-auto-import 生成的类型文件，每次提交都改变，所以加入这里吧，与 .gitignore 配合使用
      'auto-import.d.ts',
      // vite-plugin-uni-pages 生成的类型文件，每次切换分支都一堆不同的，所以直接 .gitignore
      'uni-pages.d.ts',
      // 插件生成的文件
      'src/pages.json',
      'src/manifest.json',
      // 忽略自动生成文件
      'src/service/**',
    ],
    // https://eslint-config.antfu.me/rules
    rules: {
      // ----- 纯 lint 规则（关闭不需要的检查） -----
      'no-useless-return': 'off',
      'no-console': 'off',
      'no-unused-vars': 'off',
      'vue/no-unused-refs': 'off',
      'unused-imports/no-unused-vars': 'off',
      'eslint-comments/no-unlimited-disable': 'off',
      'jsdoc/check-param-names': 'off',
      'jsdoc/require-returns-description': 'off',
      'ts/no-empty-object-type': 'off',
      'no-extend-native': 'off',

      // ----- 结构规则 -----
      'vue/block-order': [
        'error',
        {
          order: [['script', 'template'], 'style'],
        },
      ],

      // eslint-config-prettier 已关闭绝大多数格式化冲突规则
      // 此处只补它未覆盖的
      'perfectionist/sort-imports': 'off',
      'vue/first-attribute-linebreak': 'off',
    },
  },
  prettierConfig,
  {
    plugins: {
      prettier: prettierPlugin,
      style: stylistic,
    },
    rules: {
      'prettier/prettier': 'error',
    },
  }
)
