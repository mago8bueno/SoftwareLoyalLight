// tests/cypress/plugins/index.js
// Propósito: Configurar plugins de Cypress (ej: modificar config, registrar tasks)
// Buenas prácticas:
//  - Siempre retornar el objeto config para permitir overrides
//  - Documentar cada plugin habilitado

module.exports = (on, config) => {
  // Aquí podrías registrar tasks de Node.js
  // Ejemplo: on('task', { log: console.log })
  return config;
};
