<script lang="ts" setup>
import type { FormInstance } from "element-plus"
import type { AccountItem, AccountSavePayload, NotificationChannelItem, PlatformItem, StateCard } from "@@/apis/admin/type"
import { getAccountsApi, getBootstrapApi, runAccountApi, saveAccountApi, toggleAccountApi } from "@@/apis/admin"
import AdminPageShell from "@@/components/AdminPageShell.vue"

interface AccountFormState extends AccountSavePayload {
  has_password: boolean
  has_totpsecret: boolean
  has_m_team_auth: boolean
}

const formRef = ref<FormInstance>()
const loading = ref(false)
const saving = ref(false)
const drawerVisible = ref(false)
const stateCards = ref<StateCard[]>([])
const accounts = ref<AccountItem[]>([])
const channels = ref<NotificationChannelItem[]>([])
const platforms = ref<PlatformItem[]>([])
const defaults = ref({ platform_id: 0, timeout: 60, cookie_mode: "normal" })

function createEmptyForm(): AccountFormState {
  return {
    account_id: undefined,
    name: "",
    platform_id: defaults.value.platform_id,
    enabled: true,
    username: "",
    password: "",
    totpsecret: "",
    proxy: "",
    crontab: "",
    m_team_auth: "",
    m_team_did: "",
    timeout: defaults.value.timeout,
    cookie_mode: defaults.value.cookie_mode,
    skip_cache: false,
    notification_channel_ids: [],
    has_password: false,
    has_totpsecret: false,
    has_m_team_auth: false
  }
}

const form = reactive<AccountFormState>(createEmptyForm())

const channelOptions = computed(() => channels.value.filter(item => item.enabled))

function displayValue(value: string | number | boolean | null | undefined) {
  return value === null || value === undefined || value === "" ? "--" : String(value)
}

function resetForm() {
  Object.assign(form, createEmptyForm())
  formRef.value?.clearValidate()
}

function openCreateDrawer() {
  resetForm()
  drawerVisible.value = true
}

function openEditDrawer(account: AccountItem) {
  Object.assign(form, createEmptyForm(), {
    account_id: account.id,
    name: account.name,
    platform_id: account.platform_id,
    enabled: account.enabled,
    username: account.username,
    proxy: account.proxy,
    crontab: account.crontab,
    m_team_auth: "",
    m_team_did: account.m_team_did,
    timeout: account.timeout,
    cookie_mode: account.cookie_mode,
    skip_cache: account.skip_cache,
    notification_channel_ids: [...account.notification_channel_ids],
    has_password: account.has_password,
    has_totpsecret: account.has_totpsecret,
    has_m_team_auth: account.has_m_team_auth
  })
  drawerVisible.value = true
}

async function loadData() {
  loading.value = true
  try {
    const [bootstrapResponse, accountsResponse] = await Promise.all([getBootstrapApi(), getAccountsApi()])
    stateCards.value = bootstrapResponse.data.stateCards
    accounts.value = accountsResponse.data.items
    channels.value = accountsResponse.data.channels
    platforms.value = accountsResponse.data.platforms
    defaults.value = accountsResponse.data.defaults
    if (!drawerVisible.value) resetForm()
  } finally {
    loading.value = false
  }
}

async function saveAccount() {
  saving.value = true
  try {
    await saveAccountApi({
      account_id: form.account_id,
      name: form.name.trim(),
      platform_id: form.platform_id,
      enabled: form.enabled,
      username: form.username.trim(),
      password: form.password,
      totpsecret: form.totpsecret.trim(),
      proxy: form.proxy.trim(),
      crontab: form.crontab.trim(),
      m_team_auth: form.m_team_auth.trim(),
      m_team_did: form.m_team_did.trim(),
      timeout: form.timeout,
      cookie_mode: form.cookie_mode,
      skip_cache: form.skip_cache,
      notification_channel_ids: [...form.notification_channel_ids]
    })
    ElMessage.success("登录账户已保存。")
    drawerVisible.value = false
    resetForm()
    await loadData()
  } finally {
    saving.value = false
  }
}

async function toggleAccount(account: AccountItem, enabled: boolean) {
  await toggleAccountApi(account.id, enabled)
  ElMessage.success("登录账户状态已更新。")
  await loadData()
}

async function runAccount(account: AccountItem) {
  await runAccountApi(account.id)
  ElMessage.success(`已提交账户 ${account.name} 的立即执行请求。`)
  await loadData()
}

onMounted(loadData)
</script>

