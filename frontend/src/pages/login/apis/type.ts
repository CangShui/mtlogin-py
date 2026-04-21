export interface LoginRequestData {
  username: string
  password: string
}

export type LoginResponseData = ApiResponseData<{ username: string, roles: string[] }>
