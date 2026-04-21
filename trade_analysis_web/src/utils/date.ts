import dayjs, { type Dayjs } from 'dayjs'
import utc from 'dayjs/plugin/utc'
import { DEFAULT_DATE_TIME_FORMAT } from '@/constants/date'

dayjs.extend(utc)

export const formatDateTime = (
  value?: string | number | Date | Dayjs | null,
  format = DEFAULT_DATE_TIME_FORMAT,
) => {
  if (!value) {
    return '-'
  }

  const parsed = dayjs(value)
  if (!parsed.isValid()) {
    return '-'
  }

  return parsed.format(format)
}

export const toUnixTimestampSeconds = (value?: string | number | Date | null) => {
  if (!value) {
    return null
  }

  const parsed = dayjs(value)
  if (!parsed.isValid()) {
    return null
  }

  return parsed.unix()
}

export const toChartTimestampSeconds = (value?: string | number | Date | null) => {
  if (!value) {
    return null
  }

  const parsed = dayjs(value)
  if (!parsed.isValid()) {
    return null
  }

  return dayjs.utc(parsed.format(DEFAULT_DATE_TIME_FORMAT)).unix()
}

export const createRecentDateRange = (days: number) => {
  const end = dayjs().endOf('day')
  const start = dayjs().subtract(days - 1, 'day').startOf('day')

  return [start.toDate(), end.toDate()] as [Date, Date]
}

export const getLatestDateTime = (values: Array<string | null | undefined>) => {
  let latest: dayjs.Dayjs | null = null

  for (const value of values) {
    if (!value) {
      continue
    }

    const parsed = dayjs(value)
    if (!parsed.isValid()) {
      continue
    }

    if (!latest || parsed.isAfter(latest)) {
      latest = parsed
    }
  }

  return latest
}
