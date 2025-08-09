// components/Button.tsx
// UI Atom: Botón personalizado con soporte para estado de carga

import React from 'react';
import { Button as CButton, ButtonProps } from '@chakra-ui/react';

export interface CustomButtonProps extends ButtonProps {
  /** Indica si el botón muestra un spinner de carga */
  isLoading?: boolean;
}

/**
 * Button
 * @param props - Props personalizadas extendiendo Chakra ButtonProps
 * @returns CButton con colorScheme "brand" y estado de carga
 */
export function Button(props: CustomButtonProps) {
  // Separa isLoading del resto de props para no pasarlo dos veces
  const { isLoading, ...rest } = props;

  return (
    <CButton
      colorScheme="brand"
      loading={isLoading} // ← Usamos `loading` en lugar de `isLoading`
      {...rest} // spread de todas las demás props (onClick, size, etc.)
    />
  );
}
