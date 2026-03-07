"use client";

interface PricePoint {
  label: string;
  price: number;
}

export interface PriceDataResult {
  points: PricePoint[];
  type: "comparison" | "trend";
  title: string;
}

interface PriceChartProps {
  data: PriceDataResult;
}

export default function PriceChart({ data }: PriceChartProps) {
  const { points, type, title } = data;
  if (!points || points.length < 2) return null;

  const prices = points.map((d) => d.price);
  const maxPrice = Math.max(...prices);
  const minPrice = Math.min(...prices);
  const range = maxPrice - minPrice || 1;

  // For trends: green if rising, red if falling
  // For comparisons: neutral blue (no directional meaning)
  const isComparison = type === "comparison";
  const isRising = prices[prices.length - 1] >= prices[0];
  const changePct = Math.abs(
    ((prices[prices.length - 1] - prices[0]) / prices[0]) * 100
  ).toFixed(1);

  let color: string;
  let bgColor: string;
  let fillColor: string;

  if (isComparison) {
    color = "#2563eb"; // blue
    bgColor = "#eff6ff";
    fillColor = "rgba(37,99,235,0.10)";
  } else if (isRising) {
    color = "#16a34a";
    bgColor = "#dcfce7";
    fillColor = "rgba(22,163,74,0.12)";
  } else {
    color = "#dc2626";
    bgColor = "#fef2f2";
    fillColor = "rgba(220,38,38,0.12)";
  }

  // Build SVG polyline path
  const width = 280;
  const height = 100;
  const padX = 8;
  const padY = 12;
  const padBottom = 28;
  const chartW = width - padX * 2;
  const chartH = height - padY - padBottom;

  const svgPoints = points.map((d, i) => {
    const x = padX + (i / (points.length - 1)) * chartW;
    const y = padY + chartH - ((d.price - minPrice) / range) * chartH;
    return { x, y };
  });

  const polyline = svgPoints.map((p) => `${p.x},${p.y}`).join(" ");

  // Area fill
  const areaPath = `M${padX},${padY + chartH} ${svgPoints.map((p) => `L${p.x},${p.y}`).join(" ")} L${padX + chartW},${padY + chartH} Z`;

  return (
    <div
      className="mt-2 rounded-lg border border-gray-100 overflow-hidden"
      style={{ background: bgColor }}
    >
      <div className="px-3 pt-2 flex items-center justify-between">
        <span className="text-xs font-medium text-gray-600">{title}</span>
        {!isComparison && (
          <span className="text-xs font-bold" style={{ color }}>
            {isRising ? "+" : "-"}{changePct}%
          </span>
        )}
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height: 100 }}>
        <path d={areaPath} fill={fillColor} />
        <polyline
          points={polyline}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Dots and price labels on each point */}
        {svgPoints.map((p, idx) => (
          <g key={idx}>
            <circle cx={p.x} cy={p.y} r="3" fill={color} />
            <text
              x={p.x}
              y={p.y - 7}
              textAnchor="middle"
              fill={color}
              fontSize="7"
              fontWeight="600"
            >
              {points[idx].price.toLocaleString("en-IN")}
            </text>
          </g>
        ))}
        {/* X-axis labels */}
        {svgPoints.map((p, idx) => (
          <text
            key={`label-${idx}`}
            x={p.x}
            y={height - 4}
            textAnchor="middle"
            fill="#888"
            fontSize="6.5"
          >
            {points[idx].label.length > 10
              ? points[idx].label.slice(0, 9) + ".."
              : points[idx].label}
          </text>
        ))}
      </svg>
    </div>
  );
}

/**
 * Parse price data from bot message text.
 * Only returns data when there's clear, structured price information.
 */
export function extractPriceData(text: string): PriceDataResult | null {
  const points: PricePoint[] = [];

  // Pattern 1: "Mandi/Location: Rs/₹X,XXX" lines (nearby mandis / mandi comparison)
  const mandiPattern = /[•\-→]\s*(.+?):\s*₹([\d,]+)/g;
  let match;
  while ((match = mandiPattern.exec(text)) !== null) {
    const label = match[1].trim().split("(")[0].trim();
    const price = parseInt(match[2].replace(/,/g, ""), 10);
    if (price > 0 && !isNaN(price)) {
      points.push({ label, price });
    }
  }

  if (points.length >= 3) {
    // Sort by price ascending for a clean comparison chart
    points.sort((a, b) => a.price - b.price);
    return {
      points,
      type: "comparison",
      title: "Mandi Price Comparison",
    };
  }

  // Pattern 2: Date-based trend data "DD/MM or DD-Mon: ₹X,XXX"
  const trendPoints: PricePoint[] = [];
  const datePattern =
    /(\d{1,2}[\/-]\d{1,2}(?:[\/-]\d{2,4})?|\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|जन|फर|मार्च|अप्रै|मई|जून|जुल|अग|सित|अक्टू|नव|दिस)\w*(?:\s*\d{2,4})?)[:\s]*₹([\d,]+)/gi;
  while ((match = datePattern.exec(text)) !== null) {
    const label = match[1].trim();
    const price = parseInt(match[2].replace(/,/g, ""), 10);
    if (price > 0 && !isNaN(price)) {
      trendPoints.push({ label, price });
    }
  }

  if (trendPoints.length >= 3) {
    return {
      points: trendPoints,
      type: "trend",
      title: "Price Trend",
    };
  }

  return null;
}
