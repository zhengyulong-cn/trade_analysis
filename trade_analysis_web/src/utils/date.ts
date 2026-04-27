import dayjs, { type Dayjs } from 'dayjs'
import customParseFormat from 'dayjs/plugin/customParseFormat'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { DEFAULT_DATE_TIME_FORMAT } from '@/constants/date'

dayjs.extend(customParseFormat)
dayjs.extend(timezone)
dayjs.extend(utc)

const SHANGHAI_TIMEZONE = 'Asia/Shanghai'

const hasExplicitTimezone = (value: string) => {
  return /([zZ]|[+-]\d{2}:\d{2}|[+-]\d{4})$/.test(value)
}

const parseDateTime = (value?: string | number | Date | Dayjs | null) => {
  if (!value) {
    return null
  }

  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) {
      return null
    }

    if (hasExplicitTimezone(trimmed)) {
      const parsed = dayjs(trimmed)
      return parsed.isValid() ? parsed : null
    }

    const parsed = dayjs.tz(trimmed, DEFAULT_DATE_TIME_FORMAT, SHANGHAI_TIMEZONE)
    return parsed.isValid() ? parsed : null
  }

  const parsed = dayjs(value)
  return parsed.isValid() ? parsed : null
}

export const formatDateTime = (
  value?: string | number | Date | Dayjs | null,
  format = DEFAULT_DATE_TIME_FORMAT,
) => {
  const parsed = parseDateTime(value)
  if (!parsed) {
    return '-'
  }

  return parsed.format(format)
}

export const toUnixTimestampSeconds = (value?: string | number | Date | null) => {
  const parsed = parseDateTime(value)
  if (!parsed) {
    return null
  }

  return parsed.unix()
}

export const toChartTimestampSeconds = (value?: string | number | Date | null) => {
  const parsed = parseDateTime(value)
  if (!parsed) {
    return null
  }

  return parsed.utc().unix()
}

export const createRecentDateRange = (days: number) => {
  const end = dayjs().endOf('day')
  const start = dayjs().subtract(days - 1, 'day').startOf('day')

  return [start.toDate(), end.toDate()] as [Date, Date]
}

export const getLatestDateTime = (values: Array<string | null | undefined>) => {
  let latest: dayjs.Dayjs | null = null

  for (const value of values) {
    const parsed = parseDateTime(value)
    if (!parsed) {
      continue
    }

    if (!latest || parsed.isAfter(latest)) {
      latest = parsed
    }
  }

  return latest
}
