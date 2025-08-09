// Layout: Composición principal
import { Box } from '@chakra-ui/react';
import Sidebar from './Sidebar';

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <Box display="flex">
      <Sidebar />
      <Box ml={{ base: 0, md: 200 }} p={4} flex="1">
        {children}
      </Box>
    </Box>
  );
}
