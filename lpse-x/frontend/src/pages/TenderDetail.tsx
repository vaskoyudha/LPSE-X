import React from 'react'
import { useParams } from 'react-router-dom'

export function TenderDetail(): React.ReactElement {
  const { id } = useParams<{ id: string }>()
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4 text-slate-800">Tender Details: {id}</h1>
      <p>TenderDetail placeholder</p>
    </div>
  )
}
