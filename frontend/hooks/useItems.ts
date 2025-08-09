import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getItems, createItem } from '../services/items';
import type { Item } from '../types';

export function useItems() {
  const queryClient = useQueryClient();
  const query = useQuery<Item[]>({
    queryKey: ['items'],
    queryFn: async () => {
      const response = await getItems();
      return response.data;
    },
  });
  const mutation = useMutation({
    mutationFn: createItem,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['items'] }),
  });
  return { ...query, createItem: mutation.mutateAsync, isCreating: mutation.isPending };
}
