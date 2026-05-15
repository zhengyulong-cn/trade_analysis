import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getFutureContractList, type FutureContract } from '@/api/modules'

export const useContractsStore = defineStore('contracts', () => {
  const contracts = ref<FutureContract[]>([])
  const loading = ref(false)
  const loaded = ref(false)
  const loadError = ref<string | null>(null)

  const contractsMap = computed(() => {
    return new Map(contracts.value.map((contract) => [contract.symbol, contract]))
  })

  const favoriteContracts = computed(() => {
    return contracts.value.filter((contract) => contract.is_favorite === 1)
  })

  const loadContracts = async (force = false) => {
    if (loading.value) {
      return contracts.value
    }
    if (loaded.value && !force) {
      return contracts.value
    }

    loading.value = true
    loadError.value = null
    try {
      const result = await getFutureContractList()
      contracts.value = result
      loaded.value = true
      return contracts.value
    } catch (error) {
      loadError.value = error instanceof Error ? error.message : 'Failed to load contracts'
      throw error
    } finally {
      loading.value = false
    }
  }

  const setContracts = (items: FutureContract[]) => {
    contracts.value = items
    loaded.value = true
    loadError.value = null
  }

  const upsertContract = (item: FutureContract) => {
    const nextContracts = [...contracts.value]
    const index = nextContracts.findIndex((contract) => contract.contract_id === item.contract_id)
    if (index >= 0) {
      nextContracts[index] = item
    } else {
      nextContracts.push(item)
    }
    contracts.value = nextContracts
    loaded.value = true
  }

  return {
    contracts,
    loading,
    loaded,
    loadError,
    contractsMap,
    favoriteContracts,
    loadContracts,
    setContracts,
    upsertContract,
  }
})
