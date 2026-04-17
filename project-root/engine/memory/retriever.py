def get_memory(user_id: str, limit: int = 10):
    try:
        client = _get_client()

        if not client:
            return []

        res = (
            client
            .table("memory")
            .select("content, created_at")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        memories = []

        for row in res.data:
            text = row["content"]

            # 🔥 ФИЛЬТР
            if not text:
                continue

            if "🧠 GROQ" in text:
                continue  # убираем ответы модели

            if "Как меня зовут" in text:
                continue  # убираем вопросы

            if len(text) < 5:
                continue

            memories.append(text)

        print(f"🧠 CLEAN MEMORY: {memories}")

        return memories[:5]

    except Exception as e:
        print("❌ MEMORY RETRIEVE ERROR:", e)
        return []