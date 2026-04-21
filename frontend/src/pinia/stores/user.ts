import { getCurrentUserApi } from "@@/apis/users"
import { logoutCurrentUserApi } from "@@/apis/users"
import { setToken as _setToken, getToken, removeToken } from "@@/utils/local-storage"
import { pinia } from "@/pinia"
import { resetRouter } from "@/router"
import { routerConfig } from "@/router/config"
import { loginApi } from "@/pages/login/apis"
import { useSettingsStore } from "./settings"
import { useTagsViewStore } from "./tags-view"

export const useUserStore = defineStore("user", () => {
  const token = ref<string>(getToken() || "")

  const roles = ref<string[]>([])

  const username = ref<string>("")

  const tagsViewStore = useTagsViewStore()

  const settingsStore = useSettingsStore()

  const setToken = (value: string) => {
    _setToken(value)
    token.value = value
  }

  const getInfo = async () => {
    const { data } = await getCurrentUserApi()
    username.value = data.username
    roles.value = data.roles?.length > 0 ? data.roles : routerConfig.defaultRoles
  }

  const login = async (usernameValue: string, passwordValue: string) => {
    const { data } = await loginApi({ username: usernameValue, password: passwordValue })
    setToken("admin-session")
    username.value = data.username
    roles.value = data.roles?.length > 0 ? data.roles : routerConfig.defaultRoles
  }

  const clearSession = () => {
    removeToken()
    token.value = ""
    roles.value = []
    username.value = ""
    resetRouter()
    resetTagsView()
  }

  const logout = async () => {
    try {
      await logoutCurrentUserApi()
    } finally {
      clearSession()
    }
  }

  const resetTagsView = () => {
    if (!settingsStore.cacheTagsView) {
      tagsViewStore.delAllVisitedViews()
      tagsViewStore.delAllCachedViews()
    }
  }

  return { token, roles, username, setToken, getInfo, login, clearSession, logout, resetToken: clearSession }
})

/**
 * @description 在 SPA 应用中可用于在 pinia 实例被激活前使用 store
 * @description 在 SSR 应用中可用于在 setup 外使用 store
 */
export function useUserStoreOutside() {
  return useUserStore(pinia)
}
