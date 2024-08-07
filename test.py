def split_file_by_date(input_file, output_file1, output_file2, split_date):
    with open(input_file, "r") as infile:
        lines = infile.readlines()

    # Найдем индекс, по которому будем делить файл
    split_index = 0
    header = []
    write_header = True
    for i, line in enumerate(lines):
        if write_header:
            header.append(line)
        if line.strip() == "END OF HEADER":
            write_header = False
        if line.startswith(">"):
            date_str = line[1:].strip()  # Удалим '>' и пробелы
            if date_str > split_date:
                split_index = i
                break

    # Запишем данные в два новых файла
    with open(output_file1, "w") as outfile1:
        outfile1.writelines(lines[:split_index])

    with open(output_file2, "w") as outfile2:
        outfile2.writelines(header + lines[split_index:])

# Пример использования
input_file = (
    "C:/Users/zalyg/Downloads/Telegram Desktop/ALBH00CAN_R_20240010000_01D_30S_MO.rnx"
)
output_file1 = "C:/Users/zalyg/Downloads/Telegram Desktop/file1.txt"
output_file2 = "C:/Users/zalyg/Downloads/Telegram Desktop/file2.txt"
split_date = "2024 01 01 06 45 00.0000000  0 30"  # Дата для разделения

split_file_by_date(input_file, output_file1, output_file2, split_date)
