import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPurchases, createPurchase } from '../services/purchases'
import type { Purchase } from '../types'

export function usePurchases() {
  const queryClient = useQueryClient()
  const query = useQuery<Purchase[]>({
    queryKey: ['purchases'],
    queryFn: async () => {
      const response = await getPurchases();
      return response.data;
    }
  })
  const mutation = useMutation({
    mutationFn: createPurchase,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['purchases'] })
  })
  return { ...query, createPurchase: mutation.mutateAsync, isCreating: mutation.isPending }
}
