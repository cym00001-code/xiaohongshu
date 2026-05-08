import type { TrendSnapshot } from "./types";

const now = new Date().toISOString();

export const fallbackSnapshot: TrendSnapshot = {
  generated_at: now,
  window: "24h",
  refresh_minutes: 30,
  galaxies: [
    {
      id: "global_models",
      label: "全球大模型星系",
      description: "主流模型与助手的讨论热度。",
      color: "#31b7ff"
    },
    {
      id: "china_ai",
      label: "中国国内 AI 星系",
      description: "国内 AI 产品与模型信号。",
      color: "#ffb44a"
    },
    {
      id: "frontier_ai",
      label: "AI 前沿星系",
      description: "视频生成、多模态与 Agent。",
      color: "#65e28b"
    },
    {
      id: "tooling",
      label: "AI 工具生态星系",
      description: "开发、搜索与办公工具。",
      color: "#b886ff"
    }
  ],
  providers: [
    {
      platform: "github",
      label: "GitHub",
      enabled: true,
      refresh_minutes: 30,
      notes: "演示数据"
    }
  ],
  nodes: [
    {
      entity: "chatgpt",
      label: "ChatGPT",
      galaxy: "global_models",
      galaxy_label: "全球大模型星系",
      color: "#31b7ff",
      heat: 278,
      growth: 42,
      sentiment: 0.68,
      item_count: 3,
      platform_distribution: { github: 1, reddit: 1, justone: 1 },
      heat_breakdown: { mentions: 22, engagement: 63, freshness: 15 },
      trend: [
        { label: "24小时前", value: 18 },
        { label: "20小时前", value: 28 },
        { label: "16小时前", value: 44 },
        { label: "12小时前", value: 52 },
        { label: "8小时前", value: 71 },
        { label: "4小时前", value: 86 },
        { label: "现在", value: 108 }
      ],
      top_items: [
        {
          platform: "github",
          id: "demo-chatgpt",
          entity: "chatgpt",
          title: "GPT-4o Agent 更新引发开发者讨论",
          summary: "工具链与 Agent 工作流关注上升。",
          url: "https://example.com",
          author: "GitHub 信号源",
          published_at: now,
          metrics: { likes: 520, comments: 74, saves: 180, shares: 55, views: 0, stars: 0, score: 594 },
          tags: ["ChatGPT"],
          sentiment: 0.68,
          heat: 120,
          raw: {}
        }
      ],
      summary: "ChatGPT 在全球大模型星系中保持最高热度，增长由 Agent 与工作流场景推动。"
    },
    {
      entity: "deepseek",
      label: "DeepSeek",
      galaxy: "global_models",
      galaxy_label: "全球大模型星系",
      color: "#2c8dff",
      heat: 211,
      growth: 31,
      sentiment: 0.58,
      item_count: 2,
      platform_distribution: { hackernews: 1, justone: 1 },
      heat_breakdown: { mentions: 26, engagement: 58, freshness: 16 },
      trend: [
        { label: "24小时前", value: 12 },
        { label: "20小时前", value: 21 },
        { label: "16小时前", value: 34 },
        { label: "12小时前", value: 44 },
        { label: "8小时前", value: 59 },
        { label: "4小时前", value: 67 },
        { label: "现在", value: 80 }
      ],
      top_items: [],
      summary: "DeepSeek 的部署和办公自动化教程仍然有明显传播。"
    }
  ]
};
