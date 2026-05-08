import { ExternalLink, Flame, Radio, TrendingUp, X } from "lucide-react";
import type { ReactNode } from "react";
import type { TrendNode } from "../types";
import { compactNumber, formatPercent, formatSentiment, platformLabel, sentimentText } from "../format";

type DetailPanelProps = {
  node: TrendNode | null;
  onClose: () => void;
};

export function DetailPanel({ node, onClose }: DetailPanelProps) {
  if (!node) {
    return (
      <aside className="detail-panel empty-state" aria-label="趋势详情">
        <Radio size={28} />
        <strong>选择一个星体</strong>
        <span>点击任意 AI 节点，查看热度拆解、平台分布和代表信号。</span>
      </aside>
    );
  }

  const maxTrend = Math.max(...node.trend.map((point) => point.value), 1);
  const platformTotal = Math.max(Object.values(node.platform_distribution).reduce((sum, count) => sum + count, 0), 1);

  return (
    <aside className="detail-panel" aria-label={`${node.label} 趋势详情`}>
      <div className="detail-head">
        <div className="node-orb" style={{ background: node.color }} />
        <div>
          <span>{node.galaxy_label}</span>
          <h2>{node.label}</h2>
        </div>
        <button className="icon-button" onClick={onClose} aria-label="关闭详情">
          <X size={18} />
        </button>
      </div>

      <div className="metric-grid">
        <Metric icon={<Flame size={16} />} label="热度" value={compactNumber(node.heat)} />
        <Metric icon={<TrendingUp size={16} />} label="增长" value={formatPercent(node.growth, true)} tone={node.growth >= 0 ? "good" : "bad"} />
        <Metric label="口碑" value={formatSentiment(node.sentiment)} helper={sentimentText(node.sentiment)} tone={node.sentiment >= 0.35 ? "good" : node.sentiment < -0.18 ? "bad" : "neutral"} />
      </div>

      <section>
        <div className="panel-title">热度拆解</div>
        <div className="heat-stack" aria-label="热度拆解比例">
          {Object.entries(node.heat_breakdown).map(([key, value]) => (
            <span key={key} className={`heat-${key}`} style={{ width: `${value}%` }} />
          ))}
        </div>
        <div className="breakdown-list">
          <span>提及 {Math.round(node.heat_breakdown.mentions ?? 0)}%</span>
          <span>互动 {Math.round(node.heat_breakdown.engagement ?? 0)}%</span>
          <span>新鲜度 {Math.round(node.heat_breakdown.freshness ?? 0)}%</span>
        </div>
      </section>

      <section>
        <div className="panel-title">平台分布</div>
        <div className="platform-bars">
          {Object.entries(node.platform_distribution).map(([platform, count]) => (
            <div key={platform}>
              <span>{platformLabel(platform)}</span>
              <div>
                <i style={{ width: `${(count / platformTotal) * 100}%` }} />
              </div>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="panel-title">趋势曲线</div>
        <div className="sparkline">
          {node.trend.map((point) => (
            <span key={point.label} style={{ height: `${Math.max(12, (point.value / maxTrend) * 100)}%` }} title={`${point.label}：${compactNumber(point.value)}`} />
          ))}
        </div>
        <div className="spark-labels">
          <span>{node.trend[0]?.label}</span>
          <span>{node.trend[node.trend.length - 1]?.label}</span>
        </div>
      </section>

      <section className="top-signals">
        <div className="panel-title">代表信号</div>
        {node.top_items.length === 0 ? (
          <p className="muted">当前窗口没有可展开的代表信号。</p>
        ) : (
          node.top_items.map((item, index) => (
            <a key={`${item.platform}-${item.id}`} href={item.url ?? "#"} target="_blank" rel="noreferrer">
              <span>{index + 1}</span>
              <div>
                <strong>{item.title}</strong>
                <small>{platformLabel(item.platform)} · 热度 {compactNumber(item.heat)}</small>
              </div>
              <ExternalLink size={14} />
            </a>
          ))
        )}
      </section>

      <section>
        <div className="panel-title">摘要</div>
        <p className="summary-text">{node.summary}</p>
      </section>
    </aside>
  );
}

function Metric({
  icon,
  label,
  value,
  helper,
  tone
}: {
  icon?: ReactNode;
  label: string;
  value: string;
  helper?: string;
  tone?: "good" | "bad" | "neutral";
}) {
  return (
    <div className={`metric-card ${tone ? `tone-${tone}` : ""}`}>
      <span>
        {icon}
        {label}
      </span>
      <strong>{value}</strong>
      {helper && <small>{helper}</small>}
    </div>
  );
}
