import os
import time
import logging
import multiprocessing
from multiprocessing import Pool, Manager, cpu_count
from threading import Thread
import psutil
import random


# Настройка логирования
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('file_cipher.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


class EnigmaLikeCipher:
    def __init__(self, key):
        self.key = key
        self.all_chars = self._get_unicode_chars()
        random.seed(key)  # Фиксируем seed для воспроизводимости
        self.rotor1 = self._create_rotor(key)
        self.rotor2 = self._create_rotor(key * 2)
        self.rotor3 = self._create_rotor(key * 3)
        self.rotor1_pos = 0
        self.rotor2_pos = 0
        self.rotor3_pos = 0

    @staticmethod
    def _get_unicode_chars():
        chars = []
        chars.extend([chr(i) for i in range(32, 127)])  # ASCII
        # Кириллица и дополнительные символы
        cyrillic_ranges = [
            (0x0400, 0x04FF),  # Кириллица
            (0x0500, 0x052F),  # Дополнение к кириллице
        ]
        for start, end in cyrillic_ranges:
            chars.extend([chr(i) for i in range(start, end + 1)])
        return sorted(list(set(chars)))

    def _create_rotor(self, seed):
        random.seed(seed)
        rotor = self.all_chars.copy()
        random.shuffle(rotor)
        return rotor

    def _rotate_rotors(self):
        self.rotor1_pos += 1
        if self.rotor1_pos >= len(self.all_chars):
            self.rotor1_pos = 0
            self.rotor2_pos += 1
            if self.rotor2_pos >= len(self.all_chars):
                self.rotor2_pos = 0
                self.rotor3_pos += 1
                if self.rotor3_pos >= len(self.all_chars):
                    self.rotor3_pos = 0

    def _get_rotor_char(self, rotor, pos, offset):
        idx = (pos + offset) % len(self.all_chars)
        return rotor[idx]

    def encrypt_char(self, char):
        if char not in self.all_chars:
            return char

        # Проход вперед через роторы
        idx = self.all_chars.index(char)

        # Ротор 1
        char_enc = self._get_rotor_char(self.rotor1, self.rotor1_pos, idx)
        idx = self.all_chars.index(char_enc)

        # Ротор 2
        char_enc = self._get_rotor_char(self.rotor2, self.rotor2_pos, idx)
        idx = self.all_chars.index(char_enc)

        # Ротор 3
        char_enc = self._get_rotor_char(self.rotor3, self.rotor3_pos, idx)

        self._rotate_rotors()
        return char_enc

    def decrypt_char(self, char):
        if char not in self.all_chars:
            return char

        # Проход назад через роторы
        idx = self.all_chars.index(char)

        # Ротор 3 (обратный)
        char_dec = self.all_chars[(self.rotor3.index(char) - self.rotor3_pos) % len(self.all_chars)]
        idx = self.all_chars.index(char_dec)

        # Ротор 2 (обратный)
        char_dec = self.all_chars[(self.rotor2.index(char_dec) - self.rotor2_pos) % len(self.all_chars)]
        idx = self.all_chars.index(char_dec)

        # Ротор 1 (обратный)
        char_dec = self.all_chars[(self.rotor1.index(char_dec) - self.rotor1_pos) % len(self.all_chars)]

        self._rotate_rotors()
        return char_dec

    def encrypt(self, text):
        return ''.join(self.encrypt_char(c) for c in text)

    def decrypt(self, text):
        return ''.join(self.decrypt_char(c) for c in text)


def save_worker(result_queue, save_queue):
    while True:
        task = save_queue.get()
        if task is None:
            break
        try:
            task_type, data, filename = task
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(data)
            logging.info(f"Сохранено в {filename}")
            result_queue.put(('save_done', filename))
        except Exception as e:
            logging.error(f"Ошибка сохранения: {e}")


def logging_thread(log_queue, process_id):
    while True:
        message = log_queue.get()
        if message is None:
            break
        logging.info(f"[Процесс {process_id}] {message}")


def process_chunk(args):
    task_id, chunk, key, action, process_id, log_queue = args
    log_queue.put(f"Начало обработки блока {task_id}")

    cipher = EnigmaLikeCipher(key)
    result = cipher.encrypt(chunk) if action == 'encrypt' else cipher.decrypt(chunk)

    log_queue.put(f"Завершение блока {task_id}")
    return task_id, result


def read_file(filename):
    encodings = ['utf-8', 'windows-1251', 'cp866', 'koi8-r', 'iso-8859-5']
    for enc in encodings:
        try:
            with open(filename, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Не удалось определить кодировку файла {filename}")


def process_file(filename, action, key, num_processes=None):
    start_time = time.time()

    # Определение количества процессов
    cpu_load = psutil.cpu_percent(interval=1)
    max_processes = cpu_count()
    available_processes = max(1, int(max_processes * (1 - cpu_load / 100)))
    num_processes = min(num_processes, available_processes) if num_processes else available_processes

    logging.info(f"Используется {num_processes} процессов (загрузка CPU: {cpu_load}%)")

    try:
        text = read_file(filename)
    except Exception as e:
        logging.error(f"Ошибка чтения файла: {e}")
        return None

    # Разделение текста на части
    chunk_size = len(text) // num_processes
    chunks = []
    for i in range(num_processes):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < num_processes - 1 else len(text)
        chunks.append(text[start:end])

    manager = Manager()
    result_queue = manager.Queue()
    save_queue = manager.Queue()
    log_queue = manager.Queue()

    saver_process = multiprocessing.Process(
        target=save_worker,
        args=(result_queue, save_queue)
    )
    saver_process.start()

    logging_thread_instance = Thread(
        target=logging_thread,
        args=(log_queue, "Main")
    )
    logging_thread_instance.start()

    with Pool(processes=num_processes) as pool:
        tasks = [
            (i, chunks[i], key, action, i + 1, log_queue)
            for i in range(num_processes)
        ]

        results = []

        def collect_result(result):
            results.append(result)

        for task in tasks:
            pool.apply_async(
                process_chunk,
                args=(task,),
                callback=collect_result
            )

        pool.close()
        pool.join()

    results.sort(key=lambda x: x[0])
    processed_text = ''.join([chunk for _, chunk in results])

    output_filename = f"{filename}.{'enc' if action == 'encrypt' else 'dec'}"
    save_queue.put((action, processed_text, output_filename))

    while True:
        status, filename = result_queue.get()
        if status == 'save_done':
            break

    save_queue.put(None)
    log_queue.put(None)
    saver_process.join()
    logging_thread_instance.join()

    logging.info(f"Выполнено за {time.time() - start_time:.2f} сек")
    return output_filename


def main():
    setup_logging()
    logging.info("Программа шифрования/дешифрования")

    while True:
        print("\nМеню:")
        print("1. Зашифровать файл")
        print("2. Расшифровать файл")
        print("3. Выход")
        choice = input("Выберите действие: ")

        if choice == '1':
            filename = input("Введите путь к файлу: ")
            key = int(input("Введите ключ (целое число): "))
            num_processes = input("Количество процессов (Enter для авто): ")
            num_processes = int(num_processes) if num_processes.strip() else None

            if not os.path.exists(filename):
                print("Файл не найден!")
                continue

            process_file(filename, 'encrypt', key, num_processes)
            print("Шифрование завершено")

        elif choice == '2':
            filename = input("Введите путь к файлу: ")
            key = int(input("Введите ключ (целое число): "))
            num_processes = input("Количество процессов (Enter для авто): ")
            num_processes = int(num_processes) if num_processes.strip() else None

            if not os.path.exists(filename):
                print("Файл не найден!")
                continue

            process_file(filename, 'decrypt', key, num_processes)
            print("Дешифрование завершено")

        elif choice == '3':
            break

        else:
            print("Неверный выбор!")


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()