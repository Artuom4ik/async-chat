# Асинхронный чат

Данный проект представляет собой несколько скриптов с аснхронными функциями, с помощью которых вы можете поключиться к серверу `minechat.dvmn.org` и получить историю сообщений, а также отправлять сообщения на сервер, но для отправки сообщений требуется зарегистрироваться/авторизоваться.  


___
>### Системные требования
- `Python` 3.10.12(или выше)
- `Windows` 10, 11 или `Linux`(Ubuntu 22.*)
___
>### Установка

- Скачайте код командой

```bash
git clone https://github.com/Artuom4ik/async-chat.git
```
- Перейте в рабочую директорию

```bash
cd async-chat
```

- Создайте виртуальное окружение командой

```bash
python3 -m venv myvenv
```

- Активируйте виртуальное окружение командой

`Linux`

```bash
source myvenv/bin/activate
```

`Windows`

```bash
.\myvenv\Scripts\activate
```

- Установите зависимости командой 

```bash
pip install -r requirements.txt
```
___

>### Переменные окружения:

Часть настроек проекта берётся из переменных окружения. Чтобы их определить, создайте файл `.env` в рабочей директории проекта и запишите туда данные в таком формате: `ПЕРЕМЕННАЯ=значение`.

**Для запуска проекта требуется указать переменные окружения**.

- `GET_HOST` - хост сервера к которому будете поключаться. Например `minechat.dvmn.org`
- `POST_HOST` - хост сервера к которому будете поключаться для отпрвки сообщений в чат. Например `minechat.dvmn.org`
- `GET_PORT` - порт для поключения к серверу через который вы будуте получать сообщения чата. Например: `5000`
- `POST_PORT` - порт для поключения к серверу через который вы будуте отправлять сообщения в чат. Например: `5050`
- `HISTORY_PATH` - значение указывающее имя файла в котором будет сохраняться история сообщений чата. Например: `messages.txt`

___
>### Как запустить

Проект включает в себя два скрипта `minechat.py` и `minechat-interact`

- `minechat.py` - скрипт для получения истории сообщений. Данный скрипт сохраняет историюю сообщений в файл.

- Для запуска данного скрипта достаточно написать в консоли команду

`Linux`

```bash
python3 minechat.py
```

`Windows`

```bash
python minechat.py
```
___

- `minechat-interact.py` - скрипт для взаимодействия с сервером. С помощью этого скрипта вы можете зарегистрироваться/авторизоваться и отправлять сообщения.

- Для запуска данного скрипта достаточно написать в консоли команду

`Linux`

```bash
python3 minechat-interact.py
```

`Windows`

```bash
python minechat-interact.py
```
___
>### Допольнительные параметры запуска сервера

#### Данные параметры являются необязательными
___

- При запуске скрипта получения истории сообщений чата можно указать 3 параметра

`Linux`

```bash
python3 minechat.py -ho minechat.dvmn.org -p 5000 -hp messages.txt
```

```bash
python3 minechat.py --host minechat.dvmn.org --port 5000 --history_path messages.txt
```
___

`Windows`

```bash
python minechat.py -ho minechat.dvmn.org -p 5000 -hp messages.txt
```

```bash
python minechat.py --host minechat.dvmn.org --port 5000 --history_path messages.txt
```
___

- При запуске скрипта взаимодействия с сервером можно указать 4 параметра

`Linux`

```bash
python3 minechat-interact -t token -ho minechat.dvmn.org -p 5050 -n Artem4ik
```

```bash
python3 minechat-interact -token token -host minechat.dvmn.org -port 5050 -name Artem4ik
```
___

`Windows`

```bash
python minechat-interact -t token -ho minechat.dvmn.org -p 5050 -n Artem4ik
```

```bash
python minechat-interact -token token -host minechat.dvmn.org -port 5050 -name Artem4ik
```
___

- `-ho`, `--host` - параметры для указания `host` сервера.

- `-p`, `--port` - параметры для указания `port` сервера.

- `-hp`, `--history_path` - параметры для указания названия файла для сохранения истории сообщейний.

- `-t`, `--token` - параметры для указания токена авторизации на сервере. 

- `-n`, `--name` - параметры для указания вашего никнейма для регистрации.

- Параметры можно передавать по отдельности.

___
>### Пример работы скрптов

- `minechat.py`

##### Отображение в консоли истории сообщений
![pic1](pictures/minechat_1.png)

##### Сохранение сообщений в файл
![pic2](pictures/minechat_2.png)

- `minechat-interact.py`

##### Регистрация/авторизация и отправка сообщений
![pic3](pictures/minechat-interact_1.png)

___
>### Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).