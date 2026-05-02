import React, { useEffect, useRef, useState } from 'react';

const AutoSizer = ({ children }) => {
  const [size, setSize] = useState({ height: 0, width: 0 });
  const ref = useRef(null);

  useEffect(() => {
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setSize({
          height: entry.contentRect.height,
          width: entry.contentRect.width,
        });
      }
    });

    if (ref.current) {
      observer.observe(ref.current);
      const rect = ref.current.getBoundingClientRect();
      setSize({ height: rect.height, width: rect.width });
    }

    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} style={{ height: '100%', width: '100%' }}>
      {children(size)}
    </div>
  );
};

export default AutoSizer;
