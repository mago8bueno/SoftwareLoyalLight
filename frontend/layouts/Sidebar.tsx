// layouts/Sidebar.tsx
// Barra lateral colapsable con navegación (Next Link) y logout.

import React, { useState } from 'react';
import NextLink from 'next/link';
import { Box, VStack, HStack, Text, Icon, IconButton, Link as ChakraLink } from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { useRouter } from 'next/router';
import { FiMenu, FiHome, FiUsers, FiShoppingCart, FiBox } from 'react-icons/fi';
import { useAuth } from '@contexts/AuthContext';

type NavItem = {
  href: string;
  label: string;
  icon: React.ElementType;
};

const NAV_ITEMS: NavItem[] = [
  { href: '/', label: 'Dashboard', icon: FiHome },
  { href: '/clients', label: 'Clientes', icon: FiUsers },
  { href: '/purchases', label: 'Compras', icon: FiShoppingCart },
  { href: '/stock', label: 'Stock', icon: FiBox },
];

export default function Sidebar() {
  const { auth, signOut } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(true);

  // Ancho animado con framer-motion
  const MotionBox = motion(Box);

  const userLabel = (auth?.user && (auth.user.name || auth.user.email)) || 'Usuario';

  return (
    <MotionBox
      as="nav"
      position="fixed"
      left={0}
      top={0}
      h="100vh"
      bg="white"
      borderRight="1px solid"
      borderColor="gray.100"
      zIndex={100}
      animate={{ width: open ? 220 : 64 }}
      initial={false}
      transition={{ type: 'tween', duration: 0.15 }}
      px={3}
      py={3}
      overflow="hidden"
    >
      {/* Header / Toggle */}
      <HStack justify="space-between" mb={4}>
        <Text fontWeight="bold" fontSize="lg" noOfLines={1} display={open ? 'block' : 'none'}>
          Fidelización
        </Text>
        <IconButton
          aria-label="Toggle sidebar"
          size="sm"
          variant="ghost"
          icon={<FiMenu />}
          onClick={() => setOpen((v) => !v)}
        />
      </HStack>

      {/* Usuario */}
      <Box bg="gray.50" border="1px solid" borderColor="gray.100" rounded="md" px={3} py={2} mb={4}>
        <Text fontSize="sm" color="gray.500" display={open ? 'block' : 'none'}>
          Sesión
        </Text>
        <Text fontWeight="medium" noOfLines={1}>
          {open ? userLabel : userLabel.charAt(0).toUpperCase()}
        </Text>
      </Box>

      {/* Navegación */}
      <VStack align="stretch" spacing={1}>
        {NAV_ITEMS.map((item) => {
          const active = router.pathname === item.href;
          return (
            <ChakraLink
              as={NextLink}
              key={item.href}
              href={item.href}
              _hover={{ textDecoration: 'none', bg: 'gray.50' }}
              bg={active ? 'gray.100' : 'transparent'}
              rounded="md"
              px={2}
              py={2}
            >
              <HStack spacing={3}>
                <Icon as={item.icon} boxSize={5} />
                <Text display={open ? 'block' : 'none'}>{item.label}</Text>
              </HStack>
            </ChakraLink>
          );
        })}
      </VStack>

      {/* Footer / Logout */}
      <Box position="absolute" bottom={3} left={3} right={3}>
        <ChakraLink
          as="button"
          onClick={signOut}
          w="full"
          textAlign={open ? 'left' : 'center'}
          px={2}
          py={2}
          rounded="md"
          _hover={{ bg: 'gray.50' }}
        >
          <HStack spacing={3} justify={open ? 'flex-start' : 'center'}>
            <Text>{open ? 'Cerrar sesión' : '⟲'}</Text>
          </HStack>
        </ChakraLink>
      </Box>
    </MotionBox>
  );
}
