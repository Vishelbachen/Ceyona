from __future__ import annotations

# ─── EXAMPLES ─────────────────────────────────────────────────────────────────
# Структура: { "intent_name": ["пример 1", "пример 2", ...] }
# Минимум 15 примеров на интент для надёжной классификации.
#
# Augmentation (май 2026–июнь 2026):
#   recommendation — отдельная категория для travel / food / hotel / city advice.
#   recall — separate class for "what was that anime?" style memory lookups.
#   search — still covers descriptive web-search recall as a backstop.
#   This keeps advice/planning out of the generic QUESTION fallback and
#   reduces hallucinations in broad travel or recommendation prompts.

INTENT_EXAMPLES: dict[str, list[str]] = {

    "question": [
        "What is the capital of France?",
        "How does photosynthesis work?",
        "Who invented the telephone?",
        "Why is the sky blue?",
        "What causes earthquakes?",
        "How many planets are in the solar system?",
        "What is the speed of light?",
        "When did World War II end?",
        "Что такое квантовая механика?",
        "Почему вода замерзает при 0 градусов?",
        "Кто написал Войну и мир?",
        "Как работает мозг человека?",
        "Что такое инфляция?",
        "Как образуются горы?",
        "Почему небо голубое?",
        "ما هي عاصمة روسيا؟",
        "كيف يعمل الذكاء الاصطناعي؟",
        "Як працює імунна система?",
    ],

    "recommendation": [
        "What should I eat in the Netherlands?",
        "Recommend a city to visit in Japan",
        "Best area to stay in New York City",
        "Where should I go for a first trip to Italy?",
        "What are the must-try foods in Georgia?",
        "Which hotel area is best in central London?",
        "Suggest a 3-day itinerary for Kyoto",
        "What is the best city to visit in the Netherlands?",
        "Какие блюда стоит попробовать в Нидерландах?",
        "В какой город лучше поехать в Японии?",
        "Какой район лучше выбрать для отеля в Нью-Йорке?",
        "Посоветуй маршрут на 3 дня в Токио",
        "Что посмотреть в Риме за один день?",
        "Qué comer en los Países Bajos?",
        "Qué ciudad recomiendas visitar en Japón?",
        "Où aller pour un premier voyage en Italie ?",
        "Welcher Stadtteil ist in New York am besten zum Übernachten?",
        "Dove conviene alloggiare a Londra in centro?",
        "Günstigste und beste Gegend in Berlin für Hotels?",
        "What is the rough budget for a trip to Tokyo?",
        "How can I travel to Japan and what should I visit?",
        "What should I know before a trip to the Netherlands?",
        "Where should I stay near JFK airport?",
        "What is the best place to visit in Amsterdam?",
        "What food is famous in the Netherlands?",
    ],

    "code": [
        "Write a Python function to sort a list",
        "How do I reverse a string in JavaScript?",
        "Fix this bug in my code",
        "Write a SQL query to find duplicates",
        "How to implement binary search in Python?",
        "Create a REST API endpoint in FastAPI",
        "What is the difference between async and sync?",
        "Write a regex to validate email addresses",
        "How to connect to PostgreSQL in Python?",
        "Debug this TypeError in my function",
        "Напиши функцию на Python для парсинга JSON",
        "Как сделать HTTP запрос в JavaScript?",
        "Исправь ошибку в этом коде",
        "Как написать unit тест в pytest?",
        "Создай класс для работы с базой данных",
        "Write a Docker compose file for Redis and Postgres",
        "How to handle exceptions in async Python?",
        "Implement a LRU cache in Python",
    ],

    "analysis": [
        "Analyse the pros and cons of electric vehicles",
        "What are the main factors behind inflation?",
        "Compare Python and JavaScript for backend development",
        "What caused the 2008 financial crisis?",
        "Analyse this business strategy",
        "What are the implications of AI on employment?",
        "Break down the key trends in renewable energy",
        "Проанализируй плюсы и минусы удалённой работы",
        "Какие факторы влияют на курс рубля?",
        "Сравни PostgreSQL и MongoDB",
        "Каковы последствия глобального потепления?",
        "Analyse the competitive landscape of streaming services",
        "What are the risks of this investment strategy?",
        "Объясни причины демографического кризиса",
        "What are the long-term effects of social media on society?",
        "Compare microservices vs monolithic architecture",
    ],

    "creative": [
        "Write a short story about a robot who falls in love",
        "Compose a poem about the ocean",
        "Write a haiku about winter",
        "Create a dialogue between two strangers on a train",
        "Write the opening paragraph of a thriller novel",
        "Придумай историю про дракона и принцессу",
        "Напиши стихотворение о весне",
        "Сочини анекдот про программиста",
        "Write a product description for a luxury watch",
        "Create a bedtime story for a 5-year-old",
        "Write a motivational speech for a startup team",
        "Compose a song chorus about freedom",
        "Write a movie pitch in two sentences",
        "Придумай название для кафе в стиле минимализм",
        "Напиши эссе о смысле жизни",
        "Write a tweet announcing a new product launch",
    ],

    "conversation": [
        "Hello!",
        "Hi there, how are you?",
        "Good morning!",
        "Hey, what's up?",
        "Thanks for your help",
        "You're great!",
        "I'm bored, let's talk",
        "What can you do?",
        "Tell me something interesting",
        "Привет!",
        "Как дела?",
        "Добрый день!",
        "Спасибо за помощь",
        "Ты умеешь шутить?",
        "Расскажи что-нибудь интересное",
        "Скучно, поговорим?",
        "Что ты умеешь делать?",
        "مرحبا، كيف حالك؟",
    ],

    "emotional": [
        "I'm so frustrated with everything right now",
        "This is absolutely amazing, I can't believe it!",
        "I feel so lonely today",
        "I'm devastated, I lost my job",
        "I'm so happy I could cry",
        "This is so unfair, I hate this",
        "I'm overwhelmed and don't know what to do",
        "Я в отчаянии, всё идёт не так",
        "Это просто невероятно, я счастлива!",
        "Мне так грустно сегодня",
        "Я в бешенстве, это несправедливо",
        "Не могу больше, всё достало",
        "Я влюбился и не знаю что делать",
        "I'm scared about the future",
        "I just need someone to talk to",
        "I'm so proud of myself today",
    ],

    "math": [
        "Solve: 2x + 5 = 15",
        "What is the derivative of x^3?",
        "Calculate the area of a circle with radius 7",
        "Find the roots of x^2 - 5x + 6 = 0",
        "What is 15% of 240?",
        "Prove that the square root of 2 is irrational",
        "Solve the system: x + y = 10, x - y = 4",
        "What is the integral of sin(x)?",
        "Реши уравнение: 3x - 7 = 14",
        "Найди производную функции f(x) = x^2 + 3x",
        "Вычисли площадь треугольника со сторонами 3, 4, 5",
        "Сколько будет 17 процентов от 850?",
        "Реши систему уравнений",
        "What is the Pythagorean theorem?",
        "Calculate compound interest for 3 years at 5%",
        "Найди НОД чисел 48 и 36",
    ],

    "instruction": [
        "How do I make pasta carbonara?",
        "How to set up a VPN on my phone?",
        "Steps to change a car tyre",
        "How to meditate for beginners?",
        "How to write a cover letter?",
        "How to lose weight in 3 months?",
        "How to start investing with small amounts?",
        "How to learn a new language fast?",
        "Как приготовить борщ?",
        "Как установить Python на Windows?",
        "Как начать бегать с нуля?",
        "Как написать резюме?",
        "Как похудеть на 5 кг?",
        "How to build a morning routine?",
        "Guide me through setting up Redis",
        "Explain how to apply for a visa",
    ],

    "weather": [
        "What's the weather like in London today?",
        "Will it rain in Moscow tomorrow?",
        "Weather forecast for Paris this weekend",
        "Is it going to snow in Berlin?",
        "Current temperature in Tokyo",
        "Погода в Москве на завтра",
        "Какая погода сейчас в Санкт-Петербурге?",
        "Будет ли дождь в Киеве на выходных?",
        "Прогноз погоды в Алматы на неделю",
        "What is the UV index in Dubai today?",
        "Is there a storm warning for New York?",
        "Weather in Barcelona next week",
        "Температура воздуха в Минске сегодня",
        "كيف الطقس في الرياض اليوم؟",
        "How hot is it in Sydney right now?",
        # Hausa
        "Yaya yanayi yake a San Francisco yanzu?",
        "Yaya yanayi a Landan?",
        "Yaya zafin rana a Najeriya yau?",
        "Shin za a yi ruwa gobe a Abuja?",
        "Yanayi a Dubai yanzu",
        "Yaya yanayin yake a Moscow?",
        # Georgian
        "რა ამინდია ამ წუთას ლონდონში?",
        "ამინდის პროგნოზი თბილისში ხვალ",
        # Armenian
        "Ինչ եղանակ է Փարիզում հիմա?",
        # Azerbaijani
        "Bakıda hava necədir?",
        # Kazakh
        "Алматыда ауа райы қандай?",
        # Uzbek
        "Toshkentda havo qanday?",
    ],

    "search": [
        # ── Explicit web search ───────────────────────────────────────────────
        "Find information about Elon Musk",
        "Latest news about AI",
        "Search for best Python frameworks 2024",
        "Who won the Champions League this year?",
        "Find recent studies on sleep deprivation",
        "What happened in the tech industry this week?",
        "Look up the population of Brazil",
        "Find reviews for iPhone 15",
        "Какие дешёвые отели в центре Воронежа?",
        "Best cheap hotels in city center",
        "Недорогие гостиницы в Москве",
        "Список отелей рядом с аэропортом",
        "Посоветуй гостиницу в центре Киева",
        "Найди информацию о квантовых компьютерах",
        "Последние новости о криптовалюте",
        "Поищи рецепты тирамису",
        "Что происходит в мире сейчас?",
        "ابحث عن أحدث أخبار التكنولوجيا",
        "Find the best restaurants in Amsterdam",
        "Search for open source alternatives to Notion",
        "Latest research on cancer treatment",
        # Hotels / accommodation
        "Какие дешёвые отели есть в центре Воронежа?",
        "Дешёвые гостиницы в Москве в центре",
        "Где остановиться в Санкт-Петербурге недорого?",
        "Хостелы в центре Казани",
        "Бюджетные отели рядом с вокзалом",
        "Cheap hotels in downtown London",
        "Best budget hostels in Barcelona city centre",
        "Affordable accommodation near Times Square",
        "Where to stay in Tokyo cheap",
        "Günstiges Hotel in Berlin Mitte",
        "Hôtel pas cher à Paris centre",
        "Hotel barato en el centro de Madrid",
        # Routes / directions
        "Как добраться от аэропорта Воронежа до центра?",
        "Маршрут от Шереметьево до Красной площади",
        "На каком транспорте доехать до центра из аэропорта?",
        "How to get from Heathrow airport to central London",
        "Best way from JFK to Manhattan",
        "Public transport from airport to city centre",    ],


    "recall": [
        # ── Media / title recall ───────────────────────────────────────────────
        "Help me remember an anime where the protagonist starts mute and wooden",
        "I'm trying to recall an anime from 2019 about a farm and a holy child",
        "What was that anime with an father who would sacrifice anything for prosperity and harvest?",
        "I can't remember the title of the movie where the main character loses his memory",
        "What is the name of the song that goes we will we will rock you?",
        "Помоги вспомнить аниме, где главный герой в начале не умел говорить",
        "Не помню название аниме про ферму и вечный урожай",
        "Вспомни аниме, где отец готов пожертвовать всем ради благополучия земель",
        "Что за фильм, где главный герой теряет память?",
        "Напомни название песни, где есть строчка we will we will rock you",
        "Помоги найти мультфильм, который я смотрел в детстве",
        "Вспомни книгу про школу волшебников",
        "Help me recall the anime with a blue-haired character and demons",
        "What was that game about surviving on an island?",
        "Quel est le film dont le héros perd la mémoire ?",
        "¿Qué anime era ese sobre un protagonista sin voz al principio?",
        "Welcher Anime war das mit dem stummen Helden am Anfang?",
        "Вспомни сериал про химика, который варит наркотики",
    ],

    "maps": [
        "Where is the Eiffel Tower?",
        "Show me the location of Central Park",
        "How do I get from London to Edinburgh?",
        "Directions from Moscow to Saint Petersburg",
        "Where is Istanbul located?",
        "Find the coordinates of Mount Everest",
        "Navigate to the nearest airport",
        "Где находится Красная площадь?",
        "Как добраться от Киева до Львова?",
        "Покажи на карте Байкал",
        "أين تقع برج خليفة؟",
        "Map of downtown Tokyo",
        "Route from Paris to Lyon by car",
        "Show me where Dubai is on the map",
        "Где находится Большой театр в Москве?",
    ],

    "maps_poi": [
        "What are the opening hours of the Louvre?",
        "Is the Colosseum open on Mondays?",
        "Phone number for the British Museum",
        "Rating of Nobu restaurant in London",
        "How much does it cost to enter the Vatican?",
        "Время работы ГУМа в Москве",
        "Телефон Эрмитажа в Санкт-Петербурге",
        "Рейтинг ресторана Пушкин в Москве",
        "Сколько стоит билет в Третьяковскую галерею?",
        "Is IKEA open on Sunday?",
        "Reviews for this cafe",
        "Режим работы Московского зоопарка",
        "Contact details for the US Embassy in Berlin",
        "What time does this museum close?",
        "ما هي ساعات عمل متحف اللوفر؟",
    ],

    "exam": [
        "Определи тип питания организма: хлорелла, волчанка, дождевой червь",
        "Установи соответствие между организмами и типами размножения",
        "ЕГЭ биология: какой процесс происходит в митохондриях?",
        "ОГЭ химия: определи тип реакции: Na + H2O →",
        "Выбери правильный ответ: фотосинтез происходит в...",
        "Задание ОГЭ по физике: найди ускорение тела массой 5 кг",
        "ЕГЭ математика: реши уравнение log2(x+1) = 3",
        "Выпиши цифры правильных утверждений",
        "Установи последовательность этапов митоза",
        "ВПР биология 8 класс: строение клетки",
        "ОГЭ история: когда произошла Куликовская битва?",
        "Тест по географии: укажи климатический пояс",
        "Экзаменационное задание по химии",
        "Задача по физике из ЕГЭ",
        "Реши задачу из учебника Алгебра 9 класс",
        "Определи правильные и неправильные утверждения",
    ],
}


