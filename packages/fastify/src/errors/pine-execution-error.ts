export class PineExecutionError extends Error {
  public readonly statusCode = 422

  constructor(message: string, cause?: unknown) {
    super(message, { cause })
    this.name = 'PineExecutionError'
  }
}
