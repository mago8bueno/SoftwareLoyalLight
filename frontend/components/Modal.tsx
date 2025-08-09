// components/Modal.tsx
// Molecule: Modal con animación usando Chakra UI + Framer Motion

import React, { ReactNode } from 'react'
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalProps
} from '@chakra-ui/react'
import { motion, HTMLMotionProps } from 'framer-motion'

// Creamos un componente animado a partir de ModalContent
const MotionModalContent = motion<
  React.ComponentProps<typeof ModalContent> & HTMLMotionProps<'div'>
>(ModalContent)

export interface ModalWrapperProps extends ModalProps {
  title: string
  footer?: ReactNode
  children: ReactNode
}

export default function ModalWrapper({
  title,
  children,
  footer,
  ...modalProps
}: ModalWrapperProps) {
  return (
    <Modal {...modalProps}>
      <ModalOverlay />
      <MotionModalContent
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 50 }}
        transition={{ duration: 0.2 }}
      >
        <ModalHeader>{title}</ModalHeader>
        <ModalBody>{children}</ModalBody>
        {footer && <ModalFooter>{footer}</ModalFooter>}
      </MotionModalContent>
    </Modal>
  )
}
