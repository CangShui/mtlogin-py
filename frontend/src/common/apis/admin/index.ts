import type * as Admin from "./type"
import { request } from "@/http/axios"

export function getBootstrapApi() {
  return request<Admin.BootstrapResponseData>({
    url: "/bootstrap",
    method: "get"
  })
}

export function getPlatformsApi() {
  return request<Admin.PlatformListResponseData>({
    url: "/platforms",
    method: "get"
  })
}

export function togglePlatformApi(platformId: number, enabled: boolean) {
  return request<Admin.PlatformItemResponseData>({
    url: `/platforms/${platformId}/toggle`,
    method: "post",
    data: { enabled }
  })
}

export function getNotificationsApi() {
  return request<Admin.NotificationListResponseData>({
    url: "/notifications",
    method: "get"
  })
}

export function saveNotificationApi(data: Admin.NotificationSavePayload) {
  return request<Admin.NotificationItemResponseData>({
    url: "/notifications",
    method: "post",
    data
  })
}

export function toggleNotificationApi(channelId: number, enabled: boolean) {
  return request<Admin.NotificationItemResponseData>({
    url: `/notifications/${channelId}/toggle`,
    method: "post",
    data: { enabled }
  })
}

export function getAccountsApi() {
  return request<Admin.AccountListResponseData>({
    url: "/accounts",
    method: "get"
  })
}

export function saveAccountApi(data: Admin.AccountSavePayload) {
  return request<Admin.AccountItemResponseData>({
    url: "/accounts",
    method: "post",
    data
  })
}

export function toggleAccountApi(accountId: number, enabled: boolean) {
  return request<Admin.AccountItemResponseData>({
    url: `/accounts/${accountId}/toggle`,
    method: "post",
    data: { enabled }
  })
}

export function runAccountApi(accountId: number) {
  return request<Admin.AccountItemResponseData>({
    url: `/accounts/${accountId}/run`,
    method: "post"
  })
}

export function getHistoryApi(params: Record<string, string>) {
  return request<Admin.HistoryResponseData>({
    url: "/history",
    method: "get",
    params
  })
}

export function getSettingsApi() {
  return request<Admin.SettingsResponseData>({
    url: "/settings",
    method: "get"
  })
}

export function updateAdminSettingsApi(data: Admin.AdminSettingsPayload) {
  return request<Admin.AdminSettingsResponseData>({
    url: "/settings/admin",
    method: "post",
    data
  })
}
