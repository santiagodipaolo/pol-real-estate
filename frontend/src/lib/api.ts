const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

// Currency
export async function getCurrencyRates() {
  return fetchAPI<CurrencyRatesAll>("/currency/rates");
}

export async function getCurrencyHistory(type: string, fromDate?: string, toDate?: string) {
  const params = new URLSearchParams({ type });
  if (fromDate) params.set("from_date", fromDate);
  if (toDate) params.set("to_date", toDate);
  return fetchAPI<CurrencyHistory>(`/currency/rates/history?${params}`);
}

// Barrios
export async function getBarrios() {
  return fetchAPI<BarrioWithStats[]>("/barrios");
}

export async function getBarrio(slug: string) {
  return fetchAPI<BarrioDetail>(`/barrios/${slug}`);
}

export async function getBarrioTrends(slug: string, metric?: string, fromDate?: string, toDate?: string) {
  const params = new URLSearchParams();
  if (metric) params.set("metric", metric);
  if (fromDate) params.set("from_date", fromDate);
  if (toDate) params.set("to_date", toDate);
  return fetchAPI<PriceTrendPoint[]>(`/barrios/${slug}/trends?${params}`);
}

export async function getBarrioRanking(metric?: string, operationType?: string, order?: string) {
  const params = new URLSearchParams();
  if (metric) params.set("metric", metric);
  if (operationType) params.set("operation_type", operationType);
  if (order) params.set("order", order);
  return fetchAPI<BarrioRanking[]>(`/barrios/ranking?${params}`);
}

// Listings
export async function getListings(filters: Record<string, string | number | undefined> = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  return fetchAPI<ListingsPage>(`/listings?${params}`);
}

export async function getListingStats(filters: Record<string, string | number | undefined> = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  return fetchAPI<ListingStats>(`/listings/stats?${params}`);
}

// Analytics
export async function getPriceTrends(operationType?: string, currency?: string) {
  const params = new URLSearchParams();
  if (operationType) params.set("operation_type", operationType);
  if (currency) params.set("currency", currency);
  return fetchAPI<PriceTrendPoint[]>(`/analytics/price-trends?${params}`);
}

export async function getRentalYield() {
  return fetchAPI<RentalYieldBarrio[]>("/analytics/rental-yield");
}

export async function getMarketPulse() {
  return fetchAPI<MarketPulse>("/analytics/market-pulse");
}

export async function getPriceDistribution(barrioId?: number, bins?: number) {
  const params = new URLSearchParams();
  if (barrioId) params.set("barrio_id", String(barrioId));
  if (bins) params.set("bins", String(bins));
  return fetchAPI<PriceDistribution>(`/analytics/price-distribution?${params}`);
}

