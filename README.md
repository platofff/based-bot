# Based bot

Бот с нескучными демотиваторами. В перспективе возможны другие фронтенды помимо вконтакте. Работает (на момент написания ридми) вот здесь: https://vk.com/kallinux

#### Функции:
- Демотиваторы из пересланных сообщений/картинок/полностью автоматические
- Поиск ответа на сообщение в истории беседы
- Споры для редактора http://objection.lol/maker из пересланных сообщений
- Генерация предложений от известного политика
- Поддержка запуска интерпретатором [PyPy](https://pypy.org) с JiT компиляцией
- Другие мелочи

## Как использовать?
#### Подготовка
Необходимо установить `docker-compose`.

Боту требуются права на управление сообществом, сообщения сообщества, фотографии и документы.

#### Запуск
```
VK_BOT_TOKEN=<токен группы> ADMIN=<id админа> docker-compose -f docker-compose.yml up --build
```
