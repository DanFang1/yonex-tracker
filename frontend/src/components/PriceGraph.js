import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './PriceGraph.css';

export default function PriceGraph({ data, productName, onClose }) {
  if (!data || data.length === 0) {
    return (
      <div className="graph-modal">
        <div className="graph-content">
          <button className="close-btn" onClick={onClose}>×</button>
          <h2>{productName}</h2>
          <p>No price history available yet.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="graph-modal">
      <div className="graph-content">
        <button className="close-btn" onClick={onClose}>×</button>
        <h2>{productName} - Price History</h2>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis />
            <Tooltip 
              formatter={(value) => `$${value.toFixed(2)}`}
              labelFormatter={(label) => new Date(label).toLocaleString()}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="price" 
              stroke="#8884d8" 
              strokeWidth={2}
              dot={false}
              name="Price"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
