import json
import sys
from typing import List

from pydantic import BaseModel

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool
except Exception as e:
    print("Import error:", e)
    sys.exit(1)


class BacktestProbe(BaseModel):
    code: str
    symbols: List[str]


@tool(args_schema=BacktestProbe)
def backtest_strategy(code: str, symbols: List[str]):
    """Probe tool. Returns the args it received."""
    return {"received": {"code_len": len(code), "symbols": symbols}}


def main():
    llm = ChatOpenAI(
        model="openai/gpt-oss-20b",
        openai_api_key="sk-ignored",
        openai_api_base="http://localhost:1234/v1",
        streaming=True,
    )
    llm_tools = llm.bind_tools([backtest_strategy])

    messages = [
        {"role": "system", "content": "You can call tools to execute backtests."},
        {
            "role": "user",
            "content": "Call backtest_strategy with code='class X: pass' and symbols=['AAPL','MSFT'].",
        },
    ]

    print("--- INVOKE (non-stream) ---")
    try:
        resp = llm_tools.invoke(messages)
        print("type:", type(resp))
        print("content:", getattr(resp, "content", None))
        print("tool_calls:", getattr(resp, "tool_calls", None))
        print("additional_kwargs:", getattr(resp, "additional_kwargs", None))
    except Exception as e:
        print("invoke error:", e)

    print("\n--- STREAM ---")
    try:
        for i, chunk in enumerate(llm_tools.stream(messages)):
            if i > 200:
                break
            name = getattr(chunk, "name", None)
            tool_calls = getattr(chunk, "tool_calls", None)
            content = getattr(chunk, "content", None)
            addl = getattr(chunk, "additional_kwargs", None)
            if tool_calls or name or (content and str(content).strip()):
                print(f"chunk[{i}] type={type(chunk)} name={name} content={repr(content)[:120]} tool_calls={tool_calls} addl={addl}")
    except Exception as e:
        print("stream error:", e)


if __name__ == "__main__":
    main()
