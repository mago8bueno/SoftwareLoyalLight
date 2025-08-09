// pages/index.tsx
// Dashboard funcional: IA recomendaciones, gráfico de tendencias y rankings

import React from 'react'
import Link from 'next/link'
import {
  Box,
  Button,
  Heading,
  Text,
  SimpleGrid,
  VStack,
  HStack,
  Badge,
  Alert,
  AlertIcon,
  Spinner,
} from '@chakra-ui/react'
import dynamic from 'next/dynamic'
import { useQuery } from '@tanstack/react-query'
import {
  getSalesTrend7d,
  getTopCustomers90d,
  getTopProducts90d,
  getChurnRisk,
  type SalesPoint,
  type TopCustomer,
  type TopProduct,
  type ChurnRisk,
} from '../services/analytics'

// Carga perezosa del gráfico (lado cliente)
const TrendChart = dynamic(() => import('../components/TrendChart'), { ssr: false })

export default function Dashboard() {
  // Tendencia 7 días
  const {
    data: trend = [],
    isLoading: loadingTrend,
    isError: errTrend,
  } = useQuery<SalesPoint[]>({
    queryKey: ['trend7d'],
    queryFn: getSalesTrend7d,
    staleTime: 60_000,
  })

  // Top clientes 90 días
  const {
    data: topCustomers = [],
    isLoading: loadingCustomers,
    isError: errCustomers,
  } = useQuery<TopCustomer[]>({
    queryKey: ['topCustomers90d', 5],
    queryFn: () => getTopCustomers90d(5),
    staleTime: 60_000,
  })

  // Top productos 90 días
  const {
    data: topProducts = [],
    isLoading: loadingProducts,
    isError: errProducts,
  } = useQuery<TopProduct[]>({
    queryKey: ['topProducts90d', 5],
    queryFn: () => getTopProducts90d(5),
    staleTime: 60_000,
  })

  // Riesgo de churn
  const {
    data: churn = [],
    isLoading: loadingChurn,
    isError: errChurn,
  } = useQuery<ChurnRisk[]>({
    queryKey: ['churnRisk', 5],
    queryFn: () => getChurnRisk(5),
    staleTime: 60_000,
  })

  const chartData =
    loadingTrend || errTrend
      ? []
      : trend.map((p) => ({
          date: (p.day ?? '').toString().slice(5), // MM-DD
          value: Number(p.revenue ?? 0),
        }))

  return (
    <Box p={4}>
      <Heading mb={6}>Dashboard</Heading>

      {/* IA Recomendaciones */}
      <Box p={4} bg="white" rounded="md" shadow="sm" mb={6}>
        <Text fontSize="lg" fontWeight="bold">
          IA Recomendaciones
        </Text>

        {loadingChurn ? (
          <HStack mt={2}><Spinner size="sm" /><Text>Cargando…</Text></HStack>
        ) : errChurn ? (
          <Alert status="error" mt={2}><AlertIcon />No se pudo cargar el riesgo de churn.</Alert>
        ) : (
          <Text>Detectamos {churn.length} clientes en riesgo alto de fuga</Text>
        )}

        <Link href="/clients">
          <Button mt={3} size="sm" colorScheme="blue">Ver detalles</Button>
        </Link>
      </Box>

      {/* Gráfico de tendencias */}
      <Box p={4} bg="white" rounded="md" shadow="sm" mb={6}>
        <HStack justify="space-between" mb={2}>
          <Text fontSize="lg">Tendencia semanal</Text>
          <Link href="/purchases">
            <Button size="xs" variant="outline">Ver compras</Button>
          </Link>
        </HStack>

        {loadingTrend ? (
          <HStack><Spinner size="sm" /><Text>Cargando gráfico…</Text></HStack>
        ) : errTrend ? (
          <Alert status="error"><AlertIcon />No se pudo cargar la tendencia.</Alert>
        ) : (
          <TrendChart data={chartData} />
        )}
      </Box>

      {/* Rankings y alertas */}
      <SimpleGrid columns={[1, null, 3]} spacing={4}>
        {/* Ranking: clientes con más compras / gasto */}
        <Box p={4} bg="white" rounded="md" shadow="sm">
          <HStack justify="space-between" mb={2}>
            <Text fontWeight="bold">Clientes con más compras (90d)</Text>
            <Link href="/clients">
              <Button size="xs" variant="outline">Ver clientes</Button>
            </Link>
          </HStack>

          {loadingCustomers ? (
            <HStack><Spinner size="sm" /><Text>Cargando…</Text></HStack>
          ) : errCustomers ? (
            <Alert status="error"><AlertIcon />No se pudo cargar el ranking.</Alert>
          ) : topCustomers.length === 0 ? (
            <Text color="gray.500">Sin datos</Text>
          ) : (
            <VStack align="stretch" spacing={2}>
              {topCustomers.map((c, i) => (
                <HStack key={`${c.client_id}-${i}`} justify="space-between">
                  <Text>
                    {i + 1}. {c.client_name}{' '}
                    <Text as="span" color="gray.500">
                      ({c.orders_count} pedidos)
                    </Text>
                  </Text>
                  <Badge>{Number(c.total_spent ?? 0).toFixed(2)} €</Badge>
                </HStack>
              ))}
            </VStack>
          )}
        </Box>

        {/* Ranking: productos más vendidos */}
        <Box p={4} bg="white" rounded="md" shadow="sm">
          <HStack justify="space-between" mb={2}>
            <Text fontWeight="bold">Productos más vendidos (90d)</Text>
            <Link href="/stock">
              <Button size="xs" variant="outline">Ver stock</Button>
            </Link>
          </HStack>

          {loadingProducts ? (
            <HStack><Spinner size="sm" /><Text>Cargando…</Text></HStack>
          ) : errProducts ? (
            <Alert status="error"><AlertIcon />No se pudo cargar el ranking.</Alert>
          ) : topProducts.length === 0 ? (
            <Text color="gray.500">Sin datos</Text>
          ) : (
            <VStack align="stretch" spacing={2}>
              {topProducts.map((p, i) => (
                <HStack key={`${p.item_id}-${i}`} justify="space-between">
                  <Text>
                    {i + 1}. {p.item_name}{' '}
                    <Text as="span" color="gray.500">
                      ({p.units_sold} uds)
                    </Text>
                  </Text>
                  <Badge>{Number(p.revenue ?? 0).toFixed(2)} €</Badge>
                </HStack>
              ))}
            </VStack>
          )}
        </Box>

        {/* Alertas / resumen churn */}
        <Box p={4} bg="white" rounded="md" shadow="sm">
          <Text fontWeight="bold" mb={2}>Alertas de churn</Text>

          {loadingChurn ? (
            <HStack><Spinner size="sm" /><Text>Cargando…</Text></HStack>
          ) : errChurn ? (
            <Alert status="error"><AlertIcon />No se pudieron cargar las alertas.</Alert>
          ) : churn.length === 0 ? (
            <Text color="gray.500">Sin clientes en riesgo</Text>
          ) : (
            <VStack align="stretch" spacing={2}>
              {churn.map((c) => (
                <HStack key={c.client_id} justify="space-between">
                  <Text>{c.name}</Text>
                  <Badge colorScheme={c.churn_score >= 70 ? 'red' : 'yellow'}>
                    {c.churn_score}%
                  </Badge>
                </HStack>
              ))}
            </VStack>
          )}

          <Link href="/clients">
            <Button mt={3} size="sm" colorScheme="blue">Gestionar</Button>
          </Link>
        </Box>
      </SimpleGrid>
    </Box>
  )
}
