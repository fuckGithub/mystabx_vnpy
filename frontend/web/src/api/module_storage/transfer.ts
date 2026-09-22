import request from '@utils/http'

/** 对应后端 `plugin.module_storage.transfer` */
const API_PATH = '/storage/transfer'

const StorageTransferAPI = {
  getTransferList(query: StorageTransferPageQuery) {
    return request<ApiResponse<PageResult<StorageTransferTable>>>({
      url: `${API_PATH}/list`,
      method: 'get',
      params: query,
    })
  },

  getTransferDetail(id: number) {
    return request<ApiResponse<StorageTransferTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: 'get',
    })
  },

  createTransfer(body: StorageTransferForm) {
    return request<ApiResponse<StorageTransferTable>>({
      url: `${API_PATH}/create`,
      method: 'post',
      data: body,
    })
  },

  updateTransfer(id: number, body: StorageTransferForm) {
    return request<ApiResponse<StorageTransferTable>>({
      url: `${API_PATH}/update/${id}`,
      method: 'put',
      data: body,
    })
  },

  deleteTransfer(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: 'delete',
      data: body,
    })
  },
}

export default StorageTransferAPI
export { StorageTransferAPI }

export interface StorageTransferPageQuery extends PageQuery {
  name?: string
  source_id?: number
  target_id?: number
  transfer_status?: number
  status?: string
  created_time?: string[]
  updated_time?: string[]
  created_id?: number
  updated_id?: number
}

export interface StorageTransferTable extends BaseType {
  name?: string
  source_id?: number
  target_id?: number
  source_path?: string
  target_path?: string
  transfer_status?: number
  progress?: number
  error_msg?: string
  description?: string
  status?: string
}

export interface StorageTransferForm extends BaseFormType {
  name?: string
  source_id?: number
  target_id?: number
  source_path?: string
  target_path?: string
  transfer_status?: number
  progress?: number
  error_msg?: string
  description?: string
}
