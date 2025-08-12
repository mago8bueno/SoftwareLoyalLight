// hooks/useClients.ts
import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getClients,
  createClient as apiCreateClient,
  updateClient as apiUpdateClient,
  deleteClient as apiDeleteClient,
  type Client,
  type ClientCreate,
} from '@services/clients';

const KEY = (q: string) => ['clients', q] as const;

// Pequeño hook de debounce sin dependencias
function useDebounce<T>(value: T, delay = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export function useClients(search: string = '') {
  const queryClient = useQueryClient();
  const debounced = useDebounce(search, 350);

  const query = useQuery<Client[], Error>({
    queryKey: KEY(debounced),
    queryFn: () => getClients(debounced || undefined),
    staleTime: 30_000,
    // v5: en vez de keepPreviousData, usa placeholderData para mostrar lo anterior
    placeholderData: (prev) => prev,
    refetchOnWindowFocus: false,
  });

  const createMutation = useMutation<Client, Error, ClientCreate>({
    mutationFn: apiCreateClient,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY(debounced) }),
  });

  const updateMutation = useMutation<Client, Error, { id: string; data: Partial<ClientCreate> }>({
    mutationFn: ({ id, data }) => apiUpdateClient(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY(debounced) }),
  });

  const deleteMutation = useMutation<void, Error, string>({
    mutationFn: (id) => apiDeleteClient(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY(debounced) }),
  });

  return {
    data: query.data ?? [],
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error,

    createClient: createMutation.mutateAsync,
    isCreating: createMutation.isPending,

    updateClient: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,

    deleteClient: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
  };
}
