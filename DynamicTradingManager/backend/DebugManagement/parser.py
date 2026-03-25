import os
import re
from typing import List, Dict, Optional, Any

class LogParser:
    def __init__(self, console_path: str):
        self.console_path = console_path
        # Regex to parse PZ log lines: LOG  : Lua          f:0, t:1773241665869> [DynamicTrading] ...
        self.log_pattern = re.compile(r"LOG\s+:\s+(?P<type>\w+)\s+f:\d+, t:(?P<timestamp>\d+)>\s+(?P<message>.*)")
        # Regex for DT standardized logs: [Version/System/Specific] message
        self.dt_pattern = re.compile(r"^\[(?P<version>[^/\]]+)/(?P<system>[^/\]]+)/(?P<specific>[^/\]]+)\]\s+(?P<msg>.*)")

    def get_last_n_lines(self, lines: int = 500, only_dt: bool = False, levels: Optional[List[str]] = None, systems: Optional[List[str]] = None) -> Dict[str, Any]:
        """Reads the last N lines from console.txt and returns them with the next byte offset."""
        if not os.path.exists(self.console_path):
            return {
                "logs": [{"type": "Error", "message": f"Log file not found at {self.console_path}", "timestamp": "0"}],
                "next_offset": 0
            }

        results = []
        try:
            with open(self.console_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                
                buffer_size = 16384 # Larger buffer for efficiency
                pos = file_size
                buffer = b""

                # Read backwards to find enough lines
                while len(results) < lines and pos > 0:
                    chunk_size = min(pos, buffer_size)
                    pos -= chunk_size
                    f.seek(pos)
                    chunk = f.read(chunk_size)
                    buffer = chunk + buffer
                    
                    # Process lines in current buffer
                    temp_lines = buffer.decode("utf-8", errors="replace").splitlines()
                    # If we didn't read to the start of the file, the first line might be partial
                    if pos > 0 and len(temp_lines) > 0:
                        partial = temp_lines.pop(0)
                        buffer = partial.encode("utf-8")
                    else:
                        buffer = b""

                    # Add lines from end
                    for line in reversed(temp_lines):
                        if not line.strip(): continue
                        parsed = self._parse_line(line) or {"type": "General", "message": line, "timestamp": "0"}
                        
                        # Apply DT filter
                        is_dt = "dt_meta" in parsed or "[DynamicTrading]" in parsed["message"]
                        if only_dt and not is_dt:
                            continue
                            
                        # Apply Level filter
                        if levels and parsed["type"] not in levels:
                            continue
                            
                        # Apply DT System filter
                        if systems:
                            dt_system = parsed.get("dt_meta", {}).get("system")
                            if dt_system not in systems:
                                continue
                                
                        results.append(parsed)
                        if len(results) >= lines: break

            return {
                "logs": list(reversed(results)),
                "next_offset": file_size
            }
            
        except Exception as e:
            return {
                "logs": [{"type": "Error", "message": f"Failed to read logs: {str(e)}", "timestamp": "0"}],
                "next_offset": 0
            }

    def _parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        match = self.log_pattern.match(line)
        if match:
            data = match.groupdict()
            message = data["message"].strip()
            
            result = {
                "type": data["type"],
                "timestamp": data["timestamp"],
                "message": message
            }
            
            # Check if it's a standardized DT log
            dt_match = self.dt_pattern.match(message)
            if dt_match:
                result["dt_meta"] = dt_match.groupdict()
                # If it's standardized, we can extract the base message
                result["message"] = result["dt_meta"].pop("msg").strip()
                
            return result
        return None

    def get_new_lines(self, from_offset: int, only_dt: bool = False, levels: Optional[List[str]] = None, systems: Optional[List[str]] = None) -> Dict[str, Any]:
        """Reads new lines starting from a specific byte offset."""
        if not os.path.exists(self.console_path):
            return {"logs": [], "next_offset": from_offset}

        results = []
        try:
            with open(self.console_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                
                if from_offset >= file_size:
                    return {"logs": [], "next_offset": file_size}

                f.seek(from_offset)
                content = f.read(file_size - from_offset).decode("utf-8", errors="replace")
                
                for line in content.splitlines():
                    if not line.strip(): continue
                    parsed = self._parse_line(line) or {"type": "General", "message": line, "timestamp": "0"}
                    
                    # Apply DT filter
                    is_dt = "dt_meta" in parsed or "[DynamicTrading]" in parsed["message"]
                    if only_dt and not is_dt:
                        continue
                    
                    # Apply Level filter
                    if levels and parsed["type"] not in levels:
                        continue
                        
                    # Apply DT System filter
                    if systems:
                        dt_system = parsed.get("dt_meta", {}).get("system")
                        if dt_system not in systems:
                            continue
                    
                    results.append(parsed)

                return {
                    "logs": results,
                    "next_offset": file_size
                }
        except Exception as e:
            return {"logs": [{"type": "Error", "message": str(e), "timestamp": "0"}], "next_offset": from_offset}
