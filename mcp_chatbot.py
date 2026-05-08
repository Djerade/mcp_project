from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List
import asyncio
import nest_asyncio
import os
import json
from ollama import Client

nest_asyncio.apply()

load_dotenv()

class MCP_ChatBot:

    def __init__(self):
        # Initialize session and client objects
        self.session: ClientSession = None
        self.ollama = Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
        self.model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.available_tools: List[dict] = []

    @staticmethod
    def _format_tool_result(tool_result_content):
        if isinstance(tool_result_content, (dict, list)):
            return json.dumps(tool_result_content, default=str)
        return str(tool_result_content)

    async def process_query(self, query):
        messages = [{"role": "user", "content": query}]
        while True:
            response = self.ollama.chat(
                model=self.model,
                tools=self.available_tools,
                messages=messages,
            )
            assistant_message = response.get("message", {})
            assistant_text = assistant_message.get("content", "")
            tool_calls = assistant_message.get("tool_calls", []) or []

            if assistant_text:
                print(assistant_text)

            if not tool_calls:
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_text,
                    "tool_calls": tool_calls,
                }
            )

            for tool_call in tool_calls:
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name")
                tool_args = function_info.get("arguments", {}) or {}

                print(f"Calling tool {tool_name} with args {tool_args}")

                result = await self.session.call_tool(tool_name, arguments=tool_args)
                messages.append(
                    {
                        "role": "tool",
                        "name": tool_name,
                        "content": self._format_tool_result(result.content),
                    }
                )

    
    
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
        
                if query.lower() == 'quit':
                    break
                    
                await self.process_query(query)
                print("\n")
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def connect_to_server_and_run(self):
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command="uv",  # Executable
            args=["run", "research_server.py"],  # Optional command line arguments
            env=None,  # Optional environment variables
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                # Initialize the connection
                await session.initialize()
    
                # List available tools
                response = await session.list_tools()
                
                tools = response.tools
                print("\nConnected to server with tools:", [tool.name for tool in tools])
                
                self.available_tools = [{
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema or {
                            "type": "object",
                            "properties": {}
                        }
                    }
                } for tool in response.tools]
    
                await self.chat_loop()


async def main():
    chatbot = MCP_ChatBot()
    await chatbot.connect_to_server_and_run()
  

if __name__ == "__main__":
    asyncio.run(main())