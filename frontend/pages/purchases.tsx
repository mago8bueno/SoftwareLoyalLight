// pages/purchases.tsx
import React, { useMemo, useState } from 'react';
import {
  Box,
  Heading,
  HStack,
  Button,
  Table,
  Thead,
  Tr,
  Th,
  Tbody,
  Td,
  Select,
  NumberInput,
  NumberInputField,
  useToast,
  Spinner,
  Text,
  FormControl,
  FormLabel,
  SimpleGrid,
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listClients, type ClientLite } from '@services/clients';
import { listItems, type Item } from '@services/items';
import { listPurchases, createPurchase, type Purchase } from '@services/purchases';

export default function PurchasesPage() {
  const toast = useToast();
  const qc = useQueryClient();

  // --- cargar datos base en paralelo ---
  const {
    data: clients = [],
    isLoading: loadingClients,
    error: clientsErr,
  } = useQuery<ClientLite[], Error>({
    queryKey: ['clients-lite'],
    queryFn: listClients,
    staleTime: 60_000,
  });

  const {
    data: items = [],
    isLoading: loadingItems,
    error: itemsErr,
  } = useQuery<Item[], Error>({
    queryKey: ['items-lite'],
    queryFn: () => listItems(),
    staleTime: 60_000,
  });

  const {
    data: purchases = [],
    isLoading: loadingPurch,
    isFetching,
    error: purchErr,
  } = useQuery<Purchase[], Error>({
    queryKey: ['purchases'],
    queryFn: listPurchases,
    staleTime: 30_000,
    placeholderData: (old) => old,
  });

  // --- formulario de nueva compra ---
  const [clientId, setClientId] = useState<string>(''); // guardamos como string para <Select>
  const [itemId, setItemId] = useState<string>(''); // idem
  const [qty, setQty] = useState<number | ''>('');

  const createMut = useMutation({
    mutationFn: async () => {
      if (!clientId || !itemId || !qty || Number(qty) <= 0) {
        throw new Error('Completa cliente, producto y cantidad > 0');
      }
      return createPurchase({
        client_id: Number(clientId),
        item_id: Number(itemId),
        quantity: Number(qty),
      });
    },
    onSuccess: () => {
      toast({ title: 'Compra registrada', status: 'success' });
      setQty('');
      qc.invalidateQueries({ queryKey: ['purchases'] });
    },
    onError: (e: any) => {
      toast({
        title: 'No se pudo registrar',
        description: e?.response?.data?.detail || e?.message,
        status: 'error',
      });
    },
  });

  // Mapa para pintar nombre y precio en la tabla
  const itemsById = useMemo(() => {
    const m = new Map<number, Item>();
    (items as Item[]).forEach((it) => m.set(Number(it.id), it));
    return m;
  }, [items]);

  return (
    <Box p={6}>
      <Heading size="lg" mb={4}>
        Compras
      </Heading>

      {(loadingClients || loadingItems || loadingPurch) && (
        <HStack mb={4}>
          <Spinner />
          <Text>Cargando…</Text>
        </HStack>
      )}

      {(clientsErr || itemsErr || purchErr) && (
        <Box mb={4}>
          <Text color="red.500">
            {clientsErr?.message || itemsErr?.message || purchErr?.message}
          </Text>
        </Box>
      )}

      {/* Formulario alta rápida */}
      <Box bg="white" rounded="md" shadow="sm" p={4} mb={6}>
        <Heading size="sm" mb={3}>
          Registrar compra
        </Heading>

        <SimpleGrid columns={[1, 3]} spacing={4}>
          <FormControl isRequired>
            <FormLabel>Cliente</FormLabel>
            <Select
              placeholder="Selecciona cliente"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
            >
              {clients.map((c) => (
                <option key={String(c.id)} value={String(c.id)}>
                  {c.name}
                </option>
              ))}
            </Select>
          </FormControl>

          <FormControl isRequired>
            <FormLabel>Producto</FormLabel>
            <Select
              placeholder="Selecciona producto"
              value={itemId}
              onChange={(e) => setItemId(e.target.value)}
            >
              {items.map((it) => (
                <option key={String(it.id)} value={String(it.id)}>
                  {it.name}
                </option>
              ))}
            </Select>
          </FormControl>

          <FormControl isRequired>
            <FormLabel>Cantidad</FormLabel>
            <NumberInput
              min={1}
              value={qty === '' ? '' : Number(qty)}
              onChange={(v) => setQty(v === '' ? '' : Number(v))}
            >
              <NumberInputField />
            </NumberInput>
          </FormControl>
        </SimpleGrid>

        <HStack mt={4} justify="flex-end">
          <Button
            colorScheme="blue"
            onClick={() => createMut.mutate()}
            isLoading={createMut.isPending}
          >
            Guardar
          </Button>
        </HStack>
      </Box>

      {/* Listado */}
      <Box bg="white" rounded="md" shadow="sm" overflowX="auto">
        {isFetching && (
          <Text fontSize="sm" color="gray.500" p={3}>
            Actualizando…
          </Text>
        )}
        <Table>
          <Thead>
            <Tr>
              <Th>Fecha</Th>
              <Th>Cliente</Th>
              <Th>Producto</Th>
              <Th isNumeric>Cantidad</Th>
              <Th isNumeric>Importe</Th>
            </Tr>
          </Thead>
          <Tbody>
            {purchases.map((p) => {
              const it = itemsById.get(Number(p.item_id));
              const price = Number(it?.price ?? 0);
              const total = Number(p.quantity ?? 0) * price;
              return (
                <Tr key={String(p.id)}>
                  <Td>{new Date(p.created_at ?? Date.now()).toLocaleString()}</Td>
                  <Td>{p.client_id}</Td>
                  <Td>{it?.name ?? p.item_id}</Td>
                  <Td isNumeric>{p.quantity}</Td>
                  <Td isNumeric>{total.toFixed(2)} €</Td>
                </Tr>
              );
            })}
            {purchases.length === 0 && (
              <Tr>
                <Td colSpan={5}>
                  <Text color="gray.500">Sin compras.</Text>
                </Td>
              </Tr>
            )}
          </Tbody>
        </Table>
      </Box>
    </Box>
  );
}
