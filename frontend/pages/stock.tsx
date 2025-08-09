// pages/stock.tsx
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
  InputGroup,
  InputLeftElement,
  Input,
  Image as ChakraImage,
  useDisclosure,
  useToast,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  FormControl,
  FormLabel,
  NumberInput,
  NumberInputField,
  IconButton,
  Spinner,
  Text,
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon, SearchIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listItems, createItem, deleteItem, uploadItemImage, type Item } from '@services/items';

export default function StockPage() {
  const toast = useToast();
  const qc = useQueryClient();

  // Buscar
  const [search, setSearch] = useState('');

  // Listado
  const {
    data = [],
    isLoading,
    isFetching,
    error,
  } = useQuery<Item[], Error>({
    queryKey: ['items', search],
    queryFn: () => listItems(search || undefined),
    staleTime: 30_000,
    placeholderData: (old) => old,
  });

  const items = useMemo(() => data, [data]);

  // Crear (modal)
  const modal = useDisclosure();
  const [name, setName] = useState('');
  const [price, setPrice] = useState<number | ''>(''); // Chakra NumberInput friendly
  const [stock, setStock] = useState<number | ''>(''); // Chakra NumberInput friendly
  const [imageUrl, setImageUrl] = useState(''); // URL opcional
  const [file, setFile] = useState<File | null>(null); // archivo opcional

  const resetForm = () => {
    setName('');
    setPrice('');
    setStock('');
    setImageUrl('');
    setFile(null);
  };

  const createMut = useMutation({
    mutationFn: async () => {
      if (!name.trim()) {
        throw new Error('El nombre es obligatorio');
      }

      let finalUrl: string | undefined = imageUrl || undefined;
      if (!finalUrl && file) {
        // ⬅️ Firma correcta: (file, optionalFilename)
        const { image_url } = await uploadItemImage(file, file.name);
        finalUrl = image_url;
      }

      return createItem({
        name,
        price: typeof price === 'number' ? price : 0,
        stock: typeof stock === 'number' ? stock : 0,
        // No mandamos null; undefined si no hay imagen
        image_url: finalUrl,
      } as Omit<Item, 'id'> & { image_url?: string });
    },
    onSuccess: () => {
      toast({ title: 'Producto creado', status: 'success' });
      resetForm();
      modal.onClose();
      qc.invalidateQueries({ queryKey: ['items'] });
    },
    onError: (e: any) => {
      toast({
        title: 'No se pudo crear',
        description: e?.response?.data?.detail || e?.message,
        status: 'error',
      });
    },
  });

  const delMut = useMutation({
    mutationFn: (id: Item['id']) => deleteItem(id),
    onSuccess: () => {
      toast({ title: 'Eliminado', status: 'success' });
      qc.invalidateQueries({ queryKey: ['items'] });
    },
    onError: (e: any) => {
      toast({
        title: 'No se pudo eliminar',
        description: e?.response?.data?.detail || e?.message,
        status: 'error',
      });
    },
  });

  return (
    <Box p={6}>
      <HStack justify="space-between" mb={4}>
        <Heading size="lg">Stock</Heading>
        <HStack>
          <InputGroup maxW="260px">
            <InputLeftElement pointerEvents="none">
              <SearchIcon color="gray.400" />
            </InputLeftElement>
            <Input
              bg="white"
              placeholder="Buscar por nombre…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </InputGroup>
          <Button leftIcon={<AddIcon />} colorScheme="blue" onClick={modal.onOpen}>
            Añadir
          </Button>
        </HStack>
      </HStack>

      {isLoading ? (
        <HStack>
          <Spinner />
          <Text>Cargando…</Text>
        </HStack>
      ) : error ? (
        <Text color="red.500">Error: {error.message}</Text>
      ) : (
        <>
          {isFetching && (
            <Text fontSize="sm" color="gray.500" mb={2}>
              Actualizando…
            </Text>
          )}

          <Box bg="white" rounded="md" shadow="sm" overflowX="auto">
            <Table>
              <Thead>
                <Tr>
                  <Th>Imagen</Th>
                  <Th>Nombre</Th>
                  <Th isNumeric>Precio</Th>
                  <Th isNumeric>Stock</Th>
                  <Th />
                </Tr>
              </Thead>
              <Tbody>
                {items.map((it) => (
                  <Tr key={String(it.id)}>
                    <Td>
                      {it.image_url ? (
                        <ChakraImage
                          src={it.image_url}
                          alt={it.name}
                          boxSize="48px"
                          objectFit="cover"
                          rounded="md"
                        />
                      ) : (
                        <Box boxSize="48px" bg="gray.100" rounded="md" />
                      )}
                    </Td>
                    <Td>{it.name}</Td>
                    <Td isNumeric>{Number(it.price ?? 0).toFixed(2)} €</Td>
                    <Td isNumeric>{Number(it.stock ?? 0)}</Td>
                    <Td>
                      <IconButton
                        aria-label="Eliminar"
                        icon={<DeleteIcon />}
                        size="sm"
                        variant="ghost"
                        onClick={() => delMut.mutate(it.id)}
                      />
                    </Td>
                  </Tr>
                ))}

                {items.length === 0 && (
                  <Tr>
                    <Td colSpan={5}>
                      <Text color="gray.500">Sin productos.</Text>
                    </Td>
                  </Tr>
                )}
              </Tbody>
            </Table>
          </Box>
        </>
      )}

      {/* Modal crear */}
      <Modal
        isOpen={modal.isOpen}
        onClose={() => !createMut.isPending && modal.onClose()}
        isCentered
      >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Añadir producto</ModalHeader>
          <ModalCloseButton disabled={createMut.isPending} />
          <ModalBody>
            <FormControl mb={3} isRequired>
              <FormLabel>Nombre</FormLabel>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </FormControl>

            <FormControl mb={3}>
              <FormLabel>Precio</FormLabel>
              <NumberInput
                min={0}
                precision={2}
                value={price === '' ? '' : price}
                onChange={(_, n) => setPrice(Number.isNaN(n) ? '' : n)}
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>

            <FormControl mb={3}>
              <FormLabel>Stock</FormLabel>
              <NumberInput
                min={0}
                value={stock === '' ? '' : stock}
                onChange={(_, n) => setStock(Number.isNaN(n) ? '' : Math.max(0, n))}
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>

            <FormControl mb={2}>
              <FormLabel>Imagen (URL opcional)</FormLabel>
              <Input
                placeholder="https://…"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
              />
            </FormControl>

            <FormControl>
              <FormLabel>o sube un archivo</FormLabel>
              <Input
                type="file"
                accept="image/*"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                Si subes archivo, tendrá prioridad sobre la URL.
              </Text>
            </FormControl>
          </ModalBody>

          <ModalFooter>
            <Button mr={3} variant="ghost" onClick={modal.onClose} isDisabled={createMut.isPending}>
              Cancelar
            </Button>
            <Button
              colorScheme="blue"
              onClick={() => createMut.mutate()}
              isLoading={createMut.isPending}
            >
              Guardar
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}
