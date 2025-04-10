import multiprocessing
import time
import logging
from multiprocessing import Pool, Manager, Queue, Process, current_process
from typing import List, Tuple


def setup_logger():
    logger = multiprocessing.get_logger()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('sorting.log', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger


def log_worker(log_queue: Queue):
    logger = setup_logger()
    while True:
        message = log_queue.get()
        if message == 'STOP':
            break
        logger.info(message)


def merge_sort(arr: List[int]) -> List[int]:
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)


def merge(left: List[int], right: List[int]) -> List[int]:
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


def sort_part(part: Tuple[int, List[int]], log_queue: Queue) -> Tuple[int, List[int]]:
    part_id, data = part
    sorted_data = merge_sort(data)
    log_queue.put(f"Процесс {current_process().name} отсортировал часть {part_id}: {sorted_data}")
    return (part_id, sorted_data)


def parallel_sort(arr: List[int], num_processes: int, log_queue: Queue) -> List[int]:
    manager = Manager()
    logger_process = Process(target=log_worker, args=(log_queue,))
    logger_process.start()

    chunk_size = len(arr) // num_processes
    parts = [(i, arr[i * chunk_size:(i + 1) * chunk_size]) for i in range(num_processes)]

    if len(arr) % num_processes != 0:
        parts[-1] = (parts[-1][0], parts[-1][1] + arr[num_processes * chunk_size:])

    log_queue.put("Начинается параллельная сортировка.")

    with Pool(processes=num_processes) as pool:
        sorted_parts = pool.starmap(sort_part, [(part, log_queue) for part in parts])

    sorted_parts.sort(key=lambda x: x[0])
    final_sorted = []
    for part in sorted_parts:
        final_sorted.extend(part[1])

    # Объединение всех отсортированных частей
    final_sorted = merge_sort(final_sorted)

    log_queue.put("Параллельная сортировка завершена.")
    log_queue.put('STOP')
    logger_process.join()
    return final_sorted


def main():
    print("ПАРАЛЛЕЛЬНАЯ СОРТИРОВКА")
    print("----------------------")

    try:
        input_str = input("Введите числа через запятую: ").strip()
        arr = [int(x.strip()) for x in input_str.split(',') if x.strip()]

        if not arr:
            raise ValueError("Не введены числа для сортировки")

        print(f"\nИсходный массив: {arr}")

        max_cores = multiprocessing.cpu_count()
        print(f"Доступно ядер CPU: {max_cores}")

        num_proc = int(input(f"Сколько ядер использовать (1-{max_cores})? "))
        if not 1 <= num_proc <= max_cores:
            raise ValueError(f"Нужно ввести число от 1 до {max_cores}")

        log_queue = Manager().Queue()
        start_time = time.time()
        sorted_arr = parallel_sort(arr, num_proc, log_queue)
        end_time = time.time()

        print("\n✅ Результат сортировки:")
        print(sorted_arr)
        print(f"\nВремя выполнения: {end_time - start_time:.4f} сек")

        with open('sorted_array.txt', 'w') as f:
            f.write(','.join(map(str, sorted_arr)))
        print("Результат сохранён в sorted_array.txt")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        logging.error(f"Ошибка: {e}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
