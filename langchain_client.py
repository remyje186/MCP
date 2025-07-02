import asyncio
import nest_asyncio
from langchain_ollama import ChatOllama
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.tools import Tool
import httpx

nest_asyncio.apply()

REACT_TEMPLATE = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: {tool_names}
Action Input: the SQL query to execute
Observation: the result of the action
Thought: I now know the final answer
Final Answer: A summary of the result

For example:
Question: add John Doe 30 year old Engineer
Thought: I need to add a new person to the database
Action: add_data
Action Input: INSERT INTO people (name, age, profession) VALUES ('John Doe', 30, 'Engineer')
Observation: Data added successfully
Thought: I have successfully added the person
Final Answer: Added John Doe to people

Question: create a car table
Thought: I need to create a new table called car
Action: create_table
Action Input: CREATE TABLE IF NOT EXISTS car (id INTEGER PRIMARY KEY, make TEXT, year INTEGER)
Observation: Table created
Thought: Table was created successfully
Final Answer: car table created

Question: show all car records
Thought: I need to retrieve all records from the car table
Action: read_data
Action Input: SELECT * FROM car
Observation: [Formatted table with records]
Thought: I have retrieved all records
Final Answer: [Formatted car table]

Begin!

Question: {input}
{agent_scratchpad}"""

class LangchainMCPClient:
    def __init__(self, mcp_server_url="http://127.0.0.1:8000"):
        self.llm = ChatOllama(model="llama3.2", temperature=0.6, streaming=False)
        server_config = {
            "default": {
                "url": f"{mcp_server_url}/sse",
                "transport": "sse",
                "options": {
                    "timeout": 10.0,
                    "retry_connect": True,
                    "max_retries": 2,
                    "read_timeout": 5.0,
                    "write_timeout": 5.0
                }
            }
        }
        self.mcp_client = MultiServerMCPClient(server_config)
        self.chat_history = []
        self.SYSTEM_PROMPT = """You are an AI assistant that helps users interact with a database.
You can add, read from, and create tables in the database using the available tools.
Always think before acting. Ensure the SQL is correct.

        When adding data:
        1. Format the SQL query correctly
        2. Make sure to use single quotes around text values
        3. Don't use quotes around numeric values
        
        When reading data:
        1. Use WHERE clause for filtering
        2. Present results in a clear, formatted way
        
        Always:
        1. Think through each step carefully
        2. Verify actions were successful
        3. Provide clear summaries of what was done"""

    async def check_server_connection(self):
        base_url = self.mcp_client.connections["default"]["url"].replace("/sse", "")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                sse_url = f"{base_url}/sse"
                response = await client.get(sse_url, timeout=5.0)
                return response.status_code == 200
        except httpx.ReadTimeout:
            return True
        except Exception:
            return False

    async def initialize_agent(self):
        if not await self.check_server_connection():
            raise ConnectionError("MCP server not reachable")

        mcp_tools = await self.mcp_client.get_tools()

        async def add_data_wrapper(query: str):
            try:
                return await mcp_tools[0].ainvoke({"query": query.strip()})
            except Exception as e:
                return f"Add error: {str(e)}"

        async def read_data_wrapper(query: str):
            try:
                result = await mcp_tools[1].ainvoke({"query": query.strip()})
                if not result:
                    return "No data found."
                headers = result[0::4]
                rows = [result[i:i+4] for i in range(0, len(result), 4)]
                table = ["| " + " | ".join(map(str, row)) + " |" for row in rows]
                return "\n".join(table)
            except Exception as e:
                return f"Read error: {str(e)}"

        self.tools = [
            Tool(
                name="add_data",
                description="Add data using INSERT INTO ...",
                func=lambda x: "Use async",
                coroutine=add_data_wrapper
            ),
            Tool(
                name="read_data",
                description="Read data using SELECT ...",
                func=lambda x: "Use async",
                coroutine=read_data_wrapper
            ),
            Tool(
                name="create_table",
                description="Create a table using CREATE TABLE ...",
                func=lambda x: "Use async",
                coroutine=add_data_wrapper
            )
        ]

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(REACT_TEMPLATE)
        ]).partial(tool_names=", ".join(tool.name for tool in self.tools))

        self.agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=1,
            early_stopping_method="force",
            return_intermediate_steps=True
        )

    async def process_message(self, user_input: str):
        try:
            response = await self.agent_executor.ainvoke({"input": user_input, "chat_history": self.chat_history})
            if isinstance(response, dict) and "output" in response:
                self.chat_history.extend([
                    HumanMessage(content=user_input),
                    AIMessage(content=response["output"])
                ])
                return response["output"]
            return "Agent could not determine a valid result."
        except Exception as e:
            return f"Processing error: {str(e)}"

    async def interactive_chat(self):
        print("Interactive chat started. Type 'exit' to quit.")
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                print("Goodbye!")
                break
            response = await self.process_message(user_input)
            print("Agent:", response)

async def main():
    client = LangchainMCPClient()
    await client.initialize_agent()
    await client.interactive_chat()

if __name__ == "__main__":
    asyncio.run(main())

