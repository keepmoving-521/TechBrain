import js from "@eslint/js";
import prettier from "eslint-config-prettier";
import pluginVue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";

const browserGlobals = {
  console: "readonly",
  crypto: "readonly",
  document: "readonly",
  globalThis: "readonly",
  window: "readonly",
};

const nodeGlobals = {
  process: "readonly",
};

export default tseslint.config(
  {
    ignores: ["dist", "node_modules", "coverage", "*.config.js", "*.config.d.ts"],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs["flat/recommended"],
  prettier,
  {
    files: ["**/*.{ts,vue}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: browserGlobals,
      parserOptions: {
        parser: tseslint.parser,
      },
    },
    rules: {
      "vue/multi-word-component-names": "off",
      "vue/no-reserved-component-names": "off",
    },
  },
  {
    files: ["**/*.test.ts", "vitest.config.ts"],
    languageOptions: {
      globals: nodeGlobals,
    },
  },
);
