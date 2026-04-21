<script lang="ts" setup>
import ThemeSwitch from "@@/components/ThemeSwitch/index.vue"
import { useDevice } from "@@/composables/useDevice"
import { useLayoutMode } from "@@/composables/useLayoutMode"
import { ArrowDown, UserFilled } from "@element-plus/icons-vue"
import { useAppStore } from "@/pinia/stores/app"
import { useSettingsStore } from "@/pinia/stores/settings"
import { useUserStore } from "@/pinia/stores/user"
import { Breadcrumb, Hamburger, Sidebar } from "../index"

const { isMobile } = useDevice()

const { isTop } = useLayoutMode()

const router = useRouter()

const appStore = useAppStore()
const userStore = useUserStore()
const settingsStore = useSettingsStore()
const route = useRoute()
const { showThemeSwitch } = storeToRefs(settingsStore)

const currentTitle = computed(() => String(route.meta.title || "MTLogin Admin"))

/** 切换侧边栏 */
function toggleSidebar() {
  appStore.toggleSidebar(false)
}

/** 登出 */
async function logout() {
  await userStore.logout()
  router.push("/login")
}
</script>

<template>
  <div class="navigation-bar">
    <Hamburger
      v-if="!isTop || isMobile"
      :is-active="appStore.sidebar.opened"
      class="hamburger"
      @toggle-click="toggleSidebar"
    />
    <Breadcrumb v-if="!isTop || isMobile" class="breadcrumb" />
    <Sidebar v-if="isTop && !isMobile" class="sidebar" />
    <div v-if="!isTop || isMobile" class="title-pill">
      <span class="eyebrow">Admin Console</span>
      <strong>{{ currentTitle }}</strong>
    </div>
    <div class="right-menu">
      <ThemeSwitch v-if="showThemeSwitch" class="right-menu-item" />
      <el-dropdown trigger="click">
        <div class="right-menu-item user">
          <el-avatar :icon="UserFilled" :size="30" />
          <span>{{ userStore.username || "admin" }}</span>
          <el-icon><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              {{ currentTitle }}
            </el-dropdown-item>
            <el-dropdown-item divided @click="logout">
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.navigation-bar {
  height: var(--v3-navigationbar-height);
  overflow: hidden;
  color: var(--v3-navigationbar-text-color);
  display: flex;
  justify-content: space-between;
  .hamburger {
    display: flex;
    align-items: center;
    height: 100%;
    padding: 0 15px;
    cursor: pointer;
  }
  .breadcrumb {
    flex: 1;
    // 参考 Bootstrap 的响应式设计将宽度设置为 576
    @media screen and (max-width: 576px) {
      display: none;
    }
  }
  .sidebar {
    flex: 1;
    // 设置 min-width 是为了让 Sidebar 里的 el-menu 宽度自适应
    min-width: 0px;
    :deep(.el-menu) {
      background-color: transparent;
    }
    :deep(.el-sub-menu) {
      &.is-active {
        .el-sub-menu__title {
          color: var(--el-color-primary);
        }
      }
    }
  }
  .right-menu {
    margin-right: 10px;
    height: 100%;
    display: flex;
    align-items: center;
    &-item {
      margin: 0 10px;
      cursor: pointer;
      &:last-child {
        margin-left: 20px;
      }
    }
    .user {
      display: flex;
      align-items: center;
      gap: 10px;
      .el-avatar {
        border: 1px solid rgb(15 23 42 / 8%);
        background: linear-gradient(135deg, #0f766e, #38bdf8);
        color: white;
      }
      span {
        font-size: 15px;
        font-weight: 600;
      }
    }
  }

  .title-pill {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 2px;
    .eyebrow {
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: rgb(100 116 139);
    }
    strong {
      font-size: 16px;
      color: rgb(15 23 42);
    }
  }
}
</style>
