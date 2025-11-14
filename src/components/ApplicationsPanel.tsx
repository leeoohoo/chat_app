import React, { useEffect } from 'react';
import { useChatStoreFromContext } from '../lib/store/ChatStoreContext';
import { useChatStore } from '../lib/store';

const ApplicationsPanel: React.FC = () => {
  let storeData: any;
  try {
    storeData = useChatStoreFromContext();
  } catch (e) {
    storeData = useChatStore();
  }

  const {
    applications,
    selectedApplicationId,
    loadApplications,
    setSelectedApplication,
  } = storeData;

  useEffect(() => {
    loadApplications?.();
  }, [loadApplications]);

  return (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-500" />
          <span className="text-sm font-medium text-foreground">应用列表</span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            className="px-2 py-1 text-xs rounded bg-muted hover:bg-accent"
            onClick={() => setSelectedApplication?.(null)}
          >清除选择</button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {applications?.map((app: any) => (
          <button
            key={app.id}
            className={`w-full text-left p-2 rounded border transition-colors flex items-center space-x-3 ${selectedApplicationId === app.id ? 'border-blue-600 bg-blue-50 dark:bg-blue-950' : 'border-border hover:bg-muted'}`}
            onClick={() => setSelectedApplication?.(app.id)}
            title={app.url || ''}
          >
            <div className="w-8 h-8 rounded bg-blue-500/15 flex items-center justify-center overflow-hidden">
              {app.iconUrl ? (
                <img src={app.iconUrl} alt={app.name} className="w-8 h-8 object-cover" />
              ) : (
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-500" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-foreground truncate">{app.name}</div>
              {app.url && <div className="text-xs text-muted-foreground truncate">{app.url}</div>}
            </div>
            {selectedApplicationId === app.id && (
              <span className="px-2 py-0.5 text-[10px] rounded-full bg-green-600 text-white">已选择</span>
            )}
          </button>
        ))}
        {(applications?.length ?? 0) === 0 && (
          <div className="text-xs text-muted-foreground p-2">暂无应用，点击右上角按钮进行管理。</div>
        )}
      </div>
    </div>
  );
};

export default ApplicationsPanel;