# ─── SEED FUNCTION ────────────────────────────────────────────────────────────

async def seed_intent_examples(supabase, hf_client, force: bool = False) -> int:
    """
    Векторизует все примеры через BGE-large и загружает в Supabase.

    Args:
        supabase:   Supabase client (из bootstrap).
        hf_client:  HF inference client (из llm/hf_client.py).
        force:      Если True — очищает таблицу перед загрузкой.

    Returns:
        Количество загруженных примеров.

    Note:
        После добавления примеров (май 2026) необходимо запустить
        seed_intent_examples(force=True) для пересева таблицы.
        Новые примеры recall/media_identification в search-пространстве
        не активируются до пересева.
    """
    import logging

    from llm.hf_client import BGE_LARGE

    logger = logging.getLogger(__name__)

    # Проверяем — уже заполнена?
    if not force:
        result = supabase.table("intent_examples").select("id", count="exact").limit(1).execute()
        if result.count and result.count > 0:
            logger.info("intent_examples already seeded, skipping", extra={"count": result.count})
            return 0

    if force:
        supabase.table("intent_examples").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        logger.info("intent_examples cleared for re-seed")

    total = 0
    for intent_name, examples in INTENT_EXAMPLES.items():
        try:
            vectors = await hf_client.embed(examples, model=BGE_LARGE)
            if not vectors or len(vectors) != len(examples):
                logger.error("Embedding mismatch", extra={"intent": intent_name})
                continue

            rows = [
                {
                    "intent_name": intent_name,
                    "text": text,
                    "embedding": vector,
                    "lang": "any",
                }
                for text, vector in zip(examples, vectors)
            ]
            supabase.table("intent_examples").insert(rows).execute()
            total += len(rows)
            logger.info("Seeded intent", extra={"intent": intent_name, "count": len(rows)})

        except Exception as exc:
            logger.error("Seed failed for intent", extra={"intent": intent_name, "error": str(exc)})

    logger.info("intent_examples seed complete", extra={"total": total})
    return total