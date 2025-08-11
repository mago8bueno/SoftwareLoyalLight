import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listItems, createItem, type Item } from '@services/items';

export function useItems() {
  const queryClient = useQueryClient();
  const query = useQuery<Item[]>({
    queryKey: ['items'],
    queryFn: () => listItems(),
  });
  const mutation = useMutation({
    mutationFn: createItem,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['items'] }),
  });
  return { ...query, createItem: mutation.mutateAsync, isCreating: mutation.isPending };
}
