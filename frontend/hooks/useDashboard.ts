// frontend/hooks/useDashboard.ts
import { useQuery } from '@tanstack/react-query';
import { getDashboard } from '@services/analytics';

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
    staleTime: 30_000,
  });
}
