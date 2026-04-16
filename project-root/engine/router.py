if text.lower() == "force groq":
    from groq import Groq
    import os

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "say ONLY GROQ_OK"}]
    )

    return "[FORCED GROQ] " + res.choices[0].message.content