import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def test():
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Say hello"}]
    )
    print("GROQ:", res.choices[0].message.content)

if __name__ == "__main__":
    test()