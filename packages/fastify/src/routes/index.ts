import type { FastifyInstance } from 'fastify'

import { healthRoutes } from './health.js'
import { pineRoutes } from './pine.js'

export const registerRoutes = (app: FastifyInstance) => {
  app.register(healthRoutes)
  app.register(pineRoutes, { prefix: '/v1/pine' })
}
