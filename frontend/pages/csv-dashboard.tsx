// pages/csv-dashboard.tsx
import React, { useState, useRef } from 'react';
import {
  Box,
  Heading,
  VStack,
  HStack,
  Button,
  Text,
  useToast,
  Progress,
  Card,
  CardBody,
  Icon,
  Flex,
  Badge,
  Container,
  SimpleGrid,
  Divider,
  Textarea,
  IconButton,
  Avatar,
  Spinner,
} from '@chakra-ui/react';
import { 
  UploadIcon, 
  ChatIcon, 
  DownloadIcon, 
  ViewIcon,
  StarIcon,
  TrendingUpIcon 
} from '@chakra-ui/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import { uploadCSV, generateDashboard, chatWithData } from '@services/csv-ai';
import dynamic from 'next/dynamic';

// Componentes dinámicos para gráficos
const DynamicChart = dynamic(() => import('@components/DynamicChart'), { ssr: false });
const CSVPreview = dynamic(() => import('@components/CSVPreview'), { ssr: false });

type UploadedFile = {
  id: string;
  filename: string;
  columns: string[];
  rows: number;
  uploadedAt: string;
  status: 'processing' | 'ready' | 'error';
};

type DashboardData = {
  charts: Array<{
    type: 'line' | 'bar' | 'pie' | 'scatter';
    title: string;
    data: any[];
    insights: string;
    importance: 'high' | 'medium' | 'low';
  }>;
  summary: {
    totalRows: number;
    keyMetrics: Array<{ label: string; value: string; trend?: 'up' | 'down' | 'stable' }>;
    aiInsights: string[];
  };
};

type ChatMessage = {
  id: string;
  type: 'user' | 'ai';
  content: string;
  timestamp: Date;
  charts?: any[];
};

