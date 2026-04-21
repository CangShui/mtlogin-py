export interface CurrentUser {
  username: string
  roles: string[]
}

export interface StateCard {
  label: string
  value: string
}

export interface RuntimeState {
  scheduler_status: string
  schedule_message: string
  next_run_at: string
  last_message: string
  running: boolean
  status: string
}

export interface PlatformItem {
  id: number
  code: string
  name: string
  api_host: string
  referer: string
  enabled: boolean
  builtin: boolean
  created_at: string
  updated_at: string
}

export interface NotificationChannelItem {
  id: number
  name: string
  type: string
  enabled: boolean
  tgbot_chat_id: number
  tgbot_proxy: string
  has_tgbot_token: boolean
  created_at: string
  updated_at: string
}

export interface AccountItem {
  id: number
  name: string
  platform_id: number
  platform_name: string
  platform_code: string
  platform_enabled: boolean
  enabled: boolean
  username: string
  m_team_did: string
  proxy: string
  crontab: string
  timeout: number
  cookie_mode: string
  skip_cache: boolean
  notification_names: string
  notification_channel_ids: number[]
  last_status: string
  last_started_at: string
  last_finished_at: string
  last_message: string
  last_uploaded: string
  last_downloaded: string
  last_bonus: string
  last_login: string
  next_run_at: string
  has_password: boolean
  has_totpsecret: boolean
  has_m_team_auth: boolean
  created_at: string
  updated_at: string
}

export interface HistoryRecordItem {
  id: number
  account_id: number
  account_name: string
  account_username: string
  platform_id: number
  platform_name: string
  platform_code: string
  trigger_mode: string
  status: string
  result_message: string
  started_at: string
  finished_at: string
  run_username: string
  uploaded: string
  downloaded: string
  bonus: string
  last_login: string
  last_browse: string
  created_at: string
}

export interface OptionItem {
  id: number
  name: string
  code?: string
}

export interface BootstrapPayload {
  currentUser: CurrentUser
  runtimeState: RuntimeState
  stateCards: StateCard[]
  navigation: Array<{ page: string, label: string }>
}

export interface AccountsPayload {
  items: AccountItem[]
  channels: NotificationChannelItem[]
  platforms: PlatformItem[]
  defaults: {
    platform_id: number
    timeout: number
    cookie_mode: string
  }
}

export interface HistoryPayload {
  items: HistoryRecordItem[]
  accounts: OptionItem[]
  platforms: OptionItem[]
  filters: Record<string, string>
}

export interface SettingsPayload {
  adminUsername: string
  runtimeInfo: Record<string, string | number>
  logTail: string
}

export interface NotificationSavePayload {
  channel_id?: number
  name: string
  type: string
  enabled: boolean
  tgbot_token: string
  tgbot_chat_id: number | string
  tgbot_proxy: string
}

export interface AccountSavePayload {
  account_id?: number
  name: string
  platform_id: number
  enabled: boolean
  username: string
  password: string
  totpsecret: string
  proxy: string
  crontab: string
  m_team_auth: string
  m_team_did: string
  timeout: number
  cookie_mode: string
  skip_cache: boolean
  notification_channel_ids: number[]
}

export interface AdminSettingsPayload {
  admin_username: string
  current_password: string
  new_password: string
  confirm_password: string
}

export type BootstrapResponseData = ApiResponseData<BootstrapPayload>
export type PlatformListResponseData = ApiResponseData<{ items: PlatformItem[] }>
export type PlatformItemResponseData = ApiResponseData<PlatformItem>
export type NotificationListResponseData = ApiResponseData<{ items: NotificationChannelItem[] }>
export type NotificationItemResponseData = ApiResponseData<NotificationChannelItem>
export type AccountListResponseData = ApiResponseData<AccountsPayload>
export type AccountItemResponseData = ApiResponseData<AccountItem>
export type HistoryResponseData = ApiResponseData<HistoryPayload>
export type SettingsResponseData = ApiResponseData<SettingsPayload>
export type AdminSettingsResponseData = ApiResponseData<{ username: string }>
