import React, { createContext, useContext, useEffect, useState } from 'react';

const WebSocketContext = createContext({});


export const WebSocketProvider = ({ children }) => {
  const [websocket1,setWs1] = useState(null);

  useEffect(() => {
    const connect = () => {
      const ws1 = new WebSocket('ws://220.67.127.145:8000/ws/w_inter/');

      ws1.onopen = () => {
        console.log('winter Connected');
      };

      // 연결이 끊어진 경우
      ws1.onclose = (e) => {
        console.log('winter Disconnected');
        console.log('winter Reconnected')
        setTimeout(() => {
          connect();
        }, 2000 ); // 2초 후 재연결 시도
      };

      // 에러처리
      ws1.onerror = (err) => {
        setTimeout(() => {
          connect();
        }, 2000 ); // 2초 후 재연결 시도
      };
      setWs1(ws1)
    };

    // 첫 연결 시도
    connect();
    return () => {
    };
  }, []);

  return (
    <WebSocketContext.Provider value={{ websocket1 }}>
      {children}
    </WebSocketContext.Provider>
  );
};

// Custom hook to use the websocket context
export const useWebSocket = () => useContext(WebSocketContext);