<!-- 个人中心（Art 模版布局 + 当前用户接口） -->
<template>
  <div class="w-full h-full p-0 bg-transparent border-none shadow-none">
    <div class="relative flex-b mt-2.5 max-md:block max-md:mt-1">
      <!-- 左侧卡片 -->
      <div class="w-112 mr-5 max-md:w-full max-md:mr-0">
        <div class="fa-card-sm relative p-9 pb-6 overflow-hidden text-center">
          <div class="profile-cover" aria-hidden="true" />

          <div class="relative z-10 mt-30 mx-auto">
            <div class="relative inline-block">
              <img
                v-if="infoFormState.avatar"
                class="w-20 h-20 object-cover border-2 border-white rounded-full"
                :src="infoFormState.avatar"
                alt="" />
              <img
                v-else
                class="w-20 h-20 object-cover border-2 border-white rounded-full"
                src="@imgs/user/avatar.webp"
                alt="" />
              <ElUpload
                ref="uploadRef"
                v-model:file-list="fileList"
                class="profile-avatar-upload"
                name="file"
                :show-file-list="false"
                :before-upload="handleBeforeUpload"
                :http-request="handleUpload"
                :limit="1"
                :auto-upload="false"
                @change="handleAvatarFileChange">
                <template #trigger>
                  <ElButton type="primary" :icon="Camera" circle size="small" class="upload-trigger" />
                </template>
              </ElUpload>
            </div>
          </div>

          <p class="relative z-10 mt-3 text-sm text-g-600">{{ greeting }}</p>
          <h2 class="relative z-10 mt-1 text-xl font-normal">{{ infoFormState.name || '—' }}</h2>
          <p class="relative z-10 mt-2 text-sm text-g-500">
            {{ infoFormState.roles?.map((r) => r.name).join('、') || ' ' }}
          </p>

          <div class="relative z-10 w-75 mx-auto mt-7.5 text-left">
            <div class="mt-2.5 flex items-start">
              <FaSvgIcon icon="ri:mail-line" class="text-g-700 shrink-0 mt-0.5" />
              <span class="ml-2 text-sm break-all">{{ infoFormState.email || '—' }}</span>
            </div>
            <div class="mt-2.5 flex items-start">
              <FaSvgIcon icon="ri:user-3-line" class="text-g-700 shrink-0 mt-0.5" />
              <span class="ml-2 text-sm">{{ infoFormState.username || '—' }}</span>
            </div>
            <div class="mt-2.5 flex items-start">
              <FaSvgIcon icon="ri:map-pin-line" class="text-g-700 shrink-0 mt-0.5" />
              <span class="ml-2 text-sm">{{ infoFormState.dept?.name || '—' }}</span>
            </div>
            <div class="mt-2.5 flex items-start">
              <FaSvgIcon icon="ri:briefcase-line" class="text-g-700 shrink-0 mt-0.5" />
              <span class="ml-2 text-sm">
                {{ infoFormState.positions?.map((p) => p.name).join('、') || '—' }}
              </span>
            </div>
          </div>

          <div v-if="roleTagList.length" class="relative z-10 mt-10">
            <h3 class="text-sm font-medium">角色</h3>
            <div class="flex flex-wrap justify-center mt-3.5">
              <div
                v-for="item in roleTagList"
                :key="item"
                class="py-1 px-1.5 mr-2.5 mb-2.5 text-xs border border-g-300 rounded">
                {{ item }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <ElDialog
        v-model="avatarCropVisible"
        title="裁剪头像"
        width="680px"
        align-center
        append-to-body
        destroy-on-close
        class="avatar-crop-dialog"
        @closed="onAvatarCropDialogClosed">
        <FaCutterImg
          v-if="avatarCropVisible && avatarCropSrc"
          :key="avatarCropSrc"
          :img-url="avatarCropSrc"
          :box-width="420"
          :box-height="320"
          :cut-width="240"
          :cut-height="240"
          rate="1:1"
          :size-change="false"
          :quality="0.92"
          :tool="true"
          :show-preview="true"
          :preview-circle="true"
          :show-download="false"
          :original-graph="false"
          file-type="jpeg"
          title="调整头像"
          preview-title="预览"
          @update:img-url="onAvatarCropConfirm"
          @error="onAvatarCropImgError" />
      </ElDialog>

      <!-- 右侧表单 -->
      <div class="flex-1 overflow-hidden max-md:w-full max-md:mt-3.5">
        <div class="fa-card-sm">
          <h1 class="p-4 text-xl font-normal border-b border-g-300">基本设置</h1>

          <ElForm
            ref="infoFormRef"
            :model="infoFormState"
            class="box-border p-5 [&>.el-row_.el-form-item]:w-[calc(50%-10px)] [&>.el-row_.el-input]:w-full [&>.el-row_.el-select]:w-full"
            :rules="rules"
            label-width="86px"
            label-position="top">
            <ElRow>
              <ElFormItem label="姓名" prop="name">
                <ElInput v-model="infoFormState.name" :disabled="!isEdit" placeholder="请输入姓名" />
              </ElFormItem>
              <ElFormItem label="性别" prop="gender" class="ml-5">
                <ElSelect v-model="infoFormState.gender" placeholder="请选择" :disabled="!isEdit" class="w-full">
                  <ElOption
                    v-for="item in dictDataStore['sys_user_sex']"
                    :key="String(item.dict_value)"
                    :label="item.dict_label"
                    :value="normalizeGenderValue(item.dict_value)" />
                </ElSelect>
              </ElFormItem>
            </ElRow>

            <ElRow>
              <ElFormItem label="账号" prop="username">
                <ElInput v-model="infoFormState.username" disabled placeholder="登录账号" />
              </ElFormItem>
              <ElFormItem label="邮箱" prop="email" class="ml-5">
                <ElInput v-model="infoFormState.email" :disabled="!isEdit" placeholder="请输入邮箱" />
              </ElFormItem>
            </ElRow>

            <ElRow>
              <ElFormItem label="手机" prop="mobile">
                <ElInput v-model="infoFormState.mobile" :disabled="!isEdit" placeholder="请输入手机号码" />
              </ElFormItem>
              <ElFormItem label="部门" class="ml-5">
                <ElInput :model-value="infoFormState.dept?.name || '—'" disabled />
              </ElFormItem>
            </ElRow>

            <div class="flex-c justify-end [&_.el-button]:!w-27.5">
              <ElButton type="primary" class="w-22.5" :loading="infoSubmitting" v-ripple @click="onBasicToggleSave">
                {{ isEdit ? '保存' : '编辑' }}
              </ElButton>
            </div>
          </ElForm>
        </div>

        <div class="fa-card-sm my-5">
          <h1 class="p-4 text-xl font-normal border-b border-g-300">更改密码</h1>

          <ElForm
            ref="passwordFormRef"
            :model="passwordFormState"
            class="box-border p-5"
            :rules="resetPasswordRules"
            label-width="86px"
            label-position="top">
            <ElFormItem label="当前密码" prop="old_password">
              <ElInput v-model="passwordFormState.old_password" type="password" :disabled="!isEditPwd" show-password />
            </ElFormItem>

            <ElFormItem label="新密码" prop="new_password">
              <ElInput v-model="passwordFormState.new_password" type="password" :disabled="!isEditPwd" show-password />
            </ElFormItem>

            <ElFormItem label="确认新密码" prop="confirm_password">
              <ElInput
                v-model="passwordFormState.confirm_password"
                type="password"
                :disabled="!isEditPwd"
                show-password />
            </ElFormItem>

            <div class="flex-c justify-end [&_.el-button]:!w-27.5">
              <ElButton
                type="primary"
                class="w-22.5"
                :loading="passwordChanging"
                v-ripple
                @click="onPasswordToggleSave">
                {{ isEditPwd ? '保存' : '编辑' }}
              </ElButton>
            </div>
          </ElForm>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { FormInstance, UploadRequestOptions, UploadFile } from 'element-plus'
import type { ElUpload } from 'element-plus'
import UserAPI, { type InfoFormState, type PasswordFormState } from '@/api/module_system/user'
import { useUserStore, useDictStore } from '@stores'
import { Camera } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { redirectToLogin } from '@utils/auth'
import FaSvgIcon from '@/components/base/fa-svg-icon/index.vue'
import FaCutterImg from '@/components/media/fa-cutter-img/index.vue'
import { dataURLToFile } from '@utils/file/dataUrl'

defineOptions({ name: 'UserProfile' })

const { t } = useI18n()
const userStore = useUserStore()
const dictStore = useDictStore()
const infoFormRef = ref<FormInstance>()
const passwordFormRef = ref<FormInstance>()

const infoSubmitting = ref(false)
const passwordChanging = ref(false)

const isEdit = ref(false)
const isEditPwd = ref(false)

const dictDataStore = computed(() => dictStore.dictData)

const greeting = ref('')

const roleTagList = computed(() =>
  (infoFormState.roles ?? []).map((r) => r.name).filter((n): n is string => !!n && n.trim().length > 0)
)

const infoFormState = reactive<InfoFormState>({
  name: undefined,
  gender: 1,
  mobile: undefined,
  email: undefined,
  username: undefined,
  dept_name: undefined,
  dept: {},
  positions: [],
  roles: [],
  avatar: undefined,
  created_time: undefined,
})

const passwordFormState = reactive<PasswordFormState>({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const fileList = ref<any[]>([])
const uploadRef = ref<InstanceType<typeof ElUpload>>()

const avatarCropVisible = ref(false)
const avatarCropSrc = ref('')

function revokeAvatarCropSrc() {
  if (avatarCropSrc.value.startsWith('blob:')) {
    URL.revokeObjectURL(avatarCropSrc.value)
  }
  avatarCropSrc.value = ''
}

function onAvatarCropDialogClosed() {
  revokeAvatarCropSrc()
}

function onAvatarCropImgError() {
  ElMessage.error('图片加载失败，请换一张图重试')
}

async function onAvatarCropConfirm(dataURL: string) {
  try {
    const file = dataURLToFile(dataURL, 'avatar.jpg')
    const formData = new FormData()
    formData.append('file', file)
    const response = await UserAPI.uploadCurrentUserAvatar(formData)

    if (response.data.code === 0 && response.data.data) {
      const fileUrl = response.data.data.file_url
      await persistAvatarAndSyncStore(fileUrl)
      uploadRef.value?.clearFiles()
      fileList.value = []
      avatarCropVisible.value = false
    } else {
      ElMessage.error(response.data.msg || '上传失败')
    }
  } catch {
    ElMessage.error('头像上传失败，请重试')
  }
}

function normalizeGenderValue(v: string | number | undefined): number {
  if (v === undefined || v === null || v === '') return 1
  const n = Number(v)
  return Number.isFinite(n) ? n : 1
}

const getOptions = async () => {
  await dictStore.getDict(['sys_user_sex'])
}

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  mobile: [
    {
      validator: (_: unknown, v: string, cb: (e?: Error) => void) => {
        const s = v != null ? String(v).trim() : ''
        if (!s) return cb()
        if (!/^1[3-9]\d{9}$/.test(s)) {
          cb(new Error('请输入有效的手机号格式'))
          return
        }
        cb()
      },
      trigger: 'blur',
    },
  ],
  email: [
    {
      validator: (_: unknown, v: string, cb: (e?: Error) => void) => {
        const s = v != null ? String(v).trim() : ''
        if (!s) return cb()
        if (!/\w[-\w.+]*@([A-Za-z0-9][-A-Za-z0-9]+\.)+[A-Za-z]{2,14}/.test(s)) {
          cb(new Error('请输入有效的邮箱格式'))
          return
        }
        cb()
      },
      trigger: 'blur',
    },
  ],
}

const resetPasswordRules = {
  old_password: [
    {
      required: true,
      trigger: 'blur',
      message: t('login.message.password.currentRequired'),
    },
  ],
  new_password: [
    {
      required: true,
      trigger: 'blur',
      message: t('login.message.password.required'),
    },
    {
      min: 6,
      message: t('login.message.password.min'),
      trigger: 'blur',
    },
  ],
  confirm_password: [
    {
      required: true,
      trigger: 'blur',
      message: t('login.message.password.required'),
    },
    {
      min: 6,
      message: t('login.message.password.min'),
      trigger: 'blur',
    },
    {
      validator: (_: unknown, value: string) => {
        return value === passwordFormState.new_password
      },
      trigger: 'blur',
      message: t('login.message.password.inconformity'),
    },
  ],
}

function refreshGreeting() {
  const h = new Date().getHours()
  if (h >= 6 && h < 9) greeting.value = '早上好'
  else if (h >= 9 && h < 11) greeting.value = '上午好'
  else if (h >= 11 && h < 13) greeting.value = '中午好'
  else if (h >= 13 && h < 18) greeting.value = '下午好'
  else if (h >= 18 && h < 24) greeting.value = '晚上好'
  else greeting.value = '很晚了，早点休息'
}

const handleBeforeUpload = (file: File) => {
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isImage) {
    ElMessage.error('只能上传图片文件')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('上传图片大小不能超过 2MB!')
    return false
  }
  return true
}

const handleUpload = async (options: UploadRequestOptions) => {
  try {
    const file = options.file
    const formData = new FormData()
    formData.append('file', file)

    const response = await UserAPI.uploadCurrentUserAvatar(formData)

    if (response.data.code === 0 && response.data.data) {
      const fileUrl = response.data.data.file_url
      await persistAvatarAndSyncStore(fileUrl)
      options.onSuccess(response)
      uploadRef.value?.clearFiles()
      fileList.value = []
    } else {
      const errorMsg = response.data.msg || '上传失败'
      ElMessage.error(errorMsg)
      options.onError({
        ...new Error(errorMsg),
        status: response.status || 500,
        method: 'POST',
        url: '/system/user/current/avatar/upload',
      })
    }
  } catch (error) {
    ElMessage.error('头像上传失败，请重试')
    const errorObj = error instanceof Error ? error : new Error(String(error))
    options.onError({
      ...errorObj,
      status: 500,
      method: 'POST',
      url: '/system/user/current/avatar/upload',
    })
  }
}

const handleAvatarFileChange = (file: UploadFile) => {
  if (!file.raw) {
    return
  }
  if (!handleBeforeUpload(file.raw)) {
    uploadRef.value?.clearFiles()
    fileList.value = []
    return
  }
  revokeAvatarCropSrc()
  avatarCropSrc.value = URL.createObjectURL(file.raw)
  avatarCropVisible.value = true
  uploadRef.value?.clearFiles()
  fileList.value = []
}

/** 去掉头像 URL 上的缓存破坏参数，保留 OSS 签名查询串 */
function stripAvatarCacheBust(url: string): string {
  const trimmed = url.trim()
  if (!trimmed) return trimmed
  try {
    const u = new URL(trimmed, typeof window !== 'undefined' ? window.location.origin : 'http://localhost')
    u.searchParams.delete('t')
    if (/^https?:\/\//i.test(trimmed)) {
      const q = u.searchParams.toString()
      return q ? `${u.origin}${u.pathname}?${q}` : `${u.origin}${u.pathname}`
    }
    const q = u.searchParams.toString()
    return q ? `${u.pathname}?${q}` : u.pathname
  } catch {
    return trimmed.split('?')[0] || trimmed
  }
}

/** 是否为 OSS 签名 URL（追加任意 query 会使签名失效） */
function isOssSignedUrl(url: string): boolean {
  return /[?&](Signature|Expires|OSSAccessKeyId|x-oss-signature)=/i.test(url)
}

/**
 * 写入后端的稳定头像地址：剥离签名与缓存参数。
 * 私有桶签名会过期，库内只存 canonical 直链；读接口再签发。
 */
function toStoredAvatarUrl(url: string): string {
  const trimmed = url.trim()
  if (!trimmed) return trimmed
  const ephemeral = new Set(
    [
      't',
      'expires',
      'signature',
      'ossaccesskeyid',
      'security-token',
      'x-oss-credential',
      'x-oss-date',
      'x-oss-expires',
      'x-oss-signature',
      'x-oss-signature-version',
      'x-oss-security-token',
    ].map((k) => k.toLowerCase())
  )
  try {
    const u = new URL(trimmed, typeof window !== 'undefined' ? window.location.origin : 'http://localhost')
    for (const key of [...u.searchParams.keys()]) {
      if (ephemeral.has(key.toLowerCase())) {
        u.searchParams.delete(key)
      }
    }
    if (/^https?:\/\//i.test(trimmed)) {
      const q = u.searchParams.toString()
      return q ? `${u.origin}${u.pathname}?${q}` : `${u.origin}${u.pathname}`
    }
    const q = u.searchParams.toString()
    return q ? `${u.pathname}?${q}` : u.pathname
  } catch {
    return trimmed.split('?')[0] || trimmed
  }
}

/** 同路径覆盖上传时强制顶栏/侧栏刷新；签名 URL 不可追加 t= */
function withAvatarCacheBust(url: string): string {
  const clean = stripAvatarCacheBust(url)
  if (!clean) return clean
  if (isOssSignedUrl(clean)) return clean
  const sep = clean.includes('?') ? '&' : '?'
  return `${clean}${sep}t=${Date.now()}`
}

/**
 * 上传成功后：写入表单 → 立即 patch 全局 store（顶栏 FaUserMenu）→ 持久化到后端。
 * 不再要求用户再点「保存基本设置」才能同步头像。
 */
async function persistAvatarAndSyncStore(fileUrl: string) {
  const displayUrl = stripAvatarCacheBust(fileUrl)
  const storeUrl = toStoredAvatarUrl(fileUrl)
  if (!storeUrl) {
    ElMessage.error('无效的头像URL')
    return
  }

  infoFormState.avatar = displayUrl
  userStore.setAvatar(withAvatarCacheBust(displayUrl))

  const response = await UserAPI.updateCurrentUserInfo({
    name: infoFormState.name,
    gender: infoFormState.gender,
    mobile: infoFormState.mobile,
    email: infoFormState.email,
    avatar: storeUrl,
  })
  const saved = response.data.data
  const savedDisplay = saved?.avatar ? stripAvatarCacheBust(saved.avatar) : displayUrl
  infoFormState.avatar = savedDisplay
  // 合并更新，避免 setUserInfo 整表替换丢掉 menus 等运行时字段
  if (saved) {
    userStore.setUserInfo({ ...userStore.basicInfo, ...saved, avatar: withAvatarCacheBust(savedDisplay) })
  } else {
    userStore.setAvatar(withAvatarCacheBust(savedDisplay))
  }
}

const initInfoForm = () => {
  const basicInfo = userStore.basicInfo
  Object.assign(infoFormState, {
    ...basicInfo,
    avatar: basicInfo.avatar ? stripAvatarCacheBust(String(basicInfo.avatar)) : basicInfo.avatar,
  })
}

const initPasswordForm = () => {
  Object.assign(passwordFormState, {
    old_password: '',
    new_password: '',
    confirm_password: '',
  })
}

const handleSave = async () => {
  try {
    infoSubmitting.value = true
    const valid = await infoFormRef.value?.validate().catch(() => false)
    if (!valid) {
      return false
    }
    const payload = {
      ...infoFormState,
      avatar: infoFormState.avatar ? stripAvatarCacheBust(infoFormState.avatar) : infoFormState.avatar,
    }
    const response = await UserAPI.updateCurrentUserInfo(payload)
    const data = response.data.data
    if (data) {
      const nextAvatar = data.avatar ? withAvatarCacheBust(stripAvatarCacheBust(data.avatar)) : data.avatar
      userStore.setUserInfo({ ...userStore.basicInfo, ...data, avatar: nextAvatar })
    }
    initInfoForm()
    return true
  } catch (e) {
    console.error(e)
    return false
  } finally {
    infoSubmitting.value = false
  }
}

const handlePasswordChange = async () => {
  try {
    passwordChanging.value = true
    const valid = await passwordFormRef.value?.validate().catch(() => false)
    if (!valid) {
      return false
    }
    const response = await UserAPI.changeCurrentUserPassword(passwordFormState)
    initPasswordForm()
    await redirectToLogin(response.data.msg)
    return true
  } catch (error) {
    console.error(error)
    return false
  } finally {
    passwordChanging.value = false
  }
}

async function onBasicToggleSave() {
  if (!isEdit.value) {
    isEdit.value = true
    return
  }
  const ok = await handleSave()
  if (ok) {
    isEdit.value = false
  }
}

async function onPasswordToggleSave() {
  if (!isEditPwd.value) {
    isEditPwd.value = true
    initPasswordForm()
    return
  }
  await handlePasswordChange()
}

onMounted(async () => {
  refreshGreeting()
  await getOptions()
  initInfoForm()
})
</script>

<style lang="scss" scoped>
/* 品牌蓝轻渐变封面（#1677ff），替代校园照片；白边头像叠在底边对比足够 */
.profile-cover {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 12.5rem; /* 对齐原 h-50 */
  background: linear-gradient(145deg, #69b1ff 0%, #1677ff 48%, #0958d9 100%);
}

.profile-avatar-upload {
  position: absolute;
  right: 0;
  bottom: 0;
  z-index: 2;

  :deep(.el-upload) {
    display: inline-flex;
  }

  .upload-trigger {
    box-shadow: 0 1px 4px rgb(0 0 0 / 15%);
  }
}
</style>

<style lang="scss">
/* append-to-body：弹窗样式需非 scoped */
.avatar-crop-dialog.el-dialog {
  max-width: calc(100vw - 32px);
  margin-top: 8vh !important;

  .el-dialog__body {
    max-height: min(78vh, 640px);
    padding: 12px 16px 16px;
    overflow: auto;
  }
}
</style>
