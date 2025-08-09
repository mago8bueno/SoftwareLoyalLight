// Molecule: Card genérica
import { Box, BoxProps } from '@chakra-ui/react';
export function Card(props: BoxProps) {
  return <Box bg="white" shadow="md" rounded="md" p={4} {...props} />;
}
