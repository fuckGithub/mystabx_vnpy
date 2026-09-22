declare module '@wangeditor-next/editor-for-vue' {
  import { Component } from 'vue'
  export const Editor: Component
  export const Toolbar: Component
}

declare module '@wangeditor-next/editor' {
  export interface IDomEditor {
    setHtml(html: string): void
    getHtml(): string
    clear(): void
    focus(): void
    destroy(): void
    on(event: string, callback: () => void): void
    getEditableContainer(): HTMLElement
    id: string
  }

  export interface IToolbarConfig {
    toolbarKeys?: string[]
    insertKeys?: { index: number; keys: string[] }
    excludeKeys?: string[]
  }

  export interface IEditorConfig {
    placeholder?: string
    MENU_CONF?: {
      uploadImage?: {
        fieldName?: string
        maxFileSize?: number
        maxNumberOfFiles?: number
        allowedFileTypes?: string[]
        server?: string
        headers?: Record<string, string>
        onSuccess?: () => void
        onError?: (file: File, err: any, res: any) => void
        customUpload?: (file: File, insertFn: (url: string, alt: string, href: string) => void) => Promise<void>
      }
    }
  }
}
