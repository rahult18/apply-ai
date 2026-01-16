"use client"

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts"

interface StatusData {
  name: string
  value: number
}

interface StatusChartProps {
  data: StatusData[]
}

const COLORS = {
  saved: "#94a3b8",
  applied: "#3b82f6",
  interviewing: "#f59e0b",
  rejected: "#ef4444",
  offer: "#10b981",
  withdrawn: "#6b7280",
}

export function StatusChart({ data }: StatusChartProps) {
  const getColor = (name: string) => {
    const lowercaseName = name.toLowerCase()
    return COLORS[lowercaseName as keyof typeof COLORS] || "#94a3b8"
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) =>
            `${name}: ${(percent * 100).toFixed(0)}%`
          }
          outerRadius={100}
          fill="#8884d8"
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={getColor(entry.name)} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}

