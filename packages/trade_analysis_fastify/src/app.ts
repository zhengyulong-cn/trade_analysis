import Fastify from 'fastify'
import swagger from '@fastify/swagger'
import swaggerUi from '@fastify/swagger-ui'

import { registerErrorHandlers } from './plugins/error-handler.js'
import { registerRoutes } from './routes/index.js'

export const buildApp = () => {
  const app = Fastify({
    logger: {
      level: process.env.LOG_LEVEL ?? 'info',
    },
    requestIdHeader: 'x-request-id',
    genReqId: () => crypto.randomUUID(),
  })

  app.register(swagger, {
    openapi: {
      info: {
        title: 'Trade Analysis Pine Runner API',
        description: 'PineTS script execution service for Trade Analysis.',
        version: '1.0.0',
      },
    },
  })
  app.register(swaggerUi, {
    routePrefix: '/docs',
    uiConfig: {
      docExpansion: 'list',
    },
  })

  registerErrorHandlers(app)
  registerRoutes(app)

  return app
}
