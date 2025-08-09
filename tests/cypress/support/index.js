// tests/cypress/support/index.js
// Propósito: Punto de entrada para comandos y configuraciones globales
// Buenas prácticas:
//  - Importar siempre commands antes de cualquier test
//  - Limpiar estado entre pruebas

import './commands';    // Carga comandos custom

beforeEach(() => {
  // Limpieza de cookies y almacenamiento local antes de cada test
  cy.clearCookies();
  cy.clearLocalStorage();
});
