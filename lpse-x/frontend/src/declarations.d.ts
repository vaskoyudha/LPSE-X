/// <reference types="vite/client" />

/**
 * Module declarations for packages without TypeScript types
 */

declare module 'react-plotly.js' {
  import * as Plotly from 'plotly.js'
  import * as React from 'react'

  interface PlotParams {
    data: Plotly.Data[]
    layout?: Partial<Plotly.Layout>
    config?: Partial<Plotly.Config>
    frames?: Plotly.Frame[]
    style?: React.CSSProperties
    className?: string
    useResizeHandler?: boolean
    debug?: boolean
    onInitialized?: (figure: { data: Plotly.Data[]; layout: Partial<Plotly.Layout> }, graphDiv: HTMLElement) => void
    onUpdate?: (figure: { data: Plotly.Data[]; layout: Partial<Plotly.Layout> }, graphDiv: HTMLElement) => void
    onPurge?: (figure: { data: Plotly.Data[]; layout: Partial<Plotly.Layout> }, graphDiv: HTMLElement) => void
    onError?: (err: Error) => void
    divId?: string
    revision?: number
  }

  const Plot: React.ComponentType<PlotParams>
  export default Plot
}

