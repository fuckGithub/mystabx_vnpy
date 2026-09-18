<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { basicSetup } from "codemirror";
import { EditorView, keymap } from "@codemirror/view";
import { EditorState, Compartment } from "@codemirror/state";
import { indentWithTab } from "@codemirror/commands";
import { python } from "@codemirror/lang-python";
import { defaultHighlightStyle, syntaxHighlighting } from "@codemirror/language";

const props = withDefaults(
  defineProps<{
    modelValue: string;
    readonly?: boolean;
    fontSize?: number;
  }>(),
  {
    readonly: false,
    fontSize: 13,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const hostRef = ref<HTMLElement | null>(null);
let view: EditorView | null = null;
const fontCompartment = new Compartment();
const editableCompartment = new Compartment();
let applyingExternal = false;

function fontTheme(size: number) {
  return EditorView.theme({
    "&": {
      height: "100%",
      fontSize: `${size}px`,
    },
    ".cm-scroller": {
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
      lineHeight: "1.55",
      overflow: "auto",
    },
    ".cm-content": {
      padding: "12px 0",
      caretColor: "#1677ff",
    },
    ".cm-gutters": {
      backgroundColor: "#f1f5f9",
      color: "#94a3b8",
      border: "none",
      borderRight: "1px solid #e2e8f0",
    },
    ".cm-activeLineGutter": {
      backgroundColor: "#e2e8f0",
    },
    ".cm-activeLine": {
      backgroundColor: "rgba(22, 119, 255, 0.06)",
    },
    "&.cm-focused": {
      outline: "none",
    },
    "&.cm-editor": {
      backgroundColor: "#ffffff",
    },
  });
}

onMounted(() => {
  if (!hostRef.value) return;
  const state = EditorState.create({
    doc: props.modelValue || "",
    extensions: [
      basicSetup,
      python(),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      keymap.of([indentWithTab]),
      fontCompartment.of(fontTheme(props.fontSize)),
      editableCompartment.of([
        EditorView.editable.of(!props.readonly),
        EditorState.readOnly.of(props.readonly),
      ]),
      EditorView.updateListener.of((update) => {
        if (!update.docChanged || applyingExternal) return;
        emit("update:modelValue", update.state.doc.toString());
      }),
    ],
  });
  view = new EditorView({
    state,
    parent: hostRef.value,
  });
});

watch(
  () => props.modelValue,
  (next) => {
    if (!view) return;
    const cur = view.state.doc.toString();
    if (next === cur) return;
    applyingExternal = true;
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: next || "" },
    });
    applyingExternal = false;
  },
);

watch(
  () => props.fontSize,
  (size) => {
    view?.dispatch({
      effects: fontCompartment.reconfigure(fontTheme(size)),
    });
  },
);

watch(
  () => props.readonly,
  (ro) => {
    view?.dispatch({
      effects: editableCompartment.reconfigure([
        EditorView.editable.of(!ro),
        EditorState.readOnly.of(ro),
      ]),
    });
  },
);

onBeforeUnmount(() => {
  view?.destroy();
  view = null;
});
</script>

<template>
  <div ref="hostRef" class="python-code-editor" />
</template>

<style scoped>
.python-code-editor {
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  background: #fff;
}

.python-code-editor :deep(.cm-editor) {
  height: 100%;
}

.python-code-editor :deep(.cm-editor.cm-focused) {
  box-shadow: inset 0 0 0 1px rgba(22, 119, 255, 0.35);
}
</style>
