import { useEffect, useState } from 'react';
import { Button, Empty, Spin, Table, message } from 'antd';
import { Select } from 'antd';
import { RefreshCw, Radar } from 'lucide-react';
import { getReport } from '../services/api';
import type { AnalysisResult, ReportResponse } from '../types';

interface DashboardProps {
  analysis: AnalysisResult | null;
  documentIds: string[];
  query: string;
  isAnalyzing: boolean;
}

export function Dashboard({ analysis, documentIds, query, isAnalyzing }: DashboardProps) {
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [selectedCompany, setSelectedCompany] = useState<string>('');
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    if (documentIds.length === 0) {
      setReport(null);
      message.warning('请先上传本次要分析的文档');
      return;
    }
    setRefreshing(true);
    try {
      setReport(await getReport('current-session', documentIds, query));
      setSelectedCompany('');
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (analysis) {
      setReport(null);
      setSelectedCompany('');
    }
  }, [analysis]);

  useEffect(() => {
    if (isAnalyzing) {
      setReport(null);
      setSelectedCompany('');
    }
  }, [isAnalyzing]);

  const active = analysis ?? report;
  const companyRadars = active?.company_radars ?? {};
  const companyOptions = Object.keys(companyRadars);
  const activeCompany = selectedCompany || companyOptions[0] || '';
  const radar = activeCompany ? companyRadars[activeCompany] ?? [] : active?.radar ?? [];
  const points = radar.map((item, index) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / Math.max(radar.length, 1);
    const radius = 82 * (Number(item.value) / 100);
    return {
      x: 110 + Math.cos(angle) * radius,
      y: 110 + Math.sin(angle) * radius,
      labelX: 110 + Math.cos(angle) * 102,
      labelY: 110 + Math.sin(angle) * 102,
      item,
    };
  });
  const polygon = points.map((point) => `${point.x},${point.y}`).join(' ');
  const gridLevels = [20, 40, 60, 80, 100].map((value) =>
    radar
      .map((_, index) => {
        const angle = -Math.PI / 2 + (index * 2 * Math.PI) / Math.max(radar.length, 1);
        const radius = 82 * (value / 100);
        return `${110 + Math.cos(angle) * radius},${110 + Math.sin(angle) * radius}`;
      })
      .join(' '),
  );

  return (
    <section className="panel dashboard-panel">
      <div className="panel-title">
        <Radar size={18} />
        <span>竞争力仪表盘</span>
        {companyOptions.length > 0 && (
          <Select
            size="small"
            className="company-select"
            value={activeCompany}
            onChange={setSelectedCompany}
            options={companyOptions.map((company) => ({ label: company, value: company }))}
          />
        )}
        <Button size="small" loading={refreshing} icon={<RefreshCw size={14} />} onClick={load} />
      </div>
      {isAnalyzing && (
        <div className="dashboard-loading">
          <Spin />
          <span>等待本次分析结果...</span>
        </div>
      )}
      <div className="radar-chart">
        {!isAnalyzing && radar.length > 0 ? (
          <svg viewBox="0 0 220 220" role="img" aria-label={`${activeCompany || '竞品'}雷达图`}>
            {gridLevels.map((level) => (
              <polygon key={level} points={level} className="radar-grid" />
            ))}
            {points.map((point) => (
              <line key={`${point.item.metric}-axis`} x1="110" y1="110" x2={point.labelX} y2={point.labelY} className="radar-axis" />
            ))}
            <polygon points={polygon} className="radar-area" />
            {points.map((point) => (
              <g key={point.item.metric}>
                <circle cx={point.x} cy={point.y} r="3.5" className="radar-dot" />
                <text x={point.labelX} y={point.labelY} textAnchor="middle" dominantBaseline="middle" className="radar-label">
                  {point.item.metric}
                </text>
              </g>
            ))}
          </svg>
        ) : !isAnalyzing ? (
          <Empty description="运行一次流式分析后显示雷达图" />
        ) : null}
      </div>
      {activeCompany && radar.length > 0 && (
        <div className="radar-reasons">
          {radar.map((item) => (
            <p key={item.metric}>
              <strong>{item.metric}</strong> {item.value}：{item.reason || '规则评分'}
            </p>
          ))}
        </div>
      )}
      <Table
        size="small"
        pagination={false}
        locale={{ emptyText: <Empty description="运行一次流式分析后显示结果" /> }}
        dataSource={active?.matrix.rows?.map((row, index) => ({ key: index, ...row })) ?? []}
        columns={[
          { title: '公司', dataIndex: 'company' },
          { title: '价格', dataIndex: 'pricing' },
          { title: '目标客户', dataIndex: 'target_customers' },
          { title: '优势', dataIndex: 'advantages' },
        ]}
      />
    </section>
  );
}
