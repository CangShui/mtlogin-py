<script lang="ts" setup>
import type { StateCard } from "@@/apis/admin/type"
import { getBootstrapApi, getSettingsApi, updateAdminSettingsApi } from "@@/apis/admin"
import AdminPageShell from "@@/components/AdminPageShell.vue"
import { useUserStore } from "@/pinia/stores/user"

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const stateCards = ref<StateCard[]>([])
const runtimeInfo = ref<Record<string, string | number>>({})
const logTail = ref("")

const form = reactive({
  admin_username: "",
  current_password: "",
  new_password: "",
  confirm_password: ""
})

async function loadData() {
  loading.value = true
  try {
    const [bootstrapResponse, settingsResponse] = await Promise.all([getBootstrapApi(), getSettingsApi()])
    stateCards.value = bootstrapResponse.data.stateCards
    form.admin_username = settingsResponse.data.adminUsername
    runtimeInfo.value = settingsResponse.data.runtimeInfo
    logTail.value = settingsResponse.data.logTail
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    await updateAdminSettingsApi({ ...form })
    ElMessage.success("管理员账号已更新。")
    form.current_password = ""
    form.new_password = ""
    form.confirm_password = ""
    await userStore.getInfo()
    await loadData()
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <AdminPageShell
    title="系统设置"
    description="维护管理员账号，并查看服务监听地址、数据库位置、前端构建目录和最近日志输出。"
    :cards="stateCards"
  >
    <template #actions>
      <ElButton :loading="loading" plain @click="loadData">
        刷新设置
      </ElButton>
    </template>

    <div class="settings-grid">
      <ElCard class="panel-card" shadow="never">
        <template #header>
          <div class="panel-header">
            <strong>管理员账号</strong>
            <span>修改账号名或重置密码</span>
          </div>
        </template>
        <ElForm label-position="top">
          <ElFormItem label="管理员用户名">
            <ElInput v-model="form.admin_username" />
          </ElFormItem>
          <ElFormItem label="当前密码">
            <ElInput v-model="form.current_password" show-password type="password" />
          </ElFormItem>
          <ElFormItem label="新密码">
            <ElInput v-model="form.new_password" show-password type="password" />
          </ElFormItem>
          <ElFormItem label="确认新密码">
            <ElInput v-model="form.confirm_password" show-password type="password" />
          </ElFormItem>
          <ElSpace>
            <ElButton :loading="saving" type="primary" @click="saveSettings">
              保存设置
            </ElButton>
          </ElSpace>
        </ElForm>
      </ElCard>

      <ElCard class="panel-card" shadow="never">
        <template #header>
          <div class="panel-header">
            <strong>运行环境</strong>
            <span>当前 Flask 服务与前端产物信息</span>
          </div>
        </template>
        <dl class="runtime-list">
          <template v-for="(value, key) in runtimeInfo" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ value }}</dd>
          </template>
        </dl>
      </ElCard>
    </div>

    <ElCard class="panel-card" shadow="never">
      <template #header>
        <div class="panel-header">
          <strong>最近日志</strong>
          <span>展示最新 200 行日志</span>
        </div>
      </template>
      <pre class="log-tail">{{ logTail }}</pre>
    </ElCard>
  </AdminPageShell>
</template>

<style lang="scss" scoped>
.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(280px, 0.85fr);
  gap: 18px;
}

.panel-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.panel-header strong {
  color: #0f172a;
}

.panel-header span {
  color: #64748b;
  font-size: 13px;
}

.runtime-list {
  display: grid;
  grid-template-columns: minmax(120px, 160px) 1fr;
  gap: 12px 18px;
  margin: 0;
}

.runtime-list dt {
  color: #64748b;
}

.runtime-list dd {
  margin: 0;
  color: #0f172a;
  word-break: break-all;
}

.log-tail {
  margin: 0;
  padding: 18px;
  border-radius: 18px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 960px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .runtime-list {
    grid-template-columns: 1fr;
  }
}
</style>
