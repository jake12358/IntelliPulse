import { useRef, useState } from 'react';
import { Button, Collapse, Input, Space, Tag, message } from 'antd';
import { Send, Square } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { AnalysisResult, SourcePreview } from '../types';

interface ChatWindowProps {
  onAnalysis: (result: AnalysisResult) => void;
  documentIds: string[];
  onAnalysisStart: (query: string) => void;
  onAnalysisComplete: () => void;
}

function cleanMarkdown(value: string) {
  return value.replace(/<br\s*\/?>/gi, '\n').replace(/<\/?[^>]+>/g, '');
}

export function ChatWindow({ onAnalysis, documentIds, onAnalysisStart, onAnalysisComplete }: ChatWindowProps) {
  const [query, setQuery] = useState('对比飞书和钉钉');
  const [messages, setMessages] = useState<string[]>([]);
  const [sources, setSources] = useState<SourcePreview[]>([]);
  const sourceRef = useRef<EventSource | null>(null);

  const start = () => {
    if (documentIds.length === 0) {
      message.warning('请先上传本次要分析的竞品文档');
      return;
    }
    sourceRef.current?.close();
    setMessages([]);
    setSources([]);
    onAnalysisStart(query);
    const params = new URLSearchParams({
      query,
      document_ids: documentIds.join(','),
    });
    const source = new EventSource(`/api/chat/stream?${params.toString()}`);
    sourceRef.current = source;
    source.addEventListener('start', () => setMessages((items) => [...items, '开始分析...']));
    source.addEventListener('retriever', (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      setSources(data.sources ?? []);
      setMessages((items) => [...items, `完成资料检索，命中 ${data.sources?.length ?? 0} 个切片`]);
    });
    source.addEventListener('comparator', () => setMessages((items) => [...items, '生成对比矩阵']));
    source.addEventListener('sentiment', () => setMessages((items) => [...items, '完成情感分析']));
    source.addEventListener('reporter', (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      if (data.report) {
        const result = {
          report: cleanMarkdown(data.report),
          radar: data.radar ?? [],
          company_radars: data.company_radars ?? {},
          matrix: data.matrix ?? {},
          sentiment: data.sentiment ?? {},
          sources: data.sources ?? [],
        };
        onAnalysis(result);
        setSources(result.sources);
        setMessages((items) => [...items, result.report]);
      }
    });
    source.addEventListener('done', () => {
      setMessages((items) => [...items, '分析完成']);
      source.close();
      onAnalysisComplete();
    });
    source.addEventListener('error', () => {
      setMessages((items) => [...items, '分析连接中断，请检查后端服务后重试']);
      source.close();
      onAnalysisComplete();
    });
  };

  const stop = () => {
    sourceRef.current?.close();
    sourceRef.current = null;
  };

  return (
    <section className="panel chat-panel">
      <div className="panel-title">
        <Send size={18} />
        <span>流式分析</span>
      </div>
      <Space.Compact block>
        <Input value={query} onChange={(event) => setQuery(event.target.value)} onPressEnter={start} />
        <Button type="primary" icon={<Send size={16} />} onClick={start} />
        <Button icon={<Square size={16} />} onClick={stop} />
      </Space.Compact>
      <div className="scope-line">
        当前检索范围：{documentIds.length > 0 ? `本次提交的 ${documentIds.length} 份去重文档` : '未选择文档'}
      </div>
      <div className="message-list">
        {sources.length > 0 && (
          <Collapse
            size="small"
            className="source-collapse"
            items={[
              {
                key: 'sources',
                label: `本次引用资料切片 ${sources.length} 个`,
                children: (
                  <div className="source-list">
                    {sources.map((source) => (
                      <div className="source-item" key={source.id}>
                        <Space wrap>
                          <Tag color="blue">{source.company || '未知公司'}</Tag>
                          <span>{source.source_filename || source.stored_path}</span>
                        </Space>
                        <p>{source.preview}</p>
                      </div>
                    ))}
                  </div>
                ),
              },
            ]}
          />
        )}
        {messages.map((message, index) => (
          <div className="message" key={`${index}-${message.slice(0, 12)}`}>
            <ReactMarkdown>{message}</ReactMarkdown>
          </div>
        ))}
      </div>
    </section>
  );
}
