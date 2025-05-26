import { useState, useEffect, useRef } from 'react';

const USER_ID = 'user123';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConvId, setCurrentConvId] = useState('');
  const [messages, setMessages] = useState([]);
  const [newMsg, setNewMsg] = useState('');
  const [generating, setGenerating] = useState(false);
  const abortControllerRef = useRef(null);
  const taskIdRef = useRef(null);

  // 获取会话列表
  useEffect(() => {
    fetch(`/api/conversations?user=${USER_ID}`)
      .then(res => res.json())
      .then(data => setConversations(data.data || []));
  }, []);

  // 加载消息列表
  useEffect(() => {
    if (currentConvId) {
      fetch(`/api/messages?conversation_id=${currentConvId}&user=${USER_ID}`)
        .then(res => res.json())
        .then(data => setMessages((data.data || []).reverse()));
    }
  }, [currentConvId]);

  // 发送消息（流式模式）
  const handleSend = async (e, resendQuery = null) => {
    if (e) e.preventDefault();
    const query = resendQuery || newMsg;
    if (!query.trim()) return;
    setGenerating(true);
    setNewMsg('');
    abortControllerRef.current = new AbortController();
    const response = await fetch('/api/chat-messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user: USER_ID,
        conversation_id: currentConvId,
        query,
        response_mode: 'streaming'
      }),
      signal: abortControllerRef.current.signal
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let answer = '';
    let tempMsg = { id: Date.now(), query, answer: '' };
    setMessages(prev => [...prev, tempMsg]);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      chunk.split('\n').forEach(line => {
        if (line.startsWith('data:')) {
          const event = JSON.parse(line.replace('data: ', '').trim());
          taskIdRef.current = event.task_id || taskIdRef.current;
          if (event.answer) {
            answer += event.answer;
            setMessages(prev => prev.map(m => m.id === tempMsg.id ? { ...m, answer } : m));
          }
        }
      });
    }
    setGenerating(false);
  };

  // 停止生成
  const handleStop = () => {
    if (taskIdRef.current) {
      fetch(`/api/chat-messages/${taskIdRef.current}/stop`, { method: 'POST' });
      abortControllerRef.current?.abort();
      setGenerating(false);
    }
  };

  // 消息反馈
  const handleFeedback = (msgId, rating) => {
    fetch(`/api/messages/${msgId}/feedbacks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating, user: USER_ID })
    }).then(() => {
      setMessages(prev => prev.map(m => m.id === msgId ? { ...m, feedback: { rating } } : m));
    });
  };

  // 重新发送上一消息
  const handleResend = () => {
    const lastQuery = messages[messages.length - 1]?.query;
    if (lastQuery) handleSend(null, lastQuery);
  };

  return (
    <div className="flex h-screen">
      <div className="w-64 border-r p-4 overflow-y-auto">
        <h2 className="text-xl font-bold">会话列表</h2>
        {conversations.map(c => (
          <div key={c.id}>
            <button onClick={() => setCurrentConvId(c.id)} className="hover:bg-gray-100 w-full text-left p-2 rounded">
              {c.name || '新对话'}
            </button>
          </div>
        ))}
      </div>
      <div className="flex-1 flex flex-col p-4 overflow-y-auto">
        <div className="flex-1">
          {messages.map(m => (
            <div key={m.id}>
              <div className="text-right text-blue-500">{m.query}</div>
              <div className="text-left bg-gray-100 rounded p-2 my-1">
                {m.answer}
                <button onClick={() => handleFeedback(m.id, m.feedback?.rating === 'like' ? null : 'like')}>
                  {m.feedback?.rating === 'like' ? '👍' : '👍🏻'}
                </button>
                <button onClick={() => handleFeedback(m.id, m.feedback?.rating === 'dislike' ? null : 'dislike')}>
                  {m.feedback?.rating === 'dislike' ? '👎' : '👎🏻'}
                </button>
              </div>
            </div>
          ))}
        </div>
        {generating ? (
          <button onClick={handleStop} className="bg-red-500 text-white px-4 py-2 rounded">停止</button>
        ) : (
          <>
            <form onSubmit={handleSend} className="flex mt-2">
              <input value={newMsg} onChange={e => setNewMsg(e.target.value)} className="flex-1 border p-2 rounded" />
              <button className="bg-blue-500 text-white px-4 py-2 rounded ml-2">发送</button>
            </form>
            {messages.length > 0 && (
              <button onClick={handleResend} className="mt-2 text-sm text-blue-600">重新生成</button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default App;
