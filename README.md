# os-automation
Автоматизация процессов при оценивании практических заданий студентов по курсу "Операционные системы

## Описание

TODO:
1. Добавить проверку логов Travis CI и Appveyor, чтобы убедиться, что студент выполнил свой вариант.
2. Добавить задержки при работе с Google Sheets API, чтобы не выходить за ограничения количества запросов в единицу времени.
3. Предложить, обсудить с преподавателем и реализовать изменения к подходу проверки лабораторных работ так, чтобы уменьшить количество обращений к Google Sheets API.
4. Реализовать взаимодействие со студентом по электронной почте: регистрация студентом в системе проверки лабораторных работ, информирование студента об ошибках (выполнен чужой вариант, указана несуществующая группа, в группе не найден студент с указанным ФИО и т.п), информирование студента о том, что лабораторная работа выполнена корректно и он должен защитить ее на занятии в университете, а также другие виды взаимодействия (согласовать с преподавателем).
5. Отрефакторить код, использовать ООП в Python. При необходимости разбить код на модули.


Цель: автоматизировать все задачи, связанные с проверкой правильности выполнения кода, соблюдения сроков выполнения задания/ Свести к минимуму взаимодействие преподавателя с системами проверки (CI/CD).


## Примеры использования кода
### Автоматическое подключение всех имеющихся репозиториев студентов, приступивших к выполнению ЛР3, к CI/CD Appveyor
```python
import settings
import common
# get list of all GitHub repos for task No 3
task3_repos = common.get_github_repo_names(settings.github_organization, 'os-task3')
# save all repos that are connected to AppVeyour before we any new repos are added
appveyour_repos = common.get_appveyor_project_repo_names()
# add repos to AppVeyor if they are not already there and trigger build for the newly added repos
added_repos = common.add_appveyor_projects_safely(list(task3_repos), trigger_build=True)
# show repos that were added to AppVeyour
print(common.get_appveyor_project_repo_names().keys() - appveyour_repos.keys())
print(added_repos)
```

### Обновление гугл-таблицы на основе данных, присланных студентами
Проводится проверка прохождения тестов. Правильность номера варианта по логам Travis/AppVeyor НЕ проверяется. Ошибки отсутствия группы и отсутствия студента должным образом не обрабатываются.
```python
# data extracted from emails
solutions = [
  ['Z6431', 'Решетникова Светлана Андреевна', 'suai-os-2019/os-task3-svetlana-r'],
  ['Z6432K', 'Пятак Петр Александрович', 'suai-os-2019/os-task2-petrpyatak'],
  ['Z6432K', 'Пятак Петр Александрович', 'suai-os-2019/os-task3-petrpyatak'],
  ['Z6432K', 'Мошин Владислав Вячеславович', 'suai-os-2019/os-task2-Sagalscki'],
  ['Z6432K', 'Бабюк Юлия Игоревна', 'suai-os-2019/os-task2-beebzbe'],
  ['Z6432K', 'Саутыч Софья Павловна', 'suai-os-2019/os-task3-SofyaSau'], 
  ['Z6432K', 'Саутыч Софья Павловна', 'suai-os-2019/os-task2-SofyaSau'], 
  ['Z6431', 'Решетникова Светлана Андреевна', 'suai-os-2019/os-task2-svetlana-r-1'], 
  ['Z6431', 'Решетникова Светлана Андреевна', 'suai-os-2019/os-task1-svetlana-r']
]
# update Google sheet if a student exists and test are passed. Only works for tasks 2 and 3. No security checks are done: task is not verified based on the Travis/AppVeyour logs
common.gsheet(solutions, debug=True)
```
