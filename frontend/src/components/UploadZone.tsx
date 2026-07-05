import { useEffect, useState } from 'react';
import { Alert, Button, List, Segmented, Upload, message } from 'antd';
import { Database, Inbox, RefreshCw, UploadCloud } from 'lucide-react';
import type { UploadFile, UploadProps } from 'antd';
import { getKnowledge, uploadDocument } from '../services/api';
import type { KnowledgeResponse } from '../types';

interface UploadZoneProps {
  onDocumentUploaded: (documentId: string) => void;
  currentDocumentIds: string[];
  isAnalyzing: boolean;
  refreshKey: number;
}

export function UploadZone({ onDocumentUploaded, currentDocumentIds, isAnalyzing, refreshKey }: UploadZoneProps) {
  const [loading, setLoading] = useState(false);
  const [knowledge, setKnowledge] = useState<KnowledgeResponse | null>(null);
  const [view, setView] = useState<'current' | 'history'>('current');
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  const refreshKnowledge = async () => {
    try {
      setKnowledge(await getKnowledge());
    } catch {
      setKnowledge(null);
    }
  };

  useEffect(() => {
    void refreshKnowledge();
  }, [refreshKey]);

  useEffect(() => {
    if (isAnalyzing) {
      setFileList([]);
      setView('current');
    }
  }, [isAnalyzing]);

  const props: UploadProps = {
    multiple: false,
    disabled: isAnalyzing,
    showUploadList: !isAnalyzing,
    fileList,
    onChange: ({ fileList: next }) => setFileList(next),
    beforeUpload: async (file) => {
      if (isAnalyzing) return false;
      setLoading(true);
      try {
        const result = await uploadDocument(file);
        if (result.document_id) onDocumentUploaded(result.document_id);
        setView('current');
        const label = result.status === 'duplicate' ? '文档已存在，已加入本次分析范围' : '任务已创建';
        message.success(
          `${label}：${result.company || '未知竞品'} / ${result.category || '资料'}，保存到 ${result.stored_path}`,
        );
        await refreshKnowledge();
      } catch (error) {
        message.error(error instanceof Error ? error.message : '上传失败');
      } finally {
        setLoading(false);
        setFileList([]);
      }
      return false;
    },
  };

  const currentSet = new Set(currentDocumentIds);
  const registry = knowledge?.registry ?? [];
  const currentDocs = registry.filter((item) => currentSet.has(item.document_id));
  const historyDocs = registry.filter((item) => !currentSet.has(item.document_id));
  const visibleDocs = view === 'current' ? currentDocs : historyDocs;

  return (
    <section className="panel upload-panel">
      <div className="panel-title">
        <Inbox size={18} />
        <span>资料上传</span>
      </div>
      <Alert
        className="upload-hint"
        type="info"
        showIcon
        message="上传竞品资料"
        description="支持官网介绍、价格页、财报、白皮书、用户评论等文档。系统会自动识别竞品名称和资料类型，并只在本次上传的文档中检索。"
      />
      <Upload.Dragger {...props} className="dropzone">
        <UploadCloud size={34} />
        <p>{isAnalyzing ? '正在分析，本轮上传已锁定' : '拖入或选择 txt、md、pdf、docx 资料'}</p>
        <Button disabled={isAnalyzing} loading={loading} type="primary" icon={<UploadCloud size={16} />}>
          上传并解析
        </Button>
      </Upload.Dragger>
      <div className="knowledge-summary">
        <div className="panel-title compact-title">
          <Database size={16} />
          <span>知识库文件</span>
          <Button size="small" icon={<RefreshCw size={14} />} onClick={() => void refreshKnowledge()} />
        </div>
        <Segmented
          block
          value={view}
          onChange={(value) => setView(value as 'current' | 'history')}
          options={[
            { label: `本次提交 ${currentDocs.length}`, value: 'current' },
            { label: `历史文件 ${historyDocs.length}`, value: 'history' },
          ]}
        />
        <List
          size="small"
          className="knowledge-list"
          dataSource={visibleDocs}
          locale={{ emptyText: view === 'current' ? '本次尚未提交文档' : '暂无历史文件' }}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={`${item.company || '未知竞品'} · ${item.source_filename || item.document_id}`}
                description={`${item.category || '资料'} · ${item.stored_path || ''} · 切片 ${item.chunk_count ?? 0}`}
              />
            </List.Item>
          )}
        />
      </div>
    </section>
  );
}
