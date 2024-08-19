# Rinex Streaming

## Описание

Rinex Streaming — это система имитации потока данных в реальном времени на основе реальных данных. Проект предназначен для автоматической загрузки, обработки и трансляции данных в формате RINEX с различных станций.

## Установка

Для установки и запуска проекта выполните следующие шаги:

1. Клонируйте репозиторий:
```bash
git clone https://{deploy token}:{password}@git.iszf.irk.ru/gnss_services/workers/rinex_streaming.git
cd rinex_streaming
git pull
```

2. Установите необходимые зависимости:
```bash
sudo apt install python3-pip
pip install -r requirements.txt
```

3. Скачайте и установите CRX2RNX:
```bash
wget https://terras.gsi.go.jp/ja/crx2rnx/RNXCMP_4.1.0_Linux_x86_64bit.tar.gz
uncompress RNXCMP_4.1.0_Linux_x86_64bit.tar.gz
tar -xvf RNXCMP_4.1.0_Linux_x86_64bit.tar
sudo cp RNXCMP_4.1.0_Linux_x86_64bit/bin/CRX2RNX /usr/bin
```

4. Создайте необходимую директорию и настройте права доступа:
```bash
sudo mkdir /var/rnx_streamer
sudo chown user:user /var/rnx_streamer/data/
```

## Использование

Для запуска системы выполните следующую команду:
```bash
cd src/rnx_streamer
```
```bash
python3 scheduler.py <storage_path> 
<days_to_subtract> <available_RAM>
```

Пример:
```bash
python3 scheduler.py /var/rnx_streamer/data 7 75
```

### Параметры:

- <storage_path> — директория, в которую будут скачиваться архивы с данными и создаваться конфигурационные файлы.
- <days_to_subtract> — количество дней, которое нужно вычесть из текущей даты для получения данных за нужный период.
- <available_RAM> — количество оперативной памяти в процентах, которое программа не должна превышать.

### Описание работы:

- При запуске программы сначала загружается архив с данными, который затем распаковывается.
- Далее, каждый день в 23:00:00 программа автоматически загружает новый архив, распаковывает его и конвертирует данные в RINEX формат.
- После конвертации данных запускается orchestrator, который инициализирует стримеры для каждой станции. Каждая станция передает данные каждые 30 секунд.
- Реализована ежеминутная проверка статуса всех стримеров.

## Требования

Для работы проекта необходимы следующие библиотеки и утилиты:

- apscheduler==3.10.4
- requests==2.32.3
- gnss_tec==1.1.1
- psutil~=6.0.0
- CRX2RNX==4.1.0
