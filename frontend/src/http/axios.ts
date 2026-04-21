import type { AxiosInstance, AxiosRequestConfig } from "axios"
import axios from "axios"
import { get, merge } from "lodash-es"
import { useUserStore } from "@/pinia/stores/user"

function redirectToLogin() {
  const redirect = `${location.pathname}${location.search}`
  const target = `/login?redirect=${encodeURIComponent(redirect)}`
  if (location.pathname !== "/login") location.replace(target)
}

function logoutLocally() {
  useUserStore().clearSession()
  redirectToLogin()
}

/** 创建请求实例 */
function createInstance() {
  const instance = axios.create()
  instance.interceptors.request.use(
    config => config,
    error => Promise.reject(error)
  )
  instance.interceptors.response.use(
    (response) => {
      const apiData = response.data
      const responseType = response.config.responseType
      if (responseType === "blob" || responseType === "arraybuffer") return apiData
      const code = apiData.code
      if (code === undefined) {
        ElMessage.error("非本系统的接口")
        return Promise.reject(new Error("非本系统的接口"))
      }
      switch (code) {
        case 0:
          return apiData
        case 401:
          logoutLocally()
          return Promise.reject(new Error(apiData.message || "未授权"))
        default:
          ElMessage.error(apiData.message || "Error")
          return Promise.reject(new Error(apiData.message || "Error"))
      }
    },
    (error) => {
      const status = get(error, "response.status")
      const message = get(error, "response.data.message")
      switch (status) {
        case 400:
          error.message = "请求错误"
          break
        case 401:
          error.message = message || "未授权"
          logoutLocally()
          break
        case 403:
          error.message = message || "拒绝访问"
          break
        case 404:
          error.message = "请求地址出错"
          break
        case 408:
          error.message = "请求超时"
          break
        case 500:
          error.message = "服务器内部错误"
          break
        case 501:
          error.message = "服务未实现"
          break
        case 502:
          error.message = "网关错误"
          break
        case 503:
          error.message = "服务不可用"
          break
        case 504:
          error.message = "网关超时"
          break
        case 505:
          error.message = "HTTP 版本不受支持"
          break
      }
      ElMessage.error(error.message)
      return Promise.reject(error)
    }
  )
  return instance
}

/** 创建请求方法 */
function createRequest(instance: AxiosInstance) {
  return <T>(config: AxiosRequestConfig): Promise<T> => {
    const defaultConfig: AxiosRequestConfig = {
      baseURL: import.meta.env.VITE_BASE_URL,
      headers: {
        "Content-Type": "application/json"
      },
      data: {},
      timeout: 5000,
      withCredentials: true
    }
    const mergeConfig = merge(defaultConfig, config)
    return instance(mergeConfig)
  }
}

/** 用于请求的实例 */
const instance = createInstance()

/** 用于请求的方法 */
export const request = createRequest(instance)
