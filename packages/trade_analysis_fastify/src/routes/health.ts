import type { FastifyPluginAsync } from 'fastify'

export const healthRoutes: FastifyPluginAsync = async (app) => {
  app.get(
    '/health',
    {
      schema: {
        tags: ['System'],
        summary: 'Check service health',
        response: {
          200: {
            type: 'object',
            required: ['status', 'service', 'requestId'],
            properties: {
              status: { type: 'string', examples: ['ok'] },
              service: { type: 'string', examples: ['trade-analysis-fastify'] },
              requestId: { type: 'string' },
            },
          },
        },
      },
    },
    async (request) => ({
      status: 'ok',
      service: 'trade-analysis-fastify',
      requestId: request.id,
    }),
  )
}