export async function simulateROI(data: ROISimulationRequest) {
  return fetchAPI<ROISimulationResult>("/analytics/roi-simulation", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Map
export async function getChoropleth(metric?: string, operationType?: string, propertyType?: string) {
  const params = new URLSearchParams();
  if (metric) params.set("metric", metric);
  if (operationType) params.set("operation_type", operationType);
  if (propertyType) params.set("property_type", propertyType);
  return fetchAPI<GeoJSONFeatureCollection>(`/map/choropleth?${params}`);
}

export async function getHeatmapData(operationType?: string, bbox?: string, propertyType?: string) {
  const params = new URLSearchParams();
  if (operationType) params.set("operation_type", operationType);
  if (bbox) params.set("bbox", bbox);
  if (propertyType) params.set("property_type", propertyType);
  return fetchAPI<HeatmapResponse>(`/map/heatmap?${params}`);
}

// Comparador
export async function compareBarrios(slugs: string[]) {
  const params = new URLSearchParams();
  slugs.forEach((s) => params.append("slugs[]", s));
  return fetchAPI<BarrioComparison>(`/barrios/compare?${params}`);
}

// Opportunities
export async function getOpportunities(operationType?: string, threshold?: number, limit?: number) {
  const params = new URLSearchParams();
  if (operationType) params.set("operation_type", operationType);
  if (threshold != null) params.set("threshold", String(threshold));
  if (limit != null) params.set("limit", String(limit));
  return fetchAPI<OpportunitiesResponse>(`/analytics/opportunities?${params}`);
}

// Types
export interface CurrencyRate {
  rate_type: string;
  buy: number | null;
  sell: number | null;
  source: string | null;
  recorded_at: string;
}

export interface CurrencyRatesAll {
  blue: CurrencyRate | null;
  official: CurrencyRate | null;
  mep: CurrencyRate | null;
  ccl: CurrencyRate | null;
  retrieved_at: string;
}

export interface CurrencyHistory {
  rate_type: string;
  points: { date: string; buy: number | null; sell: number | null }[];
}

export interface BarrioWithStats {
  id: number;
  name: string;
  slug: string;
  comuna_id: number;
  comuna_name: string | null;
  listing_count: number | null;
  median_price_usd_m2: number | null;
  avg_price_usd_m2: number | null;
  p25_price_usd_m2: number | null;
  p75_price_usd_m2: number | null;
  avg_days_on_market: number | null;
  rental_yield_estimate: number | null;
}

export interface BarrioDetail extends BarrioWithStats {
  geometry: Record<string, unknown> | null;
  area_km2: number | null;
  centroid_lat: number | null;
  centroid_lon: number | null;
  trends: SnapshotSummary[];
}

export interface SnapshotSummary {
  snapshot_date: string;
  operation_type: string;
  listing_count: number | null;
  median_price_usd_m2: number | null;
  avg_price_usd_m2: number | null;
}

export interface BarrioRanking {
  rank: number;
  barrio_id: number;
  barrio_name: string;
  slug: string;
  value: number | null;
  metric: string;
  listing_count: number | null;
}

export interface ListingItem {
  id: string;
  title: string | null;
  operation_type: string;
  property_type: string;
  price_usd_blue: number | null;
  surface_total_m2: number | null;
  rooms: number | null;
  bedrooms: number | null;
  barrio_name: string | null;
  barrio_slug: string | null;
  price_usd_m2: number | null;
  first_seen_at: string;
  is_active: boolean;
}

export interface ListingsPage {
  items: ListingItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ListingStats {
  total_listings: number;
  active_listings: number;
  median_price_usd_m2: number | null;
  avg_price_usd_m2: number | null;
  avg_days_on_market: number | null;
}

export interface PriceTrendPoint {
  date: string;
  price_m2: number;
  currency: string;
  listing_count: number | null;
}

export interface RentalYieldBarrio {
  barrio_id: number;
  barrio_name: string;
  slug: string;
  median_sale_price_usd_m2: number | null;
  median_rent_usd_m2: number | null;
  gross_rental_yield: number | null;
  net_rental_yield: number | null;
}

export interface MarketPulse {
  active_listings: number;
  new_7d: number;
  removed_7d: number;
  avg_dom: number | null;
  median_price_usd_m2: number | null;
  absorption_rate: number | null;
  snapshot_date: string | null;
}

export interface PriceDistribution {
  bins: number[];
  counts: number[];
  stats: {
    count: number;
    mean: number | null;
    median: number | null;
    p25: number | null;
    p75: number | null;
  };
}

export interface ROISimulationRequest {
  purchase_price_usd: number;
  monthly_rent_usd: number;
  monthly_expenses_usd?: number;
  vacancy_rate?: number;
  annual_appreciation?: number;
  closing_costs_pct?: number;
  holding_period_years?: number;
  discount_rate?: number;
}

export interface ROISimulationResult {
  irr: number | null;
  npv: number | null;
  payback_years: number | null;
  cash_on_cash_return: number | null;
  total_investment: number;
  annual_net_income: number;
  cap_rate: number | null;
  gross_rental_yield: number | null;
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
  metadata?: Record<string, unknown>;
}

export interface GeoJSONFeature {
  type: "Feature";
  geometry: Record<string, unknown>;
  properties: {
    barrio_id: number;
    barrio_name?: string;
    name?: string;
    slug: string;
    metric: string;
    value: number | null;
    metric_value?: number | null;
    color?: string;
    listing_count: number | null;
    [key: string]: unknown;
  };
}

export interface HeatmapResponse {
  points: { lat: number; lon: number; weight: number }[];
  metric: string | null;
  total: number;
}

// Comparador
export interface BarrioComparisonItem {
  barrio_id: number;
  barrio_name: string;
  slug: string;
  comuna_id: number;
  listing_count: number | null;
  median_price_usd_m2: number | null;
  avg_price_usd_m2: number | null;
  p25_price_usd_m2: number | null;
  p75_price_usd_m2: number | null;
  avg_days_on_market: number | null;
  rental_yield_estimate: number | null;
  trends: SnapshotSummary[];
}

export interface BarrioComparison {
  barrios: BarrioComparisonItem[];
  generated_at: string | null;
}

// Opportunities
export interface OpportunityItem {
  id: string;
  title: string | null;
  property_type: string;
  operation_type: string;
  price_usd_blue: number | null;
  surface_total_m2: number | null;
  price_usd_m2: number | null;
  rooms: number | null;
  bedrooms: number | null;
  barrio_name: string;
  barrio_slug: string;
  median_price_usd_m2: number;
  discount_pct: number;
  url: string | null;
}

export interface OpportunitiesResponse {
  items: OpportunityItem[];
  total: number;
  avg_discount_pct: number | null;
  top_barrio: string | null;
}
