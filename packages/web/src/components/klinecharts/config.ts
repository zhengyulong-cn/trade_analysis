import type { DeepPartial, Styles } from 'klinecharts'

export const chartStylesConfig: DeepPartial<Styles> = {
  grid: {
    horizontal: {
      color: "#edf1f6",
    },
    vertical: {
      color: "#edf1f6",
    },
  },
  candle: {
    type: 'candle_solid',
    bar: {
      upColor: '#F92855',
      downColor: '#2DC08E',
      upBorderColor: '#F92855',
      downBorderColor: '#2DC08E',
      upWickColor: '#F92855',
      downWickColor: '#2DC08E',
      noChangeColor: '#888888',
      noChangeBorderColor: '#888888',
      noChangeWickColor: '#888888'
    },
    tooltip: {
      showRule: "always",
      showType: "standard",
    },
  }
}