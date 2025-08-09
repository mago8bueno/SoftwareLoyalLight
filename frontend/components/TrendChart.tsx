// components/TrendChart.tsx
// Componente: Gráfico de líneas de tendencias usando Recharts

import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

// Datos de ejemplo; en real los recibirías como prop o desde un hook
const sampleData = [
  { date: 'Mon', value: 10 },
  { date: 'Tue', value: 15 },
  { date: 'Wed', value: 12 },
  { date: 'Thu', value: 20 },
  { date: 'Fri', value: 18 },
  { date: 'Sat', value: 22 },
  { date: 'Sun', value: 16 },
];

interface TrendChartProps {
  data?: { date: string; value: number }[];
}

const TrendChart: React.FC<TrendChartProps> = ({ data = sampleData }) => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#3182ce"
          strokeWidth={2}
          dot={{ r: 3 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default TrendChart;
