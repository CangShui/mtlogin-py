export type CurrentUserResponseData = ApiResponseData<{ username: string, roles: string[] }>

export type LogoutResponseData = ApiResponseData<Record<string, never>>
