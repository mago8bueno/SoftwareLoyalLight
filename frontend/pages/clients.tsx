// pages/clients.tsx
import React, { useMemo, useState } from 'react';
import {
  Box, Heading, Table, Thead, Tbody, Tr, Th, Td, Badge, Button,
  HStack, Text, useDisclosure, useToast, Modal, ModalOverlay, ModalContent,
  ModalHeader, ModalBody, ModalFooter, ModalCloseButton, FormControl,
  FormLabel, Input, Spinner, InputGroup, InputLeftElement,
} from '@chakra-ui/react';
import { AddIcon, SearchIcon } from '@chakra-ui/icons';
import { useQuery } from '@tanstack/react-query';
import { useClients } from '@hooks/useClients';
import { getClientSuggestions, type ClientSuggestion, type ID } from '@services/ai';

type ClientRow = {
  id: ID;
  name: string;
  email?: string | null;
  phone?: string | null;
  churn_score?: number | null;
};

export default function ClientsPage() {
  const toast = useToast();

  const {
    data: rawClients = [],
    isLoading,
    isFetching,
    error,
    createClient,
    isCreating,
  } = useClients();

  const clients = useMemo<ClientRow[]>(
    () =>
      (rawClients as any[]).map((c) => ({
        id: c.id as ID,
        name: c.name,
        email: c.email ?? null,
        phone: c.phone ?? null,
        churn_score: c.churn_score ?? null,
      })),
    [rawClients],
  );

  const [search, setSearch] = useState('');
  const filtered = useMemo(
    () =>
      clients.filter((c) => {
        const q = search.trim().toLowerCase();
        if (!q) return true;
        const name = c.name?.toLowerCase?.() ?? '';
        const email = c.email?.toLowerCase?.() ?? '';
        const phone = c.phone?.toLowerCase?.() ?? '';
        return name.includes(q) || email.includes(q) || phone.includes(q);
      }),
    [clients, search],
  );

  const createModal = useDisclosure();
  const [name, setName] = useState('');
  const [emailVal, setEmailVal] = useState('');
  const [phone, setPhone] = useState('');

  const resetForm = () => {
    setName('');
    setEmailVal('');
    setPhone('');
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      toast({ title: 'El nombre es obligatorio', status: 'warning' });
      return;
    }
    try {
      const body = {
        name,
        email: emailVal.trim() ? emailVal : undefined,
        phone: phone.trim() ? phone : undefined,
      };
      await createClient(body as any);
      toast({ title: 'Cliente creado', status: 'success' });
      resetForm();
      createModal.onClose();
    } catch (e: any) {
      toast({
        title: 'No se pudo crear el cliente',
        description: e?.response?.data?.detail || e.message,
        status: 'error',
      });
    }
  };

  const iaModal = useDisclosure();
  const [selectedId, setSelectedId] = useState<ID | null>(null);

  const tenantId =
    typeof window !== 'undefined'
      ? (() => {
          try {
            const raw = localStorage.getItem('auth');
            return raw ? (JSON.parse(raw)?.user?.tenant_id as string | undefined) : undefined;
          } catch {
            return undefined;
          }
        })()
      : undefined;

  const {
    data: iaData,
    isLoading: iaLoading,
    isError: iaError,
    error: iaErrObj,
    refetch: refetchIA,
  } = useQuery<ClientSuggestion, Error>({
    queryKey: ['ai-suggestions', selectedId, tenantId],
    queryFn: () => getClientSuggestions(selectedId as ID, tenantId ? { tenantId } : undefined),
    enabled: false,
    staleTime: 30_000,
  });

  const openIAModal = (id: ID) => {
    setSelectedId(id);
    iaModal.onOpen();
    setTimeout(() => refetchIA(), 0);
  };

  const churnBadge = (score?: number | null) => {
    if (score == null) return <Badge colorScheme="gray">—</Badge>;
    if (score >= 70) return <Badge colorScheme="red">{score}%</Badge>;
    if (score >= 40) return <Badge colorScheme="yellow">{score}%</Badge>;
    return <Badge colorScheme="green">{score}%</Badge>;
  };

  if (isLoading) {
    return (
      <Box p={6}>
        <HStack>
          <Spinner />
          <Text>Cargando clientes…</Text>
        </HStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={6}>
        <Text color="red.500">Error: {(error as any).message}</Text>
      </Box>
    );
  }

  return (
    <Box p={6}>
      <HStack justify="space-between" mb={4}>
        <Heading size="lg">Clientes</Heading>
        <HStack>
          <InputGroup maxW="260px">
            <InputLeftElement pointerEvents="none">
              <SearchIcon color="gray.400" />
            </InputLeftElement>
            <Input
              placeholder="Buscar por nombre, email o teléfono…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              bg="white"
            />
          </InputGroup>
          <Button leftIcon={<AddIcon />} colorScheme="blue" onClick={createModal.onOpen}>
            Añadir cliente
          </Button>
        </HStack>
      </HStack>

      {isFetching && (
        <Text fontSize="sm" color="gray.500" mb={2}>
          Actualizando datos…
        </Text>
      )}

      <Box bg="white" rounded="md" shadow="sm" overflowX="auto">
        <Table variant="simple">
          <Thead>
            <Tr>
              <Th>Cliente</Th>
              <Th>Correo/Teléfono</Th>
              <Th>IA Sugerencia</Th>
              <Th>Churn</Th>
            </Tr>
          </Thead>
          <Tbody>
            {filtered.map((c) => (
              <Tr key={String(c.id)}>
                <Td>
                  <Text fontWeight="medium">{c.name}</Text>
                </Td>
                <Td>
                  <Text color="gray.600">
                    {c.email || '—'}
                    {c.phone ? ` · ${c.phone}` : ''}
                  </Text>
                </Td>
                <Td>
                  <Button size="sm" variant="outline" onClick={() => openIAModal(c.id)}>
                    Ver IA
                  </Button>
                </Td>
                <Td>{churnBadge(c.churn_score)}</Td>
              </Tr>
            ))}
            {filtered.length === 0 && (
              <Tr>
                <Td colSpan={4}>
                  <Text color="gray.500">No hay clientes.</Text>
                </Td>
              </Tr>
            )}
          </Tbody>
        </Table>
      </Box>

      <Modal
        isOpen={createModal.isOpen}
        onClose={() => !isCreating && createModal.onClose()}
        isCentered
      >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Añadir cliente</ModalHeader>
          <ModalCloseButton disabled={isCreating} />
          <ModalBody>
            <FormControl mb={3} isRequired>
              <FormLabel>Nombre</FormLabel>
              <Input placeholder="Nombre" value={name} onChange={(e) => setName(e.target.value)} />
            </FormControl>
            <FormControl mb={3}>
              <FormLabel>Email</FormLabel>
              <Input
                placeholder="correo@dominio.com"
                type="email"
                value={emailVal}
                onChange={(e) => setEmailVal(e.target.value)}
              />
            </FormControl>
            <FormControl>
              <FormLabel>Teléfono</FormLabel>
              <Input
                placeholder="+34 600 000 000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </FormControl>
          </ModalBody>
          <ModalFooter>
            <Button mr={3} variant="ghost" onClick={createModal.onClose} isDisabled={isCreating}>
              Cancelar
            </Button>
            <Button colorScheme="blue" onClick={handleCreate} isLoading={isCreating}>
              Guardar
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      <Modal isOpen={iaModal.isOpen} onClose={iaModal.onClose} isCentered size="lg">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Recomendaciones IA</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {iaLoading && (
              <HStack>
                <Spinner />
                <Text>Cargando sugerencias…</Text>
              </HStack>
            )}
            {iaError && (
              <Text color="red.500">
                {(iaErrObj as any)?.message || 'No se pudieron obtener las sugerencias'}
              </Text>
            )}
            {!iaLoading && !iaError && iaData && (
              <Box>
                <HStack justify="space-between" mb={2}>
                  <Text>
                    Cliente #{String(iaData.client_id)} — Última compra hace {iaData.last_purchase_days} días
                  </Text>
                  <Badge colorScheme={iaData.churn_score >= 70 ? 'red' : 'yellow'}>
                    Churn {iaData.churn_score}%
                  </Badge>
                </HStack>
                <Box>
                  <Text fontWeight="bold" mb={1}>
                    Sugerencias:
                  </Text>
                  {iaData.suggestions.map((s, idx) => (
                    <Text key={idx} mb={1}>
                      • {s.title ? `${s.title}: ` : ''}{s.description}
                    </Text>
                  ))}
                  {iaData.top_item_id && (
                    <Text mt={2} color="gray.600">
                      Producto más frecuente: #{String(iaData.top_item_id)}
                    </Text>
                  )}
                </Box>
              </Box>
            )}
          </ModalBody>
          <ModalFooter>
            <Button onClick={iaModal.onClose}>Cerrar</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}
