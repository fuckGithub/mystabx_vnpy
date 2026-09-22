<!-- WangEditor 富文本编辑器 插件地址：https://www.wangeditor.com/ -->
<template>
  <div class="editor-wrapper">
    <Toolbar class="editor-toolbar" :editor="editorRef" :mode="mode" :defaultConfig="toolbarConfig" />
    <Editor
      :style="{ height: height, overflowY: 'hidden' }"
      v-model="modelValue"
      :mode="mode"
      :defaultConfig="editorConfig"
      @onCreated="onCreateEditor" />
  </div>
</template>

<script setup lang="ts">
import '@wangeditor-next/editor/dist/css/style.css'
import { onBeforeUnmount, onMounted, shallowRef, computed } from 'vue'
import { Editor, Toolbar } from '@wangeditor-next/editor-for-vue'
import { useUserStore } from '@stores/modules/user.store'
import { EmojiText } from '@utils/ui'
import { IDomEditor, IToolbarConfig, IEditorConfig } from '@wangeditor-next/editor'
import request from '@utils/http'
import type { AxiosResponse } from 'axios'

defineOptions({ name: 'FaWangEditor' })

type InsertFnType = (url: string, alt: string, href: string) => void

const { VITE_API_URL } = import.meta.env

interface Props {
  height?: string
  toolbarKeys?: string[]
  insertKeys?: { index: number; keys: string[] }
  excludeKeys?: string[]
  mode?: 'default' | 'simple'
  placeholder?: string
  uploadConfig?: {
    maxFileSize?: number
    maxNumberOfFiles?: number
    server?: string
    isCustomUpload?: boolean
  }
}

const props = withDefaults(defineProps<Props>(), {
  height: '500px',
  mode: 'default',
  placeholder: '请输入内容...',
  excludeKeys: () => ['fontFamily'],
  isCustomUpload: false,
})

const modelValue = defineModel<string>({ required: true })

const editorRef = shallowRef<IDomEditor>()
const userStore = useUserStore()

const DEFAULT_UPLOAD_CONFIG = {
  maxFileSize: 3 * 1024 * 1024,
  maxNumberOfFiles: 10,
  fieldName: 'file',
  allowedFileTypes: ['image/*'],
} as const

const uploadServer = computed(() => props.uploadConfig?.server || `${VITE_API_URL}/common/upload/wangeditor`)

const mergedUploadConfig = computed(() => ({
  ...DEFAULT_UPLOAD_CONFIG,
  ...props.uploadConfig,
}))

const toolbarConfig = computed((): Partial<IToolbarConfig> => {
  const config: Partial<IToolbarConfig> = {}

  if (props.toolbarKeys && props.toolbarKeys.length > 0) {
    config.toolbarKeys = props.toolbarKeys
  }

  if (props.insertKeys) {
    config.insertKeys = props.insertKeys
  }

  if (props.excludeKeys && props.excludeKeys.length > 0) {
    config.excludeKeys = props.excludeKeys
  }

  return config
})

const editorConfig: Partial<IEditorConfig> = {
  placeholder: props.placeholder,
  MENU_CONF: {
    uploadImage: {
      fieldName: mergedUploadConfig.value.fieldName,
      maxFileSize: mergedUploadConfig.value.maxFileSize,
      maxNumberOfFiles: mergedUploadConfig.value.maxNumberOfFiles,
      allowedFileTypes: mergedUploadConfig.value.allowedFileTypes,
      server: uploadServer.value,
      headers: {
        Authorization: userStore.accessToken,
      },
      onSuccess() {
        ElMessage.success(`图片上传成功 ${EmojiText[200]}`)
      },
      onError(file: File, err: any, res: any) {
        console.error('图片上传失败:', err, res)
        ElMessage.error(`图片上传失败 ${EmojiText[500]}`)
      },
    },
  },
}

const uploadConfig = props.uploadConfig
if (uploadConfig?.isCustomUpload && uploadConfig.server && editorConfig.MENU_CONF) {
  const uploadServerUrl = uploadConfig.server
  editorConfig.MENU_CONF.uploadImage.customUpload = async (file: File, insertFn: InsertFnType) => {
    try {
      const formData = new FormData()
      formData.append(mergedUploadConfig.value.fieldName, file)

      type UploadImagePayload = { url: string; alt?: string; href?: string }
      const response = await request.post<
        ApiResponse<UploadImagePayload>,
        AxiosResponse<ApiResponse<UploadImagePayload>>
      >(uploadServerUrl, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          Authorization: userStore.accessToken,
        },
      })

      const { url, alt = '', href = '' } = response.data.data ?? ({} as Record<string, string>)

      if (!url) {
        throw new Error('上传失败，请检查服务端配置')
      }

      insertFn(url, alt, href)
      ElMessage.success(`图片上传成功 ${EmojiText[200]}`)
    } catch (error) {
      console.error('图片上传失败:', error)
      ElMessage.error(`图片上传失败 ${EmojiText[500]}`)
    }
  }
}

const onCreateEditor = (editor: IDomEditor) => {
  editorRef.value = editor
}

defineExpose({
  getEditor: () => editorRef.value,
  setHtml: (html: string) => editorRef.value?.setHtml(html),
  getHtml: () => editorRef.value?.getHtml(),
  clear: () => editorRef.value?.clear(),
  focus: () => editorRef.value?.focus(),
})

onMounted(() => {})

onBeforeUnmount(() => {
  const editor = editorRef.value
  if (editor) {
    editor.destroy()
  }
})
</script>

<style lang="scss">
@use './style';
</style>
