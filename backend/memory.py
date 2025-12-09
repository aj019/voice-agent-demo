from openai import OpenAI
from mem0 import AsyncMemoryClient
from dotenv import load_dotenv
import os
import asyncio
load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
memory = AsyncMemoryClient()

async def chat_with_memories(message: str, user_id: str = "alice") -> str:
    # Retrieve relevant memories
    print("user id :", user_id)
    relevant_memories = await memory.search(query=message, filters={"user_id": user_id})
    print("relevant_memories :", relevant_memories)
    memories_str = "\n".join(f"- {entry['memory']}" for entry in relevant_memories["results"])
    print("memories_str :", memories_str)
    # Generate Assistant response
    system_prompt = f"You are a helpful AI. Answer the question based on query and memories.\nUser Memories:\n{memories_str}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": message}]
    response = openai_client.chat.completions.create(model="gpt-4.1-nano-2025-04-14", messages=messages)
    assistant_response = response.choices[0].message.content

    # Create new memories from the conversation
    messages.append({"role": "assistant", "content": assistant_response})
    memory.add(messages, user_id=user_id)

    return assistant_response

def main():
    print("Chat with AI (type 'exit' to quit)")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        print(f"AI: {asyncio.run(chat_with_memories(user_input))}")

if __name__ == "__main__":
    main()