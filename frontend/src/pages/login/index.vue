<script lang="ts" setup>
import { Lock, User } from "@element-plus/icons-vue"
import { useUserStore } from "@/pinia/stores/user"

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const submitting = ref(false)
const form = reactive({
  username: "admin",
  password: "admin123456"
})

async function submit() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning("请输入用户名和密码。")
    return
  }
  submitting.value = true
  try {
    await userStore.login(form.username.trim(), form.password)
    ElMessage.success("登录成功。")
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/accounts"
    router.replace(redirect)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-page__grid">
      <section class="brand-panel">
        <span class="brand-panel__badge">MTLogin Admin</span>
        <h1>现代化管理控制台</h1>
        <p>
          使用 Vue 3 + Vite 模板重构后台界面，账户、平台、通知、执行记录和系统设置全部改为独立页面与 API 驱动交互。
        </p>
        <ul class="brand-panel__highlights">
          <li>统一运行状态卡片，快速掌握调度健康度</li>
          <li>账户列表直接展示上传量、下载量、魔力值和下次执行时间</li>
          <li>Flask Session 登录保持不变，前端刷新和深链接可直接访问</li>
        </ul>
      </section>

      <ElCard class="login-card" shadow="never">
        <template #header>
          <div class="login-card__header">
            <span class="login-card__eyebrow">Sign In</span>
            <strong>管理员登录</strong>
          </div>
        </template>
        <ElForm class="login-form" label-position="top" @submit.prevent="submit">
          <ElFormItem label="用户名">
            <ElInput v-model="form.username" :prefix-icon="User" size="large" placeholder="输入管理员账号" />
          </ElFormItem>
          <ElFormItem label="密码">
            <ElInput
              v-model="form.password"
              :prefix-icon="Lock"
              show-password
              size="large"
              type="password"
              placeholder="输入管理员密码"
              @keyup.enter="submit"
            />
          </ElFormItem>
          <ElButton :loading="submitting" class="login-card__submit" size="large" type="primary" @click="submit">
            进入控制台
          </ElButton>
        </ElForm>
      </ElCard>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgb(14 165 233 / 20%), transparent 24%),
    radial-gradient(circle at 80% 20%, rgb(34 197 94 / 18%), transparent 18%),
    linear-gradient(135deg, #e0f2fe 0%, #f8fafc 40%, #ecfeff 100%);
}

.login-page__grid {
  width: min(1120px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 430px);
  gap: 24px;
  align-items: stretch;
}

.brand-panel,
.login-card {
  border: 1px solid rgb(148 163 184 / 14%);
  border-radius: 28px;
  background: rgb(255 255 255 / 82%);
  box-shadow: 0 24px 80px rgb(15 23 42 / 12%);
  backdrop-filter: blur(22px);
}

.brand-panel {
  padding: 36px;
}

.brand-panel__badge {
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgb(15 118 110 / 10%);
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 18px 0 0;
  color: #0f172a;
  font-size: clamp(34px, 5vw, 54px);
  line-height: 1.02;
}

p {
  margin: 18px 0 0;
  color: #334155;
  font-size: 16px;
  line-height: 1.8;
}

.brand-panel__highlights {
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 12px;
}

.brand-panel__highlights li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgb(248 250 252 / 86%);
  color: #0f172a;
}

.brand-panel__highlights li::before {
  content: "";
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(135deg, #0f766e, #38bdf8);
}

.login-card {
  padding: 8px;
}

.login-card__header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.login-card__eyebrow {
  color: #64748b;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.login-card__submit {
  width: 100%;
  margin-top: 12px;
  height: 52px;
  border: none;
  border-radius: 18px;
  background: linear-gradient(135deg, #0f766e, #0ea5e9);
  box-shadow: 0 18px 36px rgb(14 165 233 / 24%);
}

.login-form :deep(.el-form-item__label) {
  color: #334155;
  font-size: 13px;
  font-weight: 700;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 54px;
  padding-inline: 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgb(248 250 252 / 98%), rgb(255 255 255));
  box-shadow:
    0 0 0 1px rgb(148 163 184 / 18%),
    0 10px 28px rgb(15 23 42 / 6%),
    inset 0 1px 0 rgb(255 255 255 / 92%);
  transition:
    box-shadow 0.2s ease,
    transform 0.2s ease,
    background-color 0.2s ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow:
    0 0 0 1px rgb(100 116 139 / 26%),
    0 14px 32px rgb(15 23 42 / 8%),
    inset 0 1px 0 rgb(255 255 255 / 94%);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  transform: translateY(-1px);
  box-shadow:
    0 0 0 1px rgb(14 165 233 / 48%),
    0 18px 40px rgb(14 165 233 / 18%),
    inset 0 1px 0 rgb(255 255 255 / 96%);
}

.login-form :deep(.el-input__inner) {
  color: #0f172a;
  font-size: 15px;
  font-weight: 500;
}

.login-form :deep(.el-input__prefix-inner),
.login-form :deep(.el-input__suffix-inner) {
  color: #64748b;
}

@media (max-width: 960px) {
  .login-page__grid {
    grid-template-columns: 1fr;
  }
}
</style>
