import type * as Users from "./type"
import { request } from "@/http/axios"

/** 获取当前登录用户详情 */
export function getCurrentUserApi() {
  return request<Users.CurrentUserResponseData>({
    url: "/session/me",
    method: "get"
  })
}

/** 退出当前登录用户 */
export function logoutCurrentUserApi() {
  return request<Users.LogoutResponseData>({
    url: "/session/logout",
    method: "post"
  })
}
