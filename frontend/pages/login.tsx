// pages/login.tsx
import React, { useState, useContext, KeyboardEvent } from 'react';
import {
  Box,
  Button,
  Heading,
  Input,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Text,
  VStack,
  Center,
  useToast,
  HStack,
} from '@chakra-ui/react';
import Image from 'next/image';
import AuthContext from '@contexts/AuthContext';

export default function Login() {
  const { signIn } = useContext(AuthContext);
  const [email, setEmail] = useState('');
  const [pwd, setPwd] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // errores de validación UI
  const [emailError, setEmailError] = useState<string | null>(null);
  const [pwdError, setPwdError] = useState<string | null>(null);
  // error general (backend)
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const toast = useToast();

  const validate = () => {
    let ok = true;
    setEmailError(null);
    setPwdError(null);
    setErrorMsg(null);

    if (!email) {
      setEmailError('El email es obligatorio');
      ok = false;
    } else if (!/^\S+@\S+\.\S+$/.test(email)) {
      setEmailError('Formato de email no válido');
      ok = false;
    }
    if (!pwd) {
      setPwdError('La contraseña es obligatoria');
      ok = false;
    }
    return ok;
  };

  const doLogin = async () => {
    if (!validate()) return;
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await signIn(email, pwd); // lanza si hay error; el AuthContext redirige a '/'
      toast({
        title: 'Sesión iniciada',
        status: 'success',
        duration: 1500,
        isClosable: true,
      });
    } catch (err: any) {
      const status = err?.response?.status;
      const backendMsg: string | undefined =
        typeof err?.response?.data === 'string' ? err.response.data : err?.response?.data?.detail;

      if (status === 401) setErrorMsg(backendMsg || 'Credenciales inválidas.');
      else if (status === 404) setErrorMsg('Ruta /auth/login no encontrada en el backend.');
      else setErrorMsg(backendMsg || 'No se pudo iniciar sesión. Intenta de nuevo.');

      toast({
        title: 'Error al iniciar sesión',
        description: backendMsg || undefined,
        status: 'error',
        duration: 2500,
        isClosable: true,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter') doLogin();
  };

  return (
    <Center minH="100vh" bg="gray.50" p={4}>
      <Box w="100%" maxW="420px" p={8} bg="white" rounded="xl" boxShadow="md" onKeyDown={onKeyDown}>
        <VStack spacing={6} align="stretch">
          <HStack justify="center" spacing={3}>
            {/* Logo en /public/logo.png */}
            <Image src="/logo.png" alt="Logo" width={48} height={48} priority />
            <Heading size="lg">Login</Heading>
          </HStack>

          <FormControl isInvalid={!!emailError}>
            <FormLabel>Email</FormLabel>
            <Input
              placeholder="usuario@correo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              autoFocus
            />
            <FormErrorMessage>{emailError}</FormErrorMessage>
          </FormControl>

          <FormControl isInvalid={!!pwdError}>
            <FormLabel>Contraseña</FormLabel>
            <Input
              placeholder="********"
              type="password"
              value={pwd}
              onChange={(e) => setPwd(e.target.value)}
            />
            <FormErrorMessage>{pwdError}</FormErrorMessage>
          </FormControl>

          {errorMsg && (
            <Text color="red.500" fontSize="sm">
              {errorMsg}
            </Text>
          )}

          <Button
            colorScheme="blue"
            onClick={doLogin}
            isLoading={submitting}
            isDisabled={!email || !pwd || submitting}
          >
            Iniciar sesión
          </Button>
        </VStack>
      </Box>
    </Center>
  );
}
