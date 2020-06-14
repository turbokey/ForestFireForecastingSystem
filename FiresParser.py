import json
import time
import requests
from requests.exceptions import HTTPError
from datetime import datetime

URL = "https://maps.kosmosnimki.ru/TileSender.ashx"
HEADERS = {'Accept': '*/*',
           'Referer': 'https://fires.ru/',
           'Accept-Language': 'ru-RU',
           'Origin': 'https://fires.ru',
           'Accept-Encoding': 'gzip, deflate',
           'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
           'Connection': 'Keep-Alive',
           'DNT': '1',
           'Cache-Control': 'no-cache'}

created = sum(1 for line in open("result.txt"))

for i in range(13548,11000,-1):
    PARAMS = {'WrapStyle': 'None',
          'key': '',
          'ModeKey': 'tile',
          'ftc': 'osm',
          'r': 'j',
          'LayerName': 'E58063D97D534BB4BBDFF07FE5CB17F2',
          'z': '1',
          'x': '1',
          'y': '0',
          'srs': '3857',
          'Level': '1',
          'Span': i,
          'sw': '1'}

    print('span #'+str(i))

    try:
        response = requests.get(url=URL, params=PARAMS, headers=HEADERS)
        response.raise_for_status()
        json_body = json.loads(response.text.replace('gmxAPI._vectorTileReceiver(', '').replace('})', '}'))
        response.close()

        output_file = open("result.txt", "a")

        values = json_body['values']

        for value in values:
            date = value[6]
            x = value[10]['coordinates'][0]
            y = value[10]['coordinates'][1]
            name = value[9]
            if (x < 13653487.74 and x > 11853242.85 and y < 8057074.81 and y > 6212802.13):
                output_file.write(str(datetime.utcfromtimestamp(date).strftime('%d.%m.%Y')) + ";" + str(x) + ";" + str(y) + ";" + name )
                created = created + 1

        print(str(datetime.utcfromtimestamp(date).strftime('%d.%m.%Y')))

        output_file.close()
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')
    else:
        print('Success!')
        print('Создано: '+str(created))

    print('span #' + str(i) + '(' + str((14736-i)*100/(14736-11000)) + '%)')
    print()
    time.sleep(1)
