<script lang="ts" setup>
import type { PlatformItem, StateCard } from "@@/apis/admin/type"
import { getBootstrapApi, getPlatformsApi, togglePlatformApi } from "@@/apis/admin"
import AdminPageShell from "@@/components/AdminPageShell.vue"

const loading = ref(false)
const stateCards = ref<StateCard[]>([])
const platforms = ref<PlatformItem[]>([])

async function loadData() {
  loading.value = true
  try {
    const [bootstrapResponse, platformsResponse] = await Promise.all([getBootstrapApi(), getPlatformsApi()])
    stateCards.value = bootstrapResponse.data.stateCards
    platforms.value = platformsResponse.data.items
  } finally {
    loading.value = false
  }
}

async function togglePlatform(platform: PlatformItem, enabled: boolean) {
  await togglePlatformApi(platform.id, enabled)
  ElMessage.success("平台状态已更新。")
  await loadData()
}

onMounted(loadData)
</script>

<template>
  <AdminPageShell
    title="平台配置"
    description="维护当前支持的平台入口和固定 API 配置。平台关闭后，关联账户将不会进入调度。"
    :cards="stateCards"
  >
    <template #actions>
      <ElButton :loading="loading" plain @click="loadData">
        刷新平台
      </ElButton>
    </template>

    <ElCard class="panel-card" shadow="never">
      <template #header>
        <div class="panel-header">
          <strong>平台列表</strong>
          <span>当前共 {{ platforms.length }} 个平台</span>
        </div>
      </template>
      <ElTable :data="platforms" stripe>
        <ElTableColumn label="平台" min-width="180">
          <template #default="{ row }">
            <div class="stack">
              <strong>{{ row.name }}</strong>
              <span>{{ row.code }}</span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="api_host" label="API Host" min-width="220" />
        <ElTableColumn prop="referer" label="Referer" min-width="240" />
        <ElTableColumn label="类型" width="100">
          <template #default="{ row }">
            <ElTag :type="row.builtin ? 'success' : 'info'">
              {{ row.builtin ? "内置" : "自定义" }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="启用" width="110">
          <template #default="{ row }">
            <ElSwitch :model-value="row.enabled" @change="(value) => togglePlatform(row, Boolean(value))" />
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>
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
