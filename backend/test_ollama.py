from ollama import chat

response = chat(
    model="llama3",
    messages=[
        {
            "role": "user",
            "content": "Explain binary search to a beginner."
        }
    ]
)

print(response["message"]["content"])