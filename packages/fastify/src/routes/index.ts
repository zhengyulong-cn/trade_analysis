import type { FastifyInstance } from 'fastify'

import { healthRoutes } from './health.js'
import { pineRoutes } from './pine.js'
import { pineScannerRoutes } from './pine-scanner.js'

export const registerRoutes = (app: FastifyInstance) => {
  app.register(healthRoutes)
  app.register(pineRoutes, { prefix: '/v1/pine' })
  app.register(pineScannerRoutes, { prefix: '/v1/pine' })
}