export default function CSVDashboardPage() {
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Estados principales
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<UploadedFile | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  
  // Mutaciones para interactuar con el backend
  const uploadMutation = useMutation({
    mutationFn: uploadCSV,
    onSuccess: (data) => {
      setUploadedFiles(prev => [...prev, data]);
      toast({
        title: 'CSV subido exitosamente',
        description: 'Procesando datos para generar dashboard...',
        status: 'success',
        duration: 3000,
      });
      generateDashboardForFile(data);
    },
    onError: (error: any) => {
      toast({
        title: 'Error al subir CSV',
        description: error?.response?.data?.detail || 'Error desconocido',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const dashboardMutation = useMutation({
    mutationFn: generateDashboard,
    onSuccess: (data) => {
      setDashboardData(data);
      setSelectedFile(prev => prev ? { ...prev, status: 'ready' } : null);
      toast({
        title: 'Dashboard generado',
        description: 'Tu análisis inteligente está listo',
        status: 'success',
        duration: 3000,
      });
    },
  });

  const chatMutation = useMutation({
    mutationFn: chatWithData,
    onSuccess: (response) => {
      const aiMessage: ChatMessage = {
        id: Date.now().toString(),
        type: 'ai',
        content: response.message,
        timestamp: new Date(),
        charts: response.charts,
      };
      setChatMessages(prev => [...prev, aiMessage]);
    },
  });

  // Funciones auxiliares
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      toast({
        title: 'Formato no soportado',
        description: 'Por favor, sube solo archivos CSV',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setIsUploading(true);
    uploadMutation.mutate(file);
  };

  const generateDashboardForFile = async (file: UploadedFile) => {
    setSelectedFile({ ...file, status: 'processing' });
    dashboardMutation.mutate(file.id);
  };

  const handleChatSubmit = () => {
    if (!chatInput.trim() || !selectedFile) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: chatInput,
      timestamp: new Date(),
    };

    setChatMessages(prev => [...prev, userMessage]);
    chatMutation.mutate({
      fileId: selectedFile.id,
      message: chatInput,
    });
    
    setChatInput('');
  };

  return (
    <Container maxW="7xl" p={6}>
      {/* Header Premium */}
      <Box 
        bgGradient="linear(135deg, blue.600, purple.600, pink.500)"
        borderRadius="2xl"
        p={8}
        color="white"
        mb={8}
        position="relative"
        overflow="hidden"
      >
        <Box position="absolute" top="0" right="0" opacity={0.1}>
          <Icon as={StarIcon} boxSize="120px" />
        </Box>
        <VStack align="start" spacing={4} position="relative" zIndex={1}>
          <HStack>
            <Icon as={TrendingUpIcon} boxSize="8" />
            <Heading size="xl" fontWeight="bold">
              Dashboard IA Inteligente
            </Heading>
            <Badge colorScheme="yellow" variant="solid" fontSize="sm" px={3} py={1}>
              PREMIUM
            </Badge>
          </HStack>
          <Text fontSize="lg" opacity={0.9}>
            Sube tus datos CSV y obtén insights profesionales al instante con IA avanzada
          </Text>
        </VStack>
      </Box>

      <SimpleGrid columns={[1, null, 2]} spacing={8}>
        {/* Panel de subida y archivos */}
        <Card variant="elevated" borderRadius="xl">
          <CardBody p={6}>
            <VStack spacing={6}>
              <Heading size="md" color="gray.700">
                Gestión de Datos
              </Heading>

              {/* Zona de subida */}
              <Box
                borderWidth={2}
                borderStyle="dashed"
                borderColor="blue.300"
                borderRadius="xl"
                p={8}
                textAlign="center"
                bg="blue.50"
                w="full"
                cursor="pointer"
                transition="all 0.3s"
                _hover={{
                  borderColor: 'blue.500',
                  bg: 'blue.100',
                  transform: 'translateY(-2px)',
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
                <Icon as={UploadIcon} boxSize="12" color="blue.500" mb={4} />
                <Text fontSize="lg" fontWeight="semibold" color="blue.700" mb={2}>
                  Arrastra tu CSV aquí
                </Text>
                <Text color="gray.600" fontSize="sm">
                  o haz clic para seleccionar archivo
                </Text>
                {isUploading && (
                  <Progress colorScheme="blue" size="sm" isIndeterminate mt={4} />
                )}
              </Box>

              <Divider />

              {/* Lista de archivos */}
              <Box w="full">
                <Text fontWeight="bold" mb={3} color="gray.700">
                  Archivos Subidos ({uploadedFiles.length})
                </Text>
                <VStack spacing={3}>
                  {uploadedFiles.map((file) => (
                    <Card
                      key={file.id}
                      variant="outline"
                      w="full"
                      cursor="pointer"
                      transition="all 0.2s"
                      _hover={{ shadow: 'md', transform: 'translateY(-1px)' }}
                      bg={selectedFile?.id === file.id ? 'blue.50' : 'white'}
                      borderColor={selectedFile?.id === file.id ? 'blue.300' : 'gray.200'}
                      onClick={() => setSelectedFile(file)}
                    >
                      <CardBody p={4}>
                        <HStack justify="space-between">
                          <VStack align="start" spacing={1}>
                            <Text fontWeight="semibold" fontSize="sm">
                              {file.filename}
                            </Text>
                            <HStack spacing={4}>
                              <Text fontSize="xs" color="gray.600">
                                {file.rows.toLocaleString()} filas
                              </Text>
                              <Text fontSize="xs" color="gray.600">
                                {file.columns.length} columnas
                              </Text>
                            </HStack>
                          </VStack>
                          <Badge
                            colorScheme={
                              file.status === 'ready' ? 'green' : 
                              file.status === 'processing' ? 'blue' : 'red'
                            }
                            variant="solid"
                          >
                            {file.status === 'ready' ? 'Listo' : 
                             file.status === 'processing' ? 'Procesando' : 'Error'}
                          </Badge>
                        </HStack>
                      </CardBody>
                    </Card>
                  ))}
                  {uploadedFiles.length === 0 && (
                    <Text color="gray.500" fontSize="sm" textAlign="center">
                      No hay archivos subidos aún
                    </Text>
                  )}
                </VStack>
              </Box>
            </VStack>
          </CardBody>
        </Card>

        {/* Panel de chat IA */}
        <Card variant="elevated" borderRadius="xl">
          <CardBody p={0}>
            <VStack spacing={0} h="600px">
              {/* Header del chat */}
              <Box p={4} w="full" bg="gray.50" borderTopRadius="xl">
                <HStack>
                  <Avatar size="sm" bg="purple.500" name="IA Assistant" />
                  <VStack align="start" spacing={0}>
                    <Text fontWeight="bold" fontSize="sm">
                      Asistente IA Avanzado
                    </Text>
                    <Text fontSize="xs" color="gray.600">
                      Pregunta cualquier cosa sobre tus datos
                    </Text>
                  </VStack>
                  <Badge colorScheme="green" ml="auto" variant="subtle">
                    Online
                  </Badge>
                </HStack>
              </Box>

              {/* Área de mensajes */}
              <Box flex={1} w="full" overflowY="auto" p={4}>
                <VStack spacing={4} align="stretch">
                  {chatMessages.length === 0 && (
                    <Box textAlign="center" py={8} color="gray.500">
                      <Icon as={ChatIcon} boxSize="8" mb={4} />
                      <Text>Sube un CSV y comienza a chatear</Text>
                    </Box>
                  )}
                  {chatMessages.map((msg) => (
                    <Flex
                      key={msg.id}
                      justify={msg.type === 'user' ? 'flex-end' : 'flex-start'}
                    >
                      <Box
                        maxW="80%"
                        p={3}
                        borderRadius="xl"
                        bg={msg.type === 'user' ? 'blue.500' : 'gray.100'}
                        color={msg.type === 'user' ? 'white' : 'gray.800'}
                      >
                        <Text fontSize="sm">{msg.content}</Text>
                        {msg.charts && msg.charts.length > 0 && (
                          <Box mt={3}>
                            {msg.charts.map((chart, idx) => (
                              <DynamicChart key={idx} {...chart} />
                            ))}
                          </Box>
                        )}
                      </Box>
                    </Flex>
                  ))}
                  {chatMutation.isPending && (
                    <Flex justify="flex-start">
                      <HStack
                        p={3}
                        borderRadius="xl"
                        bg="gray.100"
                        color="gray.800"
                      >
                        <Spinner size="sm" />
                        <Text fontSize="sm">IA pensando...</Text>
                      </HStack>
                    </Flex>
                  )}
                </VStack>
              </Box>

              {/* Input del chat */}
              <Box p={4} w="full" borderTop="1px" borderColor="gray.200">
                <HStack>
                  <Textarea
                    placeholder="Pregunta sobre tus datos..."
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleChatSubmit();
                      }
                    }}
                    resize="none"
                    rows={2}
                    disabled={!selectedFile || selectedFile.status !== 'ready'}
                  />
                  <IconButton
                    aria-label="Enviar mensaje"
                    icon={<ChatIcon />}
                    colorScheme="blue"
                    onClick={handleChatSubmit}
                    isLoading={chatMutation.isPending}
                    disabled={!chatInput.trim() || !selectedFile || selectedFile.status !== 'ready'}
                  />
                </HStack>
              </Box>
            </VStack>
          </CardBody>
        </Card>
      </SimpleGrid>

      {/* Dashboard generado */}
      {dashboardData && selectedFile && (
        <Card variant="elevated" borderRadius="xl" mt={8}>
          <CardBody p={6}>
            <VStack spacing={6}>
              <HStack justify="space-between" w="full">
                <Heading size="lg" color="gray.700">
                  Dashboard: {selectedFile.filename}
                </Heading>
                <HStack>
                  <Button leftIcon={<ViewIcon />} variant="outline" size="sm">
                    Vista Completa
                  </Button>
                  <Button leftIcon={<DownloadIcon />} colorScheme="blue" size="sm">
                    Exportar PDF
                  </Button>
                </HStack>
              </HStack>

              {/* Métricas clave */}
              <SimpleGrid columns={[2, null, 4]} spacing={4} w="full">
                {dashboardData.summary.keyMetrics.map((metric, idx) => (
                  <Card key={idx} variant="outline" borderRadius="lg">
                    <CardBody p={4} textAlign="center">
                      <Text fontSize="2xl" fontWeight="bold" color="blue.600">
                        {metric.value}
                      </Text>
                      <Text fontSize="sm" color="gray.600">
                        {metric.label}
                      </Text>
                      {metric.trend && (
                        <Badge
                          colorScheme={
                            metric.trend === 'up' ? 'green' : 
                            metric.trend === 'down' ? 'red' : 'gray'
                          }
                          size="sm"
                          mt={1}
                        >
                          {metric.trend === 'up' ? '↗️' : 
                           metric.trend === 'down' ? '↘️' : '➡️'}
                        </Badge>
                      )}
                    </CardBody>
                  </Card>
                ))}
              </SimpleGrid>

              {/* Gráficos */}
              <SimpleGrid columns={[1, null, 2]} spacing={6} w="full">
                {dashboardData.charts.map((chart, idx) => (
                  <Card key={idx} variant="outline" borderRadius="lg">
                    <CardBody p={4}>
                      <VStack align="start" spacing={4}>
                        <HStack justify="space-between" w="full">
                          <Text fontWeight="bold" color="gray.700">
                            {chart.title}
                          </Text>
                          <Badge
                            colorScheme={
                              chart.importance === 'high' ? 'red' :
                              chart.importance === 'medium' ? 'yellow' : 'green'
                            }
                            variant="subtle"
                          >
                            {chart.importance === 'high' ? 'Crítico' :
                             chart.importance === 'medium' ? 'Importante' : 'Informativo'}
                          </Badge>
                        </HStack>
                        <Box w="full" h="300px">
                          <DynamicChart type={chart.type} data={chart.data} />
                        </Box>
                        <Text fontSize="sm" color="gray.600" fontStyle="italic">
                          💡 {chart.insights}
                        </Text>
                      </VStack>
                    </CardBody>
                  </Card>
                ))}
              </SimpleGrid>

              {/* Insights de IA */}
              <Card variant="outline" borderRadius="lg" w="full">
                <CardBody p={6}>
                  <VStack align="start" spacing={4}>
                    <Heading size="md" color="purple.600">
                      🧠 Insights de IA Avanzada
                    </Heading>
                    <VStack align="start" spacing={3}>
                      {dashboardData.summary.aiInsights.map((insight, idx) => (
                        <HStack key={idx} align="start">
                          <Badge colorScheme="purple" variant="solid" minW="6" minH="6" borderRadius="full" />
                          <Text fontSize="sm" color="gray.700">
                            {insight}
                          </Text>
                        </HStack>
                      ))}
                    </VStack>
                  </VStack>
                </CardBody>
              </Card>
            </VStack>
          </CardBody>
        </Card>
      )}
    </Container>
  );
}
