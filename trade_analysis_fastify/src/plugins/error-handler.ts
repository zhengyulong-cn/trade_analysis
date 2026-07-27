import type { FastifyError, FastifyInstance } from 'fastify'

export const registerErrorHandlers = (app: FastifyInstance) => {
  app.setErrorHandler((error, request, reply) => {
    const requestError = error as FastifyError
    const statusCode =
      requestError.statusCode && requestError.statusCode >= 400 ? requestError.statusCode : 500

    if (statusCode >= 500) {
      request.log.error({ err: requestError }, 'Unhandled request error')
    } else {
      request.log.warn({ err: requestError }, 'Request failed')
    }

    return reply.status(statusCode).send({
      error: statusCode >= 500 ? 'Internal Server Error' : requestError.name,
      message: statusCode >= 500 ? 'An unexpected error occurred.' : requestError.message,
      requestId: request.id,
    })
  })

  app.setNotFoundHandler((request, reply) => {
    request.log.warn('Route not found')

    return reply.status(404).send({
      error: 'Not Found',
      message: `Route ${request.method} ${request.url} not found.`,
      requestId: request.id,
    })
  })
}
