import { useEffect, useMemo, useState } from "react";

type StockPoint = {
  date: string;
  close: number;
  volume?: number;
};

type StockResponse = {
  success?: boolean;
  ticker?: string;
  company?: string;
  currency?: string;
  current_price?: number;
  change_pct?: number;
  data_source?: string;
  demo?: boolean;
  history?: StockPoint[];
};

type StockChartProps = {
  ticker: string;
};

const API_BASE = "";

function formatPrice(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) return "—";

  return new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
  });
}

function makeDemoHistory(price: number): StockPoint[] {
  const points: StockPoint[] = [];

  let current = price * 0.91;

  for (let i = 29; i >= 0; i--) {
    const date = new Date();

    date.setDate(date.getDate() - i);

    const movement =
      Math.sin(i * 0.75) * price * 0.012 +
      Math.cos(i * 0.31) * price * 0.008;

    current += movement;

    if (current <= 0) {
      current = price * 0.8;
    }

    points.push({
      date: date.toISOString(),
      close: current,
      volume: Math.round(
        1000000 +
          Math.abs(Math.sin(i * 0.4)) * 5000000,
      ),
    });
  }

  // Make the last point equal to the current price.
  points[points.length - 1].close = price;

  return points;
}

function buildPath(
  points: StockPoint[],
  width: number,
  height: number,
  padding: number,
) {
  if (points.length === 0) return "";

  const prices = points.map((point) => point.close);

  const min = Math.min(...prices);
  const max = Math.max(...prices);

  const range = max - min || 1;

  return points
    .map((point, index) => {
      const x =
        padding +
        (index / Math.max(points.length - 1, 1)) *
          (width - padding * 2);

      const y =
        height -
        padding -
        ((point.close - min) / range) *
          (height - padding * 2);

      return `${index === 0 ? "M" : "L"} ${x.toFixed(
        2,
      )} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function buildAreaPath(
  points: StockPoint[],
  width: number,
  height: number,
  padding: number,
) {
  if (points.length === 0) return "";

  const line = buildPath(
    points,
    width,
    height,
    padding,
  );

  const bottom = height - padding;

  const lastX =
    width - padding;

  return `${line} L ${lastX} ${bottom} L ${padding} ${bottom} Z`;
}

export default function StockChart({
  ticker,
}: StockChartProps) {
  const [data, setData] =
    useState<StockResponse | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [range, setRange] =
    useState<"1M" | "3M" | "1Y">("1M");

  useEffect(() => {
    let cancelled = false;

    async function loadStock() {
      setLoading(true);
      setError(null);

      const symbol = ticker
        .toUpperCase()
        .trim();

      try {
        /*
         * First try the NEXUS backend.
         */
        const backendResponse =
          await fetch(
            `${API_BASE}/api/market/${encodeURIComponent(
              symbol,
            )}`,
          );

        if (backendResponse.ok) {
          const json =
            (await backendResponse.json()) as StockResponse;

          if (
            json.history &&
            json.history.length > 0
          ) {
            if (!cancelled) {
              setData(json);
              setLoading(false);
            }

            return;
          }
        }
      } catch {
        /*
         * Backend market endpoint may not exist yet.
         * We continue to Yahoo's public chart endpoint.
         */
      }

      /*
       * Fallback to Yahoo Finance chart API.
       *
       * Indian NSE tickers are generally represented
       * as SYMBOL.NS.
       */
      try {
        const yahooSymbol =
          symbol.endsWith(".NS") ||
          symbol.endsWith(".BO")
            ? symbol
            : `${symbol}.NS`;

        const period =
          range === "1M"
            ? "1mo"
            : range === "3M"
              ? "3mo"
              : "1y";

        const yahooUrl =
          `https://query1.finance.yahoo.com/v8/finance/chart/` +
          `${encodeURIComponent(
            yahooSymbol,
          )}?range=${period}&interval=1d&events=history`;

        const response =
          await fetch(yahooUrl);

        if (!response.ok) {
          throw new Error(
            `Market data request failed (${response.status})`,
          );
        }

        const json = await response.json();

        const result =
          json?.chart?.result?.[0];

        const timestamps =
          result?.timestamp ?? [];

        const quote =
          result?.indicators?.quote?.[0];

        const closes =
          quote?.close ?? [];

        const volumes =
          quote?.volume ?? [];

        const history: StockPoint[] = [];

        for (
          let i = 0;
          i < timestamps.length;
          i++
        ) {
          const close = Number(
            closes[i],
          );

          if (
            Number.isFinite(close) &&
            close > 0
          ) {
            history.push({
              date: new Date(
                timestamps[i] * 1000,
              ).toISOString(),

              close,

              volume:
                Number(volumes[i]) || 0,
            });
          }
        }

        if (history.length === 0) {
          throw new Error(
            `No market history found for ${symbol}`,
          );
        }

        const first =
          history[0].close;

        const last =
          history[history.length - 1].close;

        const changePct =
          first !== 0
            ? ((last - first) / first) *
              100
            : 0;

        if (!cancelled) {
          setData({
            success: true,
            ticker: symbol,
            company: symbol,
            currency: "INR",
            current_price: last,
            change_pct: changePct,
            data_source:
              "Yahoo Finance",
            demo: false,
            history,
          });

          setLoading(false);
        }

        return;
      } catch (yahooError) {
        /*
         * Final fallback:
         * keep the UI functional using the price
         * already available in NEXUS market data.
         */
        try {
          const response =
            await fetch(
              `${API_BASE}/api/investigate`,
              {
                method: "POST",

                headers: {
                  "Content-Type":
                    "application/json",
                },

                body: JSON.stringify({
                  ticker: symbol,
                  question:
                    "Give me the current market data for this company.",
                }),
              },
            );

          if (response.ok) {
            const json =
              await response.json();

            const technical =
              json?.agents?.technical;

            const currentPrice = Number(
              technical?.current_price ??
                technical?.price ??
                technical?.data?.current_price ??
                0,
            );

            if (
              Number.isFinite(
                currentPrice,
              ) &&
              currentPrice > 0
            ) {
              const history =
                makeDemoHistory(
                  currentPrice,
                );

              if (!cancelled) {
                setData({
                  success: true,
                  ticker: symbol,
                  company: symbol,
                  currency: "INR",
                  current_price:
                    currentPrice,
                  change_pct:
                    ((currentPrice -
                      history[0].close) /
                      history[0].close) *
                    100,
                  data_source:
                    "NEXUS market data",
                  demo: true,
                  history,
                });

                setLoading(false);
              }

              return;
            }
          }
        } catch {
          // Continue to final error.
        }

        if (!cancelled) {
          setError(
            yahooError instanceof Error
              ? yahooError.message
              : "Unable to load market data.",
          );

          setLoading(false);
        }
      }
    }

    loadStock();

    return () => {
      cancelled = true;
    };
  }, [ticker, range]);

  const chartData = useMemo(() => {
    if (!data?.history) return [];

    return data.history.filter(
      (point) =>
        Number.isFinite(point.close) &&
        point.close > 0,
    );
  }, [data]);

  const chartWidth = 1000;
  const chartHeight = 330;
  const padding = 35;

  const prices =
    chartData.length > 0
      ? chartData.map(
          (point) => point.close,
        )
      : [];

  const minPrice =
    prices.length > 0
      ? Math.min(...prices)
      : 0;

  const maxPrice =
    prices.length > 0
      ? Math.max(...prices)
      : 0;

  const latestPrice =
    data?.current_price ??
    chartData[chartData.length - 1]
      ?.close;

  const firstPrice =
    chartData[0]?.close;

  const change =
    latestPrice !== undefined &&
    firstPrice !== undefined &&
    firstPrice !== 0
      ? ((latestPrice - firstPrice) /
          firstPrice) *
        100
      : data?.change_pct ?? 0;

  const isPositive = change >= 0;

  const linePath = buildPath(
    chartData,
    chartWidth,
    chartHeight,
    padding,
  );

  const areaPath = buildAreaPath(
    chartData,
    chartWidth,
    chartHeight,
    padding,
  );

  return (
    <section className="stock-chart">
      <div className="chart-header">
        <div>
          <div className="chart-kicker">
            MARKET DATA / PRICE HISTORY
          </div>

          <h3>
            {ticker.toUpperCase()} Market Data
          </h3>
        </div>

        <div className="chart-price">
          <strong>
            {latestPrice !== undefined
              ? `₹${formatPrice(
                  latestPrice,
                )}`
              : "—"}
          </strong>

          <span
            className={
              isPositive
                ? "chart-up"
                : "chart-down"
            }
          >
            {isPositive ? "+" : ""}
            {change.toFixed(2)}%
          </span>
        </div>
      </div>

      <div className="chart-controls">
        <button
          type="button"
          className={
            range === "1M"
              ? "chart-range active"
              : "chart-range"
          }
          onClick={() => setRange("1M")}
        >
          1M
        </button>

        <button
          type="button"
          className={
            range === "3M"
              ? "chart-range active"
              : "chart-range"
          }
          onClick={() => setRange("3M")}
        >
          3M
        </button>

        <button
          type="button"
          className={
            range === "1Y"
              ? "chart-range active"
              : "chart-range"
          }
          onClick={() => setRange("1Y")}
        >
          1Y
        </button>
      </div>

      {loading && (
        <div className="chart-empty">
          <div>
            <strong>
              Stock chart loading
            </strong>

            <p>
              Fetching {ticker.toUpperCase()} market data...
            </p>
          </div>
        </div>
      )}

      {!loading && error && (
        <div className="chart-empty">
          <div>
            <strong>
              Market data unavailable
            </strong>

            <p>{error}</p>
          </div>
        </div>
      )}

      {!loading &&
        !error &&
        chartData.length > 0 && (
          <>
            <div className="chart-svg-wrap">
              <svg
                className="stock-svg"
                viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                preserveAspectRatio="none"
              >
                <defs>
                  <linearGradient
                    id="stockAreaGradient"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="0%"
                      stopColor="#caff19"
                      stopOpacity="0.22"
                    />

                    <stop
                      offset="100%"
                      stopColor="#caff19"
                      stopOpacity="0"
                    />
                  </linearGradient>
                </defs>

                {[0, 1, 2, 3, 4].map(
                  (row) => {
                    const y =
                      padding +
                      (row / 4) *
                        (chartHeight -
                          padding * 2);

                    return (
                      <line
                        key={row}
                        x1={padding}
                        y1={y}
                        x2={
                          chartWidth -
                          padding
                        }
                        y2={y}
                        className="chart-grid"
                      />
                    );
                  },
                )}

                <path
                  d={areaPath}
                  fill="url(#stockAreaGradient)"
                  stroke="none"
                />

                <path
                  d={linePath}
                  className={
                    isPositive
                      ? "price-line-up"
                      : "price-line-down"
                  }
                  fill="none"
                />

                {chartData.length > 0 && (
                  <circle
                    cx={
                      chartWidth -
                      padding
                    }
                    cy={
                      chartHeight -
                      padding -
                      ((chartData[
                        chartData.length - 1
                      ].close -
                        minPrice) /
                        (maxPrice -
                          minPrice || 1)) *
                        (chartHeight -
                          padding * 2)
                    }
                    r="5"
                    className={
                      isPositive
                        ? "price-dot-up"
                        : "price-dot-down"
                    }
                  />
                )}
              </svg>
            </div>

            <div className="chart-axis">
              <span>
                {formatDate(
                  chartData[0].date,
                )}
              </span>

              <span>
                ₹
                {formatPrice(
                  minPrice,
                )}
              </span>

              <span>
                ₹
                {formatPrice(
                  maxPrice,
                )}
              </span>

              <span>
                {formatDate(
                  chartData[
                    chartData.length - 1
                  ].date,
                )}
              </span>
            </div>

            <div className="chart-source">
              SOURCE:{" "}
              {data?.data_source ??
                "MARKET DATA"}
              {data?.demo
                ? " / FALLBACK DATA"
                : ""}
            </div>
          </>
        )}
    </section>
  );
}