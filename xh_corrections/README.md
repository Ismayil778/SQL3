# Xalq Həyat — Korrektəedici Müxabirləşmələr Generator

Generator korrektiruyushikh provodok dlya İpoteka sığortası (XMLI).

---

## 1. Установка

```bash
pip install -r requirements.txt
```

**Системные требования:**
- Python 3.10+
- ODBC Driver 17 for SQL Server (установить отдельно)
- Доступ к SQL Server `Base_1c77`

### Установка ODBC Driver (если не установлен)

**Windows:**
Скачать с [Microsoft Download Center](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)

**Ubuntu/Debian:**
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

---

## 2. Запуск

```bash
cd xh_corrections
python main.py
```

---

## 3. Как работает алгоритм

### Шаг 1 — Список полисов
Программа загружает все полисы `XMLI*` из таблицы `SC14632` (subconto-справочник 1С).

### Шаг 2 — История проводок
Для каждого полиса загружаются все строки из `_1SENTRY` до отчётной даты включительно.
Используется batch-загрузка через временные таблицы `#policy_codes` (по 500 кодов) — это исключает медленные OR-джойны на 1.28M строк.

### Шаг 3 — Параметры полиса
- **Дата оформления** (`inception_date`): первая проводка `dt=B7/5F → kt=9U`
- **Месячный транш** (`monthly_installment`): последняя реклассификация `dt=BA → kt=B7` (или `dt=9U → kt=AZ`) делённая на 12. При отсутствии реклассификации — первый банковский платёж `dt=BA → kt=5F`.

### Шаг 4 — Уже признанные месяцы
Суммируем все проводки типа `dt=AZ → kt=7W/7X` с маркером `"Polislerin hesablar"` в SP210.  
`months_recognised = round(total_recognised / monthly_installment)`

### Шаг 5 — Непризнанные месяцы
```
months_elapsed    = (report_year - inception_year) * 12
                    + (report_month - inception_month) + 1
months_to_correct = months_elapsed - months_recognised
```

### Шаг 6 — Генерация проводок
Если `months_to_correct > 0`:
```
amount = monthly_installment × months_to_correct

DT=84.1.1.  KT=38.1.2.   AMOUNT=amount   (краткосрочное обяз. → доход)
DT=77.1.1.1 KT=79.1.1.1  AMOUNT=amount   (текущая дебит. → краткосроч. актив)
```

---

## 4. Формат выходного файла

Excel-файл `korreksiyalar_YYYYMMDD.xlsx` содержит два листа:

### Лист 1 — "Müxabirləşmələr / Проводки"

| DT | KT | AMOUNT | Siyasət / Полис | Müştəri / Клиент | Ay / Мес. |
|---|---|---|---|---|---|
| 84.1.1. | 38.1.2. | 35.45 | XMLI 00681/23 | Əhmədli Senan | 1 |
| 77.1.1.1. | 79.1.1.1. | 35.45 | XMLI 00681/23 | Əhmədli Senan | 1 |

- Строки отсортированы по номеру полиса
- AMOUNT: формат `#,##0.00`
- Шапка: красный фон (#C8102E), белый текст

### Лист 2 — "Xülasə / Сводка"

| Параметр | Значение |
|---|---|
| Hesab tarixi / Дата расчёта | 30.06.2026 |
| Cəmi polislər / Всего полисов | 3 241 |
| Korreksiya olan polislər / Полисов с корректировками | 487 |
| Bağlı polislər (hitam) / Закрытых полисов | 12 |
| Cəmi müxabirləşmələr / Всего проводок | 974 |
| Cəmi məbləğ / Общая сумма | 124 567.89 |
| Yaradılma vaxtı / Дата создания | 02.07.2026 14:35 |

---

## 5. Граничные случаи

### Допсоглашение (CemiAzalanSH / CemiElaveEdilenSH)
При изменении суммы полиса последняя реклассификация уже отражает новый транш.  
→ Алгоритм автоматически берёт **последнюю** реклассификацию / 12.

### Хитам (досрочное расторжение, CemiQaytarilanSH)
Если есть проводка `dt=A3, kt=5F` с **положительной** суммой и после неё нет проводок Типов 3–4:  
→ Полис считается **закрытым**, корректировки **не генерируются**.  
→ Полис попадает в список `hitam_policies` (счётчик в сводке).

### Сторно хитама
Та же проводка A3→5F, но с **отрицательной** суммой:  
→ Это отмена закрытия. Полис считается **активным**, обрабатывается штатно.

### Полис в месяц оформления
`months_elapsed = 1`. Если первый месяц уже проведён системой (проводка `9U→7X`),  
`months_recognised >= 1` → `months_to_correct = 0`, корректировок не генерируется.

---

## 6. Коды счетов (справочник)

| Счёт 1С | ID в _1SENTRY | Описание |
|---|---|---|
| 78.1.1.1 | B7 | Долгосрочный актив |
| 79.1.1.1 | BA | Краткосрочный актив |
| 83.1.1   | 9U | Долгосрочное обязательство |
| 84.1.1   | AZ | Краткосрочное обязательство |
| 77.1.1.1 | 5F | Текущая дебиторка |
| 38.1.1   | 7W | Доход (юрлица, артефакт импорта) |
| 38.1.2   | 7X | Доход (физлица, основной) |
