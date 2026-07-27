import type { FastifyPluginAsync } from 'fastify'

import { executePineScript, type ExecutePineRequest } from '../services/pine-executor.js'

const candleSchema = {
  type: 'object',
  required: ['open', 'high', 'low', 'close', 'volume'],
  anyOf: [{ required: ['timestamp'] }, { required: ['openTime'] }],
  properties: {
    timestamp: { type: 'number', description: 'Candle open time in seconds or milliseconds.' },
    openTime: { type: 'number', description: 'PineTS candle open time in seconds or milliseconds.' },
    closeTime: { type: 'number', description: 'Optional candle close time in seconds or milliseconds.' },
    open: { type: 'number' },
    high: { type: 'number' },
    low: { type: 'number' },
    close: { type: 'number' },
    volume: { type: 'number' },
  },
  additionalProperties: false,
} as const

export const pineRoutes: FastifyPluginAsync = async (app) => {
  app.post<{ Body: ExecutePineRequest }>(
    '/execute',
    {
      schema: {
        tags: ['Pine Scripts'],
        summary: 'Execute a Pine Script indicator',
        description: 'Runs the supplied Pine Script against custom OHLCV candles and returns normalized plots and drawings.',
        body: {
          type: 'object',
          required: ['source', 'bars'],
          properties: {
            source: {
              type: 'string',
              minLength: 1,
              description: 'Pine Script source code.',
              examples: ['//@version=5\nindicator("SMA")\nplot(ta.sma(close, 20), "SMA 20")'],
            },
            bars: {
              type: 'array',
              minItems: 1,
              items: candleSchema,
            },
          },
          additionalProperties: false,
        },
        response: {
          200: {
            type: 'object',
            required: ['barCount', 'indicator', 'plots', 'drawings', 'warnings'],
            properties: {
              barCount: { type: 'integer', minimum: 1 },
              indicator: {
                type: 'object',
                description: 'Indicator declaration metadata emitted by PineTS.',
                additionalProperties: true,
              },
              plots: {
                type: 'array',
                description: 'Normalized continuous plot series emitted by the Pine script.',
                items: { type: 'object', additionalProperties: true },
              },
              drawings: {
                type: 'object',
                required: ['labels', 'lines', 'boxes'],
                description: 'Normalized discrete drawing objects emitted by the Pine script.',
                properties: {
                  labels: { type: 'array', items: { type: 'object', additionalProperties: true } },
                  lines: { type: 'array', items: { type: 'object', additionalProperties: true } },
                  boxes: { type: 'array', items: { type: 'object', additionalProperties: true } },
                },
              },
              warnings: {
                type: 'array',
                items: { type: 'object', additionalProperties: true },
              },
            },
          },
          422: {
            type: 'object',
            required: ['error', 'message', 'requestId'],
            properties: {
              error: { type: 'string', examples: ['PineExecutionError'] },
              message: { type: 'string' },
              requestId: { type: 'string' },
            },
          },
        },
      },
    },
    async (request) => {
      const result = await executePineScript(request.body)

      return {
        barCount: request.body.bars.length,
        ...result,
      }
    },
  )
}
