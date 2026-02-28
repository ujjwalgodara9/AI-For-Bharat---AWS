"use client";

interface PricePoint {
  label: string;
  price: number;
}

interface PriceChartProps {
  data: PricePoint[];
  title?: string;
}

export default function PriceChart({ data, title }: PriceChartProps) {
  if (!data || data.length < 2) return null;

  const prices = data.map((d) => d.price);
  const maxPrice = Math.max(...prices);
  const minPrice = Math.min(...prices);
  const range = maxPrice - minPrice || 1;

  const isRising = prices[prices.length - 1] > prices[0];
  const changePct = (((prices[prices.length - 1] - prices[0]) / prices[0]) * 100).toFixed(1);

  // Build SVG polyline path
  const width = 280;
  const height = 80;
  const padX = 8;
  const padY = 10;
  const chartW = width - padX * 2;
  const chartH = height - padY * 2;

  const points = data.map((d, i) => {
    const x = padX + (i / (data.length - 1)) * chartW;
    const y = padY + chartH - ((d.price - minPrice) / range) * chartH;
    return `${x},${y}`;
  });
  const polyline = points.join(" ");

  // Area fill
  const areaPath = `M${padX},${padY + chartH} ${points.map((p, i) => (i === 0 ? `L${p}` : `L${p}`)).join(" ")} L${padX + chartW},${padY + chartH} Z`;

  const color = isRising ? "#16a34a" : "#dc2626";
  const bgColor = isRising ? "#dcfce7" : "#fef2f2";
  const fillColor = isRising ? "rgba(22,163,74,0.12)" : "rgba(220,38,38,0.12)";

  return (
    <div className="mt-2 rounded-lg border border-gray-100 overflow-hidden" style={{ background: bgColor }}>
      {title && (
        <div className="px-3 pt-2 flex items-center justify-between">
          <span className="text-xs font-medium text-gray-600">{title}</span>
          <span className="text-xs font-bold" style={{ color }}>
            {isRising ? "▲" : "▼"} {changePct}%
          </span>
        </div>
      )}
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height: 80 }}>
        <path d={areaPath} fill={fillColor} />
        <polyline
          points={polyline}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Dots on first and last point */}
        {[0, data.length - 1].map((idx) => {
          const x = padX + (idx / (data.length - 1)) * chartW;
          const y = padY + chartH - ((data[idx].price - minPrice) / range) * chartH;
          return <circle key={idx} cx={x} cy={y} r="3" fill={color} />;
        })}
      </svg>
      <div className="flex justify-between px-3 pb-2 text-[10px] text-gray-500">
        <span>₹{minPrice.toLocaleString("en-IN")}</span>
        <span>₹{maxPrice.toLocaleString("en-IN")}</span>
      </div>
    </div>
  );
}

/**
 * Parse price data from bot message text.
 * Looks for patterns like mandi price listings with ₹ values.
 */
export function extractPriceData(text: string): PricePoint[] | null {
  const points: PricePoint[] = [];

  // Pattern 1: "Mandi: ₹X,XXX" lines (nearby mandis comparison)
  const mandiPattern = /[•→]\s*(.+?):\s*₹([\d,]+)/g;
  let match;
  while ((match = mandiPattern.exec(text)) !== null) {
    const label = match[1].trim().split("(")[0].trim();
    const price = parseInt(match[2].replace(/,/g, ""), 10);
    if (price > 0 && !isNaN(price)) {
      points.push({ label, price });
    }
  }

  if (points.length >= 2) return points;

  // Pattern 2: "₹X,XXX/quintal" or "₹X,XXX/क्विंटल" with date context
  const pricePattern = /₹([\d,]+)/g;
  const prices: number[] = [];
  while ((match = pricePattern.exec(text)) !== null) {
    const price = parseInt(match[1].replace(/,/g, ""), 10);
    if (price > 100 && price < 500000 && !isNaN(price)) {
      prices.push(price);
    }
  }

  // If we have multiple unique prices, show them as a trend
  const unique = Array.from(new Set(prices));
  if (unique.length >= 3) {
    return unique.slice(0, 6).map((p, i) => ({ label: `${i + 1}`, price: p }));
  }

  return null;
}
