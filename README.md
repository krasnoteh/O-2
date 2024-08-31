# O-2
Этот репозиторий - база всего кода к проекту "Огородник - 2", а также текущее расположение кода проекта "РобоСервер". 3d модели и прочие не кодовые данные проекта могут быть найдены по [ссылке](https://drive.google.com/drive/folders/1uUOcRc5gdFFmDTRLksJ7Ht7D-vq_HLFW?usp=drive_link).

![alt text](https://github.com/krasnoteh/O-2/blob/master/images/robot.jpg?raw=true)

![alt text](https://github.com/[username]/[reponame]/blob/[branch]/images/image.jpg?raw=true)

Проект на стадии разработки, публикую то, что есть, *не рекомендую повторять проект, в том виде, в котором он сейчас.*

## обзор репозитория

В катологе **ArduinoModules** расположен код для микроконтроллеров на с++. Код компилируется в среде arduino для контроллеров **Atmega328p**. 
В каталоге **RoboServer** находится код на python, запускающий приложение для подключения к роботу. Запускать файл **main.py**
Также отдельным файлом расположен код робота на python, запускающийся на raspberry. Весь код сейчас помещен в один файл **robot.py**.
Для запуска кода робосервера может потребоваться установить некоторые библиотеки. В reqirements.txt список всех моих библеотек на рабочем окружении, все их устанавливать не нужно точно. Если будут какие-то проблемы с версиями, можете подсмотреть в этом файле.

## обзор проекта

Процесс сборки и большую часть описания системы можно найти в основном [видео]() по пректу.

Далее информация, которой нет в видео.

#### комплектующие с али

 - [основные моторы](https://aliexpress.ru/item/1005004046255185.html?spm=a2g2w.orderdetail.0.0.77574aa6EWtSTe&sku_id=12000027850257250)
 - [raspberry](https://aliexpress.ru/item/1005005914201208.html?spm=a2g2w.orderdetail.0.0.3aa84aa6BYZ94g&sku_id=12000037090436024)
 - [мотор модуля](https://aliexpress.ru/item/32889047361.html?spm=a2g2w.orderdetail.0.0.72e64aa6TjWuWc&sku_id=12000040781705247)
 - [подшипники](https://aliexpress.ru/order-list/5385013512515995?spm=a2g2w.orderlist.0.0.40e74aa61xrMSg&filterName=archive)
 - [муфта мотор-колесо](https://aliexpress.ru/item/1005003878613208.html?spm=a2g2w.orderdetail.0.0.27684aa6GfED83&sku_id=12000027374377201)
 - [камера](https://aliexpress.ru/order-list/5385013512335995?spm=a2g2w.orderlist.0.0.40e74aa6pIiht5&filterName=archive)
 - [нагревательная гайка](https://aliexpress.ru/item/4000232925592.html?spm=a2g2w.orderdetail.0.0.3c204aa6RA1dUw&sku_id=10000000945438227)
 - [т - гайка под конструкционный профиль](https://aliexpress.ru/item/32814359094.html?spm=a2g2w.orderdetail.0.0.58544aa6acwjuA&sku_id=66498695475)
 - [винты одни](https://aliexpress.ru/item/32896175403.html?spm=a2g2w.orderdetail.0.0.57454aa6rWDtrd&sku_id=65817464634)
 - [винты другие](https://aliexpress.ru/item/1005003194617253.html?spm=a2g2w.orderdetail.0.0.39024aa6afdxc3&sku_id=12000024602444689)
 - [винты третьи](https://aliexpress.ru/item/1005003194617253.html?spm=a2g2w.orderdetail.0.0.3d6d4aa6GrkWu6&sku_id=12000024602444688)
 - [винты четвертые](https://aliexpress.ru/item/32810852732.html?spm=a2g2w.orderdetail.0.0.4c804aa6MAaPDW&sku_id=12000037550700868)

#### комплектующие не с али (все это было, ссылок нет)
- аккумулятор 18650
- bms на 5 18650
- светодиоды красные
- кнопки
- выключатель на 2 канала
- светодиод 10 в белый теплый (для переднего света)
- понижающие модули lm2596
- плата макетная
- arduino nano
- болты м5 разной длины
- силикон
- провода
- кусок стекла
- какое-то металлическое колечко, вероятно из фонаря
- линза для переднего света
- блок питания 21 v 2 a для зарядки
