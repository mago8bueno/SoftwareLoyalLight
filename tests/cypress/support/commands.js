// tests/cypress/support/commands.js
// Propósito: Definir comandos custom reutilizables en todos los tests
// Buenas prácticas:
//  - Nombres claros y actions atómicas
//  - Usar cy.request para acelerar flujos de autenticación

Cypress.Commands.add('login', (email, password) => {
  // Autentica vía API y guarda token en localStorage
  cy.request({
    method: 'POST',
    url: '/api/auth/login',
    body: { email, password }
  }).then((resp) => {
    window.localStorage.setItem('token', resp.body.token);
  });
});
