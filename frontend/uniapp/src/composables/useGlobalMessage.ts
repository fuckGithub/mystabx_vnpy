import { CommonUtil } from '@wot-ui/ui'
import type { DialogOptionsWithCallBack, DialogResult } from '@wot-ui/ui/components/wd-dialog/types'
import { defineStore } from 'pinia'
import { getCurrentPath } from '@/utils'

export type GlobalMessageOptions = DialogOptionsWithCallBack & {
  success?: (res: DialogResult) => void
  fail?: (res: DialogResult) => void
}

interface GlobalMessage {
  messageOptions: GlobalMessageOptions | null
  currentPage: string
}

export const useGlobalMessage = defineStore('global-message', {
  state: (): GlobalMessage => ({
    messageOptions: null,
    currentPage: '',
  }),
  actions: {
    show(option: GlobalMessageOptions | string) {
      this.currentPage = getCurrentPath()
      this.messageOptions = {
        ...(CommonUtil.isString(option) ? { title: option } : option),
        cancelButtonProps: {
          round: false,
        },
        confirmButtonProps: {
          round: false,
        },
      }
    },
    alert(option: GlobalMessageOptions | string) {
      const messageOptions = CommonUtil.deepMerge(
        { type: 'alert' },
        CommonUtil.isString(option) ? { title: option } : option
      ) as GlobalMessageOptions
      messageOptions.showCancelButton = false
      this.show(messageOptions)
    },
    confirm(option: GlobalMessageOptions | string) {
      const messageOptions = CommonUtil.deepMerge(
        { type: 'confirm' },
        CommonUtil.isString(option) ? { title: option } : option
      ) as GlobalMessageOptions
      messageOptions.showCancelButton = true
      this.show(messageOptions)
    },
    prompt(option: GlobalMessageOptions | string) {
      const messageOptions = CommonUtil.deepMerge(
        { type: 'prompt' },
        CommonUtil.isString(option) ? { title: option } : option
      ) as GlobalMessageOptions
      messageOptions.showCancelButton = true
      this.show(messageOptions)
    },
    close() {
      this.messageOptions = null
      this.currentPage = ''
    },
  },
})
