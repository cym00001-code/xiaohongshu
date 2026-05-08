const platformLabels: Record<string, string> = {
  justone: "小红书",
  xhs: "小红书",
  hackernews: "Hacker News",
  github: "GitHub",
  producthunt: "Product Hunt",
  reddit: "Reddit",
  weibo: "微博",
  x: "X",
  demo: "演示数据"
};

export function platformLabel(platform: string): string {
  return platformLabels[platform] ?? platform;
}

export function formatPercent(value: number, signed = false): string {
  const prefix = signed && value > 0 ? "+" : "";
  return `${prefix}${Math.round(value)}%`;
}

export function formatSentiment(value: number): string {
  return `${Math.round(((value + 1) / 2) * 100)}%`;
}

export function sentimentText(value: number): string {
  if (value > 0.35) return "正向";
  if (value < -0.18) return "谨慎";
  return "中性";
}

export function compactNumber(value: number): string {
  if (value >= 10000) return `${(value / 10000).toFixed(1)}万`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}千`;
  return `${Math.round(value)}`;
}
