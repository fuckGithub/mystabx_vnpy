import request from '@utils/http'

/** 对应后端 `plugin.module_storage.browse` */
const API_PATH = '/storage/browse'

const StorageBrowseAPI = {
  listFiles(params: BrowseQuery) {
    return request<ApiResponse<BrowseResult>>({
      url: `${API_PATH}/list`,
      method: 'get',
      params,
    })
  },
}

export default StorageBrowseAPI
export { StorageBrowseAPI }

export interface BrowseQuery {
  node_id: number
  path?: string
}

export interface BrowseItem {
  name: string
  type: string
  size?: number
  modified_time?: string
}

export interface BrowseResult {
  node_id: number
  path: string
  items: BrowseItem[]
}
