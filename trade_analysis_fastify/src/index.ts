import { buildApp } from './app.js'

const start = async () => {
  const server = buildApp()
  const port = Number(process.env.PORT ?? 8080)
  const host = process.env.HOST ?? '127.0.0.1'

  try {
    await server.listen({ port, host })
  } catch (error) {
    server.log.fatal(error, 'Unable to start server')
    process.exitCode = 1
  }
}

void start()
