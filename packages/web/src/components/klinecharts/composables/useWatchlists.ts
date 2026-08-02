import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import {
  addWatchlistContractApi,
  createWatchlistApi,
  deleteWatchlistApi,
  getWatchlistContractsApi,
  getWatchlistsApi,
  removeWatchlistContractApi,
  reorderWatchlistContractsApi,
  type Watchlist,
  type WatchlistContract,
} from '@/api/modules'

export const useWatchlists = () => {
  const watchlists = ref<Watchlist[]>([])
  const activeWatchlistId = ref<number | null>(null)
  const watchlistContracts = ref<WatchlistContract[]>([])

  const loadWatchlistContracts = async (watchlistId: number) => {
    watchlistContracts.value = await getWatchlistContractsApi(watchlistId)
  }

  const loadWatchlists = async () => {
    watchlists.value = await getWatchlistsApi()
    const activeExists = watchlists.value.some((item) => item.watchlist_id === activeWatchlistId.value)
    activeWatchlistId.value = activeExists
      ? activeWatchlistId.value
      : (watchlists.value[0]?.watchlist_id ?? null)
    if (activeWatchlistId.value !== null) {
      await loadWatchlistContracts(activeWatchlistId.value)
    }
  }

  const switchWatchlist = async (watchlistId: number) => {
    activeWatchlistId.value = watchlistId
    await loadWatchlistContracts(watchlistId)
  }

  const createWatchlist = async (name: string) => {
    const watchlist = await createWatchlistApi({ name })
    await loadWatchlists()
    await switchWatchlist(watchlist.watchlist_id)
  }

  const deleteWatchlist = async (watchlistId: number) => {
    await deleteWatchlistApi(watchlistId)
    activeWatchlistId.value = null
    await loadWatchlists()
  }

  const addContractToWatchlist = async (contractId: number) => {
    if (activeWatchlistId.value === null) return
    await addWatchlistContractApi(activeWatchlistId.value, contractId)
    await loadWatchlistContracts(activeWatchlistId.value)
    await loadWatchlists()
  }

  const removeContractFromWatchlist = async (contractId: number) => {
    if (activeWatchlistId.value === null) return
    await removeWatchlistContractApi(activeWatchlistId.value, contractId)
    await loadWatchlistContracts(activeWatchlistId.value)
    await loadWatchlists()
  }

  const reorderWatchlistContracts = async (contractIds: number[]) => {
    if (activeWatchlistId.value === null) return
    try {
      await reorderWatchlistContractsApi(activeWatchlistId.value, contractIds)
      await loadWatchlistContracts(activeWatchlistId.value)
    } catch {
      await loadWatchlistContracts(activeWatchlistId.value)
      ElMessage.error('保存自选表排序失败')
    }
  }

  return {
    watchlists,
    activeWatchlistId,
    watchlistContracts,
    loadWatchlists,
    switchWatchlist,
    createWatchlist,
    deleteWatchlist,
    addContractToWatchlist,
    removeContractFromWatchlist,
    reorderWatchlistContracts,
  }
}
