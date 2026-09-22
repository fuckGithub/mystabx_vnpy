<script lang="ts" setup>
import { deepClone, isFunction } from '@wot-ui/ui/common/util'
import { storeToRefs } from 'pinia'
import { useDialog } from '@wot-ui/ui'
import { getCurrentPath } from '@/utils'

const { messageOptions, currentPage } = storeToRefs(useGlobalMessage())

const messageBox = useDialog('globalMessage')
const currentPath = getCurrentPath()

// #ifdef MP-ALIPAY
const hackAlipayVisible = ref(false)

nextTick(() => {
  hackAlipayVisible.value = true
})
// #endif

watch(
  () => messageOptions.value,
  (newVal) => {
    if (newVal) {
      if (currentPage.value === currentPath) {
        const option = deepClone(newVal)
        messageBox
          .show(option)
          .then((res) => {
            if (isFunction(option.success)) {
              option.success(res)
            }
          })
          .catch((err) => {
            if (isFunction(option.fail)) {
              option.fail(err)
            }
          })
      }
    } else {
      messageBox.close()
    }
  }
)
</script>

<script lang="ts">
export default {
  options: {
    virtualHost: true,
    addGlobalClass: true,
    styleIsolation: 'shared',
  },
}
</script>

<template>
  <!-- #ifdef MP-ALIPAY -->
  <wd-dialog v-if="hackAlipayVisible" selector="globalMessage" />
  <!-- #endif -->
  <!-- #ifndef MP-ALIPAY -->
  <wd-dialog selector="globalMessage" />
  <!-- #endif -->
</template>