<template>
  <AdminPageShell
    title="账户管理"
    description="集中维护登录账户、调度计划、通知绑定和最近执行摘要。上传量、下载量、魔力值、最近登录和下次执行时间都直接在列表中展示。"
    :cards="stateCards"
  >
    <template #actions>
      <ElButton type="primary" @click="openCreateDrawer">
        新增账户
      </ElButton>
      <ElButton :loading="loading" plain @click="loadData">
        刷新列表
      </ElButton>
    </template>

    <ElCard class="panel-card" shadow="never">
      <template #header>
        <div class="panel-card__header">
          <div>
            <strong>账户清单</strong>
            <span>共 {{ accounts.length }} 个账户</span>
          </div>
        </div>
      </template>

      <ElTable :data="accounts" stripe>
        <ElTableColumn label="账户 / 平台" min-width="220">
          <template #default="{ row }">
            <div class="stack">
              <strong>{{ row.name }}</strong>
              <span>{{ row.platform_name }} · {{ row.username || "未配置站点账号" }}</span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="执行摘要" min-width="250">
          <template #default="{ row }">
            <div class="metric-grid">
              <span>上传 {{ displayValue(row.last_uploaded) }}</span>
              <span>下载 {{ displayValue(row.last_downloaded) }}</span>
              <span>魔力 {{ displayValue(row.last_bonus) }}</span>
              <span>状态 {{ displayValue(row.last_status) }}</span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="登录 / 调度" min-width="220">
          <template #default="{ row }">
            <div class="stack">
              <span>最近登录 {{ displayValue(row.last_login) }}</span>
              <span>下次执行 {{ displayValue(row.next_run_at) }}</span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="通知渠道" min-width="160">
          <template #default="{ row }">
            {{ row.notification_names || "未绑定" }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="启用" width="90">
          <template #default="{ row }">
            <ElSwitch :model-value="row.enabled" @change="(value) => toggleAccount(row, Boolean(value))" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <ElSpace>
              <ElButton link type="primary" @click="openEditDrawer(row)">
                编辑
              </ElButton>
              <ElButton link type="success" @click="runAccount(row)">
                立即执行
              </ElButton>
            </ElSpace>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <ElDrawer v-model="drawerVisible" :close-on-click-modal="false" size="560px" title="账户配置">
      <ElForm ref="formRef" label-position="top">
        <div class="form-grid">
          <ElFormItem label="显示名称">
            <ElInput v-model="form.name" placeholder="例如：主站账户" />
          </ElFormItem>
          <ElFormItem label="平台">
            <ElSelect v-model="form.platform_id" placeholder="选择平台">
              <ElOption v-for="item in platforms" :key="item.id" :label="item.name" :value="item.id" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="站点用户名">
            <ElInput v-model="form.username" placeholder="输入站点用户名" />
          </ElFormItem>
          <ElFormItem label="启用状态">
            <ElSwitch v-model="form.enabled" />
          </ElFormItem>
          <ElFormItem :label="form.has_password ? '登录密码（留空表示保持）' : '登录密码'">
            <ElInput v-model="form.password" show-password type="password" />
          </ElFormItem>
          <ElFormItem :label="form.has_totpsecret ? 'TOTP Secret（留空表示保持）' : 'TOTP Secret'">
            <ElInput v-model="form.totpsecret" placeholder="可选" />
          </ElFormItem>
          <ElFormItem :label="form.has_m_team_auth ? 'M-Team Auth（留空表示保持）' : 'M-Team Auth'">
            <ElInput v-model="form.m_team_auth" placeholder="使用 Cookie Token 时填写" />
          </ElFormItem>
          <ElFormItem label="M-Team DID">
            <ElInput v-model="form.m_team_did" placeholder="可选" />
          </ElFormItem>
          <ElFormItem label="代理">
            <ElInput v-model="form.proxy" placeholder="http://127.0.0.1:7890" />
          </ElFormItem>
          <ElFormItem label="CRONTAB">
            <ElInput v-model="form.crontab" placeholder="例如：2 */2 * * *" />
          </ElFormItem>
          <ElFormItem label="超时秒数">
            <ElInputNumber v-model="form.timeout" :min="1" :max="600" />
          </ElFormItem>
          <ElFormItem label="Cookie 模式">
            <ElSelect v-model="form.cookie_mode">
              <ElOption label="normal" value="normal" />
              <ElOption label="strict" value="strict" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="通知渠道">
            <ElSelect v-model="form.notification_channel_ids" multiple placeholder="选择通知渠道">
              <ElOption v-for="item in channelOptions" :key="item.id" :label="item.name" :value="item.id" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="跳过缓存">
            <ElSwitch v-model="form.skip_cache" />
          </ElFormItem>
        </div>
      </ElForm>

      <template #footer>
        <ElSpace>
          <ElButton @click="drawerVisible = false">
            取消
          </ElButton>
          <ElButton :loading="saving" type="primary" @click="saveAccount">
            保存
          </ElButton>
        </ElSpace>
      </template>
    </ElDrawer>
  </AdminPageShell>
</template>

<style lang="scss" scoped>
.panel-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-card__header strong {
  display: block;
  color: #0f172a;
  font-size: 16px;
}

.panel-card__header span {
  color: #64748b;
  font-size: 13px;
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stack strong {
  color: #0f172a;
}

.stack span {
  color: #64748b;
  font-size: 13px;
}

.metric-grid {
  display: grid;
  gap: 6px;
  color: #475569;
  font-size: 13px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
