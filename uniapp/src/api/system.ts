import { http } from '@/http'
import type { UserForm, UserInfo } from '@/api/user'

// ============ 基础分页类型 ============
export interface PageQuery {
  page_no?: number
  page_size?: number
  [key: string]: any
}

export interface PageResult<T> {
  items: T
  total: number
}

// ============ 用户管理 ============
const USER_BASE = '/system/user'

export const systemUserApi = {
  getPage(query: PageQuery): Promise<PageResult<UserInfo[]>> {
    return http.Get(`${USER_BASE}/list`, query)
  },
  getDetail(id: number): Promise<UserForm> {
    return http.Get(`${USER_BASE}/detail/${id}`)
  },
  create(data: UserForm): Promise<ApiResponse> {
    return http.Post(`${USER_BASE}/create`, data)
  },
  update(data: UserForm): Promise<ApiResponse> {
    return http.Put(`${USER_BASE}/update`, data)
  },
  delete(ids: number[]): Promise<ApiResponse> {
    return http.Delete(`${USER_BASE}/delete`, { ids })
  },
}

// ============ 岗位管理 ============
export interface PositionItem {
  id: number
  name: string
  order: number
  status: string
  description: string
  created_time: string
}

const POSITION_BASE = '/system/position'

export const systemPositionApi = {
  getPage(query: PageQuery): Promise<PageResult<PositionItem[]>> {
    return http.Get(`${POSITION_BASE}/list`, query)
  },
  getDetail(id: number): Promise<PositionItem> {
    return http.Get(`${POSITION_BASE}/detail/${id}`)
  },
  create(data: Partial<PositionItem>): Promise<ApiResponse> {
    return http.Post(`${POSITION_BASE}/create`, data)
  },
  update(data: Partial<PositionItem>): Promise<ApiResponse> {
    return http.Put(`${POSITION_BASE}/update`, data)
  },
  delete(ids: number[]): Promise<ApiResponse> {
    return http.Delete(`${POSITION_BASE}/delete`, { ids })
  },
}

// ============ 角色管理 ============
export interface RoleItem {
  id: number
  name: string
  code: string
  order: number
  data_scope: number
  status: string
  description: string
  created_time: string
}

const ROLE_BASE = '/system/role'

export const systemRoleApi = {
  getPage(query: PageQuery): Promise<PageResult<RoleItem[]>> {
    return http.Get(`${ROLE_BASE}/list`, query)
  },
  getDetail(id: number): Promise<RoleItem> {
    return http.Get(`${ROLE_BASE}/detail/${id}`)
  },
  create(data: Partial<RoleItem>): Promise<ApiResponse> {
    return http.Post(`${ROLE_BASE}/create`, data)
  },
  update(data: Partial<RoleItem>): Promise<ApiResponse> {
    return http.Put(`${ROLE_BASE}/update`, data)
  },
  delete(ids: number[]): Promise<ApiResponse> {
    return http.Delete(`${ROLE_BASE}/delete`, { ids })
  },
}

// ============ 参数管理 ============
export interface ParamItem {
  id: number
  config_name: string
  config_key: string
  config_value: string
  config_type: boolean
  status: string
  description: string
  created_time: string
}

const PARAM_BASE = '/system/param'

export const systemParamApi = {
  getPage(query: PageQuery): Promise<PageResult<ParamItem[]>> {
    return http.Get(`${PARAM_BASE}/list`, query)
  },
  getDetail(id: number): Promise<ParamItem> {
    return http.Get(`${PARAM_BASE}/detail/${id}`)
  },
  create(data: Partial<ParamItem>): Promise<ApiResponse> {
    return http.Post(`${PARAM_BASE}/create`, data)
  },
  update(data: Partial<ParamItem>): Promise<ApiResponse> {
    return http.Put(`${PARAM_BASE}/update`, data)
  },
  delete(ids: number[]): Promise<ApiResponse> {
    return http.Delete(`${PARAM_BASE}/delete`, { ids })
  },
}

// ============ 字典管理 ============
export interface DictTypeItem {
  id: number
  dict_name: string
  dict_code: string
  status: string
  description: string
  created_time: string
}

export interface DictDataItem {
  id: number
  dict_label: string
  dict_value: string
  dict_type_id: number
  order: number
  status: string
  created_time: string
}

