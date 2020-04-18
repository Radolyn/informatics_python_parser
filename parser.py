# coding=utf-8
# Дева4ки балдеем

try:
    import string
    import requests
    import json
    from operator import attrgetter
    from bs4 import BeautifulSoup
    import lxml
    import sys
    import os
    import pickle
    import yapf
    import autopep8
    from utils import parse_argv, usage, get_user_details, load_cookies, debug, headers, letters_list, print_logo, \
        rnd_wait, run_python_tool, print_unauthorized, base_url
except:
    from utils import deps_message

    deps_message()

# Этот скрипт парсит последний удачный run по problem_id, извлекает из него сурсы и создаёт файл с решением.
# API у них не задокументировано *(я нашёл роуты, но не более:
# https://github.com/InformaticsMskRu/informatics-mccme-ru/blob/master/pynformatics/__init__.py), так что парсим
# 'грязно'
# UPD: класс, парни шарят за REST API (они даже не сделали роут для получения информации о задании)

# Парсим аргументы из ком. строки
parsed = parse_argv(sys.argv[1:])

if debug:
    print(parsed)

start_id = parsed['range'][0]
end_id = parsed['range'][1]
folder = parsed['folder']

# Селектор описания задания
desc_selector = '#content > table > tbody > tr:nth-child(2) > td:nth-child(2) > div > div > div:nth-child(11) > ' \
                'div.legend > p '

# Сколько всего скачано
passes = 0

# Сессия для парсера
session = requests.Session()

print_logo()

# Создаём папку
if not os.path.exists(folder):
    os.makedirs(folder)

if not os.path.exists('session'):
    print('Запустите сначала authorize.py - получите ключ.')
    exit(420)

# Загружаем куки
cookies_cached = load_cookies()

session.cookies = cookies_cached

# Проверка на валидность
user_data = get_user_details()

if parsed['letter'] not in letters_list:
    print('Хайповая буква, но максимум AZ')
    exit(68)

letter_offset = letters_list.index(parsed['letter'])

if user_data is None:
    print_unauthorized()

print('Доброго времени суток, ' + user_data['name'])
print('Произошла авторизация, идём к выкачке.\n\n')

user_id = user_data['id']

# Главный кос... цикл
for problem_id in range(start_id, end_id + 1, 1):

    # Для удобства обозначим букву как letter
    letter = letters_list[problem_id - start_id + letter_offset]

    # Получаем всю информацию по заданию
    url = base_url + 'py/problem/%s/filter-runs?problem_id=%s&from_timestamp=-1&to_timestamp=-1' \
          '&group_id=0&user_id=%s&lang_id=-1&status_id=-1&statement_id=0&count=30&with_comment=&page=1' % (
              problem_id, problem_id, user_id)

    response = session.get(url, cookies=cookies_cached)
    data = json.loads(response.text)

    if debug:
        print(response.text)
    if data['result'] != 'success':
        print('Прикол не работает, идём дальше.')
        continue

    print('Прикол работает.')

    print('Получаем удачные run\'ы...')

    success_runs = []

    # За выполненное задание дают 100 баллов
    for item in data['data']:
        if item['ejudge_score'] == 100:
            success_runs.append(item)

    if len(success_runs) == 0:
        print('Прикол удачных run\'ов нет.\n\n')
        continue

    if debug:
        print(success_runs)

    run = success_runs[0]

    if debug:
        print('Последний удачный:')
        print(run)

    print('Получаем source код...')

    # Парсим исходный код
    source_url = base_url + 'py/problem/run/%i/source' % run['id']

    response = session.get(source_url, cookies=cookies_cached)
    data = json.loads(response.text)

    # Если не смогли - идём к след. заданию
    if debug:
        print(response.text)

    if data['status_code'] != 200:
        print('Ставлю дизлайк и идём дальше\n\n')
        continue

    print('Ставлю лайк')

    source = data['data']['source']
    source = source.replace('\r\n', '\n')

    try:
        formatted_source = yapf.yapf_api.FormatCode(source,
                                                    style_config='pep8',
                                                    verify=True)[0]
        fixed_source = autopep8.fix_code(formatted_source,
                                         options={'aggressive': 2})
    except:
        print('Форматирование змеи прошло неправильно, идём дальше.\n')
        continue

    if debug:
        print(source)

    # Парсим описание. На самом деле, это для поисковиков, чтобы лучше индексировали :)
    desc_url = base_url + 'mod/statements/view3.php?chapterid=%s' % problem_id

    page = session.get(desc_url)

    soup = BeautifulSoup(page.text, 'lxml')

    # Описание может быть просто в div'е legend, а может быть обёрнуто в параграф
    desc = soup.find('div', {'class': 'legend'})

    if desc is None:
        print('Ржомба не сработала, идём дальше.')
        continue
    else:
        desc = soup.find('div', {'class': 'legend'}).find('p')
        if desc is None:
            desc = soup.find('div', {'class': 'legend'}).text
        else:
            desc = desc.text

    if debug:
        print(desc)

    # Сохраняем описание + исходный код
    path = folder + "\\Задача %s.py" % letter

    f = open(path, "w+", encoding='utf-8', newline='\n')

    if debug:
        print(path)

    # У описания новые строки заменяем на '# ', чтобы было однородней
    # Костыль.нет
    desc = '# ' + desc
    desc = desc.replace('\r\n', '\n# ')
    desc = desc.replace('# # ', '# ')
    desc = desc.replace('#     ', '')
    desc = desc.replace('\n\n', '')
    desc = desc.replace('	', '')
    desc = desc.replace('# \n', '')
    desc = desc.replace('#  \n', '')
    desc = desc.replace('# \n', '')
    desc = desc.replace('#\n', '')

    # Бывает в горах Казахстана и такое
    if '# ' + desc[2] not in fixed_source:
        f.write(desc)

    # Костыль.нет 2
    f.write('\n\n')
    f.write(fixed_source)

    f.close()

    print('Класс работает, ставлю ржомбу. (%s, %i)\n\n' % (letter, problem_id))

    passes += 1

    rnd_wait()

print('\n\nПриколов скачано: %i из %i' % (passes, abs(start_id - end_id) + 1))
