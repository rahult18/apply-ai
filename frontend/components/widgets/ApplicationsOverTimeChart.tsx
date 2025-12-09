"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface TimeData {
  month: string
  applications: number
}

interface ApplicationsOverTimeChartProps {
  data: TimeData[]
}

export function ApplicationsOverTimeChart({
  data,
}: ApplicationsOverTimeChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Applications Over Time</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="applications" fill="#3b82f6" name="Applications" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

