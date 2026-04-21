<script lang="ts" setup>
import type { HistoryRecordItem, OptionItem, StateCard } from "@@/apis/admin/type"
import { getBootstrapApi, getHistoryApi } from "@@/apis/admin"
import AdminPageShell from "@@/components/AdminPageShell.vue"

const loading = ref(false)
const stateCards = ref<StateCard[]>([])
const records = ref<HistoryRecordItem[]>([])
const accounts = ref<OptionItem[]>([])
const platforms = ref<OptionItem[]>([])
const filters = reactive({
  account_id: "",
  platform_id: "",
  status: "",
  started_from: "",
  started_to: ""
})

function displayValue(value: string | null | undefined) {
  return value ? value : "--"
}

async function loadData() {
  loading.value = true
  try {
    const [bootstrapResponse, historyResponse] = await Promise.all([
      getBootstrapApi(),
      getHistoryApi({ ...filters })
    ])
    stateCards.value = bootstrapResponse.data.stateCards
    records.value = historyResponse.data.items
    accounts.value = historyResponse.data.accounts
    platforms.value = historyResponse.data.platforms
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.account_id = ""
  filters.platform_id = ""
  filters.status = ""
  filters.started_from = ""
  filters.started_to = ""
  loadData()
}

onMounted(loadData)
</script>

<template>
  <AdminPageShell
    title="执行记录"
    description="按账户、平台、状态和时间范围筛选执行结果，快速定位错误记录并查看最近一次运行指标。"
    :cards="stateCards"
  >
    <template #actions>
      <ElButton :loading="loading" plain @click="loadData">
        刷新记录
      </ElButton>
    </template>

    <ElCard class="panel-card" shadow="never">
      <ElForm class="filter-grid" label-position="top">
        <ElFormItem label="账户">
          <ElSelect v-model="filters.account_id" clearable placeholder="全部账户">
            <ElOption v-for="item in accounts" :key="item.id" :label="item.name" :value="String(item.id)" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="平台">
          <ElSelect v-model="filters.platform_id" clearable placeholder="全部平台">
            <ElOption v-for="item in platforms" :key="item.id" :label="item.name" :value="String(item.id)" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="状态">
          <ElSelect v-model="filters.status" clearable placeholder="全部状态">
            <ElOption label="成功" value="success" />
            <ElOption label="失败" value="error" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="开始时间">
          <ElDatePicker
            v-model="filters.started_from"
            clearable
            placeholder="开始时间"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm"
          />
        </ElFormItem>
        <ElFormItem label="结束时间">
          <ElDatePicker
            v-model="filters.started_to"
            clearable
            placeholder="结束时间"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm"
          />
        </ElFormItem>
        <ElFormItem class="filter-actions" label="操作">
          <div class="filter-actions__buttons">
            <ElButton type="primary" @click="loadData">
              查询
            </ElButton>
            <ElButton @click="resetFilters">
              重置
            </ElButton>
          </div>
        </ElFormItem>
      </ElForm>
    </ElCard>

    <ElCard class="panel-card" shadow="never">
      <ElTable :data="records" stripe>
        <ElTableColumn prop="started_at" label="开始时间" min-width="170" />
        <ElTableColumn label="账户 / 平台" min-width="200">
          <template #default="{ row }">
            <div class="stack">
              <strong>{{ row.account_name }}</strong>
              <span>{{ row.platform_name }} · {{ row.trigger_mode }}</span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="结果" min-width="240">
          <template #default="{ row }">
            <div class="stack">
              <ElTag :type="row.status === 'success' ? 'success' : 'danger'">
                {{ row.status === "success" ? "成功" : "失败" }}
              </ElTag>
              <span>{{ row.result_message }}</span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="指标" min-width="220">
          <template #default="{ row }">
            <div class="stack">
              <span>上传 {{ displayValue(row.uploaded) }}</span>
              <span>下载 {{ displayValue(row.downloaded) }}</span>
              <span>魔力 {{ displayValue(row.bonus) }}</span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="登录 / 浏览" min-width="200">
          <template #default="{ row }">
            <div class="stack">
              <span>登录 {{ displayValue(row.last_login) }}</span>
              <span>浏览 {{ displayValue(row.last_browse) }}</span>
            </div>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>
  </AdminPageShell>
</template>

<style lang="scss" scoped>
.filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0 16px;
}

.filter-actions__buttons,
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

@media (max-width: 960px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
