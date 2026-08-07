import type { FastifyPluginAsync } from 'fastify'

import { executePineScanner, type ExecutePineScanRequest } from '../services/pine-scanner.js'

const candleSchema = {
  type: 'object',
  required: ['open', 'high', 'low', 'close', 'volume'],
  anyOf: [{ required: ['timestamp'] }, { required: ['openTime'] }],
  properties: {
    timestamp: { type: 'number' },
    openTime: { type: 'number' },
    closeTime: { type: 'number' },
    open: { type: 'number' },
    high: { type: 'number' },
    low: { type: 'number' },
    close: { type: 'number' },
    volume: { type: 'number' },
  },
  additionalProperties: false,
} as const

export const pineScannerRoutes: FastifyPluginAsync = async (app) => {
  app.post<{ Body: ExecutePineScanRequest }>(
    '/scan',
    {
      schema: {
        tags: ['Pine Scripts'],
        summary: 'Scan contracts with a Pine Script alertcondition',
        description: 'Executes a scanner script for each contract and returns only the final-bar SCAN_SIGNAL alerts.',
        body: {
          type: 'object',
          required: ['source', 'contracts'],
          properties: {
            source: { type: 'string', minLength: 1 },
            signalTitle: { type: 'string', minLength: 1, default: 'SCAN_SIGNAL' },
            contracts: {
              type: 'array',
              maxItems: 100,
              items: {
                type: 'object',
                required: ['symbol', 'exchange', 'name', 'bars'],
                properties: {
                  symbol: { type: 'string', minLength: 1 },
                  exchange: { type: 'string', minLength: 1 },
                  name: { type: 'string', minLength: 1 },
                  bars: { type: 'array', minItems: 1, maxItems: 5000, items: candleSchema },
                },
                additionalProperties: false,
              },
            },
          },
          additionalProperties: false,
        },
        response: {
          200: {
            type: 'object',
            required: ['scannedCount', 'matches'],
            properties: {
              scannedCount: { type: 'integer', minimum: 0 },
              matches: {
                type: 'array',
                items: {
                  type: 'object',
                  required: ['symbol', 'exchange', 'name', 'message', 'triggeredAt'],
                  properties: {
                    symbol: { type: 'string' },
                    exchange: { type: 'string' },
                    name: { type: 'string' },
                    message: { type: 'string' },
                    triggeredAt: { type: 'number' },
                  },
                },
              },
            },
          },
        },
      },
    },
    async (request) => {
      const result = await executePineScanner(request.body)
      app.log.info({ scannedCount: result.scannedCount, matchCount: result.matches.length }, 'Pine scanner completed')
      return result
    },
  )
}
