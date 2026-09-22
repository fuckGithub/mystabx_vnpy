import request from '@utils/http'

const API_PATH = '/application/portal'

export interface ApplicationForm {
  name: string
  access_url: string
  icon_url?: string
  status: string
  description?: string
}

export interface ApplicationInfo extends ApplicationForm {
  id: number
  created_by?: { name: string }
  updated_by?: { name: string }
  created_time?: string
  updated_time?: string
}

export interface ApplicationQuery {
  name?: string
  status?: string
  page_no?: number
  page_size?: number
}

const ApplicationAPI = {
  listApp(query: ApplicationQuery) {
    return request<ApiResponse<PageResult<ApplicationInfo>>>({
      url: `${API_PATH}/list`,
      method: 'get',
      params: query,
    })
  },

  detailApp(id: number) {
    return request<ApiResponse<ApplicationInfo>>({
      url: `${API_PATH}/detail/${id}`,
      method: 'get',
    })
  },

  createApp(body: ApplicationForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/create`,
      method: 'post',
      data: body,
    })
  },

  updateApp(id: number, body: ApplicationForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/update/${id}`,
      method: 'put',
      data: body,
    })
  },

  deleteApp(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: 'delete',
      data: body,
    })
  },
}

export default ApplicationAPI
