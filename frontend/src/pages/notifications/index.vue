<script lang="ts" setup>
import type { NotificationChannelItem, NotificationSavePayload, StateCard } from "@@/apis/admin/type"
import { getBootstrapApi, getNotificationsApi, saveNotificationApi, toggleNotificationApi } from "@@/apis/admin"
import AdminPageShell from "@@/components/AdminPageShell.vue"

const loading = ref(false)
const saving = ref(false)
const drawerVisible = ref(false)
const stateCards = ref<StateCard[]>([])
const channels = ref<NotificationChannelItem[]>([])

const form = reactive<NotificationSavePayload>({
  channel_id: undefined,
  name: "",
  type: "tg",
  enabled: true,
  tgbot_token: "",
  tgbot_chat_id: "",
  tgbot_proxy: ""
})

function resetForm() {
  Object.assign(form, {
    channel_id: undefined,
    name: "",
    type: "tg",
    enabled: true,
    tgbot_token: "",
    tgbot_chat_id: "",
    tgbot_proxy: ""
  })
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
}

function openEditDrawer(channel: NotificationChannelItem) {
  Object.assign(form, {
    channel_id: channel.id,
    name: channel.name,
    type: channel.type,
    enabled: channel.enabled,
    tgbot_token: "",
    tgbot_chat_id: channel.tgbot_chat_id || "",
    tgbot_proxy: channel.tgbot_proxy
  })
  drawerVisible.value = true
}

async function loadData() {
  loading.value = true
  try {
    const [bootstrapResponse, notificationsResponse] = await Promise.all([getBootstrapApi(), getNotificationsApi()])
    stateCards.value = bootstrapResponse.data.stateCards
    channels.value = notificationsResponse.data.items
  } finally {
    loading.value = false
  }
}

async function saveChannel() {
  saving.value = true
  try {
    await saveNotificationApi({
      channel_id: form.channel_id,
      name: form.name.trim(),
      type: form.type,
      enabled: form.enabled,
      tgbot_token: form.tgbot_token.trim(),
      tgbot_chat_id: form.tgbot_chat_id,
      tgbot_proxy: form.tgbot_proxy.trim()
    })
    ElMessage.success("通知渠道已保存。")
    drawerVisible.value = false
    resetForm()
    await loadData()
  } finally {
    saving.value = false
  }
}

async function toggleChannel(channel: NotificationChannelItem, enabled: boolean) {
  await toggleNotificationApi(channel.id, enabled)
  ElMessage.success("通知渠道状态已更新。")
  await loadData()
}

onMounted(loadData)
</script>

<template>
  <AdminPageShell
    title="通知管理"
    description="维护 Telegram 通知渠道，统一查看启用状态、代理信息和密钥保留情况。"
    :cards="stateCards"
  >
    <template #actions>
      <ElButton type="primary" @click="openCreateDrawer">
        新增渠道
      </ElButton>
      <ElButton :loading="loading" plain @click="loadData">
        刷新渠道
      </ElButton>
    </template>

    <ElCard class="panel-card" shadow="never">
      <template #header>
        <div class="panel-header">
          <strong>通知渠道</strong>
          <span>共 {{ channels.length }} 个渠道</span>
        </div>
      </template>
      <ElTable :data="channels" stripe>
        <ElTableColumn label="渠道名称" min-width="180">
          <template #default="{ row }">
            <div class="stack">
              <strong>{{ row.name }}</strong>
              <span>{{ row.type.toUpperCase() }}</span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="凭据" min-width="220">
          <template #default="{ row }">
            <div class="stack">
              <span>Chat ID {{ row.tgbot_chat_id || "--" }}</span>
              <span>Token {{ row.has_tgbot_token ? "已保存" : "未配置" }}</span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="tgbot_proxy" label="代理" min-width="200" />
        <ElTableColumn label="状态" width="110">
          <template #default="{ row }">
            <ElTag :type="row.enabled ? 'success' : 'info'">
              {{ row.enabled ? "启用" : "停用" }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="启用" width="110">
          <template #default="{ row }">
            <ElSwitch :model-value="row.enabled" @change="(value) => toggleChannel(row, Boolean(value))" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openEditDrawer(row)">
              编辑
            </ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <ElDrawer v-model="drawerVisible" :close-on-click-modal="false" size="480px" title="通知渠道">
      <ElForm label-position="top">
        <ElFormItem label="渠道名称">
          <ElInput v-model="form.name" placeholder="例如：运维 TG" />
        </ElFormItem>
        <ElFormItem label="启用状态">
          <ElSwitch v-model="form.enabled" />
        </ElFormItem>
        <ElFormItem label="Telegram Bot Token">
          <ElInput v-model="form.tgbot_token" placeholder="编辑时留空表示保持已保存 Token" />
        </ElFormItem>
        <ElFormItem label="Telegram Chat ID">
          <ElInputNumber v-model="form.tgbot_chat_id" :min="-999999999999" :max="999999999999" />
        </ElFormItem>
        <ElFormItem label="代理">
          <ElInput v-model="form.tgbot_proxy" placeholder="http://127.0.0.1:7890" />
        </ElFormItem>
      </ElForm>

      <template #footer>
        <ElSpace>
          <ElButton @click="drawerVisible = false">
            取消
          </ElButton>
          <ElButton :loading="saving" type="primary" @click="saveChannel">
            保存
          </ElButton>
        </ElSpace>
      </template>
    </ElDrawer>
  </AdminPageShell>
</template>

<style lang="scss" scoped>
.panel-header,
.stack {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.panel-header strong,
.stack strong {
  color: #0f172a;
}

.panel-header span,
.stack span {
  color: #64748b;
  font-size: 13px;
}
</style>
