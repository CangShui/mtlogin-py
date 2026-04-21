import type * as Auth from "./type"
import { request } from "@/http/axios"

export function loginApi(data: Auth.LoginRequestData) {
  return request<Auth.LoginResponseData>({
    url: "/session/login",
    method: "post",
    data
  })
}
