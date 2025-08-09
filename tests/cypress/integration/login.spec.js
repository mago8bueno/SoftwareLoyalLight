// tests/cypress/integration/login.spec.js
// Propósito: Verificar flujo de login y acceso al dashboard
// Buenas prácticas:
//  - Nombre descriptivo de la suite y los tests
//  - Uso de hooks (before) para preparar estado
//  - Assertions claras y específicas

describe('Login Flow', () => {
  before(() => {
    // Reutiliza comando custom de login para no repetir pasos UI
    cy.login('user@example.com', 'password123');
  });

  it('should redirect to /dashboard after successful login', () => {
    // Verifica que la URL contiene el path esperado
    cy.url().should('include', '/dashboard');
    // Verifica que el elemento de bienvenida es visible
    cy.contains('Welcome').should('be.visible');
  });
});
