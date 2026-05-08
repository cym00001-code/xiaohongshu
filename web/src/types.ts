export type TimeWindow = "24h" | "7d";

export type TrendMetric = {
  likes: number;
  comments: number;
  saves: number;
  shares: number;
  views: number;
  stars: number;
  score: number;
};

export type TrendItem = {
  platform: string;
  id: string;
  entity: string;
  title: string;
  summary?: string | null;
  url?: string | null;
  author?: string | null;
  published_at?: string | null;
  metrics: TrendMetric;
  tags: string[];
  sentiment: number;
  heat: number;
  raw: Record<string, unknown>;
};

export type TrendPoint = {
  label: string;
  value: number;
};

export type ProviderStatus = {
  platform: string;
  label: string;
  enabled: boolean;
  refresh_minutes: number;
  last_success_at?: string | null;
  last_error?: string | null;
  notes?: string | null;
};

export type GalaxyInfo = {
  id: string;
  label: string;
  description: string;
  color: string;
};

export type TrendNode = {
  entity: string;
  label: string;
  galaxy: string;
  galaxy_label: string;
  color: string;
  heat: number;
  growth: number;
  sentiment: number;
  item_count: number;
  platform_distribution: Record<string, number>;
  heat_breakdown: Record<string, number>;
  trend: TrendPoint[];
  top_items: TrendItem[];
  summary: string;
};

export type TrendSnapshot = {
  generated_at: string;
  window: TimeWindow;
  refresh_minutes: number;
  galaxies: GalaxyInfo[];
  nodes: TrendNode[];
  providers: ProviderStatus[];
};
