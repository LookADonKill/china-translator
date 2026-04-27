import os
import json
import time
import pandas as pd
from tqdm import tqdm
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed
os.system("chcp 936")

# Translations
ch_to_en = GoogleTranslator(source='zh-CN', target='en')
en_to_ch = GoogleTranslator(source='en', target='zh-CN')

# Batch Processing Variables
INPUT_FOLDER = "C:/Users/xavie/OneDrive - Bina Nusantara/Documents/Python/LanguageConverter/Sensitive-lexicon/Vocabulary"
OUTPUT_JSON = "dictionary.json"
OUTPUT_CSV = "dictionary.csv"
CACHE_FILE = "translation_cache.json"
MAX_WORDS = 100
MAX_WORKERS = 3
SAVE_INTERVAL = 20
RETRY_ATTEMPTS = 2

# Load cache
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)
else:
    cache = {}

BAD_VALUES = ["UNKNOWN", "ERROR", "EMPTY"]

cache = {k: v for k, v in cache.items() if v not in BAD_VALUES}

def show_main_menu():
    print("======== Main Menu ========")
    print("1. Live Translation")
    print("2. Batch Folder Translation")
    print("3. Exit")
    return input("Choose an option (1-3): ")

def show_live_translation_menu():
    print("======= Live Translation =======")
    print("1. Chinese -> English")
    print("2. English -> Chinese")
    print("3. Return to Main Menu")
    return input("Choose an option (1-3): ")

def live_translation():
    while True:
        choice = show_live_translation_menu()

        if choice == '1':
            translate(ch_to_en, "Chinese", "English")
        elif choice == '2':
            translate(en_to_ch, "English", "Chinese")
        elif choice == '3':
            break
        else:
            print("Invalid input! Try again.")

def translate(translator, source, target):
    while True:
        text = input(f"Enter {source} text to translate to {target} (or 'back' to return): ")

        if text.lower() == 'back': 
            return 

        if not text.strip():
            print("Invalid input! Try again.")
            continue
        
        try:
            translation = translator.translate(text)
            print(f"Translation Result: {translation}")
            
            # Ask if user wants to translate again
            again = input("1. Translate another text \n2. Return to Translation Menu \nChoose (1-2): ")

            if again == '2':
                return 
                
        except Exception as e:
            print(f"Translation failed: {str(e)}")
            print("Please try again.")

def load_vocab(folder_path):
    data = []
    for file in os.listdir(folder_path):
        if file.endswith(".txt"):
            category = file.replace(".txt", "")
            with open(os.path.join(folder_path, file), encoding="utf-8") as f:
                for line in f:
                    word = line.strip()
                    if word:
                        data.append({
                            "word_zh": word,
                            "category": category
                        })
    return data

def deduplicate(data):
    seen = {}
    for item in data:
        word = item["word_zh"]
        if word not in seen:
            seen[word] = {
                "word_zh": word,
                "categories": set([item["category"]])
            }
        else:
            seen[word]["categories"].add(item["category"])
    
    return [
        {
            "word_zh": v["word_zh"],
            "categories": list(v["categories"])
        }
        for v in seen.values()
    ]

def translate_word(word):
    for attempt in range(RETRY_ATTEMPTS):
        try:
            result = ch_to_en.translate(word)
            if not result:
                print(f"⚠️ EMPTY: {word}")
                return "EMPTY"
            return result
        except Exception as e:
                print(f"❌ ERROR ({attempt+1}): {word} -> {e}")
                time.sleep(0.5)
    return "ERROR"


def process_word(word, index, total):
    if word in cache:
        return word, cache[word]
    print (f"[{index}/{total}] Translating: {word}")
    translation = translate_word(word)

    if translation == word:
        translation = "UNTRANSLATED"
    if len(translation) > 100:
        translation = "SUSPECT"

    return word, translation

def batch_translation():
    raw_data = load_vocab(INPUT_FOLDER)

    print(f"Loaded {len(raw_data)} entries")

    print("Deduplicating...")
    data = deduplicate(raw_data)

    print(f"After deduplication: {len(data)} unique words")

    results = []

    words_to_translate = [
        item["word_zh"]
        for item in data
        if item["word_zh"] not in cache
    ]

    words_to_translate = words_to_translate[:MAX_WORDS]

    futures = []
    completed_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for i, word in enumerate(words_to_translate):
            futures.append(
                executor.submit(process_word, word, i+1, len(words_to_translate))
                )

        for future in tqdm(as_completed(futures), total=len(futures)):
            word, translation = future.result()
            cache[word] = translation
            completed_count += 1

            if completed_count % SAVE_INTERVAL == 0:
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False, indent=2)

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
             json.dump(cache, f, ensure_ascii=False, indent=2)

    for item in data:
        word = item["word_zh"]
        results.append({
            "word_zh": word,
            "translation_en": cache.get(word, "UNKNOWN"),
            "categories": item["categories"]
        })

    print("Saving outputs...")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False)

    print("✅ Batch translation completed.")

def main():
    while True:
        choice = show_main_menu()

        if choice == '1':
            live_translation()
        elif choice == '2':
            batch_translation()
        elif choice == '3':
            print("Thanks for using this program! I hope I can see you soon!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