const DICT_BASE = '/system/dict'

export const systemDictApi = {
  getTypePage(query: PageQuery): Promise<PageResult<DictTypeItem[]>> {
    return http.Get(`${DICT_BASE}/type/list`, query)
  },
  getTypeDetail(id: number): Promise<DictTypeItem> {
    return http.Get(`${DICT_BASE}/type/detail/${id}`)
  },
  createType(data: Partial<DictTypeItem>): Promise<ApiResponse> {
    return http.Post(`${DICT_BASE}/type/create`, data)
  },
  updateType(data: Partial<DictTypeItem>): Promise<ApiResponse> {
    return http.Put(`${DICT_BASE}/type/update`, data)
  },
  deleteType(ids: number[]): Promise<ApiResponse> {
    return http.Delete(`${DICT_BASE}/type/delete`, { ids })
  },
  getDataPage(query: PageQuery): Promise<PageResult<DictDataItem[]>> {
    return http.Get(`${DICT_BASE}/data/list`, query)
  },
}

// ============ 部门管理 ============
export interface DeptItem {
  id: number
  name: string
  parent_id: number | null
  parent_name: string
  order: number
  status: string
  description: string
  leader: string
  phone: string
  email: string
  created_time: string
  children?: DeptItem[]
}

const DEPT_BASE = '/system/dept'

export const systemDeptApi = {
  getTree(query?: PageQuery): Promise<DeptItem[]> {
    return http.Get(`${DEPT_BASE}/tree`, query)
  },
  getDetail(id: number): Promise<DeptItem> {
    return http.Get(`${DEPT_BASE}/detail/${id}`)
  },
  create(data: Partial<DeptItem>): Promise<ApiResponse> {
    return http.Post(`${DEPT_BASE}/create`, data)
  },
  update(data: Partial<DeptItem>): Promise<ApiResponse> {
    return http.Put(`${DEPT_BASE}/update`, data)
  },
  delete(ids: number[]): Promise<ApiResponse> {
    return http.Delete(`${DEPT_BASE}/delete`, { ids })
  },
}

// ============ 菜单管理 ============
export interface MenuItem {
  id: number
  name: string
  type: number
  order: number
  permission: string
  icon: string
  route_name: string
  route_path: string
  component_path: string
  parent_id: number | null
  parent_name: string
  hidden: boolean
  status: string
  description: string
  created_time: string
  children?: MenuItem[]
}

const MENU_BASE = '/system/menu'

export const systemMenuApi = {
  getTree(query?: PageQuery): Promise<MenuItem[]> {
    return http.Get(`${MENU_BASE}/tree`, query)
  },
  getDetail(id: number): Promise<MenuItem> {
    return http.Get(`${MENU_BASE}/detail/${id}`)
  },
  create(data: Partial<MenuItem>): Promise<ApiResponse> {
    return http.Post(`${MENU_BASE}/create`, data)
  },
  update(data: Partial<MenuItem>): Promise<ApiResponse> {
    return http.Put(`${MENU_BASE}/update`, data)
  },
  delete(ids: number[]): Promise<ApiResponse> {
    return http.Delete(`${MENU_BASE}/delete`, { ids })
  },
}

// ============ 日志管理 ============
export interface LogItem {
  id: number
  module: string
  method: string
  request_method: string
  request_url: string
  ip: string
  status: number
  cost_time: number
  username: string
  created_time: string
}

const LOG_BASE = '/system/log'

export const systemLogApi = {
  getPage(query: PageQuery): Promise<PageResult<LogItem[]>> {
    return http.Get(`${LOG_BASE}/list`, query)
  },
  getDetail(id: number): Promise<LogItem> {
    return http.Get(`${LOG_BASE}/detail/${id}`)
  },
  delete(ids: number[]): Promise<ApiResponse> {
    return http.Delete(`${LOG_BASE}/delete`, { ids })
  },
}

// 导出所有 System API
export const systemApi = {
  user: systemUserApi,
  position: systemPositionApi,
  role: systemRoleApi,
  param: systemParamApi,
  dict: systemDictApi,
  dept: systemDeptApi,
  menu: systemMenuApi,
  log: systemLogApi,
}
